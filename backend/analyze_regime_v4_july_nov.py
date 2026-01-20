#!/usr/bin/env python3
"""
2025년 7월부터 11월까지의 레짐을 v4로 분석해서 DB에 저장
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import logging
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from market_analyzer import MarketAnalyzer
from services.regime_storage import upsert_regime
from date_helper import normalize_date

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_trading_days(start_date: str, end_date: str) -> list:
    """거래일 리스트 반환 (주말 제외)"""
    start = pd.to_datetime(start_date, format='%Y%m%d')
    end = pd.to_datetime(end_date, format='%Y%m%d')
    trading_days = pd.bdate_range(start=start, end=end, freq='B')
    return [d.strftime('%Y%m%d') for d in trading_days]

def check_existing_regime(date: str) -> bool:
    """해당 날짜의 레짐 v4 데이터가 이미 DB에 있는지 확인"""
    try:
        from services.regime_storage import load_regime
        from db_manager import db_manager
        
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM market_regime_daily 
                WHERE date = %s AND version = 'regime_v4'
            """, (formatted_date,))
            
            row = cur.fetchone()
            return row and row.get('cnt', 0) > 0
    except Exception as e:
        logger.warning(f"기존 레짐 확인 실패 ({date}): {e}")
        return False

def analyze_and_save_regime_v4(date: str, analyzer: MarketAnalyzer, skip_existing: bool = True) -> bool:
    """레짐 v4 분석 및 DB 저장"""
    try:
        # 기존 데이터 확인
        if skip_existing and check_existing_regime(date):
            logger.debug(f"이미 레짐 v4 데이터가 있음: {date}, 건너뜀")
            return True
        
        logger.info(f"레짐 v4 분석 시작: {date}")
        
        # 레짐 v4 분석 실행
        market_condition = analyzer.analyze_market_condition_v4(date, mode="backtest")
        
        if not market_condition:
            logger.error(f"레짐 v4 분석 실패: {date}")
            return False
        
        # 분석 결과가 이미 DB에 저장되었는지 확인 (analyze_market_condition_v4 내부에서 저장됨)
        # 하지만 명시적으로 저장하기 위해 regime_data 구성
        if hasattr(market_condition, 'final_regime'):
            # analyze_market_condition_v4 내부에서 이미 upsert_regime을 호출하므로
            # 여기서는 확인만 수행
            logger.info(f"✅ 레짐 v4 분석 완료: {date} -> {market_condition.final_regime}")
            return True
        else:
            logger.warning(f"레짐 v4 분석 결과에 final_regime이 없음: {date}")
            return False
            
    except Exception as e:
        logger.error(f"레짐 v4 분석 및 저장 실패 ({date}): {e}", exc_info=True)
        return False

def main():
    """메인 함수"""
    logger.info("=" * 70)
    logger.info("2025년 7월~11월 레짐 v4 분석 및 DB 저장 시작")
    logger.info("=" * 70)
    
    # 날짜 범위 설정
    start_date = '20250701'
    end_date = datetime.now().strftime('%Y%m%d')
    
    logger.info(f"대상 기간: {start_date} ~ {end_date}")
    
    # 거래일 리스트 생성
    trading_days = get_trading_days(start_date, end_date)
    logger.info(f"총 거래일: {len(trading_days)}일")
    
    # MarketAnalyzer 초기화
    analyzer = MarketAnalyzer()
    
    # 각 날짜에 대해 레짐 v4 분석 및 저장
    success_count = 0
    skip_count = 0
    failed_count = 0
    
    for i, date in enumerate(trading_days, 1):
        try:
            logger.info(f"\n[{i}/{len(trading_days)}] {date} 처리 중...")
            
            # 기존 데이터 확인
            if check_existing_regime(date):
                logger.info(f"  이미 레짐 v4 데이터가 있음: {date}, 건너뜀")
                skip_count += 1
                continue
            
            # 레짐 v4 분석 및 저장
            if analyze_and_save_regime_v4(date, analyzer, skip_existing=False):
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
    logger.info("2025년 7월~11월 레짐 v4 분석 및 DB 저장 완료")
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
                SELECT COUNT(*) as cnt, 
                       MIN(date) as min_date, 
                       MAX(date) as max_date
                FROM market_regime_daily 
                WHERE date >= %s AND date <= %s AND version = 'regime_v4'
            """, (formatted_start, formatted_end))
            
            row = cur.fetchone()
            if row:
                logger.info(f"  DB에 저장된 레짐 v4 데이터: {row.get('cnt', 0)}일")
                logger.info(f"  날짜 범위: {row.get('min_date')} ~ {row.get('max_date')}")
    except Exception as e:
        logger.warning(f"최종 확인 실패: {e}")

if __name__ == "__main__":
    main()


