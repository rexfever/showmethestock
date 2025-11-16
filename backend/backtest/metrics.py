from __future__ import annotations

"""
backend.backtest.metrics

포트폴리오 성과 지표 계산 유틸리티.
"""

from typing import Dict, Iterable, List

import numpy as np
import pandas as pd


def calculate_cagr(equity_curve: List[Dict]) -> float:
    """
    연복리수익률(CAGR) 계산.

    equity_curve: [{\"date\": YYYYMMDD, \"equity\": float}, ...] 형식의 리스트
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0

    df = pd.DataFrame(equity_curve)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    start_date = df["date"].iloc[0]
    end_date = df["date"].iloc[-1]
    start_equity = float(df["equity"].iloc[0])
    end_equity = float(df["equity"].iloc[-1])

    if start_equity <= 0 or end_equity <= 0:
        return 0.0

    years = max((end_date - start_date).days / 365.25, 1 / 365.25)
    return float((end_equity / start_equity) ** (1 / years) - 1.0)


def calculate_mdd(equity_curve: List[Dict]) -> float:
    """
    최대 낙폭(MDD, %) 계산.
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    df = pd.DataFrame(equity_curve)
    equity = df["equity"].astype(float)
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    return float(drawdown.min() * 100.0)


def calculate_sharpe(returns: Iterable[float], risk_free_rate: float = 0.02) -> float:
    """
    Sharpe Ratio 계산.

    returns: 일간 수익률(소수, 예: 0.01 = 1%) 시퀀스
    """
    rets = np.array(list(returns), dtype=float)
    if len(rets) == 0:
        return 0.0
    mean_ret = np.mean(rets)
    std_ret = np.std(rets, ddof=1) if len(rets) > 1 else 0.0
    if std_ret == 0 or np.isnan(std_ret):
        return 0.0
    # 연율화 (거래일 252일 가정)
    return float((mean_ret - risk_free_rate / 252.0) / std_ret * np.sqrt(252.0))


def calculate_winrate(trades: List[Dict]) -> float:
    """
    승률(%) 계산.
    """
    if not trades:
        return 0.0
    returns = [t.get("return_pct", 0.0) for t in trades]
    wins = sum(1 for r in returns if r > 0)
    return float(wins / len(returns) * 100.0)


def aggregate_metrics(trades: List[Dict], equity_curve: List[Dict]) -> Dict[str, float]:
    """
    트레이드 리스트와 equity curve를 기반으로 종합 지표를 계산한다.
    """
    if not trades:
        return {
            "CAGR": 0.0,
            "MDD": 0.0,
            "Sharpe": 0.0,
            "WinRate": 0.0,
            "AvgReturn": 0.0,
        }

    # 일간 수익률: equity curve 기준
    df_eq = pd.DataFrame(equity_curve)
    df_eq["equity"] = df_eq["equity"].astype(float)
    df_eq = df_eq.sort_values("date")
    if len(df_eq) >= 2:
        daily_returns = df_eq["equity"].pct_change().dropna().to_numpy()
    else:
        daily_returns = np.array([])

    cagr = calculate_cagr(equity_curve)
    mdd = calculate_mdd(equity_curve)
    sharpe = calculate_sharpe(daily_returns)
    winrate = calculate_winrate(trades)
    avg_return = float(np.mean([t.get("return_pct", 0.0) for t in trades])) if trades else 0.0

    return {
        "CAGR": float(cagr * 100.0),
        "MDD": float(mdd),
        "Sharpe": float(sharpe),
        "WinRate": float(winrate),
        "AvgReturn": float(avg_return),
    }


