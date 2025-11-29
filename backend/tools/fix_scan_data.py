"""
스캔 데이터 수정 스크립트
기존 DB 데이터의 종가와 등락률을 스캔 결과에서 가져와서 수정
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from market_analyzer import market_analyzer
from scanner_factory import scan_with_scanner
from services.scan_service import save_scan_snapshot
from kiwoom_api import api
from db_manager import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_scan_data_date(date: str):
    """
    특정 날짜의 스캔 데이터를 재스캔하여 정확한 종가/등락률로 수정
    
    Args:
        date: 수정할 날짜 (YYYYMMDD)
    """
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"스캔 데이터 수정: {date}")
        logger.info(f"{'='*80}")
        
        # 시장 분석 (레짐 v4)
        market_analyzer.clear_cache()
        market_condition = market_analyzer.analyze_market_condition(date, regime_version='v4')
        
        # 유니버스 구성
        kospi_universe = api.get_top_codes('KOSPI', 200)
        kosdaq_universe = api.get_top_codes('KOSDAQ', 200)
        universe = list(set(kospi_universe + kosdaq_universe))
        
        logger.info(f"  📋 유니버스: {len(universe)}개")
        
        # 스캔 실행 (v2)
        scan_results = scan_with_scanner(
            universe_codes=universe,
            preset_overrides=None,
            base_date=date,
            market_condition=market_condition,
            version="v2"
        )
        
        logger.info(f"  🔍 스캔 완료: {len(scan_results)}개 종목")
        
        # dict 형태로 변환
        scan_items = []
        for result in scan_results:
            if isinstance(result, dict):
                scan_items.append(result)
            else:
                item = {
                    "ticker": result.ticker,
                    "name": result.name,
                    "score": result.score,
                    "match": result.match,
                    "strategy": result.strategy,
                    "flags": result.flags,
                    "indicators": result.indicators,
                    "trend": result.trend,
                    "score_label": result.score_label
                }
                scan_items.append(item)
        
        # DB 저장 (수정된 save_scan_snapshot 사용)
        save_scan_snapshot(scan_items, date, scanner_version="v2")
        logger.info(f"  ✅ DB 수정 완료: {date} ({len(scan_items)}개 종목)")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ 수정 실패: {date} - {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_scan_data_range(start_date: str, end_date: str):
    """
    날짜 범위의 스캔 데이터 수정
    
    Args:
        start_date: 시작 날짜 (YYYYMMDD)
        end_date: 종료 날짜 (YYYYMMDD)
    """
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            dates.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"스캔 데이터 수정: {start_date} ~ {end_date}")
    logger.info(f"총 {len(dates)}개 거래일")
    logger.info(f"{'='*80}\n")
    
    success_count = 0
    failed_count = 0
    
    for date in dates:
        if fix_scan_data_date(date):
            success_count += 1
        else:
            failed_count += 1
    
    logger.info(f"\n{'='*80}")
    logger.info(f"수정 완료 요약")
    logger.info(f"{'='*80}")
    logger.info(f"  ✅ 성공: {success_count}개")
    logger.info(f"  ❌ 실패: {failed_count}개")
    logger.info(f"  총: {len(dates)}개")
    logger.info(f"{'='*80}\n")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='스캔 데이터 수정 (종가/등락률 정확도 개선)')
    parser.add_argument('--date', type=str, help='수정할 날짜 (YYYYMMDD)')
    parser.add_argument('--start', type=str, help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end', type=str, help='종료 날짜 (YYYYMMDD)')
    
    args = parser.parse_args()
    
    if args.date:
        date = args.date
        try:
            datetime.strptime(date, '%Y%m%d')
        except ValueError:
            logger.error(f"날짜 형식 오류: {date} (YYYYMMDD 형식 필요)")
            sys.exit(1)
        
        if fix_scan_data_date(date):
            logger.info(f"\n{'='*80}")
            logger.info(f"수정 완료: {date}")
            logger.info(f"{'='*80}\n")
        else:
            logger.error(f"\n{'='*80}")
            logger.error(f"수정 실패: {date}")
            logger.error(f"{'='*80}\n")
            sys.exit(1)
    
    elif args.start and args.end:
        start_date = args.start
        end_date = args.end
        try:
            datetime.strptime(start_date, '%Y%m%d')
            datetime.strptime(end_date, '%Y%m%d')
        except ValueError:
            logger.error(f"날짜 형식 오류: {start_date} 또는 {end_date} (YYYYMMDD 형식 필요)")
            sys.exit(1)
        
        fix_scan_data_range(start_date, end_date)
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

