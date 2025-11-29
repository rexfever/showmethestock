#!/usr/bin/env python3
"""
2025년 7월부터 11월까지의 v2 스캔을 실행하여 DB에 저장
"""
import os
import sys
import pandas as pd
from datetime import datetime
import logging
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner_factory import scan_with_scanner
from market_analyzer import market_analyzer
from kiwoom_api import api
from config import config
from services.scan_service import save_scan_snapshot
from date_helper import normalize_date

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_trading_days(start_date: str, end_date: str) -> list:
    """거래일 리스트 반환 (주말 제외)"""
    start = pd.to_datetime(start_date, format='%Y%m%d')
    end = pd.to_datetime(end_date, format='%Y%m%d')
    trading_days = pd.bdate_range(start=start, end=end, freq='B')
    return [d.strftime('%Y%m%d') for d in trading_days]

def check_existing_scan(date: str, scanner_version: str = 'v2') -> bool:
    """해당 날짜의 스캔 데이터가 이미 DB에 있는지 확인"""
    try:
        from db_manager import db_manager
        
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM scan_rank 
                WHERE date = %s AND scanner_version = %s
            """, (formatted_date, scanner_version))
            
            row = cur.fetchone()
            if hasattr(row, 'get'):
                return row.get('cnt', 0) > 0
            else:
                return row[0] > 0 if row else False
    except Exception as e:
        logger.warning(f"기존 스캔 확인 실패 ({date}): {e}")
        return False

def run_scan_v2_for_date(date: str, skip_existing: bool = True) -> bool:
    """특정 날짜에 대해 v2 스캔 실행 및 DB 저장"""
    try:
        normalized_date = normalize_date(date)
        
        # 기존 데이터 확인
        if skip_existing and check_existing_scan(normalized_date, 'v2'):
            logger.debug(f"이미 v2 스캔 데이터가 있음: {normalized_date}, 건너뜀")
            return True
        
        logger.info(f"v2 스캔 시작: {normalized_date}")
        
        # 유니버스 구성
        kospi_limit = 100  # 200개 중 KOSPI 100개
        kosdaq_limit = 100  # 200개 중 KOSDAQ 100개
        kospi_universe = api.get_top_codes('KOSPI', kospi_limit)
        kosdaq_universe = api.get_top_codes('KOSDAQ', kosdaq_limit)
        universe = list(set(kospi_universe + kosdaq_universe))
        
        logger.info(f"유니버스: {len(universe)}개 종목 (KOSPI: {len(kospi_universe)}, KOSDAQ: {len(kosdaq_universe)})")
        
        # 시장 조건 분석
        market_condition = None
        try:
            market_analyzer.clear_cache()
            market_condition = market_analyzer.analyze_market_condition(normalized_date, regime_version='v4')
            
            if market_condition:
                if hasattr(market_condition, 'version'):
                    if market_condition.version == 'regime_v4':
                        logger.info(f"📊 Global Regime v4: {market_condition.final_regime} (trend: {market_condition.global_trend_score:.2f}, risk: {market_condition.global_risk_score:.2f})")
                    elif market_condition.version == 'regime_v3':
                        logger.info(f"📊 Global Regime v3: {market_condition.final_regime}")
                    else:
                        logger.info(f"📊 시장 상황 분석 v1: {market_condition.market_sentiment}")
                else:
                    logger.info(f"📊 시장 상황 분석: {market_condition.market_sentiment}")
        except Exception as e:
            logger.warning(f"시장 분석 실패, 기본 조건 사용: {e}")
        
        # 시장 분리 신호에 따라 Universe 비율 조정 (양방향)
        if market_condition and hasattr(market_condition, 'market_divergence') and market_condition.market_divergence:
            divergence_type = getattr(market_condition, 'divergence_type', '')
            if divergence_type == 'kospi_up_kosdaq_down':
                # KOSPI 상승·KOSDAQ 하락 시 KOSPI 비중 증가
                adjusted_kospi_limit = int(kospi_limit * 1.5)
                adjusted_kosdaq_limit = int(kosdaq_limit * 0.5)
                logger.info(f"📊 시장 분리 신호 감지 (KOSPI↑ KOSDAQ↓) - Universe 조정: KOSPI {kospi_limit}→{adjusted_kospi_limit}, KOSDAQ {kosdaq_limit}→{adjusted_kosdaq_limit}")
                kospi_universe = api.get_top_codes('KOSPI', adjusted_kospi_limit)
                kosdaq_universe = api.get_top_codes('KOSDAQ', adjusted_kosdaq_limit)
            elif divergence_type == 'kospi_down_kosdaq_up':
                # KOSPI 하락·KOSDAQ 상승 시 KOSDAQ 비중 증가
                adjusted_kospi_limit = int(kospi_limit * 0.5)
                adjusted_kosdaq_limit = int(kosdaq_limit * 1.5)
                logger.info(f"📊 시장 분리 신호 감지 (KOSPI↓ KOSDAQ↑) - Universe 조정: KOSPI {kospi_limit}→{adjusted_kospi_limit}, KOSDAQ {kosdaq_limit}→{adjusted_kosdaq_limit}")
                kospi_universe = api.get_top_codes('KOSPI', adjusted_kospi_limit)
                kosdaq_universe = api.get_top_codes('KOSDAQ', adjusted_kosdaq_limit)
            else:
                kospi_universe = api.get_top_codes('KOSPI', kospi_limit)
                kosdaq_universe = api.get_top_codes('KOSDAQ', kosdaq_limit)
            universe = list(set(kospi_universe + kosdaq_universe))
            logger.info(f"조정된 유니버스: {len(universe)}개 종목")
        
        # KOSPI/KOSDAQ Universe 캐시
        if market_condition:
            market_condition.kospi_universe = kospi_universe
            market_condition.kosdaq_universe = kosdaq_universe
        
        # v2 스캐너로 스캔 실행
        logger.info(f"v2 스캐너 실행 중...")
        results = scan_with_scanner(
            universe_codes=universe,
            preset_overrides=None,
            base_date=normalized_date,
            market_condition=market_condition,
            version="v2"
        )
        
        if not results:
            logger.warning(f"스캔 결과 없음: {normalized_date}")
            results = []
        
        # DB에 저장
        save_scan_snapshot(results, normalized_date, scanner_version='v2')
        
        if results:
            logger.info(f"✅ v2 스캔 완료: {normalized_date} ({len(results)}개 종목)")
        else:
            logger.info(f"✅ v2 스캔 완료: {normalized_date} (NORESULT)")
        
        return True
        
    except Exception as e:
        logger.error(f"v2 스캔 실패 ({date}): {e}", exc_info=True)
        return False

def main():
    """메인 함수"""
    logger.info("=" * 70)
    logger.info("2025년 7월~11월 v2 스캔 및 DB 저장 시작")
    logger.info("=" * 70)
    
    # 날짜 범위 설정
    start_date = '20250701'
    end_date = datetime.now().strftime('%Y%m%d')
    
    logger.info(f"대상 기간: {start_date} ~ {end_date}")
    
    # 거래일 리스트 생성
    trading_days = get_trading_days(start_date, end_date)
    logger.info(f"총 거래일: {len(trading_days)}일")
    
    # 각 날짜에 대해 v2 스캔 실행 및 저장
    success_count = 0
    skip_count = 0
    failed_count = 0
    
    for i, date in enumerate(trading_days, 1):
        try:
            logger.info(f"\n[{i}/{len(trading_days)}] {date} 처리 중...")
            
            # 기존 데이터 확인
            if check_existing_scan(date, 'v2'):
                logger.info(f"  이미 v2 스캔 데이터가 있음: {date}, 건너뜀")
                skip_count += 1
                continue
            
            # v2 스캔 실행 및 저장
            if run_scan_v2_for_date(date, skip_existing=False):
                success_count += 1
                logger.info(f"  ✅ 완료: {date}")
            else:
                failed_count += 1
                logger.error(f"  ❌ 실패: {date}")
            
            # 진행 상황 출력
            if i % 10 == 0:
                logger.info(f"\n진행 상황: {i}/{len(trading_days)} ({success_count}개 성공, {skip_count}개 건너뜀, {failed_count}개 실패)")
            
            # API 호출 제한 방지
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"날짜 처리 실패 ({date}): {e}", exc_info=True)
            failed_count += 1
            continue
    
    logger.info("\n" + "=" * 70)
    logger.info("2025년 7월~11월 v2 스캔 및 DB 저장 완료")
    logger.info("=" * 70)
    logger.info(f"총 거래일: {len(trading_days)}일")
    logger.info(f"성공: {success_count}일")
    logger.info(f"건너뜀: {skip_count}일 (이미 존재)")
    logger.info(f"실패: {failed_count}일")
    
    # 최종 확인
    logger.info("\n최종 DB 상태 확인:")
    try:
        from db_manager import db_manager
        
        formatted_start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        formatted_end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT date) as cnt, 
                       MIN(date) as min_date, 
                       MAX(date) as max_date
                FROM scan_rank 
                WHERE date >= %s AND date <= %s AND scanner_version = 'v2'
            """, (formatted_start, formatted_end))
            
            row = cur.fetchone()
            if row:
                if hasattr(row, 'get'):
                    logger.info(f"  DB에 저장된 v2 스캔 데이터: {row.get('cnt', 0)}일")
                    logger.info(f"  날짜 범위: {row.get('min_date')} ~ {row.get('max_date')}")
                else:
                    logger.info(f"  DB에 저장된 v2 스캔 데이터: {row[0]}일")
                    logger.info(f"  날짜 범위: {row[1]} ~ {row[2]}")
    except Exception as e:
        logger.warning(f"최종 확인 실패: {e}")

if __name__ == "__main__":
    main()

