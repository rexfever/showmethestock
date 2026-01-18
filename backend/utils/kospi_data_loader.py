"""
KOSPI 지수 데이터 로더 (pykrx 우선, FinanceDataReader fallback)
"""
import pandas as pd
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or isinstance(df.index, pd.DatetimeIndex):
        return df
    df = df.copy()
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        return df.set_index('date')
    if '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'])
        return df.set_index('날짜')
    try:
        df.index = pd.to_datetime(df.index)
    except Exception:
        pass
    return df

def get_kospi_data(date: Optional[str] = None, days: int = 30) -> pd.DataFrame:
    """
    KOSPI 지수 데이터 조회 (우선순위: pykrx > FinanceDataReader > 캐시 > 키움 API ETF)
    
    Args:
        date: 기준 날짜 (YYYYMMDD 형식, None이면 오늘)
        days: 가져올 데이터 일수
    
    Returns:
        DataFrame with columns: open, high, low, close, volume
        Index: DatetimeIndex
    """
    if date:
        end_date = pd.to_datetime(date, format='%Y%m%d')
    else:
        end_date = pd.to_datetime(datetime.now())
    
    start_date = (end_date - pd.Timedelta(days=days)).date()
    end_date_date = end_date.date()
    
    # 1. pykrx 시도 (한국거래소 공식 데이터, 정확도 높음, 당일 데이터 제공 가능)
    try:
        from pykrx import stock
        
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date_date.strftime('%Y%m%d')
        
        df = stock.get_index_ohlcv_by_date(
            start_date_str, end_date_str, "1001", name_display=False
        )  # KOSPI 지수 코드: 1001
        
        if not df.empty:
            # 컬럼명 변환 (한국어 → 영어)
            column_mapping = {
                '시가': 'open',
                '고가': 'high',
                '저가': 'low',
                '종가': 'close',
                '거래량': 'volume'
            }
            df = df.rename(columns=column_mapping)
            
            # 필요한 컬럼만 선택
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            df = df[[col for col in required_cols if col in df.columns]]
            
            # 인덱스를 날짜로 설정
            if not isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
                if '날짜' in df.columns:
                    df['날짜'] = pd.to_datetime(df['날짜'])
                    df = df.set_index('날짜')
            
            # 날짜 필터링
            if date:
                target_date = pd.to_datetime(date, format='%Y%m%d')
                df = df[df.index <= target_date]
            
            # 데이터 검증
            if not df.empty:
                latest_close = df.iloc[-1]['close']
                if not (2000 <= latest_close <= 4000):
                    logger.warning(f"KOSPI 지수 값이 비정상적: {latest_close:.2f} (예상 범위: 2000~4000)")
            
            df.attrs["source"] = "pykrx"
            logger.debug(f"✅ pykrx로 KOSPI 지수 데이터 로드: {len(df)}개 행")
            return df
        else:
            raise Exception("pykrx 데이터가 비어있음")
            
    except ImportError:
        logger.debug("pykrx가 설치되지 않음. FinanceDataReader 사용")
    except Exception as e:
        logger.debug(f"pykrx 사용 실패: {e}, FinanceDataReader 사용")
    
    # 2. FinanceDataReader 시도 (fallback)
    try:
        import FinanceDataReader as fdr
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date_date.strftime('%Y-%m-%d')
        
        df = fdr.DataReader('KS11', start_date_str, end_date_str)
        
        if not df.empty:
            # 컬럼명 소문자로 통일
            df.columns = df.columns.str.lower()
            
            # 필요한 컬럼만 선택
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            df = df[[col for col in required_cols if col in df.columns]]
            
            # 날짜 필터링
            if date:
                target_date = pd.to_datetime(date, format='%Y%m%d')
                df = df[df.index <= target_date]
            
            # 데이터 검증
            if not df.empty:
                latest_close = df.iloc[-1]['close']
                if not (2000 <= latest_close <= 4000):
                    logger.warning(f"KOSPI 지수 값이 비정상적: {latest_close:.2f} (예상 범위: 2000~4000)")
            
            df.attrs["source"] = "fdr"
            logger.debug(f"✅ FinanceDataReader로 KOSPI 지수 데이터 로드: {len(df)}개 행")
            return df
        else:
            raise Exception("FinanceDataReader 데이터가 비어있음")
            
    except ImportError:
        logger.debug("FinanceDataReader가 설치되지 않음. 캐시 사용")
    except Exception as e:
        logger.debug(f"FinanceDataReader 사용 실패: {e}, 캐시 사용")
    
    # 3. 캐시 사용 (이미 실제 지수 데이터로 교체됨)
    try:
        cache_path = Path(__file__).resolve().parent.parent / "data_cache" / "kospi200_ohlcv.pkl"
        if cache_path.exists():
            df = pd.read_pickle(cache_path)
            if not df.empty:
                df = _ensure_datetime_index(df)
                if date:
                    target_date = pd.to_datetime(date, format='%Y%m%d')
                    df = df[df.index <= target_date].tail(days)
                else:
                    df = df.tail(days)
                
                df.attrs["source"] = "cache"
                logger.debug(f"✅ 캐시로 KOSPI 지수 데이터 로드: {len(df)}개 행")
                return df
    except Exception as e:
        logger.warning(f"캐시 로드 실패: {e}")
    
    # 4. 키움 API ETF 사용 (최후의 수단, 부정확)
    try:
        from kiwoom_api import api
        df = api.get_ohlcv("069500", days, date)  # KOSPI200 ETF
        if not df.empty:
            df = _ensure_datetime_index(df)
            df.attrs["source"] = "etf"
            logger.warning("⚠️ KOSPI 지수 대신 ETF(069500) 사용 - 정확도 저하 가능")
            return df
    except Exception as e:
        logger.error(f"키움 API ETF 사용 실패: {e}")
    
    logger.error("❌ KOSPI 지수 데이터를 가져올 수 없음")
    return pd.DataFrame()
