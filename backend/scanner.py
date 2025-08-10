import time
from typing import Dict, List, Tuple
import pandas as pd

from backend.config import config
from backend.indicators import (
    tema_smooth,
    dema_smooth,
    macd,
    rsi_standard,
    rsi_tema,
    rsi_dema,
    obv,
)


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)

    df["TEMA20"] = tema_smooth(close, 20)
    df["DEMA10"] = dema_smooth(close, 10)
    macd_line, signal_line, osc = macd(close, 12, 26, 9)
    df["MACD_OSC"] = osc
    df["RSI"] = rsi_standard(close, 14)
    df["RSI_TEMA"] = rsi_tema(close, config.rsi_period)
    df["RSI_DEMA"] = rsi_dema(close, config.rsi_period)
    df["OBV"] = obv(close, volume)
    df["VOL_MA5"] = volume.rolling(5).mean()
    return df


def match_condition(df: pd.DataFrame) -> bool:
    if len(df) < 21:
        return False
    cur = df.iloc[-1]
    prev = df.iloc[-2]

    # 골든크로스: 최근 N일 내 교차 발생 또는 현재 단기선이 장기선 위
    lookback = min(5, len(df) - 1)
    crossed_recently = False
    for i in range(lookback):
        a_prev = df.iloc[-2 - i]
        a_cur = df.iloc[-1 - i]
        if (a_prev.TEMA20 <= a_prev.DEMA10) and (a_cur.TEMA20 > a_cur.DEMA10):
            crossed_recently = True
            break
    cond_gc = crossed_recently or (cur.TEMA20 > cur.DEMA10)
    cond_macd = cur.MACD_OSC > config.macd_osc_min

    thr = config.rsi_threshold
    mode = config.rsi_mode.lower()
    if mode == "standard":
        cond_rsi = cur.RSI > thr
    elif mode == "tema":
        cond_rsi = cur.RSI_TEMA > thr
    elif mode == "dema":
        cond_rsi = cur.RSI_DEMA > thr
    else:  # hybrid
        cond_rsi = (cur.RSI > thr) and (cur.RSI_TEMA > thr)

    cond_vol = cur.volume > (cur.VOL_MA5 * config.vol_ma5_mult if pd.notna(cur.VOL_MA5) else cur.volume)

    # 최소 신호 개수(기본 2개 이상) 충족 시 매칭 인정
    signals_true = sum([bool(cond_gc), bool(cond_macd), bool(cond_rsi), bool(cond_vol)])
    return bool(signals_true >= max(1, config.min_signals))


def strategy_text(df: pd.DataFrame) -> str:
    cur = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else cur
    msgs: List[str] = []
    if (cur.TEMA20 > cur.DEMA10) and (prev.TEMA20 <= prev.DEMA10):
        msgs.append("골든크로스 형성")
    if cur.MACD_OSC > 0:
        msgs.append("모멘텀 양전환")
    if cur.volume > (cur.VOL_MA5 * config.vol_ma5_mult if pd.notna(cur.VOL_MA5) else 0):
        msgs.append("거래확대")
    if not msgs:
        return "관망"
    return " / ".join(msgs)


