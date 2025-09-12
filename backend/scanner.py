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
    details = {}
    W = config.dynamic_score_weights() if hasattr(config, 'dynamic_score_weights') else {
        'cross': config.score_w_cross,
        'volume': config.score_w_vol,
        'macd': config.score_w_macd,
        'rsi': config.score_w_rsi,
        'tema_slope': config.score_w_tema_slope,
        'dema_slope': config.score_w_dema_slope,
        'obv_slope': config.score_w_obv_slope,
        'above_cnt5': config.score_w_above_cnt,
    }

    # 1) 골든크로스 교차(+3)
    cross = (cur.TEMA20 > cur.DEMA10) and (prev.TEMA20 <= prev.DEMA10)
    flags["cross"] = bool(cross)
    if cross:
        score += W['cross']
    details['cross'] = {'ok': bool(cross), 'w': W['cross'], 'gain': W['cross'] if cross else 0}

    # 2) 거래량 확장(+2)
    volx = cur.volume > (cur.VOL_MA5 * config.vol_ma5_mult if pd.notna(cur.VOL_MA5) else cur.volume)
    flags["vol_expand"] = bool(volx)
    if volx:
        score += W['volume']
    details['volume'] = {'ok': bool(volx), 'w': W['volume'], 'gain': W['volume'] if volx else 0}

    # 3) MACD_OSC > -50 (+1)
    macd_ok = cur.MACD_OSC > config.macd_osc_min
    flags["macd_ok"] = bool(macd_ok)
    if macd_ok:
        score += W['macd']
    details['macd'] = {'ok': bool(macd_ok), 'w': W['macd'], 'gain': W['macd'] if macd_ok else 0}

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
        score += W['rsi']
    details['rsi'] = {'ok': bool(rsi_ok), 'w': W['rsi'], 'gain': W['rsi'] if rsi_ok else 0}

    # 5) TEMA20 SLOPE > 0 (+2)
    tema_slope_ok = float(df.iloc[-1]["TEMA20_SLOPE20"]) > 0
    flags["tema_slope_ok"] = bool(tema_slope_ok)
    if tema_slope_ok:
        score += W['tema_slope']
    details['tema_slope'] = {'ok': bool(tema_slope_ok), 'w': W['tema_slope'], 'gain': W['tema_slope'] if tema_slope_ok else 0}

    # 6) OBV SLOPE > 0 (+2)
    obv_slope_ok = float(df.iloc[-1]["OBV_SLOPE20"]) > 0
    flags["obv_slope_ok"] = bool(obv_slope_ok)
    if obv_slope_ok:
        score += W['obv_slope']
    details['obv_slope'] = {'ok': bool(obv_slope_ok), 'w': W['obv_slope'], 'gain': W['obv_slope'] if obv_slope_ok else 0}

    # 7) 최근 5봉 TEMA20>DEMA10 횟수 ≥ 3 (+2)
    above_ok = above_cnt >= 3
    flags["above_cnt5_ok"] = bool(above_ok)
    if above_ok:
        score += W['above_cnt5']
    details['above_cnt5'] = {'ok': bool(above_ok), 'w': W['above_cnt5'], 'gain': W['above_cnt5'] if above_ok else 0}

    # (선택) DEMA10 SLOPE > 0 점수/필수 여부
    dema_slope_ok = float(df.iloc[-1]["DEMA10_SLOPE20"]) > 0
    flags["dema_slope_ok"] = bool(dema_slope_ok)
    details['dema_slope'] = {'ok': bool(dema_slope_ok), 'w': W['dema_slope'], 'gain': W['dema_slope'] if dema_slope_ok else 0}
    mode = str(getattr(config, 'require_dema_slope', 'required')).lower()
    if mode == 'required' and not dema_slope_ok:
        flags["label"] = "제외"
        flags["match"] = False  # 제외 종목은 매칭되지 않음
        return 0, details
    elif mode == 'optional':
        if dema_slope_ok:
            score += W['dema_slope']
    # off: 무시

    # 레이블링 (더 세분화된 평가)
    if score >= 10:
        flags["label"] = "강한 매수"
    elif score >= 9:
        flags["label"] = "매수 후보"
    elif score >= 8:
        flags["label"] = "관심"
    elif score >= 6:
        flags["label"] = "관망"
    else:
        flags["label"] = "제외"
        flags["match"] = False  # 제외 종목은 매칭되지 않음
    details['total'] = int(score)
    return int(score), {**flags, 'details': details}


def match_condition(df: pd.DataFrame) -> bool:
    matched, _, _ = match_stats(df)
    return matched


def strategy_text(df: pd.DataFrame) -> str:
    """주식 상태를 사용자 친화적인 용어로 반환"""
    cur = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else cur
    msgs: List[str] = []
    
    # 골든크로스: 상승신호
    if (cur.TEMA20 > cur.DEMA10) and (prev.TEMA20 <= prev.DEMA10):
        msgs.append("상승신호")
    
    # 모멘텀 양전환: 상승시작
    if cur.MACD_OSC > 0:
        msgs.append("상승시작")
    
    # 거래확대: 관심증가
    if cur.volume > (cur.VOL_MA5 * config.vol_ma5_mult if pd.notna(cur.VOL_MA5) else 0):
        msgs.append("관심증가")
    
    # 추세 보조 문구: 상승추세정착
    slope_lb = int(getattr(config, 'trend_slope_lookback', 20))
    above_lb = int(getattr(config, 'trend_above_lookback', 5))
    above_cnt = int((df["TEMA20"] > df["DEMA10"]).tail(above_lb).sum()) if len(df) >= above_lb else 0
    if "TEMA20_SLOPE20" in df.columns and "OBV_SLOPE20" in df.columns:
        if df.iloc[-1]["TEMA20_SLOPE20"] > 0 and df.iloc[-1]["OBV_SLOPE20"] > 0:
            msgs.append("상승추세정착")
    
    if not msgs:
        return "관심"
    return " / ".join(msgs)


