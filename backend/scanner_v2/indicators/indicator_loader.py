from __future__ import annotations

"""
scanner_v2.indicators.indicator_loader

기존 data_loader / indicators 모듈을 재사용하여
OHLCV + 핵심 기술지표를 한 번에 로딩하는 래퍼.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

import numpy as np
import pandas as pd

from data_loader import load_price_data
from indicators import ema, macd, rsi_standard, atr


@dataclass
class IndicatorConfig:
    """indicator_loader에서 사용하는 기본 설정."""

    ema_fast: int = 20
    ema_mid: int = 60
    ema_long1: int = 120
    ema_long2: int = 200
    rsi_period: int = 14
    atr_period: int = 14


CONFIG = IndicatorConfig()


def _compute_relative_strength(
    symbol_df: pd.DataFrame, benchmark_df: pd.DataFrame
) -> pd.Series:
    """
    간단한 상대 강도(RS) 계산:
    - 각 날짜별 symbol_close / benchmark_close 비율의 20일 이동평균을 사용.
    """
    if symbol_df.empty or benchmark_df.empty:
        return pd.Series(index=symbol_df.index, dtype=float)

    sym = symbol_df.set_index("date")
    bench = benchmark_df.set_index("date")
    joined = sym[["close"]].join(
        bench[["close"]].rename(columns={"close": "bench_close"}), how="left"
    )
    ratio = joined["close"] / joined["bench_close"].replace(0, np.nan)
    rs = ratio.rolling(20).mean()
    rs = rs.reindex(sym.index)
    rs.name = "RS"
    return rs


def load_indicator_df(symbol: str, end_date: str, lookback: int = 120) -> pd.DataFrame:
    """
    심볼별로 end_date까지 lookback일 만큼의
    OHLCV + EMA/RSI/MACD/ATR/RS 등을 포함한 데이터프레임을 반환한다.

    인덱스는 정렬된 일자, 필수 컬럼:
      - date, open, high, low, close, volume
      - EMA20, EMA60, EMA120, EMA200
      - RSI (14)
      - MACD_LINE, MACD_SIGNAL, MACD_HIST
      - ATR_PCT
      - RS (KOSPI200(069500) 대비 상대 강도)
    """
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    start_dt = end_dt - timedelta(days=lookback * 2)  # 여유 버퍼
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date_str = end_dt.strftime("%Y-%m-%d")

    # 1) 심볼 OHLCV
    df = load_price_data(symbol, start_date, end_date_str, cache=True)
    if df.empty:
        return pd.DataFrame()
    df = df.sort_values("date").reset_index(drop=True)

    # 2) EMA
    close = df["close"].astype(float)
    df["EMA20"] = ema(close, CONFIG.ema_fast)
    df["EMA60"] = ema(close, CONFIG.ema_mid)
    df["EMA120"] = ema(close, CONFIG.ema_long1)
    df["EMA200"] = ema(close, CONFIG.ema_long2)

    # 3) RSI
    df["RSI"] = rsi_standard(close, CONFIG.rsi_period)

    # 4) MACD
    macd_line, signal_line, osc = macd(close, 12, 26, 9)
    df["MACD_LINE"] = macd_line
    df["MACD_SIGNAL"] = signal_line
    df["MACD_HIST"] = osc

    # 5) ATR 및 ATR_PCT
    atr_series = atr(df["high"].astype(float), df["low"].astype(float), close, CONFIG.atr_period)
    df["ATR"] = atr_series
    df["ATR_PCT"] = (df["ATR"] / close.replace(0, np.nan)) * 100.0

    # 6) 상대 강도 RS (KOSPI200 069500 기준)
    try:
        benchmark_df = load_price_data("069500", start_date, end_date_str, cache=True)
    except Exception:
        benchmark_df = pd.DataFrame()
    df["RS"] = _compute_relative_strength(df, benchmark_df)

    # 필요 범위로 슬라이스 (lookback일)
    cutoff_dt = end_dt - timedelta(days=lookback * 1.2)
    df = df[df["date"] >= cutoff_dt].reset_index(drop=True)

    return df


