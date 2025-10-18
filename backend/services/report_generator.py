"""
보고서 생성 서비스
"""
import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import calendar
from services.returns_service import calculate_returns


class ReportGenerator:
    def __init__(self):
        self.reports_dir = "backend/reports"
        self.db_path = "snapshots.db"
        
    def _get_db_path(self):
        """데이터베이스 경로 반환"""
        return self.db_path
    
    def _save_report(self, report_type: str, filename: str, data: Dict):
        """보고서 파일 저장"""
        report_dir = os.path.join(self.reports_dir, report_type)
        os.makedirs(report_dir, exist_ok=True)
        
        filepath = os.path.join(report_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"보고서 저장 완료: {filepath}")
    
    def _load_report(self, report_type: str, filename: str) -> Optional[Dict]:
        """보고서 파일 로드"""
        filepath = os.path.join(self.reports_dir, report_type, filename)
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_scan_data(self, start_date: str, end_date: str) -> List[Dict]:
        """지정 기간의 스캔 데이터 조회"""
        conn = sqlite3.connect(self._get_db_path())
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT date, code, name, close_price, volume, change_rate, market, strategy, indicators, trend, flags, details, returns, recurrence
            FROM scan_rank 
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        """, (start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        return rows
    
    def _calculate_returns_for_stocks(self, stocks_data: List) -> List[Dict]:
        """종목별 수익률 계산"""
        processed_stocks = []
        
        for row in stocks_data:
            date, code, name, close_price, volume, change_rate, market, strategy, indicators, trend, flags, details, returns, recurrence = row
            
            if not name or not close_price:
                continue
            
            # 수익률 계산
            try:
                returns_info = calculate_returns(code, date)
                if returns_info:
                    current_return = returns_info.get('current_return', 0)
                    max_return = returns_info.get('max_return', 0)
                    min_return = returns_info.get('min_return', 0)
                    days_elapsed = returns_info.get('days_elapsed', 0)
                else:
                    current_return = 0
                    max_return = 0
                    min_return = 0
                    days_elapsed = 0
            except Exception as e:
                print(f"수익률 계산 오류 ({code}): {e}")
                current_return = 0
                max_return = 0
                min_return = 0
                days_elapsed = 0
            
            stock_data = {
                "ticker": code,
                "name": name,
                "scan_price": close_price,
                "scan_date": date,
                "current_return": current_return,
                "max_return": max_return,
                "min_return": min_return,
                "days_elapsed": days_elapsed,
                "volume": volume,
                "change_rate": change_rate,
                "market": market,
                "strategy": strategy
            }
            
            processed_stocks.append(stock_data)
        
        return processed_stocks
    
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
        
        total_return = sum(stock["max_return"] for stock in stocks)
        positive_count = sum(1 for stock in stocks if stock["max_return"] > 0)
        
        total_stocks = len(stocks)
        avg_return = total_return / total_stocks if total_stocks > 0 else 0
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
            
            # 스캔 데이터 조회
            scan_data = self._get_scan_data(start_date, end_date)
            
            if not scan_data:
                print(f"주간 보고서 생성 실패: {year}년 {month}월 {week}주차 데이터 없음")
                return False
            
            # 수익률 계산
            stocks = self._calculate_returns_for_stocks(scan_data)
            
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
                "dates": list(set(row[0] for row in scan_data))
            }
            
            # 파일 저장
            filename = f"weekly_{year}_{month:02d}_week{week}.json"
            self._save_report("weekly", filename, report_data)
            
            return True
            
        except Exception as e:
            print(f"주간 보고서 생성 오류: {e}")
            return False
    
    def generate_monthly_report(self, year: int, month: int) -> bool:
        """월간 보고서 생성"""
        try:
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
            
            if not all_stocks:
                print(f"월간 보고서 생성 실패: {year}년 {month}월 주간 보고서 없음")
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
            
            # 보고서 데이터 구성
            report_data = {
                "report_type": "monthly",
                "year": year,
                "month": month,
                "generated_at": datetime.now().isoformat(),
                "statistics": stats,
                "stocks": all_stocks,
                "dates": sorted(list(all_dates))
            }
            
            # 파일 저장
            filename = f"monthly_{year}_{month:02d}.json"
            self._save_report("monthly", filename, report_data)
            
            return True
            
        except Exception as e:
            print(f"월간 보고서 생성 오류: {e}")
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
            
            # 보고서 데이터 구성
            report_data = {
                "report_type": "quarterly",
                "year": year,
                "quarter": quarter,
                "generated_at": datetime.now().isoformat(),
                "statistics": stats,
                "stocks": all_stocks,
                "dates": sorted(list(all_dates))
            }
            
            # 파일 저장
            filename = f"quarterly_{year}_Q{quarter}.json"
            self._save_report("quarterly", filename, report_data)
            
            return True
            
        except Exception as e:
            print(f"분기 보고서 생성 오류: {e}")
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
            print(f"연간 보고서 생성 오류: {e}")
            return False


# 전역 인스턴스
report_generator = ReportGenerator()
