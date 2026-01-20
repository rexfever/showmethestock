"""
미국 시장 데이터 로딩 헬퍼 (Global Regime Model v3용)
Kiwoom API 기반으로 변경 (yfinance 제거)
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)

TICKERS = ["SPY", "QQQ", "^VIX", "^TNX"]

def get_us_prev_snapshot(date: str) -> Dict[str, Any]:
    """
    date 기준으로, 그 '전날' 미국 정규장 데이터를 가져온다.
    - Kiwoom API 기반 (yfinance 제거)
    - SPY/QQQ r1/r3/r5 계산
    - VIX 현재값 및 변화율
    - US10Y 수익률 변화율
    """
    try:
        from .market_data_provider import market_data_provider
        return market_data_provider.get_us_prev_snapshot(date)
        
    except Exception as e:
        logger.error(f"US market data fetch failed: {e}")
        return {
            "spy_r1": 0.0, "spy_r3": 0.0, "spy_r5": 0.0,
            "qqq_r1": 0.0, "qqq_r3": 0.0, "qqq_r5": 0.0,
            "vix": 20.0, "vix_change": 0.0,
            "ust10y_change": 0.0,
            "valid": False
        }

def get_us_preopen_snapshot(date: str) -> Dict[str, Any]:
    """
    mode='live' 에서만 쓸 예정.
    - ES futures, NQ futures, VIX futures, USDKRW
    - Kiwoom API 기반 (yfinance 제거)
    - 전일 종가 대비 수익률 계산
    """
    try:
        from .market_data_provider import market_data_provider
        return market_data_provider.get_us_preopen_snapshot(date)
        
    except Exception as e:
        logger.error(f"US preopen data fetch failed: {e}")
        return {
            "es_change": 0.0,
            "nq_change": 0.0, 
            "vix_fut_change": 0.0,
            "usdkrw_change": 0.0,
            "valid": False
        }