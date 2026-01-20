"""
레짐 분석용 캐시 관리 (증분 업데이트 방식)
"""
import pandas as pd
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import os

logger = logging.getLogger(__name__)

# 캐시 경로
KOSPI_CACHE_PATH = Path("data_cache/kospi200_ohlcv.pkl")
KOSDAQ_CACHE_PATH = Path("data_cache/ohlcv/229200.csv")


def ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame의 인덱스를 DatetimeIndex로 변환
    
    Args:
        df: DataFrame (date 컬럼 또는 DatetimeIndex)
    
    Returns:
        DatetimeIndex를 가진 DataFrame
    """
    if isinstance(df.index, pd.DatetimeIndex):
        return df.copy()
    elif 'date' in df.columns:
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        return df
    else:
        raise ValueError("DataFrame에 날짜 정보가 없습니다 (인덱스 또는 date 컬럼 필요)")


def compare_dates_only(date1: pd.Timestamp, date2: pd.Timestamp) -> bool:
    """날짜만 비교 (시간 제외)
    
    Args:
        date1: 첫 번째 날짜
        date2: 두 번째 날짜
    
    Returns:
        date1이 date2보다 이전인지 여부
    """
    return date1.normalize() < date2.normalize()


def merge_cache_data(old_df: pd.DataFrame, new_df: pd.DataFrame, max_days: int = 365) -> pd.DataFrame:
    """캐시 데이터 병합 (인덱스 타입 통일, 중복 제거, 정렬)
    
    Args:
        old_df: 기존 캐시 데이터
        new_df: 새 데이터
        max_days: 최대 유지할 일수
    
    Returns:
        병합된 DataFrame
    """
    # 인덱스 타입 통일
    old_df = ensure_datetime_index(old_df)
    new_df = ensure_datetime_index(new_df)
    
    # 병합
    combined = pd.concat([old_df, new_df])
    
    # 중복 제거 (최신 데이터 우선)
    combined = combined[~combined.index.duplicated(keep='last')]
    
    # 정렬
    combined = combined.sort_index()
    
    # 크기 제한
    if len(combined) > max_days:
        combined = combined.tail(max_days)
    
    return combined


def load_kospi_cache() -> Optional[pd.DataFrame]:
    """KOSPI 캐시 로드"""
    try:
        if KOSPI_CACHE_PATH.exists():
            df = pd.read_pickle(KOSPI_CACHE_PATH)
            if not df.empty:
                # 인덱스 타입 확인 및 변환
                if not isinstance(df.index, pd.DatetimeIndex):
                    try:
                        df = ensure_datetime_index(df)
                    except ValueError as e:
                        logger.warning(f"KOSPI 캐시 인덱스 변환 실패: {e}")
                        return None
                
                logger.debug(f"KOSPI 캐시 로드: {len(df)}개 행 (최신: {df.index.max().date()})")
                return df
        return None
    except Exception as e:
        logger.warning(f"KOSPI 캐시 로드 실패: {e}")
        return None


def save_kospi_cache(df: pd.DataFrame) -> bool:
    """KOSPI 캐시 저장"""
    try:
        KOSPI_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_pickle(KOSPI_CACHE_PATH)
        logger.debug(f"KOSPI 캐시 저장: {len(df)}개 행")
        return True
    except Exception as e:
        logger.error(f"KOSPI 캐시 저장 실패: {e}")
        return False


def update_kospi_cache_incremental() -> bool:
    """KOSPI 캐시 증분 업데이트"""
    try:
        from utils.kospi_data_loader import get_kospi_data
        
        # 기존 캐시 로드
        cached_df = load_kospi_cache()
        today = pd.Timestamp.now().normalize()
        
        if cached_df is None or cached_df.empty:
            # 캐시 없으면 초기 생성 (365일분)
            logger.info("KOSPI 캐시 없음 - 초기 생성 중...")
            today_str = today.strftime('%Y%m%d')
            df = get_kospi_data(date=today_str, days=365)
            if not df.empty:
                save_kospi_cache(df)
                logger.info(f"✅ KOSPI 캐시 초기 생성 완료: {len(df)}개 행")
                return True
            else:
                logger.warning("KOSPI 초기 데이터 생성 실패")
                return False
        
        # 캐시의 최신 날짜 확인
        if not isinstance(cached_df.index, pd.DatetimeIndex):
            cached_df = ensure_datetime_index(cached_df)
        
        latest_date = cached_df.index.max()
        
        # 오늘보다 오래된 경우에만 증분 업데이트 (날짜만 비교)
        if compare_dates_only(latest_date, today):
            logger.info(f"KOSPI 캐시 증분 업데이트 (최신: {latest_date.date()}, 오늘: {today.date()})")
            # 최근 30일 데이터 가져오기 (당일 포함)
            today_str = today.strftime('%Y%m%d')
            new_data = get_kospi_data(date=today_str, days=30)
            
            if not new_data.empty:
                # 기존 데이터와 병합 (인덱스 타입 통일 포함)
                try:
                    combined = merge_cache_data(cached_df, new_data, max_days=365)
                except ValueError as e:
                    logger.warning(f"KOSPI 캐시 병합 실패 (인덱스 타입 문제): {e}")
                    return False
                
                save_kospi_cache(combined)
                added_rows = len(combined) - len(cached_df)
                logger.info(f"✅ KOSPI 캐시 증분 업데이트 완료: +{added_rows}개 행 (총 {len(combined)}개 행)")
                return True
            else:
                logger.warning("KOSPI 증분 데이터 가져오기 실패")
                return False
        else:
            logger.debug(f"KOSPI 캐시 최신 상태 (최신: {latest_date.date()})")
            return True
            
    except Exception as e:
        logger.error(f"KOSPI 캐시 증분 업데이트 실패: {e}")
        return False


def load_kosdaq_cache() -> Optional[pd.DataFrame]:
    """KOSDAQ 캐시 로드"""
    try:
        if KOSDAQ_CACHE_PATH.exists():
            df = pd.read_csv(KOSDAQ_CACHE_PATH, index_col=0, parse_dates=True)
            if not df.empty:
                # 인덱스 타입 확인 및 변환
                if not isinstance(df.index, pd.DatetimeIndex):
                    try:
                        df = ensure_datetime_index(df)
                    except ValueError as e:
                        logger.warning(f"KOSDAQ 캐시 인덱스 변환 실패: {e}")
                        return None
                
                logger.debug(f"KOSDAQ 캐시 로드: {len(df)}개 행 (최신: {df.index.max().date()})")
                return df
        return None
    except Exception as e:
        logger.warning(f"KOSDAQ 캐시 로드 실패: {e}")
        return None


def save_kosdaq_cache(df: pd.DataFrame) -> bool:
    """KOSDAQ 캐시 저장"""
    try:
        KOSDAQ_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(KOSDAQ_CACHE_PATH)
        logger.debug(f"KOSDAQ 캐시 저장: {len(df)}개 행")
        return True
    except Exception as e:
        logger.error(f"KOSDAQ 캐시 저장 실패: {e}")
        return False


def update_kosdaq_cache_incremental() -> bool:
    """KOSDAQ 캐시 증분 업데이트"""
    try:
        from kiwoom_api import api
        
        # 기존 캐시 로드
        cached_df = load_kosdaq_cache()
        today = pd.Timestamp.now().normalize()
        
        if cached_df is None or cached_df.empty:
            # 캐시 없으면 초기 생성 (365일분)
            logger.info("KOSDAQ 캐시 없음 - 초기 생성 중...")
            today_str = today.strftime('%Y%m%d')
            df = api.get_ohlcv("229200", 365, today_str)  # KOSDAQ 지수
            
            if not df.empty:
                # date 컬럼을 인덱스로 변환 (인덱스 타입 통일)
                try:
                    df = ensure_datetime_index(df)
                except ValueError as e:
                    logger.warning(f"KOSDAQ 초기 데이터 날짜 정보 없음: {e}")
                    return False
                
                save_kosdaq_cache(df)
                logger.info(f"✅ KOSDAQ 캐시 초기 생성 완료: {len(df)}개 행")
                return True
            else:
                logger.warning("KOSDAQ 초기 데이터 생성 실패")
                return False
        
        # 캐시의 최신 날짜 확인 (인덱스 타입 통일)
        if not isinstance(cached_df.index, pd.DatetimeIndex):
            try:
                cached_df = ensure_datetime_index(cached_df)
            except ValueError as e:
                logger.warning(f"KOSDAQ 캐시 날짜 정보 없음: {e}")
                return False
        
        latest_date = cached_df.index.max()
        
        # 오늘보다 오래된 경우에만 증분 업데이트 (날짜만 비교)
        if compare_dates_only(latest_date, today):
            logger.info(f"KOSDAQ 캐시 증분 업데이트 (최신: {latest_date.date()}, 오늘: {today.date()})")
            # 최근 5일 데이터 가져오기 (당일 포함)
            today_data = api.get_ohlcv("229200", 5, None)
            
            if not today_data.empty:
                # 기존 데이터와 병합 (인덱스 타입 통일 포함)
                try:
                    combined = merge_cache_data(cached_df, today_data, max_days=365)
                except ValueError as e:
                    logger.warning(f"KOSDAQ 캐시 병합 실패 (인덱스 타입 문제): {e}")
                    return False
                
                save_kosdaq_cache(combined)
                added_rows = len(combined) - len(cached_df)
                logger.info(f"✅ KOSDAQ 캐시 증분 업데이트 완료: +{added_rows}개 행 (총 {len(combined)}개 행)")
                return True
            else:
                logger.warning("KOSDAQ 증분 데이터 가져오기 실패")
                return False
        else:
            logger.debug(f"KOSDAQ 캐시 최신 상태 (최신: {latest_date.date()})")
            return True
            
    except Exception as e:
        logger.error(f"KOSDAQ 캐시 증분 업데이트 실패: {e}")
        return False


def update_us_futures_cache_incremental(symbols: list = None) -> bool:
    """미국 선물 캐시 증분 업데이트 (SPY, QQQ, VIX, ES=F, NQ=F, DX-Y.NYB)"""
    try:
        from services.us_futures_data_v8 import us_futures_data_v8
        
        if symbols is None:
            symbols = ['SPY', 'QQQ', '^VIX']
        
        success_count = 0
        
        for symbol in symbols:
            try:
                # fetch_data()는 내부적으로 증분 업데이트 처리
                df = us_futures_data_v8.fetch_data(symbol, period='1y')
                if not df.empty:
                    logger.debug(f"✅ {symbol} 캐시 확인/업데이트 완료: {len(df)}개 행")
                    success_count += 1
                else:
                    logger.warning(f"{symbol} 캐시 없음 또는 업데이트 실패")
            except Exception as e:
                logger.error(f"{symbol} 캐시 업데이트 오류: {e}")
        
        return success_count == len(symbols)
        
    except Exception as e:
        logger.error(f"미국 선물 캐시 증분 업데이트 실패: {e}")
        return False

