#!/usr/bin/env python3
"""
오늘 날짜 V3 스캔 실행 스크립트
"""
import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# config를 먼저 import하여 .env 로드 (config.py가 dotenv를 로드함)
import config

from date_helper import get_kst_now
from db_manager import db_manager
from scanner_v3 import ScannerV3
from market_analyzer import MarketAnalyzer
from scanner_settings_manager import get_regime_version
from services.scan_service import save_v3_results_to_db

def load_universe():
    """유니버스 종목 목록 로드"""
    try:
        from scanner_midterm.core.universe import load_universe as load_universe_midterm
        universe = load_universe_midterm()
        return universe
    except Exception as e:
        print(f"⚠️ 유니버스 로드 실패: {e}")
        return []

def main():
    """오늘 날짜 또는 지정 날짜 V3 스캔 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='V3 스캔 실행')
    parser.add_argument('--date', type=str, help='스캔 날짜 (YYYYMMDD 형식). 지정하지 않으면 오늘 날짜 사용')
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 V3 스캔 실행")
    print("=" * 60)
    
    # 날짜 결정
    if args.date:
        today_str = args.date
        print(f"\n📅 지정된 날짜: {today_str}")
    else:
        today_str = get_kst_now().strftime('%Y%m%d')
        print(f"\n📅 오늘 날짜: {today_str}")
    
    # 기존 결과 확인
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute("""
            SELECT COUNT(*) FROM scan_rank 
            WHERE date = %s AND scanner_version = 'v3' AND code != 'NORESULT'
        """, (today_str,))
        count = cur.fetchone()[0]
        if count > 0:
            print(f"⏭️ 이미 DB에 저장된 결과가 있습니다. ({count}개)")
            print("스캔을 건너뜁니다.")
            # 하지만 recommendations가 없으면 생성해야 함
            with db_manager.get_cursor(commit=False) as rec_cur:
                rec_cur.execute("""
                    SELECT COUNT(*) FROM recommendations
                    WHERE DATE(anchor_date) = %s::date
                    AND scanner_version = 'v3'
                    AND status = 'ACTIVE'
                """, (today_str,))
                rec_count = rec_cur.fetchone()[0]
                if rec_count == 0:
                    print("⚠️ scan_rank는 있지만 recommendations가 없습니다.")
                    print("recommendations 생성을 위해 스캔을 다시 실행합니다.")
                else:
                    return
    
    # 유니버스 로드
    print("\n📋 유니버스 로드 중...")
    universe = load_universe()
    if not universe:
        print("⚠️ 유니버스가 비어있습니다.")
        return
    print(f"✅ 유니버스 로드 완료: {len(universe)}개 종목")
    
    # 레짐 분석
    print("\n📊 레짐 분석 중...")
    market_analyzer = MarketAnalyzer()
    regime_version = get_regime_version()
    market_condition = market_analyzer.analyze_market_condition(today_str, regime_version=regime_version)
    risk_label = getattr(market_condition, 'risk_label', getattr(market_condition, 'risk', 'unknown'))
    print(f"✅ 레짐: {market_condition.final_regime}/{risk_label}")
    
    # V3 스캔 실행
    print(f"\n🔍 V3 스캔 실행 중...")
    scanner_v3 = ScannerV3()
    v3_result = scanner_v3.scan(universe, today_str, market_condition)
    
    # 결과 확인
    midterm_count = len(v3_result.get("results", {}).get("midterm", {}).get("candidates", []))
    v2_lite_count = len(v3_result.get("results", {}).get("v2_lite", {}).get("candidates", []))
    regime = v3_result.get("regime", {})
    
    print(f"📊 midterm {midterm_count}개, v2_lite {v2_lite_count}개 (레짐: {regime.get('final', 'unknown')}/{regime.get('risk', 'unknown')})")
    
    # DB 저장
    print(f"\n💾 DB 저장 중...")
    save_v3_results_to_db(v3_result, today_str)
    
    print("\n" + "=" * 60)
    print("✅ V3 스캔 완료 및 DB 저장 완료")
    print("=" * 60)

if __name__ == "__main__":
    main()

