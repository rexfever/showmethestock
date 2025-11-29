"""
특정 날짜 재스캔 스크립트
수정된 코드로 정확한 종가와 등락률로 재저장
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
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rescan_date(date: str, skip_existing: bool = False):
    """
    특정 날짜 재스캔 실행 및 DB 저장
    
    Args:
        date: 스캔 날짜 (YYYYMMDD)
    """
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"재스캔 실행: {date}")
        logger.info(f"{'='*80}")
        
        # 기존 데이터 확인
        if skip_existing:
            try:
                from db_manager import db_manager
                with db_manager.get_cursor() as cur:
                    date_obj = datetime.strptime(date, '%Y%m%d').date()
                    cur.execute("""
                        SELECT COUNT(*) FROM scan_rank 
                        WHERE date = %s AND scanner_version = 'v2'
                    """, (date_obj,))
                    count = cur.fetchone()[0]
                    if count > 0:
                        logger.info(f"  ⏭️  기존 데이터 존재 (건너뜀): {date}")
                        return True
            except Exception as e:
                logger.debug(f"기존 데이터 확인 실패 (계속 진행): {e}")
        
        # 시장 분석 (레짐 v4)
        market_analyzer.clear_cache()
        market_condition = market_analyzer.analyze_market_condition(date, regime_version='v4')
        
        logger.info(f"  📊 레짐 분석 완료:")
        logger.info(f"     - longterm_regime: {getattr(market_condition, 'longterm_regime', 'N/A')}")
        logger.info(f"     - midterm_regime: {getattr(market_condition, 'midterm_regime', 'N/A')}")
        logger.info(f"     - short_term_risk_score: {getattr(market_condition, 'short_term_risk_score', 'N/A')}")
        logger.info(f"     - final_regime: {getattr(market_condition, 'final_regime', 'N/A')}")
        
        # 유니버스 구성
        kospi_universe = api.get_top_codes('KOSPI', 200)
        kosdaq_universe = api.get_top_codes('KOSDAQ', 200)
        universe = list(set(kospi_universe + kosdaq_universe))
        
        logger.info(f"  📋 유니버스: KOSPI {len(kospi_universe)}개, KOSDAQ {len(kosdaq_universe)}개, 총 {len(universe)}개")
        
        # 스캔 실행 (v2)
        scan_results = scan_with_scanner(
            universe_codes=universe,
            preset_overrides=None,
            base_date=date,
            market_condition=market_condition,
            version="v2"
        )
        
        logger.info(f"  🔍 스캔 완료: {len(scan_results)}개 종목")
        
        # horizon별 후보 수 계산
        from scanner_v2.config_regime import REGIME_CUTOFFS
        regime = getattr(market_condition, 'midterm_regime', None) or getattr(market_condition, 'final_regime', 'neutral')
        cutoffs = REGIME_CUTOFFS.get(regime, REGIME_CUTOFFS['neutral'])
        
        swing_count = 0
        position_count = 0
        longterm_count = 0
        
        for result in scan_results:
            if isinstance(result, dict):
                score = result.get("score", 0)
                flags = result.get("flags", {})
                risk_score = flags.get("risk_score", 0) if flags else 0
            else:
                score = result.score
                risk_score = result.flags.get("risk_score", 0) if hasattr(result, 'flags') and result.flags else 0
            
            effective_score = (score or 0) - (risk_score or 0)
            
            if effective_score >= cutoffs['swing']:
                swing_count += 1
            if effective_score >= cutoffs['position']:
                position_count += 1
            if effective_score >= cutoffs['longterm']:
                longterm_count += 1
        
        logger.info(f"  🎯 horizon별 후보:")
        logger.info(f"     - swing (단기): {swing_count}개 (cutoff: {cutoffs['swing']})")
        logger.info(f"     - position (중기): {position_count}개 (cutoff: {cutoffs['position']})")
        logger.info(f"     - longterm (장기): {longterm_count}개 (cutoff: {cutoffs['longterm']})")
        
        # DB 저장
        if scan_results:
            # dict 형태로 변환 (save_scan_snapshot이 dict를 기대)
            scan_items = []
            for result in scan_results:
                if isinstance(result, dict):
                    scan_items.append(result)
                else:
                    # ScanResult 객체를 dict로 변환
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
            
            save_scan_snapshot(scan_items, date, scanner_version="v2")
            logger.info(f"  ✅ DB 저장 완료: {date} ({len(scan_items)}개 종목)")
            
            # 저장된 데이터 확인
            from db_manager import db_manager
            with db_manager.get_cursor() as cur:
                date_obj = datetime.strptime(date, '%Y%m%d').date()
                cur.execute("""
                    SELECT code, name, close_price, change_rate
                    FROM scan_rank
                    WHERE date = %s AND scanner_version = 'v2' AND code != 'NORESULT'
                    ORDER BY score DESC
                    LIMIT 3
                """, (date_obj,))
                results = cur.fetchall()
                logger.info(f"\n  📊 저장된 데이터 확인 (상위 3개):")
                for row in results:
                    code, name, close_price, change_rate = row
                    logger.info(f"     {code} ({name}): 종가={close_price}, 등락률={change_rate}%")
        else:
            logger.info(f"  ⚠️  스캔 결과 없음: {date}")
            save_scan_snapshot([], date, scanner_version="v2")
            logger.info(f"  ✅ DB 저장 완료 (결과 없음): {date}")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ 재스캔 실패: {date} - {e}")
        import traceback
        traceback.print_exc()
        return False

def rescan_date_range(start_date: str, end_date: str, skip_existing: bool = False):
    """
    날짜 범위의 재스캔 실행 및 DB 저장
    
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
    
    logger.info(f"\n{'='*80}")
    logger.info(f"재스캔 실행: {start_date} ~ {end_date}")
    logger.info(f"스캐너: v2, 레짐: v4")
    logger.info(f"총 {len(dates)}개 거래일")
    logger.info(f"{'='*80}\n")
    
    success_count = 0
    failed_count = 0
    
    for date in dates:
        if rescan_date(date, skip_existing=skip_existing):
            success_count += 1
        else:
            failed_count += 1
    
    logger.info(f"\n{'='*80}")
    logger.info(f"재스캔 완료 요약")
    logger.info(f"{'='*80}")
    logger.info(f"  ✅ 성공: {success_count}개")
    logger.info(f"  ❌ 실패: {failed_count}개")
    logger.info(f"  총: {len(dates)}개")
    logger.info(f"{'='*80}\n")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='특정 날짜 또는 날짜 범위 재스캔 실행')
    parser.add_argument('--date', type=str, help='스캔 날짜 (YYYYMMDD)')
    parser.add_argument('--start', type=str, help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end', type=str, help='종료 날짜 (YYYYMMDD)')
    parser.add_argument('--skip-existing', action='store_true', help='기존 데이터가 있으면 건너뛰기')
    
    args = parser.parse_args()
    
    skip_existing = args.skip_existing
    
    if args.date:
        # 단일 날짜
        date = args.date
        try:
            datetime.strptime(date, '%Y%m%d')
        except ValueError:
            logger.error(f"날짜 형식 오류: {date} (YYYYMMDD 형식 필요)")
            sys.exit(1)
        
        if rescan_date(date, skip_existing=skip_existing):
            logger.info(f"\n{'='*80}")
            logger.info(f"재스캔 완료: {date}")
            logger.info(f"{'='*80}\n")
        else:
            logger.error(f"\n{'='*80}")
            logger.error(f"재스캔 실패: {date}")
            logger.error(f"{'='*80}\n")
            sys.exit(1)
    
    elif args.start and args.end:
        # 날짜 범위
        start_date = args.start
        end_date = args.end
        try:
            datetime.strptime(start_date, '%Y%m%d')
            datetime.strptime(end_date, '%Y%m%d')
        except ValueError:
            logger.error(f"날짜 형식 오류: {start_date} 또는 {end_date} (YYYYMMDD 형식 필요)")
            sys.exit(1)
        
        rescan_date_range(start_date, end_date, skip_existing=skip_existing)
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

