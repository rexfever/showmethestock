"""
보고서 생성 서비스
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import calendar
from collections import Counter, defaultdict
from services.returns_service import calculate_returns
from db_manager import db_manager
import concurrent.futures

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self):
        # 절대 경로 사용 - 프로젝트 루트 찾기
        current_file = os.path.abspath(__file__)
        # backend/services/report_generator.py -> backend/services -> backend -> 프로젝트 루트
        current = current_file
        # backend 디렉토리를 찾을 때까지 상위로 이동
        while current != os.path.dirname(current):
            if os.path.basename(current) == "backend":
                # backend를 찾았으면 그 상위가 프로젝트 루트
                project_root = os.path.dirname(current)
                break
            current = os.path.dirname(current)
        else:
            # backend를 찾지 못한 경우 (fallback)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        
        self.reports_dir = os.path.join(project_root, "backend", "reports")
        self.db_path = os.path.join(project_root, "backend", "snapshots.db")
    
    def _save_report(self, report_type: str, filename: str, data: Dict):
        """보고서 파일 저장"""
        try:
            report_dir = os.path.join(self.reports_dir, report_type)
            os.makedirs(report_dir, exist_ok=True)
            
            filepath = os.path.join(report_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"보고서 저장 완료: {filepath}")
        except Exception as e:
            logger.error(f"보고서 저장 오류 ({filename}): {e}", exc_info=True)
            raise
    
    def _load_report(self, report_type: str, filename: str) -> Optional[Dict]:
        """보고서 파일 로드"""
        try:
            filepath = os.path.join(self.reports_dir, report_type, filename)
            if not os.path.exists(filepath):
                logger.debug(f"보고서 파일 없음: {filepath}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"보고서 로드 오류 ({filename}): {e}", exc_info=True)
            return None
    
    def _get_scan_data(self, start_date: str, end_date: str) -> List[Dict]:
        """지정 기간의 스캔 데이터 조회"""
        # 날짜 형식 통일: YYYY-MM-DD → YYYYMMDD
        start_compact = start_date.replace('-', '') if '-' in start_date else start_date
        end_compact = end_date.replace('-', '') if '-' in end_date else end_date
        
        try:
            with db_manager.get_cursor(commit=False) as cursor:
                cursor.execute("""
                SELECT date, code, name, current_price, volume, change_rate, market, strategy, indicators, trend, flags, details, returns, recurrence
                FROM scan_rank
                WHERE date >= %s AND date <= %s AND code != 'NORESULT'
                ORDER BY date
            """, (start_compact, end_compact))
                dict_rows = cursor.fetchall()
            
            rows = [
                (
                    row.get("date"),
                    row.get("code"),
                    row.get("name"),
                    row.get("current_price"),
                    row.get("volume"),
                    row.get("change_rate"),
                    row.get("market"),
                    row.get("strategy"),
                    row.get("indicators"),
                    row.get("trend"),
                    row.get("flags"),
                    row.get("details"),
                    row.get("returns"),
                    row.get("recurrence"),
                )
                for row in dict_rows
            ]
        except Exception as e:
            logger.error(f"스캔 데이터 조회 오류: {e}")
            rows = []
        
        return rows
    
    def _process_single_stock_return(self, row: tuple, retry_count: int = 0) -> Optional[Dict]:
        """단일 종목 수익률 계산 (병렬 처리용)"""
        try:
            date, code, name, current_price, volume, change_rate, market, strategy, indicators, trend, flags, details, returns, recurrence = row
            
            # 데이터 검증
            if not name or not code or code == 'NORESULT':
                return None
            
            # 비정상적인 가격 필터링 (1000원 미만 제외)
            if current_price and current_price < 1000:
                if retry_count == 0:  # 첫 번째 시도에서만 로그 출력
                    logger.warning(f"비정상적인 가격으로 제외: {code} {name} - 가격: {current_price}원")
                return None
            
            # 가격이 0이어도 수익률 계산은 시도 (과거 데이터로 계산 가능)
            # 가격이 없으면 수익률 계산 시 scan_date 기준으로 가격을 조회
            if not current_price or current_price <= 0:
                if retry_count == 0:  # 첫 번째 시도에서만 로그 출력
                    logger.warning(f"가격 정보 없음: {code} {name} - 수익률 계산 시도 (과거 데이터 사용)")
            
            # 수익률 계산 (재시도 로직 포함)
            returns_info = calculate_returns(code, date)
            if not returns_info and retry_count < 2:  # 최대 2번 재시도
                import time
                time.sleep(0.1)  # 짧은 대기 후 재시도
                return self._process_single_stock_return(row, retry_count + 1)
            
            if not returns_info:
                if retry_count == 0:  # 첫 번째 시도에서만 로그 출력
                    logger.warning(f"수익률 계산 실패: {code} {name} (날짜: {date})")
                return None
            
            # 가격이 없으면 수익률 계산 결과에서 가격 추출 시도
            scan_price = current_price if current_price and current_price > 0 else returns_info.get('scan_price', 0)
            
            if retry_count == 0:  # 첫 번째 시도에서만 로그 출력
                logger.info(f"수익률 계산 성공: {code} {name} - 현재 {returns_info.get('current_return', 0)}%, 최고 {returns_info.get('max_return', 0)}%")
            
            return {
                "ticker": code,
                "name": name,
                "scan_price": scan_price,
                "scan_date": date,
                "current_return": returns_info.get('current_return', 0),
                "max_return": returns_info.get('max_return', 0),
                "min_return": returns_info.get('min_return', 0),
                "days_elapsed": returns_info.get('days_elapsed', 0),
                "volume": volume or 0,
                "change_rate": change_rate or 0,
                "market": market or "",
                "strategy": strategy or ""
            }
        except Exception as e:
            logger.error(f"종목 처리 오류 ({row[1] if len(row) > 1 else 'unknown'}): {e}", exc_info=True)
            return None
    
    def _calculate_returns_for_stocks(self, stocks_data: List) -> List[Dict]:
        """종목별 수익률 계산 (병렬 처리)"""
        processed_stocks = []
        
        if not stocks_data:
            return processed_stocks
        
        # 병렬 처리로 성능 개선
        max_workers = min(5, len(stocks_data))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._process_single_stock_return, row): row 
                for row in stocks_data
            }
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        processed_stocks.append(result)
                except Exception as e:
                    row = futures[future]
                    code = row[1] if len(row) > 1 else 'unknown'
                    logger.error(f"수익률 계산 오류 ({code}): {e}")
        
        return processed_stocks
    
    def _analyze_repeat_scans(self, start_date: str, end_date: str) -> Dict:
        """반복 스캔 종목 분석"""
        # 날짜 형식 통일: YYYY-MM-DD → YYYYMMDD
        start_compact = start_date.replace('-', '') if '-' in start_date else start_date
        end_compact = end_date.replace('-', '') if '-' in end_date else end_date
        
        try:
            with db_manager.get_cursor(commit=False) as cursor:
                cursor.execute("""
                SELECT date, code, name, strategy 
                FROM scan_rank
                WHERE date >= %s AND date <= %s AND code != 'NORESULT'
                ORDER BY date DESC
            """, (start_compact, end_compact))
                dict_rows = cursor.fetchall()
            
            data = [
                (
                    row.get("date"),
                    row.get("code"),
                    row.get("name"),
                    row.get("strategy"),
                )
                for row in dict_rows
            ]
        except Exception as e:
            logger.error(f"반복 스캔 분석 오류: {e}")
            data = []
        
        if not data:
            return {"repeat_analysis": None}
        
        # 종목별 스캔 횟수 계산
        stock_counts = Counter()
        stock_info = {}
        strategy_patterns = Counter()
        
        for date, code, name, strategy in data:
            stock_counts[code] += 1
            stock_info[code] = name
            if strategy:
                strategy_patterns[strategy] += 1
        
        # 반복 스캔 종목 (2회 이상)
        frequent_stocks = [(code, count, stock_info[code]) 
                          for code, count in stock_counts.items() if count >= 2]
        frequent_stocks.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 5개 반복 종목
        top_frequent = frequent_stocks[:5]
        
        # 주요 전략 패턴 (상위 3개)
        top_strategies = strategy_patterns.most_common(3)
        
        return {
            "repeat_analysis": {
                "total_repeat_stocks": len(frequent_stocks),
                "top_frequent_stocks": [
                    {"ticker": code, "name": name, "scan_count": count}
                    for code, count, name in top_frequent
                ],
                "top_strategies": [
                    {"strategy": strategy, "count": count}
                    for strategy, count in top_strategies if strategy
                ],
                "insights": {
                    "high_momentum_stocks": len([s for s in frequent_stocks if s[1] >= 5]),
                    "consistent_pattern_stocks": len([s for s in frequent_stocks if s[1] >= 3]),
                    "market_interest_level": "높음" if len(frequent_stocks) >= 10 else "보통" if len(frequent_stocks) >= 5 else "낮음"
                }
            }
        }
    
    def _calculate_statistics(self, stocks: List[Dict]) -> Dict:
        """통계 계산"""
        if not stocks:
            return {
                "total_stocks": 0,
                "avg_return": 0,
                "positive_rate": 0,
                "best_stock": None,
                "worst_stock": None
            }
        
        # 모든 지표를 최고 수익률 기준으로 변경
        total_max_return = sum(stock["max_return"] for stock in stocks)
        positive_count = sum(1 for stock in stocks if stock["max_return"] > 0)
        
        total_stocks = len(stocks)
        avg_return = total_max_return / total_stocks if total_stocks > 0 else 0
        positive_rate = (positive_count / total_stocks * 100) if total_stocks > 0 else 0
        
        best_stock = max(stocks, key=lambda x: x['max_return']) if stocks else None
        worst_stock = min(stocks, key=lambda x: x['max_return']) if stocks else None
        
        return {
            "total_stocks": total_stocks,
            "avg_return": round(avg_return, 2),
            "positive_rate": round(positive_rate, 2),
            "best_stock": best_stock,
            "worst_stock": worst_stock
        }
    
    def generate_weekly_report(self, year: int, month: int, week: int) -> bool:
        """주간 보고서 생성"""
        try:
            # 주차별 날짜 범위 계산
            last_day = calendar.monthrange(year, month)[1]
            week_start = (week - 1) * 7 + 1
            week_end = min(week_start + 6, last_day)
            
            start_date = f"{year}-{month:02d}-{week_start:02d}"
            end_date = f"{year}-{month:02d}-{week_end:02d}"
            
            logger.info(f"주간 보고서 생성 시작: {year}년 {month}월 {week}주차 ({start_date} ~ {end_date})")
            
            # 스캔 데이터 조회
            scan_data = self._get_scan_data(start_date, end_date)
            
            if not scan_data:
                logger.warning(f"주간 보고서 생성 실패: {year}년 {month}월 {week}주차 데이터 없음")
                return False
            
            logger.info(f"스캔 데이터 조회: {len(scan_data)}건")
            
            # 수익률 계산 (병렬 처리)
            stocks = self._calculate_returns_for_stocks(scan_data)
            
            if not stocks:
                logger.warning(f"처리된 종목 없음: {year}년 {month}월 {week}주차")
                return False
            
            # 주간 보고서에서 중복 제거 및 추천 날짜 정보 수집
            unique_stocks = {}
            stock_dates = {}
            
            for stock in stocks:
                ticker = stock["ticker"]
                
                # 추천 날짜 수집
                if ticker not in stock_dates:
                    stock_dates[ticker] = []
                stock_dates[ticker].append(stock["scan_date"])
                
                # 최고 수익률 기준으로 대표 데이터 선택
                if ticker not in unique_stocks or stock["max_return"] > unique_stocks[ticker]["max_return"]:
                    unique_stocks[ticker] = stock
            
            # 추천 날짜 정보 추가
            for ticker, stock in unique_stocks.items():
                stock["recommendation_dates"] = sorted(list(set(stock_dates[ticker])))
                stock["recommendation_count"] = len(stock["recommendation_dates"])
            
            stocks = list(unique_stocks.values())
            
            # 최고 수익률 기준으로 정렬
            stocks.sort(key=lambda x: x['max_return'], reverse=True)
            
            # 통계 계산
            stats = self._calculate_statistics(stocks)
            
            # 보고서 데이터 구성
            report_data = {
                "report_type": "weekly",
                "year": year,
                "month": month,
                "week": week,
                "start_date": start_date,
                "end_date": end_date,
                "generated_at": datetime.now().isoformat(),
                "statistics": stats,
                "stocks": stocks,
                "dates": sorted(list(set(row[0] for row in scan_data)))
            }
            
            # 파일 저장
            filename = f"weekly_{year}_{month:02d}_week{week}.json"
            self._save_report("weekly", filename, report_data)
            
            logger.info(f"주간 보고서 생성 완료: {year}년 {month}월 {week}주차 ({len(stocks)}개 종목)")
            return True
            
        except Exception as e:
            logger.error(f"주간 보고서 생성 오류 ({year}/{month}/{week}): {e}", exc_info=True)
            return False
    
    def generate_monthly_report(self, year: int, month: int) -> bool:
        """월간 보고서 생성"""
        try:
            logger.info(f"월간 보고서 생성 시작: {year}년 {month}월")
            
            # 해당 월의 주간 보고서들을 합치기
            last_day = calendar.monthrange(year, month)[1]
            weeks_in_month = (last_day - 1) // 7 + 1
            
            all_stocks = []
            all_dates = set()
            
            for week in range(1, weeks_in_month + 1):
                filename = f"weekly_{year}_{month:02d}_week{week}.json"
                weekly_data = self._load_report("weekly", filename)
                
                if weekly_data:
                    all_stocks.extend(weekly_data["stocks"])
                    all_dates.update(weekly_data["dates"])
            
            # 주간 보고서가 없으면 DB에서 직접 생성 시도
            if not all_stocks:
                logger.info(f"주간 보고서 없음, DB에서 직접 생성 시도: {year}년 {month}월")
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year}-{month:02d}-{last_day:02d}"
                scan_data = self._get_scan_data(start_date, end_date)
                
                if scan_data:
                    all_stocks = self._calculate_returns_for_stocks(scan_data)
                    all_dates = set(row[0] for row in scan_data)
            
            if not all_stocks:
                logger.warning(f"월간 보고서 생성 실패: {year}년 {month}월 데이터 없음")
                return False
            
            # 중복 종목 제거 (같은 종목이 여러 주차에 나타날 경우, 최고 수익률 기준으로 유지)
            unique_stocks = {}
            for stock in all_stocks:
                ticker = stock["ticker"]
                if ticker not in unique_stocks or stock["max_return"] > unique_stocks[ticker]["max_return"]:
                    unique_stocks[ticker] = stock
            
            all_stocks = list(unique_stocks.values())
            
            # 최고 수익률 기준으로 정렬
            all_stocks.sort(key=lambda x: x['max_return'], reverse=True)
            
            # 통계 계산
            stats = self._calculate_statistics(all_stocks)
            
            # 반복 스캔 분석 추가
            start_date = f"{year}-{month:02d}-01"
            last_day = calendar.monthrange(year, month)[1]
            end_date = f"{year}-{month:02d}-{last_day:02d}"
            repeat_analysis = self._analyze_repeat_scans(start_date, end_date)
            
            # 보고서 데이터 구성
            report_data = {
                "report_type": "monthly",
                "year": year,
                "month": month,
                "generated_at": datetime.now().isoformat(),
                "statistics": stats,
                "stocks": all_stocks,
                "dates": sorted(list(all_dates)),
                **repeat_analysis
            }
            
            # 파일 저장
            filename = f"monthly_{year}_{month:02d}.json"
            self._save_report("monthly", filename, report_data)
            
            logger.info(f"월간 보고서 생성 완료: {year}년 {month}월 ({len(all_stocks)}개 종목)")
            return True
            
        except Exception as e:
            logger.error(f"월간 보고서 생성 오류 ({year}/{month}): {e}", exc_info=True)
            return False
    
    def generate_quarterly_report(self, year: int, quarter: int) -> bool:
        """분기 보고서 생성"""
        try:
            # 해당 분기의 월간 보고서들을 합치기
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            
            all_stocks = []
            all_dates = set()
            
            for month in range(start_month, end_month + 1):
                filename = f"monthly_{year}_{month:02d}.json"
                monthly_data = self._load_report("monthly", filename)
                
                if monthly_data:
                    all_stocks.extend(monthly_data["stocks"])
                    all_dates.update(monthly_data["dates"])
            
            if not all_stocks:
                print(f"분기 보고서 생성 실패: {year}년 {quarter}분기 월간 보고서 없음")
                return False
            
            # 중복 종목 제거 (같은 종목이 여러 월에 나타날 경우, 최고 수익률 기준으로 유지)
            unique_stocks = {}
            for stock in all_stocks:
                ticker = stock["ticker"]
                if ticker not in unique_stocks or stock["max_return"] > unique_stocks[ticker]["max_return"]:
                    unique_stocks[ticker] = stock
            
            all_stocks = list(unique_stocks.values())
            
            # 최고 수익률 기준으로 정렬
            all_stocks.sort(key=lambda x: x['max_return'], reverse=True)
            
            # 통계 계산
            stats = self._calculate_statistics(all_stocks)
            
            # 반복 스캔 분석 추가
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            start_date = f"{year}-{start_month:02d}-01"
            last_day = calendar.monthrange(year, end_month)[1]
            end_date = f"{year}-{end_month:02d}-{last_day:02d}"
            repeat_analysis = self._analyze_repeat_scans(start_date, end_date)
            
            # 보고서 데이터 구성
            report_data = {
                "report_type": "quarterly",
                "year": year,
                "quarter": quarter,
                "generated_at": datetime.now().isoformat(),
                "statistics": stats,
                "stocks": all_stocks,
                "dates": sorted(list(all_dates)),
                **repeat_analysis
            }
            
            # 파일 저장
            filename = f"quarterly_{year}_Q{quarter}.json"
            self._save_report("quarterly", filename, report_data)
            
            return True
            
        except Exception as e:
            logger.error(f"분기 보고서 생성 오류 ({year}/{quarter}): {e}", exc_info=True)
            return False
    
    def generate_yearly_report(self, year: int) -> bool:
        """연간 보고서 생성"""
        try:
            # 해당 연도의 분기 보고서들을 합치기
            all_stocks = []
            all_dates = set()
            
            for quarter in range(1, 5):
                filename = f"quarterly_{year}_Q{quarter}.json"
                quarterly_data = self._load_report("quarterly", filename)
                
                if quarterly_data:
                    all_stocks.extend(quarterly_data["stocks"])
                    all_dates.update(quarterly_data["dates"])
            
            if not all_stocks:
                print(f"연간 보고서 생성 실패: {year}년 분기 보고서 없음")
                return False
            
            # 중복 종목 제거 (같은 종목이 여러 분기에 나타날 경우, 최고 수익률 기준으로 유지)
            unique_stocks = {}
            for stock in all_stocks:
                ticker = stock["ticker"]
                if ticker not in unique_stocks or stock["max_return"] > unique_stocks[ticker]["max_return"]:
                    unique_stocks[ticker] = stock
            
            all_stocks = list(unique_stocks.values())
            
            # 최고 수익률 기준으로 정렬
            all_stocks.sort(key=lambda x: x['max_return'], reverse=True)
            
            # 통계 계산
            stats = self._calculate_statistics(all_stocks)
            
            # 보고서 데이터 구성
            report_data = {
                "report_type": "yearly",
                "year": year,
                "generated_at": datetime.now().isoformat(),
                "statistics": stats,
                "stocks": all_stocks,
                "dates": sorted(list(all_dates))
            }
            
            # 파일 저장
            filename = f"yearly_{year}.json"
            self._save_report("yearly", filename, report_data)
            
            return True
            
        except Exception as e:
            logger.error(f"연간 보고서 생성 오류 ({year}): {e}", exc_info=True)
            return False


# 전역 인스턴스
report_generator = ReportGenerator()