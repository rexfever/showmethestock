"""
미국 주식 OHLCV 데이터 수집기 (Chart API 사용)
"""
import pandas as pd
import requests
import logging
from typing import Optional, Dict
from pathlib import Path
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class USStocksData:
    """미국 주식 OHLCV 데이터 수집"""
    
    def __init__(self):
        self.cache_dir = Path("cache/us_stocks_ohlcv")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.request_delay = 0.1  # API 호출 간 딜레이 (초)
        self.last_request_time = 0
    
    def _rate_limit(self):
        """API 호출 속도 제한"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    def get_ohlcv(self, symbol: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
        """
        미국 주식 OHLCV 데이터 가져오기
        
        Args:
            symbol: 종목 심볼 (예: "AAPL")
            count: 가져올 데이터 개수
            base_dt: 기준 날짜 (YYYYMMDD 형식, None이면 최신)
        
        Returns:
            DataFrame with columns: open, high, low, close, volume
            Index: DatetimeIndex
        """
        # 캐시 확인
        cache_path = self.cache_dir / f"{symbol}.csv"
        if cache_path.exists():
            try:
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                df = df.sort_index()
                
                # base_dt가 지정된 경우 필터링 및 캐시 최신성 확인
                if base_dt:
                    base_date = pd.to_datetime(base_dt, format='%Y%m%d')
                    df = df[df.index <= base_date]
                    
                    # 캐시의 최신 날짜가 base_dt보다 오래된 경우 API로 업데이트
                    if not df.empty and df.index[-1] < base_date:
                        logger.debug(f"{symbol} 캐시가 오래됨 (최신: {df.index[-1]}, 요청: {base_date}), API로 업데이트")
                        new_data = self._fetch_chart_api(symbol, period='1y')
                        if not new_data.empty:
                            combined = pd.concat([df, new_data])
                            combined = combined[~combined.index.duplicated(keep='last')]
                            combined = combined.sort_index()
                            combined = combined[combined.index <= base_date]
                            combined.tail(count * 2).to_csv(cache_path)
                            return combined.tail(count)
                
                # 충분한 데이터가 있으면 반환
                if len(df) >= count:
                    return df.tail(count)
                
                # 데이터가 부족하면 API로 업데이트
                if len(df) < count:
                    new_data = self._fetch_chart_api(symbol, period='1y')
                    if not new_data.empty:
                        # 기존 데이터와 병합
                        combined = pd.concat([df, new_data])
                        combined = combined[~combined.index.duplicated(keep='last')]
                        combined = combined.sort_index()
                        
                        # base_dt 필터링
                        if base_dt:
                            base_date = pd.to_datetime(base_dt, format='%Y%m%d')
                            combined = combined[combined.index <= base_date]
                        
                        # 캐시 저장
                        combined.tail(count * 2).to_csv(cache_path)  # 여유분 저장
                        
                        return combined.tail(count)
            except Exception as e:
                logger.warning(f"{symbol} 캐시 로드 실패: {e}")
        
        # 캐시가 없거나 실패한 경우 API 호출
        df = self._fetch_chart_api(symbol, period='1y')
        if not df.empty:
            # base_dt 필터링
            if base_dt:
                base_date = pd.to_datetime(base_dt, format='%Y%m%d')
                df = df[df.index <= base_date]
            
            # 캐시 저장
            try:
                df.tail(count * 2).to_csv(self.cache_dir / f"{symbol}.csv")
            except Exception as e:
                logger.warning(f"{symbol} 캐시 저장 실패: {e}")
            
            return df.tail(count)
        
        return pd.DataFrame()
    
    def _fetch_chart_api(self, symbol: str, period: str = '1y', interval: str = '1d') -> pd.DataFrame:
        """
        Chart API로 데이터 수집
        
        Args:
            symbol: 종목 심볼
            period: 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 간격 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        
        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        self._rate_limit()
        
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                'range': period,
                'interval': interval
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"{symbol} Chart API 호출 실패: {response.status_code}")
                return pd.DataFrame()
            
            data = response.json()
            if 'chart' not in data or not data['chart']['result']:
                logger.warning(f"{symbol} Chart API 응답 형식 오류")
                return pd.DataFrame()
            
            result = data['chart']['result'][0]
            
            # 타임스탬프와 가격 데이터 추출
            timestamps = result.get('timestamp', [])
            quotes = result.get('indicators', {}).get('quote', [{}])[0]
            
            if not timestamps or not quotes:
                logger.warning(f"{symbol} Chart API 데이터 없음")
                return pd.DataFrame()
            
            # DataFrame 생성
            df_data = []
            for i, ts in enumerate(timestamps):
                if i < len(quotes.get('open', [])) and quotes['open'][i] is not None:
                    df_data.append({
                        'open': quotes['open'][i],
                        'high': quotes['high'][i],
                        'low': quotes['low'][i],
                        'close': quotes['close'][i],
                        'volume': quotes.get('volume', [0] * len(timestamps))[i] or 0
                    })
            
            if not df_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(df_data, index=pd.to_datetime(timestamps[:len(df_data)], unit='s'))
            df = df.sort_index()
            df = df.dropna(subset=['open', 'high', 'low', 'close'])
            
            logger.debug(f"{symbol} Chart API 성공: {len(df)}개 행")
            return df
            
        except Exception as e:
            logger.error(f"{symbol} Chart API 오류: {e}")
            return pd.DataFrame()
    
    def get_stock_quote(self, symbol: str) -> Optional[Dict]:
        """
        실시간 주가 정보 가져오기
        
        Args:
            symbol: 종목 심볼
        
        Returns:
            {
                "symbol": "AAPL",
                "current_price": 150.0,
                "change": 1.5,
                "change_rate": 1.01,
                "volume": 1000000
            }
        """
        self._rate_limit()
        
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            if 'chart' not in data or not data['chart']['result']:
                return None
            
            result = data['chart']['result'][0]
            meta = result.get('meta', {})
            quotes = result.get('indicators', {}).get('quote', [{}])[0]
            
            current_price = meta.get('regularMarketPrice') or meta.get('previousClose', 0)
            prev_close = meta.get('previousClose', 0)
            change = current_price - prev_close if prev_close > 0 else 0
            change_rate = (change / prev_close * 100) if prev_close > 0 else 0
            
            return {
                'symbol': symbol,
                'current_price': float(current_price),
                'prev_close': float(prev_close),
                'change': float(change),
                'change_rate': float(change_rate),
                'volume': int(meta.get('regularMarketVolume', 0))
            }
            
        except Exception as e:
            logger.error(f"{symbol} 실시간 주가 조회 실패: {e}")
            return None

# 전역 인스턴스
us_stocks_data = USStocksData()

