from __future__ import annotations

"""
scanner_v2.stage1.stage1_filter

목적: 유니버스 내 종목 중에서 "살아 있는, 트레이딩 가능한 종목"만 거르는 매우 느슨한 필터.
"""

from typing import Optional

import pandas as pd


def stage1_filter(symbol: str, df: pd.DataFrame) -> bool:
    """
    Stage1 필터.

    df는 최근 최소 20~60봉의 인디케이터가 포함된 DataFrame.
    조건을 만족하면 True, 아니면 False를 반환한다.

    규칙 (최근 5 거래일 윈도우 기준):
      - close >= 2_000 (원)
      - TURNOVER_MA20 >= 300_000_000 (3억)
      - 0.8 <= ATR_PCT <= 6.0
    위 조건을 동시에 만족하는 날이 1일 이상 있으면 PASS.
    """
    if df is None or df.empty:
        return False

    # 최신 순으로 정렬되어 있다고 가정하지만, 방어적으로 정렬
    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)

    recent = df.tail(5).copy()

    # TURNOVER_MA20이 없다면 계산
    if "TURNOVER_MA20" not in recent.columns:
        if {"close", "volume"}.issubset(recent.columns):
            recent["turnover"] = recent["close"].astype(float) * recent["volume"].astype(float)
            recent["TURNOVER_MA20"] = recent["turnover"].rolling(20, min_periods=1).mean()
        else:
            return False

    # ATR_PCT가 없다면 필터 불가 → 실패 처리
    if "ATR_PCT" not in recent.columns:
        return False

    cond_price = recent["close"].astype(float) >= 2_000.0
    cond_turnover = recent["TURNOVER_MA20"].astype(float) >= 300_000_000.0
    atr_pct = recent["ATR_PCT"].astype(float)
    cond_atr = (atr_pct >= 0.8) & (atr_pct <= 6.0)

    mask = cond_price & cond_turnover & cond_atr
    return bool(mask.any())


