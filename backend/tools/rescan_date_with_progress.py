"""
날짜 범위 재스캔 스크립트 (진행 상황 표시)
1일 단위로 스캔하고 성공 여부를 확인한 후 다음 스캔 진행
"""
import os
import sys
# tools 디렉토리에서 실행 시 상위 디렉토리(backend)를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from market_analyzer import market_analyzer
from scanner_factory import scan_with_scanner
from services.scan_service import save_scan_snapshot
from kiwoom_api import api
from db_manager import db_manager
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def rescan_date(date: str, skip_existing: bool = False):
    """
    특정 날짜 재스캔 실행 및 DB 저장
    
    Args:
        date: 스캔 날짜 (YYYYMMDD)
        skip_existing: 기존 데이터가 있으면 건너뛰기
    
    Returns:
        tuple: (success: bool, result_count: int, error_msg: str)
    """
    try:
        # 기존 데이터 확인
        if skip_existing:
            try:
                date_obj = datetime.strptime(date, '%Y%m%d').date()
                with db_manager.get_cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) FROM scan_rank 
                        WHERE date = %s AND scanner_version = 'v2'
                    """, (date_obj,))
                    count = cur.fetchone()[0]
                    if count > 0:
                        return (True, count, "기존 데이터 존재")
            except Exception as e:
                logger.debug(f"기존 데이터 확인 실패 (계속 진행): {e}")
        
        # 시장 분석 (레짐 v4)
        market_analyzer.clear_cache()
        market_condition = market_analyzer.analyze_market_condition(date, regime_version='v4')
        
        # 유니버스 구성
        kospi_universe = api.get_top_codes('KOSPI', 200)
        kosdaq_universe = api.get_top_codes('KOSDAQ', 200)
        universe = list(set(kospi_universe + kosdaq_universe))
        
        # 스캔 실행 (v2)
        scan_results = scan_with_scanner(
            universe_codes=universe,
            preset_overrides=None,
            base_date=date,
            market_condition=market_condition,
            version="v2"
        )
        
        # dict 형태로 변환 (save_scan_snapshot이 dict를 기대)
        scan_items = []
        for result in scan_results:
            if isinstance(result, dict):
                scan_items.append(result)
            else:
                # ScanResult 객체를 dict로 변환
                indicators = result.indicators
                if not isinstance(indicators, dict):
                    if hasattr(indicators, '__dict__'):
                        indicators = indicators.__dict__
                    else:
                        indicators = {}
                
                trend = result.trend
                if not isinstance(trend, dict):
                    if hasattr(trend, '__dict__'):
                        trend = trend.__dict__
                    else:
                        trend = {}
                
                flags = result.flags
                if not isinstance(flags, dict):
                    if hasattr(flags, '__dict__'):
                        flags = flags.__dict__
                    else:
                        flags = {}
                
                item = {
                    "ticker": result.ticker,
                    "name": result.name,
                    "score": result.score,
                    "match": result.match,
                    "strategy": result.strategy,
                    "flags": flags,
                    "indicators": indicators,
                    "trend": trend,
                    "score_label": result.score_label
                }
                scan_items.append(item)
        
        # DB 저장
        if scan_items:
            save_scan_snapshot(scan_items, date, scanner_version="v2")
            result_count = len(scan_items)
        else:
            save_scan_snapshot([], date, scanner_version="v2")
            result_count = 0
        
        # 저장 확인
        date_obj = datetime.strptime(date, '%Y%m%d').date()
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM scan_rank
                WHERE date = %s AND scanner_version = 'v2' AND code != 'NORESULT'
            """, (date_obj,))
            saved_count = cur.fetchone()[0]
        
        return (True, saved_count, None)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"재스캔 실패: {date} - {error_msg}")
        return (False, 0, error_msg)

def rescan_date_range_with_progress(start_date: str, end_date: str, skip_existing: bool = False):
    """
    날짜 범위의 재스캔 실행 및 DB 저장 (진행 상황 표시)
    
    Args:
        start_date: 시작 날짜 (YYYYMMDD)
        end_date: 종료 날짜 (YYYYMMDD)
        skip_existing: 기존 데이터가 있으면 건너뛰기
    """
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    
    dates = []
    current = start
    while current <= end:
        # 주말 제외 (월~금만)
        if current.weekday() < 5:  # 0=월요일, 4=금요일
            dates.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    
    print("\n" + "=" * 80)
    print(f"재스캔 실행: {start_date} ~ {end_date}")
    print(f"스캐너: v2, 레짐: v4")
    print(f"총 {len(dates)}개 거래일")
    print("=" * 80 + "\n")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    total_results = 0
    
    for idx, date in enumerate(dates, 1):
        date_display = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%d')
        print(f"[{idx}/{len(dates)}] {date_display} ({date}) 스캔 중...", end=" ", flush=True)
        
        success, result_count, error_msg = rescan_date(date, skip_existing=skip_existing)
        
        if error_msg == "기존 데이터 존재":
            skipped_count += 1
            print(f"⏭️  건너뜀 (기존 데이터 존재)")
        elif success:
            success_count += 1
            total_results += result_count
            if result_count > 0:
                print(f"✅ 성공 ({result_count}개 종목)")
            else:
                print(f"✅ 성공 (결과 없음)")
        else:
            failed_count += 1
            print(f"❌ 실패: {error_msg}")
        
        # 진행 상황 요약 (10개마다)
        if idx % 10 == 0:
            print(f"\n  진행 상황: 성공={success_count}, 실패={failed_count}, 건너뜀={skipped_count}, 총 종목={total_results}개\n")
    
    print("\n" + "=" * 80)
    print("재스캔 완료 요약")
    print("=" * 80)
    print(f"  ✅ 성공: {success_count}개")
    print(f"  ❌ 실패: {failed_count}개")
    print(f"  ⏭️  건너뜀: {skipped_count}개")
    print(f"  📊 총 종목: {total_results}개")
    print(f"  총: {len(dates)}개")
    print("=" * 80 + "\n")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='날짜 범위 재스캔 실행 (진행 상황 표시)')
    parser.add_argument('--start', type=str, required=True, help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end', type=str, required=True, help='종료 날짜 (YYYYMMDD)')
    parser.add_argument('--skip-existing', action='store_true', help='기존 데이터가 있으면 건너뛰기')
    
    args = parser.parse_args()
    
    start_date = args.start
    end_date = args.end
    
    try:
        datetime.strptime(start_date, '%Y%m%d')
        datetime.strptime(end_date, '%Y%m%d')
    except ValueError:
        logger.error(f"날짜 형식 오류: {start_date} 또는 {end_date} (YYYYMMDD 형식 필요)")
        sys.exit(1)
    
    rescan_date_range_with_progress(start_date, end_date, skip_existing=args.skip_existing)

if __name__ == "__main__":
    main()




































