#!/usr/bin/env python3
"""
2025년 1월 2일 ~ 8월 31일 V2 스캐너로 스캔 및 DB 저장

이 스크립트는 지정된 기간의 모든 거래일에 대해 V2 스캐너로 스캔을 실행하고
결과를 DB에 저장합니다.
"""

import os
import sys
from datetime import datetime, timedelta
import holidays

# 환경 변수 설정
os.environ.setdefault("SCANNER_VERSION", "v2")
os.environ.setdefault("SCANNER_V2_ENABLED", "true")

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from config import config
from scanner_factory import scan_with_scanner
from market_analyzer import market_analyzer
from db_manager import db_manager
import kiwoom_api

def get_trading_days(start_date, end_date):
    """거래일 목록 생성 (주말, 공휴일 제외)"""
    kr_holidays = holidays.SouthKorea()
    trading_days = []
    current = start_date
    
    while current <= end_date:
        # 주말(토일) 및 공휴일 제외
        if current.weekday() < 5 and current not in kr_holidays:
            trading_days.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    
    return trading_days

def save_scan_results_to_db(results, scan_date, scanner_version="v2"):
    """스캔 결과를 DB에 저장"""
    if not results:
        print(f"  ↳ {scan_date}: 저장할 결과 없음")
        return
    
    # scan_rank 테이블에 저장
    insert_query = """
        INSERT INTO scan_rank (
            date, ticker, name, score, strategy, match_flag,
            indicators, trend, flags, score_label, scanner_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    with db_manager.get_cursor(commit=True) as cur:
        for result in results:
            try:
                cur.execute(insert_query, (
                    scan_date,
                    result.get("ticker", ""),
                    result.get("name", ""),
                    result.get("score", 0),
                    result.get("strategy", ""),
                    1 if result.get("match", False) else 0,
                    str(result.get("indicators", {})),
                    str(result.get("trend", {})),
                    str(result.get("flags", {})),
                    result.get("score_label", ""),
                    scanner_version
                ))
            except Exception as e:
                print(f"  ⚠️ DB 저장 오류 ({result.get('ticker', 'Unknown')}): {e}")
    
    print(f"  ✅ {scan_date}: {len(results)}건 DB 저장 완료")

def main():
    print("🚀 2025년 1월-8월 V2 스캐너 배치 실행 시작")
    print(f"📊 스캐너 버전: {config.scanner_version}")
    print(f"🔧 V2 활성화: {config.scanner_v2_enabled}")
    
    # 날짜 범위 설정
    start_date = datetime(2025, 1, 2)
    end_date = datetime(2025, 8, 31)
    
    # 거래일 목록 생성
    trading_days = get_trading_days(start_date, end_date)
    print(f"📅 총 {len(trading_days)}개 거래일 처리 예정")
    
    # 유니버스 구성
    try:
        kospi_universe = kiwoom_api.api.get_top_codes("KOSPI", config.universe_kospi)
        kosdaq_universe = kiwoom_api.api.get_top_codes("KOSDAQ", config.universe_kosdaq)
        universe = kospi_universe + kosdaq_universe
        print(f"🎯 유니버스: KOSPI {len(kospi_universe)}개 + KOSDAQ {len(kosdaq_universe)}개 = 총 {len(universe)}개")
    except Exception as e:
        print(f"❌ 유니버스 구성 실패: {e}")
        return
    
    success_count = 0
    error_count = 0
    
    for i, date_str in enumerate(trading_days, 1):
        try:
            print(f"\n📈 [{i}/{len(trading_days)}] {date_str} 스캔 시작...")
            
            # 시장 조건 분석
            market_condition = market_analyzer.analyze_market_condition(date_str)
            
            # V2 스캐너로 스캔 실행
            results = scan_with_scanner(
                universe_codes=universe,
                preset_overrides=None,
                base_date=date_str,
                market_condition=market_condition,
                version="v2"
            )
            
            # DB에 저장
            save_scan_results_to_db(results, date_str, "v2")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ {date_str} 스캔 실패: {e}")
            error_count += 1
            continue
    
    print(f"\n🎉 배치 실행 완료!")
    print(f"✅ 성공: {success_count}일")
    print(f"❌ 실패: {error_count}일")
    print(f"📊 성공률: {success_count/(success_count+error_count)*100:.1f}%")

if __name__ == "__main__":
    main()