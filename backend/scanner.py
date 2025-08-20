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
    linreg_slope,
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


def is_trend_up(series: pd.Series, periods: int = 3) -> bool:
    """최근 periods 구간에서 상승 우세 여부(상승 일수 ≥ 과반). NaN은 무시.
    """
    if len(series) < periods + 1:
        return False
    diffs = series.astype(float).diff().tail(periods)
    return (diffs > 0).sum() >= (periods // 2 + 1)


def match_stats(df: pd.DataFrame) -> tuple:
    """매칭 여부와 신호 카운트(stats)를 함께 반환.
    Returns: (matched: bool, signals_true: int, total_signals: int)
    """
    if len(df) < 21:
        return False, 0, 4
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
    # 추세 피처
    slope_lb = int(getattr(config, 'trend_slope_lookback', 20))
    above_lb = int(getattr(config, 'trend_above_lookback', 5))
    df["TEMA20_SLOPE20"] = linreg_slope(df["TEMA20"], slope_lb)
    df["OBV_SLOPE20"] = linreg_slope(df["OBV"], slope_lb)
    # 항상 계산해 두고, 필수 여부/점수 반영은 설정으로 제어
    df["DEMA10_SLOPE20"] = linreg_slope(df["DEMA10"], slope_lb)

    above_cnt = int((df["TEMA20"] > df["DEMA10"]).tail(above_lb).sum()) if len(df) >= above_lb else 0

    cond_gc = (crossed_recently or (cur.TEMA20 > cur.DEMA10)) and (df.iloc[-1]["TEMA20_SLOPE20"] > 0)
    cond_macd = (cur.MACD_OSC > config.macd_osc_min) and is_trend_up(df["MACD_OSC"], 3)

    thr = config.rsi_threshold
    mode = config.rsi_mode.lower()
    if mode == "standard":
        cond_rsi = (cur.RSI > thr) and is_trend_up(df["RSI"], 3)
    elif mode == "tema":
        cond_rsi = (cur.RSI_TEMA > thr) and is_trend_up(df["RSI_TEMA"], 3)
    elif mode == "dema":
        cond_rsi = (cur.RSI_DEMA > thr) and is_trend_up(df["RSI_DEMA"], 3)
    else:  # hybrid
        cond_rsi = (cur.RSI > thr) and (cur.RSI_TEMA > thr) and (
            is_trend_up(df["RSI"], 3) or is_trend_up(df["RSI_TEMA"], 3)
        )

    cond_vol = (
        cur.volume > (cur.VOL_MA5 * config.vol_ma5_mult if pd.notna(cur.VOL_MA5) else cur.volume)
        and is_trend_up(df["VOL_MA5"], 3)
        and (df.iloc[-1]["OBV_SLOPE20"] > 0)
    )

    # 추세 필터: TEMA20_SLOPE20>0, OBV_SLOPE20>0, above_cnt>=3
    trend_ok = (
        (df.iloc[-1]["TEMA20_SLOPE20"] > 0)
        and (df.iloc[-1]["OBV_SLOPE20"] > 0)
        and (above_cnt >= 3)
    )

    total = 4
    signals_true = sum([bool(cond_gc), bool(cond_macd), bool(cond_rsi), bool(cond_vol)])
    matched = bool(signals_true >= max(1, config.min_signals)) and trend_ok
    return matched, int(signals_true), int(total)


def score_conditions(df: pd.DataFrame) -> tuple:
    """조건별 점수 계산 및 근거 플래그 반환.
    Returns: (score:int, flags:Dict[str,bool])
    """
    if len(df) < 21:
        return 0, {}
    cur = df.iloc[-1]
    prev = df.iloc[-2]

    # 추세 피처가 없다면 보강
    slope_lb = int(getattr(config, 'trend_slope_lookback', 20))
    above_lb = int(getattr(config, 'trend_above_lookback', 5))
    if "TEMA20_SLOPE20" not in df.columns:
        df["TEMA20_SLOPE20"] = linreg_slope(df["TEMA20"], slope_lb)
    if "OBV_SLOPE20" not in df.columns:
        df["OBV_SLOPE20"] = linreg_slope(df["OBV"], slope_lb)
    above_cnt = int((df["TEMA20"] > df["DEMA10"]).tail(above_lb).sum()) if len(df) >= above_lb else 0

    flags = {}
    score = 0

    # 1) 골든크로스 교차(+3)
    cross = (cur.TEMA20 > cur.DEMA10) and (prev.TEMA20 <= prev.DEMA10)
    flags["cross"] = bool(cross)
    if cross:
        score += config.score_w_cross

    # 2) 거래량 확장(+2)
    volx = cur.volume > (cur.VOL_MA5 * config.vol_ma5_mult if pd.notna(cur.VOL_MA5) else cur.volume)
    flags["vol_expand"] = bool(volx)
    if volx:
        score += config.score_w_vol

    # 3) MACD_OSC > -50 (+1)
    macd_ok = cur.MACD_OSC > config.macd_osc_min
    flags["macd_ok"] = bool(macd_ok)
    if macd_ok:
        score += config.score_w_macd

    # 4) RSI 조건(+1)
    thr = config.rsi_threshold
    mode = config.rsi_mode.lower()
    if mode == "standard":
        rsi_ok = cur.RSI > thr
    elif mode == "tema":
        rsi_ok = cur.RSI_TEMA > thr
    elif mode == "dema":
        rsi_ok = cur.RSI_DEMA > thr
    else:  # hybrid
        rsi_ok = (cur.RSI > thr) and (cur.RSI_TEMA > thr)
    flags["rsi_ok"] = bool(rsi_ok)
    if rsi_ok:
        score += config.score_w_rsi

    # 5) TEMA20 SLOPE > 0 (+2)
    tema_slope_ok = float(df.iloc[-1]["TEMA20_SLOPE20"]) > 0
    flags["tema_slope_ok"] = bool(tema_slope_ok)
    if tema_slope_ok:
        score += config.score_w_tema_slope

    # 6) OBV SLOPE > 0 (+2)
    obv_slope_ok = float(df.iloc[-1]["OBV_SLOPE20"]) > 0
    flags["obv_slope_ok"] = bool(obv_slope_ok)
    if obv_slope_ok:
        score += config.score_w_obv_slope

    # 7) 최근 5봉 TEMA20>DEMA10 횟수 ≥ 3 (+2)
    above_ok = above_cnt >= 3
    flags["above_cnt5_ok"] = bool(above_ok)
    if above_ok:
        score += config.score_w_above_cnt

    # (선택) DEMA10 SLOPE > 0 점수/필수 여부
    dema_slope_ok = float(df.iloc[-1]["DEMA10_SLOPE20"]) > 0
    flags["dema_slope_ok"] = bool(dema_slope_ok)
    # 점수 부여(기본 2)
    if dema_slope_ok:
        score += config.score_w_dema_slope
    # 필수 조건으로 강제하려면 require_dema_slope=true
    if getattr(config, 'require_dema_slope', False) and not dema_slope_ok:
        score = 0  # 강제 실패 시 제외로 처리
        flags["label"] = "제외"
        return int(score), flags

    # 레이블링
    if score >= config.score_level_strong:
        flags["label"] = "강한 매수"
    elif score >= config.score_level_watch:
        flags["label"] = "관심"
    else:
        flags["label"] = "제외"
    return int(score), flags


def match_condition(df: pd.DataFrame) -> bool:
    matched, _, _ = match_stats(df)
    return matched


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
    # 추세 보조 문구
    slope_lb = int(getattr(config, 'trend_slope_lookback', 20))
    above_lb = int(getattr(config, 'trend_above_lookback', 5))
    above_cnt = int((df["TEMA20"] > df["DEMA10"]).tail(above_lb).sum()) if len(df) >= above_lb else 0
    if "TEMA20_SLOPE20" in df.columns and "OBV_SLOPE20" in df.columns:
        if df.iloc[-1]["TEMA20_SLOPE20"] > 0 and df.iloc[-1]["OBV_SLOPE20"] > 0:
            msgs.append(f"상승 추세 정착({above_cnt}/{above_lb})")
    if not msgs:
        return "관망"
    return " / ".join(msgs)


