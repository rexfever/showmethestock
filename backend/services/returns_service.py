"""
수익률 계산 서비스
"""
import pandas as pd
import concurrent.futures
from typing import Dict, List, Optional
from kiwoom_api import api
from date_helper import get_kst_now


def _get_cached_ohlcv(ticker: str, count: int, base_dt: str = None) -> str:
    """OHLCV 데이터 조회 (api.get_ohlcv() 내부 TTL 캐시 및 디스크 캐시 사용)
    
    주의: @lru_cache를 제거하여 TTL 기반 캐시가 제대로 작동하도록 함
    api.get_ohlcv() 내부에서 TTL 기반 캐시 및 디스크 캐시를 사용하므로 중복 캐싱 불필요
    """
    try:
        # 디스크 캐시 우선 확인 (키움 API 인증 실패 시에도 사용 가능)
        df = api.get_ohlcv(ticker, count, base_dt)
        if df.empty:
            return ""
        return df.to_json(orient='records')
    except Exception as e:
        # API 실패 시에도 디스크 캐시에서 로드 시도
        try:
            from pathlib import Path
            import pickle
            cache_dir = Path("cache/ohlcv")
            if base_dt:
                cache_file = cache_dir / f"{ticker}_{count}_{base_dt}.pkl"
                if cache_file.exists():
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                        df, _ = cached_data
                        if not df.empty:
                            return df.to_json(orient='records')
        except:
            pass
        return ""


# 캐시 클리어 함수 (api.get_ohlcv() 내부 캐시는 별도로 관리됨)
def clear_cache():
    """캐시를 클리어합니다 (현재는 사용하지 않음, api.get_ohlcv() 내부 캐시 사용)"""
    pass


def _parse_cached_ohlcv(json_str: str) -> pd.DataFrame:
    """캐시된 JSON을 DataFrame으로 변환"""
    if not json_str:
        return pd.DataFrame()
    try:
        return pd.read_json(json_str, orient='records')
    except Exception:
        return pd.DataFrame()


def calculate_returns(ticker: str, scan_date: str, current_date: str = None, scan_price_from_db: float = None) -> Optional[Dict]:
    """
    특정 종목의 수익률 계산 (캐시 적용)
    
    Args:
        ticker: 종목 코드
        scan_date: 스캔 날짜 (YYYYMMDD)
        current_date: 현재 날짜 (YYYYMMDD), None이면 오늘
        scan_price_from_db: DB에 저장된 스캔일 종가 (있으면 우선 사용)
    """
    try:
        if current_date is None:
            # KST 기준 오늘 날짜 사용
            current_date = get_kst_now().strftime('%Y%m%d')
        
        # 날짜 형식 처리: 이미 YYYYMMDD 형식
        scan_date_formatted = scan_date
        
        # 스캔일 종가 결정: DB 값이 있으면 우선 사용, 없으면 API로 조회
        if scan_price_from_db and scan_price_from_db > 0:
            scan_price = float(scan_price_from_db)
        else:
            # 스캔 날짜 데이터 가져오기
            df_scan = _parse_cached_ohlcv(_get_cached_ohlcv(ticker, 1, scan_date_formatted))
            
            if df_scan.empty:
                print(f"스캔 날짜 데이터 없음: {ticker} {scan_date}")
                return None
                
            scan_price = float(df_scan.iloc[-1]['close'])
        
        # 현재 날짜 데이터 가져오기
        current_date_formatted = current_date
        df_current = _parse_cached_ohlcv(_get_cached_ohlcv(ticker, 1, current_date_formatted))
        
        if df_current.empty:
            return None
            
        current_price = float(df_current.iloc[-1]['close'])
        
        # 날짜 형식 통일 (YYYYMMDD -> datetime)
        scan_date_dt = pd.to_datetime(scan_date_formatted, format='%Y%m%d')
        current_date_dt = pd.to_datetime(current_date_formatted, format='%Y%m%d')
        days_diff = (current_date_dt - scan_date_dt).days
        
        # 스캔일과 현재일이 같은 경우 (당일 스캔)
        if days_diff == 0:
            # 당일 스캔인 경우, 스캔일 종가와 현재가가 같으면 0% 반환
            if abs(current_price - scan_price) < 0.01:  # 가격 차이가 거의 없으면
                return {
                    'current_return': 0.0,
                    'max_return': 0.0,
                    'min_return': 0.0,
                    'scan_price': scan_price,
                    'current_price': current_price,
                    'max_price': scan_price,
                    'min_price': scan_price,
                    'days_elapsed': 0
                }
            else:
                # 가격 차이가 있으면 수익률 계산
                current_return = ((current_price - scan_price) / scan_price) * 100
                return {
                    'current_return': round(current_return, 2),
                    'max_return': round(current_return, 2),
                    'min_return': round(current_return, 2),
                    'scan_price': scan_price,
                    'current_price': current_price,
                    'max_price': max(scan_price, current_price),
                    'min_price': min(scan_price, current_price),
                    'days_elapsed': 0
                }
        
        # 스캔일부터 현재까지의 모든 데이터 가져오기 (최고/최저가 계산용)
        period_count = min(days_diff + 10, 100)  # 여유분 포함
        
        df_period = _parse_cached_ohlcv(_get_cached_ohlcv(ticker, period_count, current_date_formatted))
        if df_period.empty:
            # 기간 데이터가 없으면 스캔일과 현재일 데이터만으로 계산
            if scan_price > 0:
                current_return = ((current_price - scan_price) / scan_price) * 100
                return {
                    'current_return': round(current_return, 2),
                    'max_return': round(current_return, 2),
                    'min_return': round(current_return, 2),
                    'scan_price': scan_price,
                    'current_price': current_price,
                    'max_price': max(scan_price, current_price),
                    'min_price': min(scan_price, current_price),
                    'days_elapsed': days_diff
                }
            return None
        
        df_period['date_dt'] = pd.to_datetime(df_period['date'], format='%Y%m%d')
        
        # 스캔일부터 현재일까지의 데이터만 필터링
        df_period_filtered = df_period[
            (df_period['date_dt'] >= scan_date_dt) & 
            (df_period['date_dt'] <= current_date_dt)
        ]
        
        if df_period_filtered.empty:
            # 필터링된 데이터가 없으면 스캔일과 현재일 데이터만으로 계산
            if scan_price > 0:
                current_return = ((current_price - scan_price) / scan_price) * 100
                return {
                    'current_return': round(current_return, 2),
                    'max_return': round(current_return, 2),
                    'min_return': round(current_return, 2),
                    'scan_price': scan_price,
                    'current_price': current_price,
                    'max_price': max(scan_price, current_price),
                    'min_price': min(scan_price, current_price),
                    'days_elapsed': days_diff
                }
            return None
        
        # 최고가/최저가 계산 (현재가도 포함, 0 이하 값 제외)
        high_prices = []
        low_prices = []
        
        for _, row in df_period_filtered.iterrows():
            high_val = row['high'] if row['high'] > 0 else row['close']
            low_val = row['low'] if row['low'] > 0 else row['close']
            high_prices.append(high_val)
            low_prices.append(low_val)
        
        all_prices = high_prices + low_prices + [current_price]
        # 0 이하 값 제거
        all_prices = [p for p in all_prices if p > 0]
        
        if not all_prices:
            return None
            
        max_price = max(all_prices)
        min_price = min(all_prices)
        
        # 수익률 계산
        current_return = ((current_price - scan_price) / scan_price) * 100
        max_return = ((max_price - scan_price) / scan_price) * 100
        min_return = ((min_price - scan_price) / scan_price) * 100
        
        days_elapsed = (current_date_dt - scan_date_dt).days
        
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


def calculate_returns_batch(tickers: List[str], scan_date: str, current_date: str = None, scan_prices: Dict[str, float] = None) -> Dict[str, Dict]:
    """
    여러 종목의 수익률을 병렬로 계산
    
    Args:
        tickers: 종목 코드 리스트
        scan_date: 스캔 날짜 (YYYYMMDD)
        current_date: 현재 날짜 (YYYYMMDD), None이면 오늘
        scan_prices: 스캔일 종가 딕셔너리 {ticker: price} (DB의 close_price 사용)
    """
    if current_date is None:
        # KST 기준 오늘 날짜 사용
        current_date = get_kst_now().strftime('%Y%m%d')
    
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ticker = {
            executor.submit(calculate_returns, ticker, scan_date, current_date, scan_prices.get(ticker) if scan_prices else None): ticker 
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
