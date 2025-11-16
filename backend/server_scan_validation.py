#!/usr/bin/env python3
from __future__ import annotations

"""
서버 스캔 로직을 이용한 10월 마지막주 & 11월 첫째주 성과 검증

기간:
- 10월 마지막주: 2025-10-27 (월) ~ 2025-10-31 (금)
- 11월 첫째주: 2025-11-03 (월) ~ 2025-11-07 (금)
"""

import argparse
import os
import sys
import json
from datetime import datetime, timedelta
import holidays
import pandas as pd
import numpy as np

# 환경 변수 설정
os.environ.setdefault("DB_ENGINE", "postgres")
os.environ.setdefault("DATABASE_URL", "postgresql://stockfinder:stockfinder_pass@localhost/stockfinder")

# 유니버스 크기 (시장별 종목 수). 기본 100개씩(총 200개).
UNIVERSE_PER_MARKET = int(os.getenv("UNIVERSE_PER_MARKET", "100"))

from kiwoom_api import api as kiwoom_api
from scanner import scan_one_symbol
from services.scan_service import execute_scan_with_fallback
from market_analyzer import MarketAnalyzer
from config import config

# MarketAnalyzer 인스턴스 생성
market_analyzer = MarketAnalyzer()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="서버 스캔 로직 성과 검증")
    parser.add_argument(
        "--mode",
        choices=["range", "dates"],
        default="range",
        help="range: 기간 기반, dates: 특정 일자 목록",
    )
    parser.add_argument(
        "--start-date",
        default="2025-10-27",
        help="기간 스캔 시작일 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        default="2025-11-07",
        help="기간 스캔 종료일 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dates",
        nargs="+",
        help="특정 일자 목록 (YYYYMMDD 또는 YYYY-MM-DD)",
    )
    parser.add_argument(
        "--report-path",
        default="server_scan_validation_report.txt",
        help="리포트 저장 경로",
    )
    return parser.parse_args()


def _normalize_date_str(date_str: str) -> str:
    clean = date_str.replace("-", "")
    if len(clean) != 8 or not clean.isdigit():
        raise ValueError(f"잘못된 날짜 형식입니다: {date_str}")
    return clean


def determine_scan_dates(args: argparse.Namespace) -> tuple[list[str], str]:
    if args.mode == "range":
        dates = get_trading_days(args.start_date, args.end_date)
        period_label = f"{args.start_date} ~ {args.end_date} ({len(dates)}거래일)"
    else:
        if not args.dates:
            raise ValueError("--dates 옵션으로 최소 1개 이상의 일자를 지정해야 합니다.")
        dates = sorted({_normalize_date_str(d) for d in args.dates})
        period_label = ", ".join(dates)
    if not dates:
        raise ValueError("스캔할 거래일이 없습니다. 입력 파라미터를 확인하세요.")
    return dates, period_label


def get_trading_days(start_date: str, end_date: str) -> list:
    """거래일 목록 생성 (주말, 공휴일 제외)"""
    kr_holidays = holidays.KR()
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    trading_days = []
    current = start
    
    while current <= end:
        # 주말(토요일=5, 일요일=6) 제외
        if current.weekday() < 5:
            # 공휴일 제외
            if current.date() not in kr_holidays:
                trading_days.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    
    return trading_days


def get_universe_codes(date: str) -> list:
    """유니버스 종목 코드 가져오기"""
    print(f"\n📊 유니버스 종목 가져오기: {date}")
    print(f"  - 시장별 종목 수 설정: {UNIVERSE_PER_MARKET}")
    
    try:
        # KOSPI 상위 N개
        kospi_codes = kiwoom_api.get_top_codes(market="KOSPI", limit=UNIVERSE_PER_MARKET)
        print(f"  - KOSPI: {len(kospi_codes)}개")
        
        # KOSDAQ 상위 N개
        kosdaq_codes = kiwoom_api.get_top_codes(market="KOSDAQ", limit=UNIVERSE_PER_MARKET)
        print(f"  - KOSDAQ: {len(kosdaq_codes)}개")
        
        universe = kospi_codes + kosdaq_codes
        print(f"  - 전체 유니버스: {len(universe)}개")
        
        return universe
    except Exception as e:
        print(f"❌ 유니버스 가져오기 실패: {e}")
        return []


def scan_with_server_logic(universe: list, date: str) -> dict:
    """서버 스캔 로직 실행"""
    print(f"\n🔍 스캔 실행: {date}")
    
    try:
        # 1. 장세 분석
        market_condition = market_analyzer.analyze_market_condition(date)
        print(f"  - 장세: {market_condition.market_sentiment}")
        print(f"  - KOSPI 수익률: {market_condition.kospi_return:.2f}%")
        
        # 2. Fallback 스캔 실행
        items, chosen_step = execute_scan_with_fallback(
            universe=universe,
            date=date,
            market_condition=market_condition
        )
        
        print(f"  - Fallback Step: {chosen_step}")
        print(f"  - 선정 종목: {len(items)}개")
        
        # 3. 결과 정리
        result = {
            "date": date,
            "market_sentiment": market_condition.market_sentiment,
            "kospi_return": market_condition.kospi_return,
            "chosen_step": chosen_step,
            "items": []
        }
        
        for item in items:
            result["items"].append({
                "ticker": item.get("ticker"),
                "name": item.get("name"),
                "score": item.get("score"),
                "score_label": item.get("score_label"),
                "current_price": item.get("indicators", {}).get("close", 0),
                "change_rate": item.get("indicators", {}).get("change_rate", 0),
            })
        
        return result
        
    except Exception as e:
        print(f"❌ 스캔 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            "date": date,
            "error": str(e),
            "items": []
        }


def calculate_returns(scan_result: dict, hold_days: int = 5) -> dict:
    """스캔 종목의 수익률 계산"""
    date = scan_result["date"]
    items = scan_result["items"]
    
    if not items:
        return {
            "date": date,
            "count": 0,
            "returns": []
        }
    
    print(f"\n📈 수익률 계산: {date} (보유기간: {hold_days}일)")
    
    returns_data = []
    
    for item in items:
        ticker = item["ticker"]
        name = item["name"]
        buy_price = item["current_price"]
        
        try:
            # OHLCV 데이터 가져오기 (스캔일 + 보유기간)
            df = kiwoom_api.get_ohlcv(ticker, count=hold_days + 10)
            
            if df is None or len(df) == 0:
                print(f"  ⚠️  {ticker} {name}: 데이터 없음")
                continue
            
            # 스캔일 찾기
            scan_date_obj = datetime.strptime(date, "%Y%m%d")
            df['date'] = pd.to_datetime(df['date'])
            
            # 스캔일 이후 데이터만
            future_df = df[df['date'] >= scan_date_obj].copy()
            
            if len(future_df) < 2:
                print(f"  ⚠️  {ticker} {name}: 미래 데이터 부족")
                continue
            
            # 보유기간 동안의 최고가, 최저가, 종가
            hold_period = future_df.iloc[1:min(hold_days + 1, len(future_df))]
            
            if len(hold_period) == 0:
                print(f"  ⚠️  {ticker} {name}: 보유기간 데이터 없음")
                continue
            
            max_price = hold_period['high'].max()
            min_price = hold_period['low'].min()
            final_price = hold_period.iloc[-1]['close']
            
            # 수익률 계산
            max_return = ((max_price - buy_price) / buy_price) * 100
            min_return = ((min_price - buy_price) / buy_price) * 100
            final_return = ((final_price - buy_price) / buy_price) * 100
            
            # 매매 전략 시뮬레이션 (손절 -7%, 익절 +3%, 보존 +1.5%)
            stop_loss = -7.0
            take_profit = 3.0
            preserve = 1.5
            
            realized_return = final_return  # 기본값
            exit_reason = "보유 종료"
            
            # 일별 체크
            for idx, row in hold_period.iterrows():
                day_high = row['high']
                day_low = row['low']
                
                day_max_return = ((day_high - buy_price) / buy_price) * 100
                day_min_return = ((day_low - buy_price) / buy_price) * 100
                
                # 손절 체크 (최우선)
                if day_min_return <= stop_loss:
                    realized_return = stop_loss
                    exit_reason = "손절"
                    break
                
                # 익절 체크
                if day_max_return >= take_profit:
                    realized_return = take_profit
                    exit_reason = "익절"
                    break
                
                # 보존 체크 (익절 도달 후 preserve 이상 유지)
                if day_max_return >= take_profit:
                    # 익절 도달 후 하락 체크
                    day_close = row['close']
                    day_close_return = ((day_close - buy_price) / buy_price) * 100
                    
                    if day_close_return >= preserve:
                        realized_return = day_close_return
                        exit_reason = "보존"
                        break
            
            returns_data.append({
                "ticker": ticker,
                "name": name,
                "buy_price": buy_price,
                "max_return": round(max_return, 2),
                "min_return": round(min_return, 2),
                "final_return": round(final_return, 2),
                "realized_return": round(realized_return, 2),
                "exit_reason": exit_reason,
                "hold_days": len(hold_period)
            })
            
            print(f"  ✅ {ticker} {name}: {realized_return:+.2f}% ({exit_reason})")
            
        except Exception as e:
            print(f"  ❌ {ticker} {name}: 오류 - {e}")
            continue
    
    return {
        "date": date,
        "count": len(returns_data),
        "returns": returns_data
    }


def generate_report(scan_results: list, returns_results: list, output_file: str, period_label: str):
    """성과 리포트 생성"""
    print(f"\n📊 리포트 생성 중...")
    
    report = []
    report.append("=" * 100)
    report.append("서버 스캔 로직 성과 검증 리포트")
    report.append("=" * 100)
    report.append("")
    report.append(f"검증 기간: {period_label}")
    report.append(f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 1. 일별 스캔 결과
    report.append("=" * 100)
    report.append("1. 일별 스캔 결과")
    report.append("=" * 100)
    report.append("")
    
    total_scanned = 0
    for scan in scan_results:
        date = scan["date"]
        sentiment = scan.get("market_sentiment", "N/A")
        kospi = scan.get("kospi_return", 0)
        step = scan.get("chosen_step", "N/A")
        count = len(scan.get("items", []))
        total_scanned += count
        
        report.append(f"📅 {date} ({sentiment}, KOSPI: {kospi:+.2f}%)")
        report.append(f"   - Fallback Step: {step}")
        report.append(f"   - 선정 종목: {count}개")
        
        for item in scan.get("items", []):
            report.append(f"      • {item['ticker']} {item['name']}: {item['score']:.1f}점 ({item['score_label']})")
        
        report.append("")
    
    report.append(f"총 스캔 종목: {total_scanned}개")
    report.append("")
    
    # 2. 성과 분석
    report.append("=" * 100)
    report.append("2. 성과 분석 (손절 -7%, 익절 +3%, 보존 +1.5%, 보유기간 5일)")
    report.append("=" * 100)
    report.append("")
    
    all_returns = []
    win_count = 0
    loss_count = 0
    
    for ret in returns_results:
        date = ret["date"]
        count = ret["count"]
        
        if count == 0:
            report.append(f"📅 {date}: 종목 없음")
            report.append("")
            continue
        
        report.append(f"📅 {date}: {count}개 종목")
        report.append("")
        
        for r in ret["returns"]:
            all_returns.append(r["realized_return"])
            
            if r["realized_return"] > 0:
                win_count += 1
                status = "✅"
            else:
                loss_count += 1
                status = "❌"
            
            report.append(
                f"   {status} {r['ticker']} {r['name']}: "
                f"{r['realized_return']:+.2f}% ({r['exit_reason']}) "
                f"[최고: {r['max_return']:+.2f}%, 최저: {r['min_return']:+.2f}%]"
            )
        
        report.append("")
    
    # 3. 전체 통계
    report.append("=" * 100)
    report.append("3. 전체 통계")
    report.append("=" * 100)
    report.append("")
    
    if all_returns:
        avg_return = np.mean(all_returns)
        median_return = np.median(all_returns)
        max_return = np.max(all_returns)
        min_return = np.min(all_returns)
        win_rate = (win_count / len(all_returns)) * 100
        
        report.append(f"총 종목 수:      {len(all_returns)}개")
        report.append(f"승률:           {win_rate:.1f}% ({win_count}승 {loss_count}패)")
        report.append(f"평균 수익률:     {avg_return:+.2f}%")
        report.append(f"중앙값 수익률:   {median_return:+.2f}%")
        report.append(f"최대 수익률:     {max_return:+.2f}%")
        report.append(f"최소 수익률:     {min_return:+.2f}%")
        report.append("")
        
        # 수익률 분포
        report.append("수익률 분포:")
        report.append(f"  익절 (+3% 이상):     {len([r for r in all_returns if r >= 3])}개 ({len([r for r in all_returns if r >= 3])/len(all_returns)*100:.1f}%)")
        report.append(f"  보존 (+1.5~3%):     {len([r for r in all_returns if 1.5 <= r < 3])}개 ({len([r for r in all_returns if 1.5 <= r < 3])/len(all_returns)*100:.1f}%)")
        report.append(f"  소폭 수익 (0~1.5%): {len([r for r in all_returns if 0 < r < 1.5])}개 ({len([r for r in all_returns if 0 < r < 1.5])/len(all_returns)*100:.1f}%)")
        report.append(f"  소폭 손실 (0~-7%):  {len([r for r in all_returns if -7 < r <= 0])}개 ({len([r for r in all_returns if -7 < r <= 0])/len(all_returns)*100:.1f}%)")
        report.append(f"  손절 (-7% 이하):    {len([r for r in all_returns if r <= -7])}개 ({len([r for r in all_returns if r <= -7])/len(all_returns)*100:.1f}%)")
    else:
        report.append("분석할 데이터가 없습니다.")
    
    report.append("")
    report.append("=" * 100)
    
    # 파일 저장
    report_text = "\n".join(report)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_text)
    
    print(f"✅ 리포트 저장: {output_file}")
    print("")
    print(report_text)
    
    return report_text


def main():
    args = parse_args()
    print("=" * 100)
    print("서버 스캔 로직 성과 검증")
    print("=" * 100)
    
    # 1. 거래일 생성
    print("\n📅 거래일 생성")
    try:
        all_dates, period_label = determine_scan_dates(args)
    except ValueError as exc:
        print(f"❌ 입력 오류: {exc}")
        sys.exit(1)
    
    print(f"  - 스캔 모드: {args.mode}")
    if args.mode == "range":
        print(f"  - 기간: {args.start_date} ~ {args.end_date}")
    else:
        print(f"  - 일자 목록: {', '.join(all_dates)}")
    print(f"  - 총 거래일: {len(all_dates)}일")
    
    # 2. 일별 스캔 실행
    scan_results = []
    
    for date in all_dates:
        print(f"\n{'='*80}")
        print(f"📅 {date} 스캔 시작")
        print(f"{'='*80}")
        
        # 유니버스 가져오기
        universe = get_universe_codes(date)
        
        if not universe:
            print(f"⚠️  {date}: 유니버스 없음, 건너뜀")
            continue
        
        # 스캔 실행
        scan_result = scan_with_server_logic(universe, date)
        scan_results.append(scan_result)
    
    # 3. 수익률 계산
    returns_results = []
    
    for scan in scan_results:
        if scan.get("items"):
            ret = calculate_returns(scan, hold_days=5)
            returns_results.append(ret)
    
    # 4. 리포트 생성
    generate_report(scan_results, returns_results, args.report_path, period_label)
    
    print("\n" + "=" * 100)
    print("✅ 검증 완료!")
    print("=" * 100)


if __name__ == "__main__":
    main()

