"""
수익률 계산 서비스
"""
import pandas as pd
import concurrent.futures
from typing import Dict, List, Optional
from functools import lru_cache
from kiwoom_api import api


@lru_cache(maxsize=1000)
def _get_cached_ohlcv(ticker: str, count: int, base_dt: str = None) -> str:
    """캐시된 OHLCV 데이터 조회"""
    try:
        df = api.get_ohlcv(ticker, count, base_dt)
        if df.empty:
            return ""
        return df.to_json(orient='records')
    except Exception:
        return ""


def _parse_cached_ohlcv(json_str: str) -> pd.DataFrame:
    """캐시된 JSON을 DataFrame으로 변환"""
    if not json_str:
        return pd.DataFrame()
    try:
        return pd.read_json(json_str, orient='records')
    except Exception:
        return pd.DataFrame()


def calculate_returns(ticker: str, scan_date: str, current_date: str = None) -> Optional[Dict]:
    """특정 종목의 수익률 계산 (캐시 적용)"""
    try:
        if current_date is None:
            from datetime import datetime
            # 실제 현재 날짜 사용 (2025-10-10)
            current_date = '2025-10-10'
        
        # 날짜 형식 처리: YYYY-MM-DD -> YYYYMMDD
        if '-' in scan_date:
            scan_date_formatted = scan_date.replace('-', '')
        else:
            scan_date_formatted = scan_date
            
        df_scan = _parse_cached_ohlcv(_get_cached_ohlcv(ticker, 1, scan_date_formatted))
        
        if df_scan.empty:
            print(f"스캔 날짜 데이터 없음: {ticker} {scan_date}")
            return None
            
        scan_price = float(df_scan.iloc[-1]['close'])
        
        # 현재 날짜 데이터 직접 가져오기
        current_date_formatted = current_date.replace('-', '')
        df_current = _parse_cached_ohlcv(_get_cached_ohlcv(ticker, 1, current_date_formatted))
        
        if df_current.empty:
            return None
            
        current_price = float(df_current.iloc[-1]['close'])
        
        # 기간 데이터 가져오기 (최고/최저가 계산용)
        df_period = _parse_cached_ohlcv(_get_cached_ohlcv(ticker, 100))
        if df_period.empty:
            return None
            
        # 날짜 형식 통일 (YYYYMMDD -> datetime)
        scan_date_dt = pd.to_datetime(scan_date_formatted, format='%Y%m%d')
        df_period['date_dt'] = pd.to_datetime(df_period['date'], format='%Y%m%d')
        df_period_filtered = df_period[df_period['date_dt'] >= scan_date_dt]
        
        if df_period_filtered.empty:
            return None
        
        high_prices = df_period_filtered['high'].where(df_period_filtered['high'] > 0, df_period_filtered['close'])
        low_prices = df_period_filtered['low'].where(df_period_filtered['low'] > 0, df_period_filtered['close'])
        
        max_price = float(high_prices.max())
        min_price = float(low_prices.min())
        
        current_return = ((current_price - scan_price) / scan_price) * 100
        max_return = ((max_price - scan_price) / scan_price) * 100
        min_return = ((min_price - scan_price) / scan_price) * 100
        
        days_elapsed = (pd.to_datetime(current_date) - scan_date_dt).days
        
        return {
            'current_return': round(current_return, 2),
            'max_return': round(max_return, 2),
            'min_return': round(min_return, 2),
            'scan_price': scan_price,
            'current_price': current_price,
            'max_price': max_price,
            'min_price': min_price,
            'days_elapsed': days_elapsed
        }
        
    except Exception as e:
        print(f"수익률 계산 오류 ({ticker}): {e}")
        return None


def calculate_returns_batch(tickers: List[str], scan_date: str, current_date: str = None) -> Dict[str, Dict]:
    """여러 종목의 수익률을 병렬로 계산"""
    if current_date is None:
        from datetime import datetime
        # 실제 현재 날짜 사용 (2025-10-10)
        current_date = '2025-10-10'
    
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ticker = {
            executor.submit(calculate_returns, ticker, scan_date, current_date): ticker 
            for ticker in tickers
        }
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result()
                if result is not None:
                    results[ticker] = result
            except Exception as e:
                print(f"수익률 계산 오류 ({ticker}): {e}")
                results[ticker] = None
    
    return results
