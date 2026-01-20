from __future__ import annotations

"""
backend.backtest.backtest_runner

scanner_v2 기반 백테스트를 실행하는 통합 러너.
"""

from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from data_loader import load_price_data
from scanner_v2.scan_v2 import run_scan_v2
from .trade_logic import Horizon, Trade, generate_trades
from .metrics import aggregate_metrics


def _iter_dates(start: str, end: str) -> List[str]:
    """YYYYMMDD 문자열 구간을 일 단위로 순회한다 (양끝 포함)."""
    start_dt = datetime.strptime(start, "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d")
    days = []
    cur = start_dt
    while cur <= end_dt:
        days.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return days


def _load_price_panel_for_symbols(
    symbols: List[str],
    start_date: str,
    end_date: str,
    max_hold_days: int,
) -> Dict[str, pd.DataFrame]:
    """
    필요한 심볼들에 대해 OHLCV 데이터를 한 번에 로드한다.
    hold 기간을 고려하여 end_date 이후로 약간의 버퍼를 둔다.
    """
    if not symbols:
        return {}

    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d") + timedelta(days=max_hold_days + 5)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    panel: Dict[str, pd.DataFrame] = {}
    for sym in sorted(set(symbols)):
        try:
            df = load_price_data(sym, start_str, end_str, cache=True)
            if df.empty:
                continue
            df = df.sort_values("date").reset_index(drop=True)
            panel[sym] = df
        except Exception:
            continue
    return panel


def _build_equity_curve(trades: List[Trade]) -> List[Dict[str, Any]]:
    """
    트레이드 리스트를 기반으로 간단한 equity curve를 생성한다.

    가정:
      - 각 트레이드는 독립적으로 1 단위 자본을 사용하고,
        트레이드 종료 시점에 수익/손실이 확정되어 누적된다.
      - equity는 트레이드 종료 시점 기준으로만 업데이트된다.
    """
    if not trades:
        return []
    df = pd.DataFrame([asdict(t) for t in trades])
    df["exit_date_ts"] = pd.to_datetime(df["exit_date"])
    df = df.sort_values("exit_date_ts")

    equity = 1.0
    curve: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        ret = float(row["return_pct"]) / 100.0
        equity *= 1.0 + ret
        curve.append(
            {
                "date": row["exit_date"],
                "equity": float(equity),
            }
        )
    return curve


def run_backtest(
    start_date: str,
    end_date: str,
    horizon: Horizon,
    *,
    max_trades_per_day: Optional[int] = None,
) -> Dict[str, Any]:
    """
    지정된 기간 동안 scanner_v2 결과를 기반으로 백테스트를 수행한다.

    Args:
        start_date: 시작일 (YYYYMMDD)
        end_date:   종료일 (YYYYMMDD)
        horizon:    'swing' | 'position' | 'longterm'
        max_trades_per_day: (옵션) 하루 최대 트레이드 수 제한

    Returns:
        {
          \"horizon\": str,
          \"metrics\": {...},
          \"trades\": [ ... ],
          \"equity_curve\": [ {\"date\": ..., \"equity\": ...}, ... ],
        }
    """
    dates = _iter_dates(start_date, end_date)

    # 1) 날짜별 스캔 실행
    daily_results: List[Dict[str, Any]] = []
    for d in dates:
        res = run_scan_v2(d)
        # 필요하다면 하루 최대 트레이드 수 제한을 위해 상위 N개만 남김
        key = f"{horizon}_candidates"
        if max_trades_per_day is not None and key in res:
            res[key] = sorted(
                res.get(key, []),
                key=lambda x: (-x.get("score", 0.0), x.get("risk_score", 0.0)),
            )[:max_trades_per_day]
        daily_results.append(res)

    # 2) 백테스트에 필요한 심볼 목록 수집
    needed_symbols: List[str] = []
    key = f"{horizon}_candidates"
    for res in daily_results:
        for item in res.get(key, []):
            sym = item.get("symbol") or item.get("ticker")
            if sym:
                needed_symbols.append(sym)

    # 3) OHLCV 패널 로드
    from .trade_logic import HOLD_DAYS

    max_hold = HOLD_DAYS[horizon]
    price_panel = _load_price_panel_for_symbols(needed_symbols, start_date, end_date, max_hold)

    # 4) 트레이드 생성
    raw_trades = generate_trades(daily_results, price_panel, horizon)
    trades = [Trade(**t) for t in raw_trades]

    # 5) equity curve 생성
    equity_curve = _build_equity_curve(trades)

    # 6) 성과 지표 계산
    metrics = aggregate_metrics([t.__dict__ for t in trades], equity_curve)

    return {
        "horizon": horizon,
        "metrics": metrics,
        "trades": [t.__dict__ for t in trades],
        "equity_curve": equity_curve,
    }


