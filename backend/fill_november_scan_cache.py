#!/usr/bin/env python3
"""
11월 스캔 캐시 데이터 부족분 채우기
- Universe OHLCV 캐시 업데이트 (200개 종목)
- 개별 종목 CSV 캐시 업데이트
- 디스크 캐시 (cache/ohlcv/*.pkl) 업데이트
"""
import os
import sys
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime, timedelta
import logging
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kiwoom_api import api
from config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_trading_days(start_date: str, end_date: str) -> list:
    """거래일 리스트 반환 (주말 제외)"""
    start = pd.to_datetime(start_date, format='%Y%m%d')
    end = pd.to_datetime(end_date, format='%Y%m%d')
    trading_days = pd.bdate_range(start=start, end=end, freq='B')
    return [d.strftime('%Y%m%d') for d in trading_days]

def update_universe_cache(end_date: str = None) -> bool:
    """Universe OHLCV 캐시 업데이트"""
    try:
        cache_path = Path("data_cache/universe_ohlcv.pkl")
        cache_dir = cache_path.parent
        cache_dir.mkdir(exist_ok=True)
        
        # 기존 캐시 로드
        universe_data = {}
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    universe_data = pickle.load(f)
                logger.info(f"기존 Universe 캐시 로드: {len(universe_data)}개 종목")
            except Exception as e:
                logger.warning(f"기존 Universe 캐시 로드 실패: {e}")
        
        # Universe 종목 리스트 가져오기 (200개로 고정)
        logger.info("Universe 종목 리스트 가져오는 중...")
        kospi_limit = 100  # 200개 중 KOSPI 100개
        kosdaq_limit = 100  # 200개 중 KOSDAQ 100개
        kospi_codes = api.get_top_codes('KOSPI', kospi_limit)
        kosdaq_codes = api.get_top_codes('KOSDAQ', kosdaq_limit)
        universe_codes = list(set(kospi_codes + kosdaq_codes))
        logger.info(f"Universe 종목: {len(universe_codes)}개 (KOSPI {len(kospi_codes)}개 + KOSDAQ {len(kosdaq_codes)}개)")
        
        # 기존 캐시에서 유효한 종목만 유지
        valid_universe_data = {}
        for code in universe_codes:
            if code in universe_data:
                valid_universe_data[code] = universe_data[code]
        universe_data = valid_universe_data
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        # 각 종목의 11월 데이터 업데이트
        updated_count = 0
        failed_count = 0
        
        for i, code in enumerate(universe_codes, 1):
            try:
                # 기존 데이터 확인
                existing_df = universe_data.get(code, pd.DataFrame())
                
                # 7월부터 11월까지의 데이터 확인
                july_start = pd.to_datetime('20250701', format='%Y%m%d')
                july_end = pd.to_datetime(end_date, format='%Y%m%d')
                
                if not existing_df.empty:
                    if isinstance(existing_df.index, pd.DatetimeIndex):
                        # 7~11월 기간의 데이터 확인
                        period_data = existing_df[(existing_df.index >= july_start) & (existing_df.index <= july_end)]
                        if len(period_data) > 0:
                            # 기간 내 최신 날짜 확인
                            last_date = period_data.index.max()
                            start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d')
                        else:
                            # 7~11월 데이터가 없으면 7월부터 시작
                            start_date = '20250701'
                    else:
                        start_date = '20250701'
                else:
                    start_date = '20250701'  # 7월부터 시작
                
                # 부족한 날짜 확인
                if start_date > end_date:
                    continue  # 이미 최신
                
                # 데이터 가져오기
                if i % 10 == 0:
                    logger.info(f"[{i}/{len(universe_codes)}] {code} 데이터 수집 중...")
                df_new = api.get_ohlcv(code, count=220, base_dt=end_date)
                
                if df_new.empty:
                    # 실패한 종목은 기존 데이터 유지 (새로 추가하지 않음)
                    if code in universe_data:
                        continue  # 기존 데이터 유지
                    else:
                        failed_count += 1
                        continue
                
                # 날짜 컬럼을 인덱스로 변환
                if 'date' in df_new.columns:
                    df_new['date'] = pd.to_datetime(df_new['date'], format='%Y%m%d', errors='coerce')
                    df_new = df_new.set_index('date')
                elif not isinstance(df_new.index, pd.DatetimeIndex):
                    logger.warning(f"{code} 날짜 인덱스 변환 실패")
                    failed_count += 1
                    continue
                
                # 기존 데이터와 병합
                if not existing_df.empty:
                    combined = pd.concat([existing_df, df_new])
                    combined = combined[~combined.index.duplicated(keep='last')]
                    combined = combined.sort_index()
                else:
                    combined = df_new.sort_index()
                
                universe_data[code] = combined
                updated_count += 1
                
                # 진행 상황 출력
                if i % 20 == 0:
                    logger.info(f"진행 중: {i}/{len(universe_codes)} ({updated_count}개 업데이트, {failed_count}개 실패)")
                
                # API 호출 제한 방지
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"{code} 업데이트 실패: {e}")
                failed_count += 1
                continue
        
        # 캐시 저장
        with open(cache_path, 'wb') as f:
            pickle.dump(universe_data, f)
        
        logger.info(f"✅ Universe 캐시 업데이트 완료: {updated_count}개 종목 업데이트, {failed_count}개 실패")
        return True
        
    except Exception as e:
        logger.error(f"Universe 캐시 업데이트 실패: {e}", exc_info=True)
        return False

def update_individual_csv_cache(end_date: str = None) -> bool:
    """개별 종목 CSV 캐시 업데이트"""
    try:
        cache_dir = Path("data_cache/ohlcv")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Universe 종목 리스트 가져오기 (200개로 고정)
        kospi_limit = 100  # 200개 중 KOSPI 100개
        kosdaq_limit = 100  # 200개 중 KOSDAQ 100개
        kospi_codes = api.get_top_codes('KOSPI', kospi_limit)
        kosdaq_codes = api.get_top_codes('KOSDAQ', kosdaq_limit)
        universe_codes = list(set(kospi_codes + kosdaq_codes))
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        updated_count = 0
        failed_count = 0
        
        for i, code in enumerate(universe_codes, 1):
            try:
                csv_path = cache_dir / f"{code}.csv"
                
                # 기존 캐시 로드
                existing_df = pd.DataFrame()
                if csv_path.exists():
                    try:
                        existing_df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
                    except Exception as e:
                        logger.debug(f"{code} 기존 CSV 로드 실패: {e}")
                
                # 7월부터 11월까지의 데이터 확인
                july_start = pd.to_datetime('20250701', format='%Y%m%d')
                july_end = pd.to_datetime(end_date, format='%Y%m%d')
                
                if not existing_df.empty:
                    # 7~11월 기간의 데이터 확인
                    period_data = existing_df[(existing_df.index >= july_start) & (existing_df.index <= july_end)]
                    if len(period_data) > 0:
                        # 기간 내 최신 날짜 확인
                        last_date = period_data.index.max()
                        start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d')
                    else:
                        # 7~11월 데이터가 없으면 7월부터 시작
                        start_date = '20250701'
                else:
                    start_date = '20250701'  # 7월부터 시작
                
                # 부족한 날짜 확인
                if start_date > end_date:
                    continue  # 이미 최신
                
                # 데이터 가져오기
                logger.debug(f"[{i}/{len(universe_codes)}] {code} CSV 업데이트 중...")
                df_new = api.get_ohlcv(code, count=220, base_dt=end_date)
                
                if df_new.empty:
                    failed_count += 1
                    continue
                
                # 날짜 컬럼을 인덱스로 변환
                if 'date' in df_new.columns:
                    df_new['date'] = pd.to_datetime(df_new['date'], format='%Y%m%d', errors='coerce')
                    df_new = df_new.set_index('date')
                elif not isinstance(df_new.index, pd.DatetimeIndex):
                    failed_count += 1
                    continue
                
                # 기존 데이터와 병합
                if not existing_df.empty:
                    combined = pd.concat([existing_df, df_new])
                    combined = combined[~combined.index.duplicated(keep='last')]
                    combined = combined.sort_index()
                else:
                    combined = df_new.sort_index()
                
                # CSV로 저장
                combined.to_csv(csv_path)
                updated_count += 1
                
                # 진행 상황 출력
                if i % 20 == 0:
                    logger.info(f"CSV 진행 중: {i}/{len(universe_codes)} ({updated_count}개 업데이트, {failed_count}개 실패)")
                
                # API 호출 제한 방지
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"{code} CSV 업데이트 실패: {e}")
                failed_count += 1
                continue
        
        logger.info(f"✅ 개별 종목 CSV 캐시 업데이트 완료: {updated_count}개 업데이트, {failed_count}개 실패")
        return True
        
    except Exception as e:
        logger.error(f"개별 종목 CSV 캐시 업데이트 실패: {e}", exc_info=True)
        return False

def main():
    """메인 함수"""
    logger.info("=" * 70)
    logger.info("7월~11월 스캔 캐시 데이터 부족분 채우기 시작")
    logger.info("=" * 70)
    
    # 7월부터 11월까지 날짜 범위
    start_date = '20250701'
    end_date = datetime.now().strftime('%Y%m%d')
    
    logger.info(f"대상 기간: {start_date} ~ {end_date}")
    
    # 1. Universe 캐시 업데이트
    logger.info("\n[1/2] Universe OHLCV 캐시 업데이트")
    update_universe_cache(end_date)
    
    # 2. 개별 종목 CSV 캐시 업데이트
    logger.info("\n[2/2] 개별 종목 CSV 캐시 업데이트")
    update_individual_csv_cache(end_date)
    
    logger.info("\n" + "=" * 70)
    logger.info("7월~11월 스캔 캐시 데이터 업데이트 완료")
    logger.info("=" * 70)
    
    # 최종 확인
    logger.info("\n최종 캐시 상태:")
    try:
        universe_path = Path("data_cache/universe_ohlcv.pkl")
        if universe_path.exists():
            with open(universe_path, 'rb') as f:
                universe_data = pickle.load(f)
            
            july_nov_count = 0
            for code, df in universe_data.items():
                if isinstance(df.index, pd.DatetimeIndex):
                    july_nov_data = df[(df.index >= '2025-07-01') & (df.index <= '2025-11-30')]
                    if not july_nov_data.empty:
                        july_nov_count += 1
            
            logger.info(f"  Universe: {len(universe_data)}개 종목, 7~11월 데이터 있는 종목: {july_nov_count}개")
        
        csv_dir = Path("data_cache/ohlcv")
        if csv_dir.exists():
            csv_files = list(csv_dir.glob("*.csv"))
            logger.info(f"  개별 CSV: {len(csv_files)}개 파일")
    except Exception as e:
        logger.warning(f"최종 확인 실패: {e}")

if __name__ == "__main__":
    main()

