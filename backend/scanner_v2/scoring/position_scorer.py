from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def score(symbol: str, df: pd.DataFrame) -> Dict[str, float]:
    """
    Position Horizon (2~12주) 점수 계산.

    EMA20/60 관계, EMA60 기울기, 상대강도(RS) 경사 등을 이용해
    중기 추세를 평가한다.
    """
    if df is None or len(df) < 30:
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

    # EMA20 > EMA60 → 1점
    if {"EMA20", "EMA60"}.issubset(df.columns):
        if float(cur["EMA20"]) > float(cur["EMA60"]):
            score_val += 1.0

    # EMA60 상승 추세 (최근 20봉) → 0~3.5점 (약/정상/강한 우상향 3단계)
    if "EMA60" in df.columns:
        ema60 = df["EMA60"].tail(20)
        if len(ema60) >= 2:
            start = float(ema60.iloc[0])
            end = float(ema60.iloc[-1])
            slope_pct = (end / start - 1.0) if start > 0 else 0.0
            # 약한 우상향
            if slope_pct > 0.0:
                score_val += 0.5
            # 정상 우상향(~2% 이상)
            if slope_pct > 0.02:
                score_val += 1.0
            # 강한 우상향(5% 이상)
            if slope_pct > 0.05:
                score_val += 2.0

    # RS_SLOPE (최근 10봉) > 0 → 0~3.5점 (EMA60과 동일한 3단계 규칙)
    if "RS" in df.columns:
        rs = df["RS"].tail(10).dropna()
        if len(rs) >= 2:
            start = float(rs.iloc[0])
            end = float(rs.iloc[-1])
            slope_pct = (end / start - 1.0) if start != 0 else 0.0
            if slope_pct > 0.0:
                score_val += 0.5
            if slope_pct > 0.02:
                score_val += 1.0
            if slope_pct > 0.05:
                score_val += 2.0

    # ATR_PCT ∈ [0.8, 4.0] → 최대 0.5점 (비중 축소)
    if "ATR_PCT" in df.columns:
        atr_pct = float(cur["ATR_PCT"])
        if 0.8 <= atr_pct <= 4.0:
            score_val += 0.5

    # Risk score: 급락/갑작스러운 변동성
    # - 최근 5봉 중 하루 이상 -7% 이상 하락 → +2
    # - ATR_PCT <0.6 또는 >6.0 이면 +1 (변동성 리스크는 risk_score로 이동)
    if {"close"}.issubset(df.columns):
        close = df["close"].astype(float)
        if len(close) >= 6:
            ret = close.pct_change().tail(5)
            if (ret <= -0.07).any():
                risk_score += 2.0
    if "ATR_PCT" in df.columns:
        atr_pct = float(cur["ATR_PCT"])
        if atr_pct > 6.0 or atr_pct < 0.8:
            risk_score += 1.0

    score_val = float(max(0.0, min(10.0, score_val)))
    risk_score = float(max(0.0, risk_score))

    return {
        "swing_score": 0.0,
        "position_score": score_val,
        "longterm_score": 0.0,
        "risk_score": risk_score,
    }


