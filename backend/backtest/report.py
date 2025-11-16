from __future__ import annotations

"""
backend.backtest.report

백테스트 결과 요약 출력 및 CSV 저장을 담당한다.
"""

from pathlib import Path
from typing import Dict, List

import pandas as pd


def print_summary(horizon: str, metrics: Dict[str, float]) -> None:
    """
    콘솔에 간단한 텍스트 요약을 출력한다.
    """
    print(f"[Horizon: {horizon.capitalize()}]")
    print(f"CAGR    : {metrics.get('CAGR', 0.0):5.2f}%")
    print(f"MDD     : {metrics.get('MDD', 0.0):5.2f}%")
    print(f"Sharpe  : {metrics.get('Sharpe', 0.0):5.2f}")
    print(f"WinRate : {metrics.get('WinRate', 0.0):5.2f}%")
    print(f"Avg P/L : {metrics.get('AvgReturn', 0.0):5.2f}%")


def save_trades_csv(trades: List[Dict], filename: str) -> None:
    """
    트레이드 리스트를 CSV로 저장한다.
    """
    if not trades:
        return
    df = pd.DataFrame(trades)
    out_path = Path(filename)
    df.to_csv(out_path, index=False)


def save_equity_curve_csv(equity: List[Dict], filename: str) -> None:
    """
    equity curve 리스트를 CSV로 저장한다.
    """
    if not equity:
        return
    df = pd.DataFrame(equity)
    out_path = Path(filename)
    df.to_csv(out_path, index=False)


