#!/usr/bin/env python3
"""
Shadow 모드로 Scanner v2 스캔 실행 (로그 생성용)
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# backend 디렉토리를 Python 경로에 추가
backend_path = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, backend_path)
os.chdir(backend_path)

# Shadow 모드 설정
os.environ['SCANNER_V2_REGIME_POLICY_MODE'] = 'shadow'

from scanner_v2 import ScannerV2
from scanner_v2.config_v2 import scanner_v2_config
from market_analyzer import MarketAnalyzer
from scanner_v2_lite.backtest.cli import load_universe
from main import is_trading_day

def run_shadow_scan(start_date: str, end_date: str):
    """지정 기간 동안 shadow 모드로 스캔 실행"""
    # MarketAnalyzer 생성
    market_analyzer = MarketAnalyzer()
    
    # Scanner v2 생성
    scanner = ScannerV2(scanner_v2_config, market_analyzer)
    
    # 유니버스 로드
    universe = load_universe(use_refined=True)
    print(f"유니버스: {len(universe)}개 종목")
    
    # 날짜 리스트 생성
    current = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    dates = []
    
    while current <= end:
        date_str = current.strftime('%Y%m%d')
        if is_trading_day(date_str):
            dates.append(date_str)
        current += timedelta(days=1)
    
    print(f"스캔 대상 날짜: {len(dates)}일")
    
    # 각 날짜 스캔
    for i, date_str in enumerate(dates, 1):
        print(f"[{i}/{len(dates)}] {date_str} 스캔 중...")
        try:
            # Market condition 가져오기 (선택적)
            market_condition = market_analyzer.analyze_market_condition_v4(date_str)
            
            # 스캔 실행
            results = scanner.scan(universe, date=date_str, market_condition=market_condition)
            print(f"  ✅ {len(results)}개 후보")
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print("\nShadow 로그 생성 완료!")
    print(f"로그 파일: backend/backtest/output/regime_policy_shadow_log.jsonl")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=str, required=True, help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end', type=str, required=True, help='종료 날짜 (YYYYMMDD)')
    args = parser.parse_args()
    
    run_shadow_scan(args.start, args.end)
























