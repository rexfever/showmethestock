from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def score(symbol: str, df: pd.DataFrame) -> Dict[str, float]:
    """
    Long-term Horizon (3개월 이상) 점수 계산.

    EMA120/200 추세와 장기 RS, 안정적인 ATR 범위를 기반으로 장기 투자 적합도를 평가한다.
    """
    if df is None or len(df) < 60:
        return {
            "swing_score": 0.0,
            "position_score": 0.0,
            "longterm_score": 0.0,
            "risk_score": 0.0,
        }

    df = df.sort_values("date").reset_index(drop=True)
    cur = df.iloc[-1]

    score_val = 0.0
    risk_score = 0.0

    # close > EMA200 → 1점
    if {"close", "EMA200"}.issubset(df.columns):
        if float(cur["close"]) > float(cur["EMA200"]):
            score_val += 1.0

    # EMA120, EMA200 SLOPE ≥ 0 → 0~3점 (각각 0~1.5점 정도 느낌으로)
    if "EMA120" in df.columns:
        ema120 = df["EMA120"].tail(40)
        if len(ema120) >= 2:
            slope_120 = float(ema120.iloc[-1] - ema120.iloc[0])
            if slope_120 > 0:
                score_val += 1.0
    if "EMA200" in df.columns:
        ema200 = df["EMA200"].tail(60)
        if len(ema200) >= 2:
            slope_200 = float(ema200.iloc[-1] - ema200.iloc[0])
            if slope_200 > 0:
                score_val += 2.0  # 장기 기준이므로 비중을 더 높게

    # RS 장기(최근 60봉) 우상향 → 0~3점
    if "RS" in df.columns:
        rs = df["RS"].tail(60)
        if rs.notna().all() and len(rs) >= 10:
            slope = float(rs.iloc[-1] - rs.iloc[0])
            if slope > 0:
                score_val += 1.0
            if slope > 0.05 * abs(float(rs.iloc[0]) or 1.0):
                score_val += 2.0

    # ATR_PCT ∈ [0.5, 3.0] → 0~2점
    if "ATR_PCT" in df.columns:
        atr_pct = float(cur["ATR_PCT"])
        if 0.5 <= atr_pct <= 3.0:
            if 1.0 <= atr_pct <= 2.0:
                score_val += 2.0
            else:
                score_val += 1.0

    # Risk score: 변동성 과대/급등 리스크
    if "ATR_PCT" in df.columns:
        if float(cur["ATR_PCT"]) > 5.0:
            risk_score += 1.0
    if {"close"}.issubset(df.columns):
        close = df["close"].astype(float)
        if len(close) >= 20:
            ret = close.pct_change().tail(10)
            if (ret >= 0.15).any():  # 최근 10봉 내 15% 이상 급등
                risk_score += 2.0

    score_val = float(max(0.0, min(10.0, score_val)))
    risk_score = float(max(0.0, risk_score))

    return {
        "swing_score": 0.0,
        "position_score": 0.0,
        "longterm_score": score_val,
        "risk_score": risk_score,
    }


