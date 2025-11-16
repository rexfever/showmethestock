"""
Backtesting engine for the ScreenerV2 strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

from data_loader import load_price_data
from screener_v2 import ScreenerParams, ScreenerV2


@dataclass
class TradeResult:
    """Single simulated trade."""

    symbol: str
    signal_date: pd.Timestamp
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    return_pct: float
    hold_days: int
    signal_step: Optional[int]
    step0_score: float
    step2_score: float
    signals_true: int


def run_backtest_for_symbol(
    symbol: str,
    prices: pd.DataFrame,
    screener: ScreenerV2,
    *,
    hold_days: int = 5,
    exit_mode: str = "close",
) -> List[TradeResult]:
    """
    Simulate trades for a single symbol.
    """
    evaluated = screener.evaluate(prices)
    if evaluated.empty:
        return []

    evaluated = evaluated.reset_index(drop=True)
    trades: List[TradeResult] = []
    idx = 0

    while idx < len(evaluated) - 1:
        row = evaluated.iloc[idx]
        if bool(row["signal"]):
            entry_idx = idx + 1
            exit_idx = entry_idx + hold_days - 1
            if exit_idx >= len(evaluated):
                break

            entry_row = evaluated.iloc[entry_idx]
            exit_row = evaluated.iloc[exit_idx]
            next_open_idx = min(exit_idx + 1, len(evaluated) - 1)

            entry_price = float(entry_row["open"])
            if exit_mode == "next_open":
                exit_price = float(evaluated.iloc[next_open_idx]["open"])
                exit_date = evaluated.iloc[next_open_idx]["date"]
            else:
                exit_price = float(exit_row["close"])
                exit_date = exit_row["date"]

            if entry_price <= 0 or exit_price <= 0:
                idx += 1
                continue

            return_pct = (exit_price - entry_price) / entry_price * 100
            trades.append(
                TradeResult(
                    symbol=symbol,
                    signal_date=row["date"],
                    entry_date=entry_row["date"],
                    exit_date=exit_date,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    return_pct=return_pct,
                    hold_days=hold_days,
                    signal_step=int(row["signal_step"]) if not np.isnan(row["signal_step"]) else None,
                    step0_score=float(row["step0_score"]),
                    step2_score=float(row["step2_score"]),
                    signals_true=int(row["signals_true"]),
                )
            )
            idx = exit_idx + 1
        else:
            idx += 1
    return trades


def run_backtest_for_universe(
    universe: Sequence[str],
    params: ScreenerParams,
    start_date: str,
    end_date: str,
    *,
    price_cache: Optional[Dict[str, pd.DataFrame]] = None,
    price_loader: Callable[[str, str, str], pd.DataFrame] = load_price_data,
    hold_days: int = 5,
    exit_mode: str = "close",
) -> List[TradeResult]:
    """
    Run the screener for every symbol in the universe and aggregate trades.
    """
    trades: List[TradeResult] = []
    screener = ScreenerV2(params)
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)

    for symbol in universe:
        if price_cache and symbol in price_cache:
            df = price_cache[symbol]
            mask = (df["date"] >= start_ts) & (df["date"] <= end_ts)
            prices = df.loc[mask].reset_index(drop=True)
        else:
            prices = price_loader(symbol, start_date, end_date)

        if prices.empty:
            continue
        symbol_trades = run_backtest_for_symbol(
            symbol,
            prices,
            screener,
            hold_days=hold_days,
            exit_mode=exit_mode,
        )
        trades.extend(symbol_trades)

    return trades


def calculate_metrics(
    trades: Iterable[TradeResult],
    *,
    risk_free_rate: float = 0.02,
) -> Dict[str, float]:
    """
    Calculate Sharpe, CAGR, and Max Drawdown from trade history.
    """
    trades_list = list(trades)
    if not trades_list:
        return {"sharpe": 0.0, "cagr": 0.0, "mdd": 0.0, "total_trades": 0, "win_rate": 0.0, "avg_return": 0.0}

    df = pd.DataFrame([t.__dict__ for t in trades_list])
    df["return"] = df["return_pct"] / 100.0
    df["daily_return"] = df["return"] / df["hold_days"]

    mean_daily = df["daily_return"].mean()
    std_daily = df["daily_return"].std(ddof=1)
    if std_daily == 0 or np.isnan(std_daily):
        sharpe = 0.0
    else:
        sharpe = np.sqrt(252) * ((mean_daily - risk_free_rate / 252) / std_daily)

    df = df.sort_values("exit_date")
    equity = 1.0
    equity_curve = []
    for _, row in df.iterrows():
        equity *= 1 + row["return"]
        equity_curve.append((row["exit_date"], equity))

    start_date = df["entry_date"].min()
    end_date = df["exit_date"].max()
    years = max((pd.Timestamp(end_date) - pd.Timestamp(start_date)).days / 365.25, 1 / 365.25)
    cagr = equity ** (1 / years) - 1 if equity > 0 else 0.0

    peak = -np.inf
    max_drawdown = 0.0
    for _, value in equity_curve:
        if value > peak:
            peak = value
        drawdown = (value - peak) / peak if peak > 0 else 0
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    wins = (df["return_pct"] > 0).sum()
    total_trades = len(df)
    win_rate = wins / total_trades * 100 if total_trades else 0.0
    avg_return = df["return_pct"].mean()

    return {
        "sharpe": float(sharpe),
        "cagr": float(cagr),
        "mdd": float(max_drawdown * 100),  # convert to percentage
        "total_trades": total_trades,
        "win_rate": float(win_rate),
        "avg_return": float(avg_return),
    }


