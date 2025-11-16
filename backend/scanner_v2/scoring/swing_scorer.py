from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def score(symbol: str, df: pd.DataFrame) -> Dict[str, float]:
    """
    Swing Horizon (2~10일) 점수 계산.

    df의 마지막 행(최신 봉)을 기준으로 단기 모멘텀/변동성을 평가한다.

    반환 예:
        {
            "swing_score": 7.0,
            "position_score": 0.0,
            "longterm_score": 0.0,
            "risk_score": 2.0,
        }
    """
    if df is None or len(df) < 10:
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

    # RSI(14) ∈ [45, 65], 최근 3봉 중 2봉 이상 RSI 증가 → 0~2점
    if "RSI" in df.columns:
        recent_rsi = df["RSI"].tail(3)
        if recent_rsi.notna().all():
            rsi_window_ok = (45 <= float(cur["RSI"]) <= 65)
            rsi_up = (recent_rsi.diff() > 0).sum()
            if rsi_window_ok:
                if rsi_up >= 2:
                    score_val += 2.0
                elif rsi_up == 1:
                    score_val += 1.0

    # MACD_HIST 최근 2~3봉 연속 증가 → 0~2점
    if "MACD_HIST" in df.columns:
        macd_hist = df["MACD_HIST"].tail(3)
        if macd_hist.notna().all():
            inc_cnt = (macd_hist.diff() > 0).sum()
            if inc_cnt >= 2:
                score_val += 2.0
            elif inc_cnt == 1:
                score_val += 1.0

    # EMA20 SLOPE > 0 → 1점 (간단히 최근 5봉 EMA20 상승 여부로 근사)
    if "EMA20" in df.columns:
        ema20 = df["EMA20"].tail(5)
        if len(ema20) >= 2 and ema20.iloc[-1] > ema20.iloc[0]:
            score_val += 1.0

    # volume >= VOL_MA5 * 1.2 → 0~2점
    if {"volume", "EMA20"}.issubset(df.columns):
        vol = df["volume"].astype(float)
        vol_ma5 = vol.rolling(5).mean()
        cur_vol = float(vol.iloc[-1])
        cur_vol_ma5 = float(vol_ma5.iloc[-1]) if not np.isnan(vol_ma5.iloc[-1]) else 0.0
        if cur_vol_ma5 > 0:
            ratio = cur_vol / cur_vol_ma5
            if ratio >= 1.8:
                score_val += 2.0
            elif ratio >= 1.2:
                score_val += 1.0

    # ATR_PCT ∈ [1.0, 5.0] → 0~2점
    if "ATR_PCT" in df.columns:
        atr_pct = float(cur["ATR_PCT"])
        if 1.0 <= atr_pct <= 5.0:
            # 중간에 가까우면 더 높은 점수
            if 2.0 <= atr_pct <= 4.0:
                score_val += 2.0
            else:
                score_val += 1.0

    # Risk score: 과열 및 변동성 과대 페널티
    # RSI > 75 → +2, ATR_PCT >6 또는 <0.8 → +1
    if "RSI" in df.columns:
        if float(cur["RSI"]) > 75:
            risk_score += 2.0
    if "ATR_PCT" in df.columns:
        atr_pct = float(cur["ATR_PCT"])
        if atr_pct > 6.0 or atr_pct < 0.8:
            risk_score += 1.0

    # 0~10 범위로 클리핑
    score_val = float(max(0.0, min(10.0, score_val)))
    risk_score = float(max(0.0, risk_score))

    return {
        "swing_score": score_val,
        "position_score": 0.0,
        "longterm_score": 0.0,
        "risk_score": risk_score,
    }


