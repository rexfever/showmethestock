from __future__ import annotations

"""
backend.backtest.trade_logic

scanner_v2 스캔 결과와 시세 데이터를 기반으로 트레이드 생성 및 시뮬레이션을 수행한다.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Iterable, List, Literal, Optional

import pandas as pd

Horizon = Literal["swing", "position", "longterm"]


@dataclass
class Trade:
    """단일 트레이드 결과."""

    symbol: str
    horizon: str
    signal_date: str  # YYYYMMDD
    entry_date: str   # YYYYMMDD
    exit_date: str    # YYYYMMDD
    entry_price: float
    exit_price: float
    return_pct: float
    hold_days: int


HOLD_DAYS: Dict[Horizon, int] = {
    "swing": 5,
    "position": 10,
    "longterm": 20,
}


def simulate_trade(
    symbol: str,
    signal_date: str,
    horizon: Horizon,
    price_df: pd.DataFrame,
) :  # -> Optional[Trade]
    """
    단일 트레이드를 시뮬레이션한다.

    - signal_date 다음 거래일의 시가에 진입
    - Horizon별 고정 보유일수 후 종가에 청산
    - 데이터 부족 또는 가격 이상(0/NaN) 시 None 반환
    """
    if price_df.empty or "date" not in price_df.columns:
        return None

    df = price_df.sort_values("date").reset_index(drop=True)
    sig_ts = datetime.strptime(signal_date, "%Y%m%d")
    mask = df["date"] == pd.to_datetime(sig_ts)
    if not mask.any():
        # 시그널 날짜에 해당하는 거래일이 없으면 스킵
        return None

    sig_idx = df.index[mask][0]
    entry_idx = sig_idx + 1  # 다음 거래일 시가 진입
    if entry_idx >= len(df):
        return None

    hold_days = HOLD_DAYS[horizon]
    exit_idx = entry_idx + hold_days - 1
    if exit_idx >= len(df):
        # 충분한 데이터가 없으면 스킵
        return None

    entry_row = df.iloc[entry_idx]
    exit_row = df.iloc[exit_idx]

    entry_price = float(entry_row.get("open", 0.0))
    exit_price = float(exit_row.get("close", 0.0))
    if entry_price <= 0 or exit_price <= 0:
        return None

    ret_pct = (exit_price - entry_price) / entry_price * 100.0
    hold_days_actual = (exit_row["date"] - entry_row["date"]).days or hold_days

    return Trade(
        symbol=symbol,
        horizon=horizon,
        signal_date=signal_date,
        entry_date=entry_row["date"].strftime("%Y%m%d"),
        exit_date=exit_row["date"].strftime("%Y%m%d"),
        entry_price=entry_price,
        exit_price=exit_price,
        return_pct=ret_pct,
        hold_days=hold_days_actual,
    )


def generate_trades(
    scan_results: Iterable[Dict],
    price_data: Dict[str, pd.DataFrame],
    horizon: Horizon,
) -> List[Dict]:
    """
    스캔 결과와 시세 데이터를 기반으로 지정된 Horizon 의 트레이드 리스트를 생성한다.

    Args:
        scan_results: scanner_v2.run_scan_v2() 결과들의 리스트
                      각 원소는 { 'date', '<horizon>_candidates': [...] } 형태의 dict
        price_data:   symbol -> OHLCV DataFrame 매핑
        horizon:      'swing' | 'position' | 'longterm'

    Returns:
        트레이드 dict 리스트 (직렬화 가능한 형태)
    """
    trades: List[Dict] = []
    key = f"{horizon}_candidates"

    for daily in scan_results:
        signal_date = daily.get("date")
        if not signal_date:
            continue
        candidates = daily.get(key, []) or []
        for item in candidates:
            symbol = item.get("symbol") or item.get("ticker")  # 일부 구조 호환
            if not symbol:
                continue
            df = price_data.get(symbol)
            if df is None:
                continue
            trade = simulate_trades_for_symbol(symbol, signal_date, horizon, df)
            if trade is not None:
                trades.append(asdict(trade))

    return trades


def simulate_trades_for_symbol(
    symbol: str,
    signal_date: str,
    horizon: Horizon,
    price_df: pd.DataFrame,
):
    """
    generate_trades 내부에서 사용하기 위한 래퍼.
    여러 번 호출될 수 있으므로, 여기서는 단일 시그널에 대해 하나의 트레이드만 생성한다.
    """
    return simulate_trade(symbol, signal_date, horizon, price_df)



