#!/usr/bin/env python3
"""11월 1일부터 18일까지의 실제 스캔 결과 및 장세 분석 확인"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# DB 연결 없이 키움 API만 사용
from kiwoom_api import api
from market_analyzer import MarketAnalyzer
from datetime import datetime, timedelta

def check_november_scans():
    """11월 1일부터 18일까지의 장세 분석"""
    analyzer = MarketAnalyzer()
    
    start_date = datetime(2025, 11, 1)
    end_date = datetime(2025, 11, 18)
    
    results = []
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        weekday = current_date.weekday()  # 0=월요일, 6=일요일
        
        # 주말 체크
        is_weekend = weekday >= 5
        
        if is_weekend:
            results.append({
                'date': date_str,
                'day_of_week': current_date.strftime('%A'),
                'is_trading_day': False,
                'reason': '주말',
                'scan_executed': False
            })
        else:
            try:
                # 장세 분석
                condition = analyzer.analyze_market_condition(date_str)
                
                # 스캔 실행 여부 (crash면 스캔 안 함)
                scan_executed = condition.market_sentiment != 'crash'
                
                results.append({
                    'date': date_str,
                    'day_of_week': current_date.strftime('%A'),
                    'is_trading_day': True,
                    'market_sentiment': condition.market_sentiment,
                    'kospi_return': condition.kospi_return * 100,
                    'scan_executed': scan_executed,
                    'rsi_threshold': condition.rsi_threshold,
                    'min_signals': condition.min_signals
                })
            except Exception as e:
                # 공휴일이거나 데이터 없음
                results.append({
                    'date': date_str,
                    'day_of_week': current_date.strftime('%A'),
                    'is_trading_day': True,
                    'error': str(e),
                    'scan_executed': False
                })
        
        current_date += timedelta(days=1)
    
    # 결과 출력
    print("=" * 120)
    print("11월 1일 ~ 18일 장세 분석 및 스캔 실행 여부")
    print("=" * 120)
    print(f"{'날짜':<12} {'요일':<10} {'거래일':<8} {'장세':<10} {'KOSPI 수익률':<18} {'스캔 실행':<12} {'RSI 임계값':<12} {'최소 신호':<10}")
    print("-" * 120)
    
    for r in results:
        date = r['date']
        day = r['day_of_week']
        
        if not r.get('is_trading_day', False):
            reason = r.get('reason', '주말/공휴일')
            print(f"{date} {day:<10} {'❌':<8} {'-':<10} {'-':<18} {'❌':<12} {'-':<12} {'-':<10} ({reason})")
        elif 'error' in r:
            error_msg = r['error'][:30] if len(r['error']) > 30 else r['error']
            print(f"{date} {day:<10} {'✅':<8} {'에러':<10} {'-':<18} {'❌':<12} {'-':<12} {'-':<10} ({error_msg})")
        else:
            sentiment = r['market_sentiment']
            kospi_ret = f"{r['kospi_return']:+.2f}%"
            scan = '✅ 실행' if r['scan_executed'] else '❌ 미실행'
            rsi_th = f"{r['rsi_threshold']:.1f}"
            min_sig = f"{r['min_signals']}"
            
            print(f"{date} {day:<10} {'✅':<8} {sentiment:<10} {kospi_ret:<18} {scan:<12} {rsi_th:<12} {min_sig:<10}")
    
    print("=" * 120)
    
    # 요약
    total_days = len(results)
    trading_days = sum(1 for r in results if r.get('is_trading_day', False) and 'error' not in r)
    scan_days = sum(1 for r in results if r.get('scan_executed', False))
    crash_days = sum(1 for r in results if r.get('market_sentiment') == 'crash')
    bear_days = sum(1 for r in results if r.get('market_sentiment') == 'bear')
    neutral_days = sum(1 for r in results if r.get('market_sentiment') == 'neutral')
    bull_days = sum(1 for r in results if r.get('market_sentiment') == 'bull')
    error_days = sum(1 for r in results if 'error' in r)
    weekend_days = sum(1 for r in results if not r.get('is_trading_day', False))
    
    print("\n📊 요약:")
    print(f"  - 전체 기간: {total_days}일")
    print(f"  - 거래일: {trading_days}일 (주말 제외)")
    print(f"  - 스캔 실행: {scan_days}일")
    print(f"  - 스캔 미실행: {trading_days - scan_days}일")
    print(f"    * Crash 장세: {crash_days}일")
    print(f"    * 데이터 오류: {error_days}일")
    print(f"    * 주말: {weekend_days}일")
    print(f"\n📈 장세 분포:")
    print(f"  - Bull: {bull_days}일")
    print(f"  - Neutral: {neutral_days}일")
    print(f"  - Bear: {bear_days}일")
    print(f"  - Crash: {crash_days}일")
    
    # 스캔 미실행 날짜 상세
    no_scan_dates = [r for r in results if not r.get('scan_executed', False)]
    if no_scan_dates:
        print(f"\n❌ 스캔 미실행 날짜:")
        for r in no_scan_dates:
            if not r.get('is_trading_day', False):
                print(f"  - {r['date']} ({r['day_of_week']}): {r.get('reason', '주말/공휴일')}")
            elif r.get('market_sentiment') == 'crash':
                print(f"  - {r['date']} ({r['day_of_week']}): Crash 장세 (KOSPI {r.get('kospi_return', 0)*100:+.2f}%)")
            else:
                error_msg = r.get('error', '알 수 없는 오류')
                print(f"  - {r['date']} ({r['day_of_week']}): {error_msg}")

if __name__ == '__main__':
    check_november_scans()

