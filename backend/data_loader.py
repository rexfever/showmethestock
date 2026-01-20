"""
Utility helpers for loading historical price data and universe constituents.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from kiwoom_api import api as kiwoom_api

# Optional dependency: FinanceDataReader (only used when Kiwoom data is unavailable)
try:
    import FinanceDataReader as fdr  # type: ignore

    _HAS_FDR = True
except Exception:  # pragma: no cover - dependency might be absent
    _HAS_FDR = False
DATA_CACHE_ROOT = Path(__file__).resolve().parent / "data_cache"
DATA_CACHE_DIR = DATA_CACHE_ROOT / "ohlcv"
INDICATOR_CACHE_DIR = DATA_CACHE_ROOT / "indicators"
UNIVERSE_CACHE_PATH = DATA_CACHE_ROOT / "universe_cache.json"


def _ensure_cache_dirs() -> None:
    DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    INDICATOR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    UNIVERSE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_universe(limit_per_market: Optional[int] = 300, use_cache: bool = True) -> List[str]:
    """
    Load the trading universe (KOSPI + KOSDAQ).

    Args:
        limit_per_market: Maximum number of symbols to fetch for each market.
        use_cache: Whether to read/write a cached universe file.

    Returns:
        Sorted list of unique tickers.
    """
    _ensure_cache_dirs()
    if use_cache and UNIVERSE_CACHE_PATH.exists():
        try:
            with open(UNIVERSE_CACHE_PATH, "r", encoding="utf-8") as cache_file:
                data = json.load(cache_file)
            if isinstance(data, list) and data:
                return sorted(set(str(code) for code in data))
        except Exception:
            pass

    limit = limit_per_market or 300
    kospi = kiwoom_api.get_top_codes("KOSPI", limit=limit)
    kosdaq = kiwoom_api.get_top_codes("KOSDAQ", limit=limit)
    universe = sorted(set([*kospi, *kosdaq]))

    if use_cache and universe:
        with open(UNIVERSE_CACHE_PATH, "w", encoding="utf-8") as cache_file:
            json.dump(universe, cache_file, ensure_ascii=False, indent=2)
    return universe


def _fetch_from_kiwoom(symbol: str, count: int, base_date: str) -> pd.DataFrame:
    df = kiwoom_api.get_ohlcv(symbol, count=count, base_dt=base_date)
    if df.empty:
        return df
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"].astype(str))
    df = df.sort_values("date").reset_index(drop=True)
    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()
    return df


def _fetch_from_fdr(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    if not _HAS_FDR:
        return pd.DataFrame()
    try:
        df = fdr.DataReader(symbol, start_date, end_date)
        if df.empty:
            return df
        df = df.reset_index().rename(
            columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume", "Date": "date"}
        )
        df["date"] = pd.to_datetime(df["date"])
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna()
        return df
    except Exception:
        return pd.DataFrame()


def _derive_count(start_date: pd.Timestamp, end_date: pd.Timestamp) -> int:
    days = max((end_date - start_date).days, 252)
    # add buffer to account for non-trading days
    return int(days * 1.5)


def load_price_data(
    symbol: str,
    start_date: str,
    end_date: str,
    *,
    cache: bool = True,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Load OHLCV data for a single symbol within the specified date range.

    Data is cached on disk (CSV) to avoid redundant API calls.
    """
    _ensure_cache_dirs()
    cache_path = DATA_CACHE_DIR / f"{symbol}.csv"
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)

    df: Optional[pd.DataFrame] = None
    if cache and cache_path.exists() and not force_refresh:
        try:
            df = pd.read_csv(cache_path, parse_dates=["date"])
        except Exception:
            df = None

    if df is None or force_refresh or df.empty:
        count = _derive_count(start_ts, end_ts)
        df = _fetch_from_kiwoom(symbol, count=count, base_date=end_ts.strftime("%Y%m%d"))
        if df.empty:
            df = _fetch_from_fdr(symbol, start_date, end_date)
        if df.empty:
            return pd.DataFrame()
        if cache:
            df.to_csv(cache_path, index=False)

    mask = (df["date"] >= start_ts) & (df["date"] <= end_ts)
    return df.loc[mask].reset_index(drop=True)


def load_indicator_cache(symbol: str) -> pd.DataFrame:
    """
    Load precomputed indicators for the given symbol if available.
    """
    _ensure_cache_dirs()
    cache_path = INDICATOR_CACHE_DIR / f"{symbol}.csv"
    if not cache_path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(cache_path, parse_dates=["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()


def save_indicator_cache(symbol: str, df: pd.DataFrame) -> None:
    """
    Persist precomputed indicators for reuse.
    """
    if df.empty or "date" not in df.columns:
        return
    _ensure_cache_dirs()
    cache_path = INDICATOR_CACHE_DIR / f"{symbol}.csv"
    try:
        df.to_csv(cache_path, index=False)
    except Exception:
        pass


def load_price_panel(
    universe: List[str],
    start_date: str,
    end_date: str,
    *,
    cache: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Convenience helper to load prices for multiple symbols at once.
    """
    panel: Dict[str, pd.DataFrame] = {}
    for symbol in universe:
        df = load_price_data(symbol, start_date, end_date, cache=cache)
        if df.empty:
            continue
        panel[symbol] = df
    return panel


