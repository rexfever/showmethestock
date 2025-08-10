import time
from typing import Dict, List, Tuple
import pandas as pd

from config import config
from indicators import (
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

    cond_gc = (cur.TEMA20 > cur.DEMA10) and (prev.TEMA20 < prev.DEMA10)
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

    return bool(cond_gc and cond_macd and cond_rsi and cond_vol)


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


