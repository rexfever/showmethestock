#!/usr/bin/env python3
"""
과거 날짜 스캔 데이터 백필 스크립트
- 로컬 캐시 사용
- 스캐너 v1 사용
- 레짐 분석 v4 사용
- scan_rank 테이블에 저장
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging

# 백엔드 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from date_helper import normalize_date
from services.scan_service import execute_scan_with_fallback, save_scan_snapshot
from kiwoom_api import api
from config import config
from market_analyzer import market_analyzer
from scanner_settings_manager import get_scanner_version, get_regime_version
from main import is_trading_day
from datetime import datetime, timedelta
import holidays

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_scan_for_date(date_str: str, kospi_limit: int = 25, kosdaq_limit: int = 25) -> bool:
    """특정 날짜에 대해 스캔 실행 및 저장"""
    try:
        # 날짜 정규화
        normalized_date = normalize_date(date_str)
        
        # 거래일 체크
        if not is_trading_day(normalized_date):
            logger.info(f"⏭️  {normalized_date}: 거래일이 아님 (스킵)")
            return False
        
        logger.info(f"📅 스캔 시작: {normalized_date}")
        
        # 레짐 분석 먼저 실행 (분리 신호 감지를 위해)
        market_condition = None
        if config.market_analysis_enable:
            try:
                market_analyzer.clear_cache()
                regime_version = get_regime_version() or 'v4'
                market_condition = market_analyzer.analyze_market_condition(normalized_date, regime_version=regime_version)
            except Exception as e:
                logger.warning(f"⚠️  시장 분석 실패, 기본 조건 사용: {e}")
        
        # 시장 분리 신호에 따라 Universe 비율 조정 (양방향)
        if market_condition and hasattr(market_condition, 'market_divergence') and market_condition.market_divergence:
            divergence_type = getattr(market_condition, 'divergence_type', '')
            if divergence_type == 'kospi_up_kosdaq_down':
                # KOSPI 상승·KOSDAQ 하락 시 KOSPI 비중 증가
                adjusted_kospi_limit = int(kospi_limit * 1.5)  # 100 -> 150
                adjusted_kosdaq_limit = int(kosdaq_limit * 0.5)  # 100 -> 50
                logger.info(f"📊 시장 분리 신호 감지 (KOSPI↑ KOSDAQ↓) - Universe 조정: KOSPI {kospi_limit}→{adjusted_kospi_limit}, KOSDAQ {kosdaq_limit}→{adjusted_kosdaq_limit}")
                kospi_limit = adjusted_kospi_limit
                kosdaq_limit = adjusted_kosdaq_limit
            elif divergence_type == 'kospi_down_kosdaq_up':
                # KOSPI 하락·KOSDAQ 상승 시 KOSDAQ 비중 증가
                adjusted_kospi_limit = int(kospi_limit * 0.5)  # 100 -> 50
                adjusted_kosdaq_limit = int(kosdaq_limit * 1.5)  # 100 -> 150
                logger.info(f"📊 시장 분리 신호 감지 (KOSPI↓ KOSDAQ↑) - Universe 조정: KOSPI {kospi_limit}→{adjusted_kospi_limit}, KOSDAQ {kosdaq_limit}→{adjusted_kosdaq_limit}")
                kospi_limit = adjusted_kospi_limit
                kosdaq_limit = adjusted_kosdaq_limit
        
        # 유니버스 조회
        kospi = api.get_top_codes('KOSPI', kospi_limit)
        kosdaq = api.get_top_codes('KOSDAQ', kosdaq_limit)
        universe = [*kospi, *kosdaq]
        
        # 성능 최적화: market_condition에 KOSPI/KOSDAQ 리스트 저장 (가산점 로직에서 재사용)
        if market_condition:
            market_condition.kospi_universe = kospi
            market_condition.kosdaq_universe = kosdaq
        
        if not universe:
            logger.warning(f"⚠️  {normalized_date}: 유니버스가 비어있음")
            return False
        
        logger.info(f"📊 유니버스: {len(universe)}개 종목 (KOSPI: {len(kospi)}, KOSDAQ: {len(kosdaq)})")
        
        # 레짐 분석 로그 (이미 위에서 실행됨)
        if market_condition:
            if hasattr(market_condition, 'version'):
                if market_condition.version == 'regime_v4':
                    logger.info(f"📊 Global Regime v4: {market_condition.final_regime} (trend: {market_condition.global_trend_score:.2f}, risk: {market_condition.global_risk_score:.2f})")
                elif market_condition.version == 'regime_v3':
                    logger.info(f"📊 Global Regime v3: {market_condition.final_regime} (점수: {market_condition.final_score:.2f})")
                else:
                    logger.info(f"📊 시장 상황 분석 v1: {market_condition.market_sentiment}")
            else:
                logger.info(f"📊 시장 상황 분석: {market_condition.market_sentiment}")
        
        # 스캔 실행 (v1 사용)
        result = execute_scan_with_fallback(universe, normalized_date, market_condition)
        if len(result) == 3:
            items, chosen_step, scanner_version = result
        else:
            items, chosen_step = result
            scanner_version = get_scanner_version() or 'v1'
        
        logger.info(f"✅ 스캔 완료: {len(items)}개 종목 (Step {chosen_step})")
        
        # DB 저장 (결과가 없어도 NORESULT 레코드 저장)
        save_scan_snapshot(items, normalized_date, scanner_version)
        if items:
            logger.info(f"💾 DB 저장 완료: {normalized_date} ({len(items)}개 종목)")
        else:
            logger.info(f"💾 DB 저장 완료: {normalized_date} (NORESULT 레코드)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ {date_str} 스캔 실패: {e}", exc_info=True)
        return False

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='과거 날짜 스캔 데이터 백필')
    parser.add_argument('--start', type=str, required=True, help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end', type=str, required=True, help='종료 날짜 (YYYYMMDD)')
    parser.add_argument('--kospi', type=int, default=100, help='KOSPI 종목 수 (기본값: 100)')
    parser.add_argument('--kosdaq', type=int, default=100, help='KOSDAQ 종목 수 (기본값: 100)')
    
    args = parser.parse_args()
    
    # 날짜 정규화
    start_date = normalize_date(args.start)
    end_date = normalize_date(args.end)
    
    logger.info(f"🚀 백필 시작: {start_date} ~ {end_date}")
    logger.info(f"⚙️  설정: 스캐너=v1, 레짐=v4, KOSPI={args.kospi}, KOSDAQ={args.kosdaq}")
    
    # 거래일 목록 생성
    trading_days = []
    start_dt = datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    current_dt = start_dt
    
    while current_dt <= end_dt:
        date_str = current_dt.strftime('%Y%m%d')
        if is_trading_day(date_str):
            trading_days.append(date_str)
        current_dt += timedelta(days=1)
    
    logger.info(f"📅 총 {len(trading_days)}개 거래일")
    
    # 각 날짜에 대해 스캔 실행
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for date_str in trading_days:
        # 이미 처리된 날짜인지 확인
        try:
            from date_helper import yyyymmdd_to_date
            from db_manager import db_manager
            date_obj = yyyymmdd_to_date(date_str)
            
            with db_manager.get_cursor(commit=False) as cur:
                # 스캔 데이터 확인
                cur.execute("SELECT COUNT(*) FROM scan_rank WHERE date = %s AND scanner_version = 'v1'", (date_obj,))
                scan_exists = cur.fetchone()[0] > 0
                
                # 레짐 데이터 확인
                cur.execute("SELECT COUNT(*) FROM market_regime_daily WHERE date = %s AND version = 'regime_v4'", (date_obj,))
                regime_exists = cur.fetchone()[0] > 0
                
                if scan_exists and regime_exists:
                    logger.info(f"⏭️  {date_str}: 이미 처리됨 (스킵)")
                    skip_count += 1
                    continue
        except Exception as e:
            logger.debug(f"기존 데이터 확인 실패 ({date_str}): {e}, 계속 진행")
        
        # 스캔 실행
        if run_scan_for_date(date_str, args.kospi, args.kosdaq):
            success_count += 1
        else:
            fail_count += 1
        
        # 각 날짜 처리 후 짧은 대기 (DB 연결 풀 부담 감소)
        import time
        time.sleep(0.5)
    
    logger.info(f"✅ 백필 완료: 성공 {success_count}건, 실패 {fail_count}건, 스킵 {skip_count}건")

if __name__ == '__main__':
    main()

