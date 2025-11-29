"""
레짐 분석 스크립트
특정 날짜 또는 날짜 범위의 레짐을 분석하고 DB에 저장
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from market_analyzer import market_analyzer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_regime_date(date: str, skip_existing: bool = False):
    """
    특정 날짜의 레짐 분석 및 DB 저장
    
    Args:
        date: 분석 날짜 (YYYYMMDD)
        skip_existing: 기존 데이터가 있으면 건너뛰기
    """
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"레짐 분석 실행: {date}")
        logger.info(f"{'='*80}")
        
        # 기존 데이터 확인
        if skip_existing:
            try:
                from db_manager import db_manager
                with db_manager.get_cursor() as cur:
                    date_obj = datetime.strptime(date, '%Y%m%d').date()
                    cur.execute("""
                        SELECT COUNT(*) FROM market_regime_daily 
                        WHERE date = %s AND version = 'regime_v4'
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
        logger.info(f"     - global_trend_score: {getattr(market_condition, 'global_trend_score', 'N/A')}")
        logger.info(f"     - global_risk_score: {getattr(market_condition, 'global_risk_score', 'N/A')}")
        logger.info(f"     - kospi_return: {getattr(market_condition, 'kospi_return', 0)*100:.2f}%")
        
        logger.info(f"  ✅ 레짐 분석 및 DB 저장 완료: {date}")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ 레짐 분석 실패: {date} - {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_regime_range(start_date: str, end_date: str, skip_existing: bool = False):
    """
    날짜 범위의 레짐 분석 및 DB 저장
    
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
    logger.info(f"레짐 분석 실행: {start_date} ~ {end_date}")
    logger.info(f"총 {len(dates)}개 거래일")
    logger.info(f"{'='*80}\n")
    
    success_count = 0
    failed_count = 0
    
    for date in dates:
        if analyze_regime_date(date, skip_existing=skip_existing):
            success_count += 1
        else:
            failed_count += 1
    
    logger.info(f"\n{'='*80}")
    logger.info(f"레짐 분석 완료 요약")
    logger.info(f"{'='*80}")
    logger.info(f"  ✅ 성공: {success_count}개")
    logger.info(f"  ❌ 실패: {failed_count}개")
    logger.info(f"  총: {len(dates)}개")
    logger.info(f"{'='*80}\n")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='레짐 분석 실행')
    parser.add_argument('--date', type=str, help='분석 날짜 (YYYYMMDD)')
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
        
        if analyze_regime_date(date, skip_existing=skip_existing):
            logger.info(f"\n{'='*80}")
            logger.info(f"레짐 분석 완료: {date}")
            logger.info(f"{'='*80}\n")
        else:
            logger.error(f"\n{'='*80}")
            logger.error(f"레짐 분석 실패: {date}")
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
        
        analyze_regime_range(start_date, end_date, skip_existing=skip_existing)
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

