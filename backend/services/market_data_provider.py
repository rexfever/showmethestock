"""
Market Data Provider - 시장 데이터 공급 레이어
Kiwoom API 기반 데이터 수집
"""
import logging
import pickle
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

class BaseMarketDataProvider(ABC):
    """Market Data Provider 인터페이스"""
    
    @abstractmethod
    def get_ohlcv_korea(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """한국 종목 OHLCV 데이터 조회"""
        pass
    
    @abstractmethod
    def get_ohlcv_us(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """미국 종목 OHLCV 데이터 조회"""
        pass
    
    @abstractmethod
    def get_vix(self, start: str, end: str) -> pd.DataFrame:
        """VIX 데이터 조회"""
        pass

class KiwoomMarketDataProvider(BaseMarketDataProvider):
    """Kiwoom API 기반 Market Data Provider"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_db = self.cache_dir / "market_data.db"
        self._init_cache_db()
        
        # US 종목 매핑 (Kiwoom에서 지원하는 미국 종목)
        self.us_symbol_map = {
            "SPY": "SPY",
            "QQQ": "QQQ", 
            "^VIX": "VIX",
            "^TNX": "TNX",
            "ES=F": "ES",
            "NQ=F": "NQ",
            "VX=F": "VX",
            "KRW=X": "USDKRW"
        }
    
    def _init_cache_db(self):
        """캐시 DB 초기화"""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ohlcv_cache (
                        symbol TEXT,
                        date_start TEXT,
                        date_end TEXT,
                        market TEXT,
                        data BLOB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (symbol, date_start, date_end, market)
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cache_symbol_date 
                    ON ohlcv_cache(symbol, date_start, date_end)
                """)
        except Exception as e:
            logger.warning(f"캐시 DB 초기화 실패: {e}")
    
    def get_ohlcv_korea(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """한국 종목 OHLCV 데이터 조회"""
        try:
            from kiwoom_api import api
            
            # 날짜 범위 계산
            start_dt = datetime.strptime(start, '%Y%m%d')
            end_dt = datetime.strptime(end, '%Y%m%d')
            days_diff = (end_dt - start_dt).days + 10  # 여유분 추가
            
            # Kiwoom API로 데이터 조회
            df = api.get_ohlcv(symbol, count=min(days_diff, 500), base_dt=end)
            
            if df.empty:
                logger.warning(f"한국 종목 데이터 없음: {symbol}")
                return pd.DataFrame()
            
            # 날짜 필터링
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            start_dt = pd.to_datetime(start, format='%Y%m%d')
            end_dt = pd.to_datetime(end, format='%Y%m%d')
            df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
            
            logger.info(f"한국 종목 데이터 조회 완료: {symbol}, {len(df)}개 행")
            return df
            
        except Exception as e:
            logger.error(f"한국 종목 데이터 조회 실패 {symbol}: {e}")
            return pd.DataFrame()
    
    def get_ohlcv_us(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """미국 종목 OHLCV 데이터 조회 (Yahoo Finance CSV 사용)"""
        try:
            from services.us_futures_data import us_futures_data
            
            # Yahoo Finance CSV로 데이터 조회
            df = us_futures_data.fetch_csv(symbol)
            
            if df.empty:
                logger.warning(f"미국 종목 데이터 없음: {symbol}")
                return pd.DataFrame()
            
            # 날짜 필터링
            start_dt = pd.to_datetime(start, format='%Y%m%d')
            end_dt = pd.to_datetime(end, format='%Y%m%d')
            df = df[(df.index >= start_dt) & (df.index <= end_dt)]
            
            logger.info(f"미국 종목 데이터 조회 완료: {symbol}, {len(df)}개 행")
            return df
            
        except Exception as e:
            logger.error(f"미국 종목 데이터 조회 실패 {symbol}: {e}")
            return pd.DataFrame()
    
    def get_vix(self, start: str, end: str) -> pd.DataFrame:
        """VIX 데이터 조회"""
        return self.get_ohlcv_us("^VIX", start, end)
    
    def get_us_prev_snapshot(self, date: str) -> Dict[str, Any]:
        """미국 전일 시장 스냅샷 조회"""
        try:
            # 60일 전부터 데이터 조회
            end_date = datetime.strptime(date, '%Y%m%d')
            start_date = end_date - timedelta(days=90)
            
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            
            result = {
                "spy_r1": 0.0, "spy_r3": 0.0, "spy_r5": 0.0,
                "qqq_r1": 0.0, "qqq_r3": 0.0, "qqq_r5": 0.0,
                "vix": 20.0, "vix_change": 0.0,
                "ust10y_change": 0.0,
                "valid": False
            }
            
            # SPY 데이터
            spy_df = self.get_ohlcv_us("SPY", start_str, end_str)
            if not spy_df.empty and len(spy_df) >= 6:
                spy_prices = spy_df['Close'].values
                result["spy_r1"] = (spy_prices[-1] / spy_prices[-2] - 1) if len(spy_prices) >= 2 else 0.0
                result["spy_r3"] = (spy_prices[-1] / spy_prices[-4] - 1) if len(spy_prices) >= 4 else 0.0
                result["spy_r5"] = (spy_prices[-1] / spy_prices[-6] - 1) if len(spy_prices) >= 6 else 0.0
            
            # QQQ 데이터
            qqq_df = self.get_ohlcv_us("QQQ", start_str, end_str)
            if not qqq_df.empty and len(qqq_df) >= 6:
                qqq_prices = qqq_df['Close'].values
                result["qqq_r1"] = (qqq_prices[-1] / qqq_prices[-2] - 1) if len(qqq_prices) >= 2 else 0.0
                result["qqq_r3"] = (qqq_prices[-1] / qqq_prices[-4] - 1) if len(qqq_prices) >= 4 else 0.0
                result["qqq_r5"] = (qqq_prices[-1] / qqq_prices[-6] - 1) if len(qqq_prices) >= 6 else 0.0
            
            # VIX 데이터
            vix_df = self.get_vix(start_str, end_str)
            if not vix_df.empty and len(vix_df) >= 2:
                vix_prices = vix_df['Close'].values
                result["vix"] = float(vix_prices[-1])
                result["vix_change"] = (vix_prices[-1] / vix_prices[-2] - 1) if len(vix_prices) >= 2 else 0.0
            
            result["valid"] = True
            logger.info(f"미국 시장 스냅샷 조회 완료: SPY r1={result['spy_r1']:.3f}, VIX={result['vix']:.1f}")
            
            return result
            
        except Exception as e:
            logger.error(f"미국 시장 스냅샷 조회 실패: {e}")
            return result
    
    def get_us_preopen_snapshot(self, date: str) -> Dict[str, Any]:
        """미국 pre-open 스냅샷 조회"""
        result = {
            "es_change": 0.0,
            "nq_change": 0.0,
            "vix_fut_change": 0.0,
            "usdkrw_change": 0.0,
            "valid": False
        }
        
        try:
            # 선물 데이터는 실시간에서만 의미가 있으므로 기본값 반환
            logger.info("Pre-open 데이터는 실시간 모드에서만 유효")
            return result
            
        except Exception as e:
            logger.error(f"Pre-open 스냅샷 조회 실패: {e}")
            return result

# 전역 인스턴스
market_data_provider = KiwoomMarketDataProvider()