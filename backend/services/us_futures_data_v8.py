"""
미국 선물 데이터 수집 v8 - 캐시 통합
"""
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class USFuturesDataV8:
    """미국 선물 데이터 수집 v8 (캐시 통합)"""
    
    def __init__(self):
        self.symbols = {
            'SPY': 'SPY',           # SPDR S&P 500 ETF
            'QQQ': 'QQQ',           # Invesco QQQ ETF
            'ES=F': 'ES=F',         # E-mini S&P 500 Futures
            'NQ=F': 'NQ=F',         # E-mini NASDAQ-100 Futures
            '^VIX': '^VIX',         # VIX Index
            'DX-Y.NYB': 'DX-Y.NYB', # US Dollar Index
        }
    
    def fetch_data(self, symbol: str, period: str = '6mo') -> pd.DataFrame:
        """데이터 수집 (기존 캐시 + 증분 업데이트)"""
        try:
            # CSV 캐시 우선 로드
            csv_df = self._load_csv_cache(symbol)
            
            if not csv_df.empty:
                # 최신 데이터 확인 후 증분 업데이트
                updated_df = self._update_incremental(symbol, csv_df)
                logger.debug(f"{symbol} 캐시 활용: {len(updated_df)}개 행")
                return updated_df
            
            # 캐시 없으면 기본 반환
            logger.warning(f"{symbol} 캐시 없음")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"{symbol} 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def _load_csv_cache(self, symbol: str) -> pd.DataFrame:
        """CSV 캐시 로드"""
        import os
        cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'us_futures')
        # 심볼별 파일명 매핑
        filename_map = {
            '^VIX': '^VIX.csv',
            'DX-Y.NYB': 'DX_Y_NYB.csv'
        }
        filename = filename_map.get(symbol, symbol.replace('=', '_').replace('^', '').replace('-', '_').replace('.', '_') + '.csv')
        csv_path = os.path.join(cache_dir, filename)
        
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
                return df.sort_index()
            except Exception as e:
                logger.warning(f"{symbol} CSV 로드 실패: {e}")
        return pd.DataFrame()
    
    def _update_incremental(self, symbol: str, cached_df: pd.DataFrame) -> pd.DataFrame:
        """증분 업데이트 (Chart API 사용)"""
        try:
            from datetime import datetime, timedelta
            
            # 마지막 날짜 확인
            last_date = cached_df.index[-1]
            days_old = (datetime.now() - last_date).days
            
            # 1일 이상 오래되면 업데이트 시도 (매일 최신 데이터)
            if days_old >= 1:
                new_data = self._fetch_chart_api(symbol)
                if not new_data.empty:
                    # 중복 제거 후 병합
                    combined = pd.concat([cached_df, new_data])
                    combined = combined[~combined.index.duplicated(keep='last')]
                    combined = combined.sort_index()
                    
                    # 새 데이터가 있으면 CSV 업데이트
                    if len(combined) > len(cached_df):
                        self._save_csv_cache(symbol, combined)
                        logger.info(f"{symbol} 증분 업데이트: +{len(combined) - len(cached_df)}개 행")
                    
                    return combined
            
            return cached_df
            
        except Exception as e:
            logger.warning(f"{symbol} 증분 업데이트 실패: {e}")
            return cached_df
    
    def _fetch_chart_api(self, symbol: str) -> pd.DataFrame:
        """Chart API로 최근 데이터 수집"""
        try:
            import requests
            
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return pd.DataFrame()
            
            data = response.json()
            if 'chart' not in data or not data['chart']['result']:
                return pd.DataFrame()
            
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            quotes = result['indicators']['quote'][0]
            
            df_data = []
            for i, ts in enumerate(timestamps):
                df_data.append({
                    'Open': quotes['open'][i],
                    'High': quotes['high'][i], 
                    'Low': quotes['low'][i],
                    'Close': quotes['close'][i],
                    'Volume': quotes['volume'][i] or 0
                })
            
            df = pd.DataFrame(df_data, index=pd.to_datetime(timestamps, unit='s'))
            return df.dropna()
            
        except Exception as e:
            logger.warning(f"{symbol} Chart API 실패: {e}")
            return pd.DataFrame()
    
    def _save_csv_cache(self, symbol: str, df: pd.DataFrame):
        """CSV 캐시 저장"""
        try:
            import os
            cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'us_futures')
            os.makedirs(cache_dir, exist_ok=True)
            
            filename_map = {
                '^VIX': '^VIX.csv',
                'DX-Y.NYB': 'DX_Y_NYB.csv'
            }
            filename = filename_map.get(symbol, symbol.replace('=', '_').replace('^', '').replace('-', '_').replace('.', '_') + '.csv')
            csv_path = os.path.join(cache_dir, filename)
            
            df.to_csv(csv_path)
            
        except Exception as e:
            logger.error(f"{symbol} CSV 저장 실패: {e}")
    
    def get_latest_data(self, symbol: str) -> Optional[dict]:
        """최신 데이터 조회"""
        try:
            df = self.fetch_data(symbol, period='6mo')
            if df.empty:
                return None
            
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            return {
                'symbol': symbol,
                'close': float(latest['Close']),
                'prev_close': float(prev['Close']),
                'change': float(latest['Close'] - prev['Close']),
                'change_pct': float((latest['Close'] / prev['Close'] - 1) * 100),
                'volume': int(latest.get('Volume', 0)),
                'timestamp': latest.name.isoformat() if hasattr(latest.name, 'isoformat') else str(latest.name)
            }
        except Exception as e:
            logger.error(f"{symbol} 최신 데이터 조회 실패: {e}")
            return None
    
    def get_all_latest_data(self) -> dict:
        """모든 심볼의 최신 데이터 조회"""
        results = {}
        for symbol in self.symbols.keys():
            data = self.get_latest_data(symbol)
            if data:
                results[symbol] = data
        return results
    
    def clear_cache(self) -> None:
        """캐시 클리어"""
        regime_cache.clear_cache('us_stocks')
        regime_cache.clear_cache('us_futures')
        logger.info("미국 데이터 캐시 클리어 완료")

def get_cached_data(date: str) -> dict:
    """캐시된 데이터 반환 (v4 호환)"""
    try:
        data = {}
        for symbol in ['SPY', 'QQQ', '^VIX']:
            df = us_futures_data_v8.fetch_data(symbol)
            if not df.empty:
                # 컬럼명 통일 (OHLCV)
                df_renamed = df.rename(columns={
                    'Open': 'open', 'High': 'high', 'Low': 'low', 
                    'Close': 'close', 'Volume': 'volume'
                })
                data[symbol] = df_renamed
            else:
                data[symbol] = pd.DataFrame()
        return data
    except Exception as e:
        logger.error(f"캐시 데이터 로드 실패: {e}")
        return {'SPY': pd.DataFrame(), 'QQQ': pd.DataFrame(), '^VIX': pd.DataFrame()}

# 전역 인스턴스
us_futures_data_v8 = USFuturesDataV8()