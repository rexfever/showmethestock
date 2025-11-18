import time
from typing import Dict, List, Tuple
import pandas as pd
import concurrent.futures

from config import config
from indicators import (
    tema_smooth,
    dema_smooth,
    macd,
    rsi_standard,
    rsi_tema,
    rsi_dema,
    obv,
    linreg_slope,
    atr,
)
from market_analyzer import market_analyzer, MarketCondition


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)

    df["TEMA20"] = tema_smooth(close, 20)
    df["DEMA10"] = dema_smooth(close, 10)
    macd_line, signal_line, osc = macd(close, 12, 26, 9)
    df["MACD_OSC"] = osc
    df["MACD_LINE"] = macd_line
    df["MACD_SIGNAL"] = signal_line
    # === RSI 계산 ===
    # RSI_TEMA: TEMA 평활화된 RSI
    df["RSI_TEMA"] = rsi_tema(close, 14)
    # RSI_DEMA: DEMA 평활화된 RSI  
    df["RSI_DEMA"] = rsi_dema(close, 14)
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


def match_stats(df: pd.DataFrame, market_condition: MarketCondition = None, stock_name: str = None) -> tuple:
    """매칭 여부와 신호 카운트(stats)를 함께 반환.
    Returns: (matched: bool, signals_true: int, total_signals: int)
    """
    if len(df) < 21:
        return False, 0, 4
    cur = df.iloc[-1]
    prev = df.iloc[-2]

    # 시장 상황에 따른 동적 조건 적용
    if market_condition and config.market_analysis_enable:
        # 시장 상황 기반 조건 사용
        rsi_threshold = market_condition.rsi_threshold
        min_signals = market_condition.min_signals
        macd_osc_min = market_condition.macd_osc_min
        vol_ma5_mult = market_condition.vol_ma5_mult
        gap_max = market_condition.gap_max
        ext_from_tema20_max = market_condition.ext_from_tema20_max
    else:
        # 기본 조건 사용
        rsi_threshold = config.rsi_threshold
        min_signals = config.min_signals
        macd_osc_min = config.macd_osc_min
        vol_ma5_mult = config.vol_ma5_mult
        gap_max = config.gap_max
        ext_from_tema20_max = config.ext_from_tema20_max

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

    # ----- 유동성/가격/연속신호 컷 (매칭 초반에 하드 필터 추가) -----
    
    # 인버스 ETF 필터링은 scan_one_symbol에서 이미 처리됨
    # (중복 제거를 위해 주석 처리)
    
    # 유동성: 최근 20일 평균 거래대금(= close * volume) 계산
    if len(df) >= 20:
        avg_turnover = (df["close"].iloc[-20:] * df["volume"].iloc[-20:]).mean()
        if avg_turnover < config.min_turnover_krw:
            return False, 0, 4

    # 가격 하한
    if cur.close < config.min_price:
        return False, 0, 4

    # 연속 신호 디바운스 (구현되어 있다 가정, 없으면 skip)
    # last_dt = get_last_entry_date(cur.code)  # 구현되어 있다 가정 (없으면 skip)
    # if last_dt is not None and (df.index[-1] - last_dt).days < config.entry_cooldown_days:
    #     return False, 0, 4

    # ----- 하드 제외: 과열 -----
    overheat = (
        (cur.RSI_TEMA >= config.overheat_rsi_tema) and
        (cur.VOL_MA5 and cur.volume >= config.overheat_vol_mult * cur.VOL_MA5)
    )
    if overheat:
        return False, 0, 4   # 즉시 제외

    # ----- 교차 갭 품질 & 추격 이격 제한 -----
    gap_now = (cur.TEMA20 - cur.DEMA10) / cur.close if cur.close else 0.0
    ext_pct = (cur.close - cur.TEMA20) / cur.TEMA20 if cur.TEMA20 else 0.0
    if not (max(gap_now, 0.0) >= config.gap_min and gap_now <= gap_max and ext_pct <= ext_from_tema20_max):
        return False, 0, 4

    # ----- 변동성 컷(너무 출렁/너무 잠잠 배제) -----
    if config.use_atr_filter:
        _atr = atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        if cur.close:
            atr_pct = _atr / cur.close
            if not (config.atr_pct_min <= atr_pct <= config.atr_pct_max):
                return False, 0, 4

    cond_gc = (crossed_recently or (cur.TEMA20 > cur.DEMA10)) and (df.iloc[-1]["TEMA20_SLOPE20"] > 0)
    
    # ---- MACD: 상승 초입 신호 조건 ----
    # MACD 신호: 골든크로스 또는 오실레이터 양수
    cond_macd = (cur.MACD_LINE > cur.MACD_SIGNAL) or (cur.MACD_OSC > 0)

    # ---- RSI: 상승 초입 모멘텀 조건 ----
    # RSI 모멘텀: TEMA > DEMA 또는 수렴 후 상승 (동적 rsi_threshold 사용)
    rsi_momentum = (cur.RSI_TEMA > cur.RSI_DEMA) or (abs(cur.RSI_TEMA - cur.RSI_DEMA) < 3 and cur.RSI_TEMA > rsi_threshold)
    cond_rsi = rsi_momentum

    # ---- 거래량: 상승 초입 급증 조건 ----
    # 거래량 급증: 평균 대비 설정값 배수 이상
    cond_vol = (cur.VOL_MA5 and cur.volume >= config.vol_ma5_mult * cur.VOL_MA5)

    # 상승 초입 추세 필터: 가격 상승 + OBV 상승 + 연속 상승 + DEMA 슬로프 (설정에 따라)
    trend_ok = (
        (df.iloc[-1]["TEMA20_SLOPE20"] > 0)  # 가격 상승 추세
        and (df.iloc[-1]["OBV_SLOPE20"] > 0)  # OBV 상승 (자금 유입)
        and (above_cnt >= 3)  # 연속 상승 (5일 중 3일 이상으로 강화)
    )
    
    # DEMA 슬로프 조건 추가 (설정에 따라)
    if config.require_dema_slope == "required":
        trend_ok = trend_ok and (df.iloc[-1]["DEMA10_SLOPE20"] > 0)
    elif config.require_dema_slope == "optional":
        # 선택사항이므로 점수에만 반영
        pass

    # ----- 신호 요건 상향 (동적 MIN_SIGNALS + 볼륨 강화 + MACD 강화 + RSI 타이트) -----
    # 기존 cond_gc(교차/정렬)와 trend_ok(TEMA/DEMA/OBV slope 등)는 유지
    
    # 기본 신호 4개
    basic_signals = sum([bool(cond_gc), bool(cond_macd), bool(cond_rsi), bool(cond_vol)])
    
    # 추가 신호 3개 (통과율이 높은 신호들)
    obv_slope_ok = df.iloc[-1]["OBV_SLOPE20"] > 0.001
    tema_slope_ok = (df.iloc[-1]["TEMA20_SLOPE20"] > 0.001) and (cur.close > cur.TEMA20)
    above_ok = above_cnt >= 3
    
    additional_signals = sum([bool(obv_slope_ok), bool(tema_slope_ok), bool(above_ok)])
    
    # 총 신호 개수 (기본 4개 + 추가 3개 = 최대 7개)
    signals_true = basic_signals + additional_signals
    
    if signals_true < min_signals or not trend_ok:
        return False, signals_true, 7  # 총 신호 개수 반환
    
    # 최종 매칭: 신호 요건 충족 + 추세
    matched = True
    return matched, int(signals_true), 4


def calculate_risk_score(df: pd.DataFrame) -> tuple:
    """위험도 점수 계산 (높을수록 위험)
    Returns: (risk_score: int, risk_flags: Dict[str, bool])
    """
    if len(df) < 21:
        return 0, {}
    
    cur = df.iloc[-1]
    risk_score = 0
    risk_flags = {}
    
    # 1. 과매수 구간 위험 (RSI_TEMA > 80) - 새로운 RSI 로직 사용
    rsi_overbought = cur.RSI_TEMA > 80  # config.rsi_overbought_threshold 대신 고정값 사용
    risk_flags["rsi_overbought"] = rsi_overbought
    if rsi_overbought:
        risk_score += 2
    
    # 2. 거래량 급증 위험 (평균 대비 3배 이상)
    vol_spike = cur.volume > (cur.VOL_MA5 * config.vol_spike_threshold if pd.notna(cur.VOL_MA5) else cur.volume)
    risk_flags["vol_spike"] = vol_spike
    if vol_spike:
        risk_score += 2
    
    # 3. 모멘텀 지속성 부족 위험 (MACD 상승 기간이 짧음)
    macd_trend_duration = 0
    for i in range(min(10, len(df) - 1)):
        if df.iloc[-(i+1)]["MACD_OSC"] > df.iloc[-(i+2)]["MACD_OSC"]:
            macd_trend_duration += 1
        else:
            break
    
    momentum_weak = macd_trend_duration < config.momentum_duration_min
    risk_flags["momentum_weak"] = momentum_weak
    if momentum_weak:
        risk_score += 1
    
    # 4. 가격 급등 후 조정 위험 (최근 5일 중 4일 이상 상승)
    recent_up_days = 0
    for i in range(min(5, len(df) - 1)):
        if df.iloc[-(i+1)]["close"] > df.iloc[-(i+2)]["close"]:
            recent_up_days += 1
    
    price_exhaustion = recent_up_days >= 4
    risk_flags["price_exhaustion"] = price_exhaustion
    if price_exhaustion:
        risk_score += 1
    
    return risk_score, risk_flags


def score_conditions(df: pd.DataFrame, market_condition=None) -> tuple:
    """조건별 점수 계산 및 근거 플래그 반환.
    Returns: (score:int, flags:Dict[str,bool])
    """
    if len(df) < 21:
        return 0, {}
    cur = df.iloc[-1]
    prev = df.iloc[-2]

    # ----- 유동성/가격/연속신호 컷 (매칭 초반에 하드 필터 추가) -----
    
    # 유동성: 최근 20일 평균 거래대금(= close * volume) 계산
    if len(df) >= 20:
        avg_turnover = (df["close"].iloc[-20:] * df["volume"].iloc[-20:]).mean()
        if avg_turnover < config.min_turnover_krw:
            return 0, {
                "label": "유동성부족",
                "match": False,
                "avg_turnover": round(float(avg_turnover), 0),
                "min_turnover": config.min_turnover_krw
            }

    # 가격 하한
    if cur.close < config.min_price:
        return 0, {
            "label": "저가종목",
            "match": False,
            "price": round(float(cur.close), 0),
            "min_price": config.min_price
        }

    # ----- 하드 제외: 과열 -----
    overheat = (
        (cur.RSI_TEMA >= config.overheat_rsi_tema) and
        (cur.VOL_MA5 and cur.volume >= config.overheat_vol_mult * cur.VOL_MA5)
    )
    if overheat:
        return 0, {
            "label": "과열",
            "match": False,
            "overheated_rsi_tema": True,
            "rsi_tema_value": round(float(cur.RSI_TEMA), 2),
            "volume_ratio": round(float(cur.volume / cur.VOL_MA5), 2) if cur.VOL_MA5 else 0
        }

    # ----- 노이즈/추격 방지 -----
    gap_now = (cur.TEMA20 - cur.DEMA10) / cur.close if cur.close else 0.0
    ext_pct = (cur.close - cur.TEMA20) / cur.TEMA20 if cur.TEMA20 else 0.0
    gap_ok = (max(gap_now, 0.0) >= config.gap_min) and (gap_now <= config.gap_max)   # 음수=역배열 방지
    ext_ok = (ext_pct <= config.ext_from_tema20_max)
    if not (gap_ok and ext_ok):
        return 0, {
            "label": "노이즈/추격",
            "match": False,
            "gap_now": round(float(gap_now), 4),
            "gap_ok": bool(gap_ok),
            "ext_pct": round(float(ext_pct), 4),
            "ext_ok": bool(ext_ok)
        }

    # ----- 변동성 컷(너무 출렁/너무 잠잠 배제) -----
    if config.use_atr_filter:
        _atr = atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        if cur.close:
            atr_pct = _atr / cur.close
            if not (config.atr_pct_min <= atr_pct <= config.atr_pct_max):
                return 0, {
                    "label": "변동성부적절",
                    "match": False,
                    "atr_pct": round(float(atr_pct), 4),
                    "atr_min": config.atr_pct_min,
                    "atr_max": config.atr_pct_max
                }
    
    # 위험도 점수 계산
    risk_score, risk_flags = calculate_risk_score(df)
    
    # 위험도가 임계값을 초과하면 제외
    if risk_score >= config.risk_score_threshold:
        return 0, {
            "match": False,
            "label": "위험종목",
            "risk_score": risk_score,
            "risk_flags": risk_flags,
            "details": {"risk_excluded": True, "risk_score": risk_score}
        }

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

    # 0) 하향 추세 필터링 비활성화 (새로운 RSI 로직으로 대체)
    # downward_trend = cur.close < min(cur.TEMA20, cur.DEMA10)
    # if downward_trend:
    #     flags["label"] = "하향추세"
    #     flags["match"] = False
    #     return 0, {**flags, 'details': details}
    
    # 1) 골든크로스 교차(+3)
    cross = (cur.TEMA20 > cur.DEMA10) and (prev.TEMA20 <= prev.DEMA10)
    flags["cross"] = bool(cross)
    if cross:
        score += W['cross']
    details['cross'] = {'ok': bool(cross), 'w': W['cross'], 'gain': W['cross'] if cross else 0}

    # 2) 거래량: 당일 > MA5*1.8 그리고 당일 > MA20*1.2 (둘 다)
    volx = (cur.VOL_MA5 and cur.volume >= config.vol_ma5_mult * cur.VOL_MA5) and \
           (df["volume"].iloc[-20:].mean() > 0 and cur.volume >= config.vol_ma20_mult * df["volume"].iloc[-20:].mean())
    flags["vol_expand"] = bool(volx)
    if volx:
        score += W['volume']
    details['volume'] = {'ok': bool(volx), 'w': W['volume'], 'gain': W['volume'] if volx else 0}

    # 3) MACD 조건 (+1) - 골든크로스 또는 상승 모멘텀
    macd_golden_cross = (cur.MACD_LINE > cur.MACD_SIGNAL) and (prev.MACD_LINE <= prev.MACD_SIGNAL)
    macd_line_up = cur.MACD_LINE > cur.MACD_SIGNAL  # MACD Line이 Signal 위에 있음
    macd_osc_ok = cur.MACD_OSC > config.macd_osc_min
    macd_ok = macd_golden_cross or macd_line_up or macd_osc_ok  # 세 조건 중 하나라도 만족
    flags["macd_ok"] = bool(macd_ok)
    flags["macd_golden_cross"] = bool(macd_golden_cross)
    flags["macd_line_up"] = bool(macd_line_up)
    if macd_ok:
        score += W['macd']
    details['macd'] = {'ok': bool(macd_ok), 'w': W['macd'], 'gain': W['macd'] if macd_ok else 0}

    # 4) RSI: 상승 초입 모멘텀 조건 (TEMA > DEMA 또는 수렴 후 상승)
    # RSI 모멘텀: 동적 rsi_threshold 사용 (market_condition 또는 config에서 가져옴)
    # market_condition이 있으면 동적 값 사용, 없으면 config 기본값 사용
    if market_condition and config.market_analysis_enable:
        rsi_threshold_for_momentum = market_condition.rsi_threshold
    else:
        rsi_threshold_for_momentum = config.rsi_threshold
    
    rsi_momentum = (cur.RSI_TEMA > cur.RSI_DEMA) or (abs(cur.RSI_TEMA - cur.RSI_DEMA) < 3 and cur.RSI_TEMA > rsi_threshold_for_momentum)
    rsi_ok = rsi_momentum
    
    flags["rsi_ok"] = bool(rsi_ok)
    flags["rsi_mode"] = "tema_dema_momentum"
    flags["rsi_thr"] = "momentum"
    if rsi_ok:
        score += W['rsi']
    details['rsi'] = {'ok': bool(rsi_ok), 'w': W['rsi'], 'gain': W['rsi'] if rsi_ok else 0}

    # 5) TEMA20 SLOPE > 0 AND 주가 > TEMA20 (+2)
    tema_slope_ok = (float(df.iloc[-1]["TEMA20_SLOPE20"]) > 0.001) and (cur.close > cur.TEMA20)
    flags["tema_slope_ok"] = bool(tema_slope_ok)
    if tema_slope_ok:
        score += W['tema_slope']
    details['tema_slope'] = {'ok': bool(tema_slope_ok), 'w': W['tema_slope'], 'gain': W['tema_slope'] if tema_slope_ok else 0}

    # 6) OBV SLOPE > 0.001 (+2) - 더 강한 자금 유입만 선택
    obv_slope_ok = float(df.iloc[-1]["OBV_SLOPE20"]) > 0.001
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

    # (선택) DEMA10 SLOPE > 0 AND 주가 > DEMA10 점수/필수 여부
    if "DEMA10_SLOPE20" not in df.columns:
        df["DEMA10_SLOPE20"] = linreg_slope(df["DEMA10"], 20)
    dema_slope_ok = (float(df.iloc[-1]["DEMA10_SLOPE20"]) > 0) and (cur.close > cur.DEMA10)
    flags["dema_slope_ok"] = bool(dema_slope_ok)
    details['dema_slope'] = {'ok': bool(dema_slope_ok), 'w': W['dema_slope'], 'gain': W['dema_slope'] if dema_slope_ok else 0}
    mode = str(getattr(config, 'require_dema_slope', 'optional')).lower()
    if mode == 'required' and not dema_slope_ok:
        flags["label"] = "제외"
        flags["match"] = False  # 제외 종목은 매칭되지 않음
        return 0, {**flags, 'details': details}
    elif mode == 'optional':
        if dema_slope_ok:
            score += W['dema_slope']
    # off: 무시

    # 위험도 정보 추가
    flags["risk_score"] = risk_score
    flags["risk_flags"] = risk_flags
    
    # 필터 정보 추가 (디버깅/튜닝 편의)
    flags.update({
        "overheated_rsi_tema": bool(overheat),
        "gap_now": round(float(gap_now), 4),
        "gap_ok": bool(gap_ok),
        "ext_pct": round(float(ext_pct), 4),
        "ext_ok": bool(ext_ok),
    })
    
    # ----- 신호 요건 상향 (동적 MIN_SIGNALS) -----
    # market_condition이 있으면 동적 조건 사용, 없으면 기본값 사용
    if market_condition and config.market_analysis_enable:
        min_signals = market_condition.min_signals
    else:
        min_signals = config.min_signals
    
    # 신호 개수 계산: 기본 4개 + 추가 신호 (OBV, TEMA slope, above_cnt)
    # 기본 신호 4개
    basic_signals = sum([
        bool(flags.get("cross", False)),      # 골든크로스
        bool(flags.get("vol_expand", False)),  # 거래량
        bool(flags.get("macd_ok", False)),    # MACD
        bool(flags.get("rsi_ok", False))      # RSI
    ])
    
    # 추가 신호 3개 (통과율이 높은 신호들)
    additional_signals = sum([
        bool(flags.get("obv_slope_ok", False)),    # OBV 상승 (73% 통과율)
        bool(flags.get("tema_slope_ok", False)),  # TEMA 상승 (68% 통과율)
        bool(flags.get("above_cnt5", False))      # 연속 상승 (68% 통과율)
    ])
    
    # 총 신호 개수 (기본 4개 + 추가 3개 = 최대 7개)
    signals_true = basic_signals + additional_signals
    flags["signals_count"] = signals_true
    flags["signals_basic"] = basic_signals
    flags["signals_additional"] = additional_signals
    flags["min_signals_required"] = min_signals
    
    # 신호 충족 여부 확인
    signals_sufficient = signals_true >= min_signals
    
    # 신호 충족 시 점수 기준 완화: 신호가 충족되면 점수 기준을 낮춤
    # 신호 3개 이상이면 10점 → 6점, 8점 → 4점으로 완화
    if signals_sufficient:
        # 신호 충족 시 점수 보너스 추가 (신호 개수에 비례)
        signal_bonus = max(0, (signals_true - min_signals) * 1)  # 추가 신호당 1점 보너스
        adjusted_score = score + signal_bonus
        flags["signal_bonus"] = signal_bonus
        flags["adjusted_score_for_signals"] = adjusted_score
    else:
        adjusted_score = score
        flags["signal_bonus"] = 0
        flags["adjusted_score_for_signals"] = score
    
    # 레이블링 (신호 우선, 점수 = 순위)
    # 신호 충족 = 무조건 후보군 포함 (점수 무관)
    # 점수 = 후보군 내에서 순위 매기기용 (높은 점수 우선)
    if signals_sufficient:
        # 신호 충족 = 후보군 (점수와 무관하게 매칭)
        flags["match"] = True
        flags["fallback"] = False
        
        # 점수는 순위 매기기용 (레이블만 구분)
        if adjusted_score >= 10:
            flags["label"] = "강한 매수"
        elif adjusted_score >= 8:
            flags["label"] = "매수 후보"
        elif adjusted_score >= 6:
            flags["label"] = "관심 종목"
        else:
            flags["label"] = "후보 종목"
    else:
        # 신호 미충족 = 후보군 아님 (점수와 무관하게 제외)
        flags["label"] = f"신호부족({signals_true}/{min_signals})"
        flags["match"] = False
        flags["fallback"] = False
        # 점수가 높아도 신호 미충족이면 제외 (신호 우선 원칙)
    
    # 위험도에 따른 점수 조정
    if risk_score > 0:
        adjusted_score = max(0, score - risk_score)
        flags["adjusted_score"] = adjusted_score
        details['total'] = int(adjusted_score)
        details['original_score'] = int(score)
        details['risk_penalty'] = risk_score
    else:
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


def apply_preset_to_runtime(cfg_overrides: dict):
    """
    이 함수는 run-time으로 전역/모듈에서 참조하는 임계값을 임시 덮어쓰기 위한 헬퍼입니다.
    프로젝트가 class Config를 쓴다면 인스턴스 값을 바꾸고, 모듈 상수면 globals() 업데이트 방식으로 반영.
    """
    from config import config
    for k, v in cfg_overrides.items():
        setattr(config, k, v)


def scan_one_symbol(code: str, base_date: str = None, market_condition=None) -> dict:
    """
    단일 종목 스캔 함수 (기존 스캔 로직을 함수로 분리)
    """
    try:
        from kiwoom_api import api
        df = api.get_ohlcv(code, config.ohlcv_count, base_date)
        if df.empty or len(df) < 21 or df[["open","high","low","close","volume"]].isna().any().any():
            return None
        
        # 인버스 ETF 필터링 (9월 손실 방지)
        stock_name = api.get_stock_name(code)
        if any(keyword in stock_name for keyword in config.inverse_etf_keywords):
            return None  # 인버스 ETF 즉시 제외
        
        # 금리/채권 ETF 필터링 (투자 가치 없음)
        if any(keyword in stock_name for keyword in config.bond_etf_keywords):
            return None  # 금리/채권 ETF 즉시 제외
        
        df = compute_indicators(df)
        # 종목명을 DataFrame에 추가
        df['name'] = stock_name
        
        # OHLCV 데이터로 등락률 계산 (유효한 전일 데이터 찾기)
        change_rate = 0.0
        if len(df) >= 2:
            current_close = float(df.iloc[-1]["close"])
            # 유효한 전일 종가 찾기 (최대 5일 전까지)
            prev_close = 0
            for i in range(2, min(6, len(df) + 1)):
                candidate_close = float(df.iloc[-i]["close"])
                if candidate_close > 0:
                    prev_close = candidate_close
                    break
            
            if prev_close > 0:
                change_rate = round(((current_close - prev_close) / prev_close) * 100, 2)
        
        # RSI 상한선 필터링 (과매수 구간 진입 방지)
        # market_condition이 있으면 동적 조정된 상한선 사용, 없으면 기본값 사용
        if market_condition and config.market_analysis_enable:
            # 시장 상황에 따라 RSI 상한선도 조정 (rsi_threshold + 여유분)
            # rsi_threshold는 신호 판단용, 상한선은 과매수 방지용이므로 더 높게 설정
            # 여유분을 15.0 → 25.0으로 증가 (더 많은 종목 통과)
            rsi_upper_limit = market_condition.rsi_threshold + 25.0  # 기본 70 = 57 + 13 → 82 = 57 + 25
        else:
            rsi_upper_limit = config.rsi_upper_limit
        
        cur = df.iloc[-1]
        if cur.RSI_TEMA > rsi_upper_limit:
            return None  # RSI 상한선 초과 종목 즉시 제외
        
        matched, sig_true, sig_total = match_stats(df, market_condition, stock_name)
        score, flags = score_conditions(df, market_condition)
        # 새로운 RSI 로직에서는 flags["match"]를 우선 사용
        matched = flags.get("match", bool(matched))
        
        if not matched:
            return None
            
        cur = df.iloc[-1]
        
        return {
            "ticker": code,
            "name": api.get_stock_name(code),
            "match": matched,
            "score": score,
            "indicators": {
                "TEMA": cur.TEMA20,
                "DEMA": cur.DEMA10,
                "MACD_OSC": cur.MACD_OSC,
                "MACD_LINE": cur.MACD_LINE,
                "MACD_SIGNAL": cur.MACD_SIGNAL,
                "RSI_TEMA": cur.RSI_TEMA,
                "RSI_DEMA": cur.RSI_DEMA,
                "OBV": cur.OBV,
                "VOL": cur.volume,
                "VOL_MA5": cur.VOL_MA5,
                "close": cur.close,
                "change_rate": change_rate,
            },
            "trend": {
                "TEMA20_SLOPE20": df.iloc[-1]["TEMA20_SLOPE20"],
                "OBV_SLOPE20": df.iloc[-1]["OBV_SLOPE20"],
                "ABOVE_CNT5": int((df["TEMA20"] > df["DEMA10"]).tail(5).sum()),
                "DEMA10_SLOPE20": df.iloc[-1]["DEMA10_SLOPE20"],
            },
            "strategy": strategy_text(df),
            "flags": flags,
            "score_label": flags.get("label", "제외"),
        }
    except Exception:
        return None


def scan_with_preset(universe_codes: List[str], preset_overrides: dict, base_date: str = None, market_condition=None) -> List[dict]:
    """
    프리셋을 적용하여 스캔을 실행하는 함수
    """
    
    # 1) preset 적용
    if preset_overrides:
        print(f"🔧 프리셋 적용: {preset_overrides}")
        apply_preset_to_runtime(preset_overrides)
        
        # market_condition에도 프리셋 반영 (동적 조건 우선 사용)
        if market_condition:
            from copy import deepcopy
            market_condition = deepcopy(market_condition)
            if 'min_signals' in preset_overrides:
                market_condition.min_signals = preset_overrides['min_signals']
            if 'vol_ma5_mult' in preset_overrides:
                market_condition.vol_ma5_mult = preset_overrides['vol_ma5_mult']
            if 'vol_ma20_mult' in preset_overrides:
                market_condition.vol_ma20_mult = preset_overrides.get('vol_ma20_mult', market_condition.vol_ma20_mult if hasattr(market_condition, 'vol_ma20_mult') else config.vol_ma20_mult)
            if 'gap_max' in preset_overrides:
                market_condition.gap_max = preset_overrides['gap_max']
            if 'ext_from_tema20_max' in preset_overrides:
                market_condition.ext_from_tema20_max = preset_overrides['ext_from_tema20_max']
            if 'require_dema_slope' in preset_overrides:
                # require_dema_slope는 config에만 적용
                pass

    # 2) 병렬 처리로 스캔 실행 (하드 컷 로직은 기존대로 유지)
    items = []
    matched_count = 0
    filtered_count = 0
    
    # 병렬 처리로 성능 개선 (최대 10개 워커)
    max_workers = min(10, len(universe_codes))
    
    # market_condition이 수정되었으면 수정된 버전 사용
    final_market_condition = market_condition
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 각 종목 스캔을 병렬로 실행
        future_to_code = {
            executor.submit(scan_one_symbol, code, base_date, final_market_condition): code
            for code in universe_codes
        }
        
        # 완료된 작업부터 결과 수집
        for future in concurrent.futures.as_completed(future_to_code):
            code = future_to_code[future]
            try:
                res = future.result()
                if res is None:
                    filtered_count += 1
                else:
                    items.append(res)
                    matched_count += 1
            except Exception as e:
                # 개별 종목 오류는 무시하고 계속 진행
                filtered_count += 1
                pass

    # 3) 정렬 및 상위 N개 자르기
    items.sort(key=lambda x: x["score"], reverse=True)
    
    print(f"📊 스캔 완료: {matched_count}개 매칭, {filtered_count}개 필터링, 총 {len(universe_codes)}개 중")
    return items


