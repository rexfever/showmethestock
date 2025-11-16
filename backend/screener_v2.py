"""
Second generation screener that exposes Trend / Momentum / Volume / RiskVol scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Optional

import numpy as np
import pandas as pd

from config import config
from indicators import (
    atr,
    dema_smooth,
    linreg_slope,
    macd,
    obv,
    rsi_dema,
    rsi_tema,
    tema_smooth,
)


@dataclass
class ScreenerParams:
    """Parameter overrides for ScreenerV2."""

    # Stage2 기본 유동성 컷
    min_turnover_krw: float = float(config.min_turnover_krw)
    # Stage1 완화 유동성 컷 (MarketCondition에서 계산된 값 사용)
    min_turnover_krw_stage1: float = float(config.min_turnover_krw) * 0.5
    min_price: float = float(config.min_price)
    rsi_threshold: float = 58.0
    # Stage 1: 최소 신호 수 (장세와 무관하게 항상 1로 운용)
    min_signals_stage1: int = 1
    # Stage 2: 엄격 필터용 최소 신호 수 (MarketCondition에 의해 2~3 수준으로 조정)
    min_signals: int = int(config.min_signals)
    macd_osc_min: float = float(config.macd_osc_min)
    vol_ma5_mult: float = float(config.vol_ma5_mult)
    vol_ma20_mult: float = float(config.vol_ma20_mult)
    overheat_rsi_tema: float = float(config.overheat_rsi_tema)
    overheat_vol_mult: float = float(config.overheat_vol_mult)
    gap_min: float = -1.0
    gap_max: float = 4.0
    ext_from_tema20_max: float = 3.0
    atr_pct_min: float = float(config.atr_pct_min * 100)  # convert to %
    atr_pct_max: float = float(config.atr_pct_max * 100)  # convert to %
    ema60_slope_min: float = 0.0
    tema20_slope_min: float = 0.0
    dema20_slope_min: float = -0.001
    require_dema_slope: str = "optional"
    score_cut: float = 10.0

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class ScreenerV2:
    """
    Implements the Trend / Momentum / Volume / RiskVol scoring model.
    """

    def __init__(self, params: Optional[ScreenerParams] = None):
        self.params = params or ScreenerParams()

    def evaluate(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        (기존 1-Stage) 단일 종목 스크리너 평가.
        신규 2-Stage 파이프라인(Stage1/Stage2)은
        사전 계산된 인디케이터 DataFrame을 대상으로
        별도의 evaluate_stage1/evaluate_stage2 함수를 사용한다.

        Args:
            prices: DataFrame with date, open, high, low, close, volume columns.
        """
        if prices is None or prices.empty:
            return pd.DataFrame()

        df = prices.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        if len(df) < 80:
            return pd.DataFrame()

        # 기존 evaluate는 인디케이터를 내부에서 계산하는
        # 1-Stage 레거시 인터페이스를 유지한다.
        # 신규 2-Stage 파이프라인에서는 scanner.compute_indicators()에서
        # 모든 인디케이터를 사전 계산한 뒤 evaluate_stage1/2를 사용한다.
        df["TEMA20"] = tema_smooth(df["close"], 20)
        df["DEMA20"] = dema_smooth(df["close"], 20)
        df["DEMA10"] = dema_smooth(df["close"], 10)
        df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
        df["EMA60"] = df["close"].ewm(span=60, adjust=False).mean()
        df["VOL_MA5"] = df["volume"].rolling(5).mean()
        df["VOL_MA20"] = df["volume"].rolling(20).mean()
        df["TURNOVER_MA20"] = (df["close"] * df["volume"]).rolling(20).mean()
        df["OBV"] = obv(df["close"], df["volume"])

        macd_line, macd_signal, macd_osc = macd(df["close"])
        df["MACD_LINE"] = macd_line
        df["MACD_SIGNAL"] = macd_signal
        df["MACD_OSC"] = macd_osc
        df["RSI_TEMA"] = rsi_tema(df["close"], 14)
        df["RSI_DEMA"] = rsi_dema(df["close"], 14)
        df["ATR"] = atr(df["high"], df["low"], df["close"], 14)
        df["ATR_PCT"] = (df["ATR"] / df["close"]) * 100
        df["EMA60_SLOPE"] = linreg_slope(df["EMA60"], 20)
        df["TEMA20_SLOPE"] = linreg_slope(df["TEMA20"], 20)
        df["DEMA20_SLOPE"] = linreg_slope(df["DEMA20"], 20)
        df["OBV_SLOPE"] = linreg_slope(df["OBV"], 20)
        df["GAP_PCT"] = ((df["close"] / df["EMA20"]) - 1.0) * 100
        df["EXT_TEMA20_PCT"] = ((df["close"] / df["TEMA20"]) - 1.0) * 100

        params = self.params

        # Hard filters
        df["turnover_ok"] = df["TURNOVER_MA20"] >= params.min_turnover_krw
        df["price_ok"] = df["close"] >= params.min_price
        df["gap_ok"] = (df["GAP_PCT"] >= params.gap_min) & (df["GAP_PCT"] <= params.gap_max)
        df["ext_ok"] = df["EXT_TEMA20_PCT"] <= params.ext_from_tema20_max
        df["atr_ok"] = (df["ATR_PCT"] >= params.atr_pct_min) & (df["ATR_PCT"] <= params.atr_pct_max)
        df["ema60_slope_ok"] = df["EMA60_SLOPE"] >= params.ema60_slope_min
        df["overheat"] = (
            (df["RSI_TEMA"] >= params.overheat_rsi_tema)
            & (df["VOL_MA5"] > 0)
            & (df["volume"] >= params.overheat_vol_mult * df["VOL_MA5"])
        )
        df["base_pass"] = (
            df["turnover_ok"]
            & df["price_ok"]
            & df["gap_ok"]
            & df["ext_ok"]
            & df["atr_ok"]
            & df["ema60_slope_ok"]
        )

        # Signal primitives
        cond_trend = (df["close"] > df["EMA60"]) & (df["TEMA20"] > df["DEMA20"])
        cond_macd = (df["MACD_OSC"] >= params.macd_osc_min) & (df["MACD_LINE"] > df["MACD_SIGNAL"])
        cond_rsi = (df["RSI_TEMA"] >= params.rsi_threshold) & (df["RSI_TEMA"] > df["RSI_DEMA"])
        cond_vol = (df["VOL_MA5"] > 0) & (df["volume"] >= params.vol_ma5_mult * df["VOL_MA5"])
        cond_vol_ma20 = (df["VOL_MA20"] > 0) & (
            df["volume"] >= params.vol_ma20_mult * df["VOL_MA20"]
        )

        df["signals_true"] = (
            cond_trend.astype(int)
            + cond_macd.astype(int)
            + cond_rsi.astype(int)
            + cond_vol.astype(int)
        )
        df["min_signal_ok"] = df["signals_true"] >= params.min_signals

        # Trend score (max 3)
        trend_score = (
            (df["EMA60_SLOPE"] >= params.ema60_slope_min).astype(int)
            + (df["TEMA20_SLOPE"] >= params.tema20_slope_min).astype(int)
            + (df["DEMA20_SLOPE"] >= params.dema20_slope_min).astype(int)
        )

        # Momentum score (max 3)
        momentum_score = cond_macd.astype(int) + cond_rsi.astype(int) + (
            df["MACD_OSC"] > 0
        ).astype(int)

        # Volume score (max 2)
        volume_score = cond_vol.astype(int) + cond_vol_ma20.astype(int)

        # RiskVol (max 2)
        risk_score = ((~df["overheat"]).astype(int) + df["atr_ok"].astype(int))

        df["trend_score"] = trend_score
        df["momentum_score"] = momentum_score
        df["volume_score"] = volume_score
        df["risk_score"] = risk_score
        df["score"] = trend_score + momentum_score + volume_score + risk_score
        df["score_cut"] = params.score_cut
        df["total_signals"] = 4

        require_mode = str(params.require_dema_slope).lower()
        if require_mode == "required":
            df["base_pass"] &= df["DEMA20_SLOPE"] >= params.dema20_slope_min

        df["signal"] = (
            df["base_pass"]
            & df["min_signal_ok"]
            & (~df["overheat"])
            & (df["score"] >= params.score_cut)
        )

        df["signal_step"] = np.where(df["signal"], 0, np.nan)

        return df


def _ensure_unified_slopes(df: pd.DataFrame) -> pd.DataFrame:
    """
    슬로프 컬럼 이름을 통일한다.
    - EMA60_SLOPE
    - TEMA20_SLOPE
    - DEMA20_SLOPE

    레거시 컬럼이 있는 경우 폴백 매핑을 적용한다.
    """
    # 레거시 대비 폴백
    if "TEMA20_SLOPE" not in df.columns and "TEMA20_SLOPE20" in df.columns:
        df["TEMA20_SLOPE"] = df["TEMA20_SLOPE20"]
    if "DEMA20_SLOPE" not in df.columns and "DEMA10_SLOPE20" in df.columns:
        df["DEMA20_SLOPE"] = df["DEMA10_SLOPE20"]

    # EMA60_SLOPE이 없으면 EMA60 기준으로 다시 계산
    if "EMA60_SLOPE" not in df.columns and "EMA60" in df.columns:
        df["EMA60_SLOPE"] = linreg_slope(df["EMA60"], 20)

    return df


def evaluate_stage1(df: pd.DataFrame, params: ScreenerParams) -> pd.DataFrame:
    """
    Stage 1 - Wide Universe Scanner

    - 기본 추세/변동성/유동성 필터만 적용
    - MACD/RSI/거래량 신호는 선택적(signals_true ≥ 1)
    - 점수/과열(score_cut, overheat) 필터는 사용하지 않음
    - 인디케이터는 scanner.compute_indicators()에서 사전 계산되었다고 가정
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

    if len(df) < 80:
        return pd.DataFrame()

    df = _ensure_unified_slopes(df)

    # --- 하드 필터 (Stage1 전용, 매우 완화된 유동성/변동성 필터만 사용) ---
    df["turnover_ok"] = df["TURNOVER_MA20"] >= params.min_turnover_krw_stage1
    df["price_ok"] = df["close"] >= params.min_price

    # Stage2용 ATR 필터(기존 로직 유지) - score/risk 계산에서 사용
    df["atr_ok"] = (df["ATR_PCT"] >= params.atr_pct_min) & (
        df["ATR_PCT"] <= params.atr_pct_max
    )

    # Stage1 전용 ATR 필터 (매우 느슨한 범위)
    df["atr_ok_stage1"] = (
        (df["ATR_PCT"] >= getattr(params, "atr_pct_min_stage1", params.atr_pct_min))
        & (df["ATR_PCT"] <= getattr(params, "atr_pct_max_stage1", params.atr_pct_max))
    )

    # Stage1 base_pass는 turnover / price / atr_stage1 만 사용
    df["base_pass"] = df["turnover_ok"] & df["price_ok"] & df["atr_ok_stage1"]

    # 최근 3봉 중 한 번이라도 base_pass=True면 Stage1 후보로 인정
    df["base_pass_recent"] = df["base_pass"].rolling(window=3, min_periods=1).max()

    # --- Stage1 디버그 로그 (base_pass 전체/최근/마지막 봉 상태 출력) ---
    total = len(df)
    if total > 0:
        base_pass_rows = int(df["base_pass"].sum())
        recent_rows = int((df["base_pass_recent"] == 1).sum())
        print(f"[STAGE1] base_pass_rows = {base_pass_rows} / {total}, recent={recent_rows}/{total}")
        last = df.iloc[-1]
        print(
            "[STAGE1-LAST] base_pass=",
            bool(last.get("base_pass", False)),
            "base_pass_recent=",
            bool(last.get("base_pass_recent", False)),
            "turnover_ok=",
            bool(last.get("turnover_ok", False)),
            "atr_ok_stage1=",
            bool(last.get("atr_ok_stage1", False)),
        )

    # Stage1은 MACD/RSI/VOL 신호를 전혀 요구하지 않는다.
    # 최근 3봉 안에 base_pass=True가 한 번이라도 있으면 Stage1 신호로 간주.
    df["signal_stage1"] = df["base_pass_recent"] == 1

    return df


def evaluate_stage2(df: pd.DataFrame, params: ScreenerParams) -> pd.DataFrame:
    """
    Stage 2 - High-Quality Signal Filter

    - 반드시 Stage1 결과(signal_stage1=True) 위에서만 동작해야 한다.
    - 점수(Trend/Momentum/Volume/Risk) 계산 및 score_cut 적용
    - 과열(overheat) 필터 및 min_signals 적용
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

    if len(df) < 80:
        return pd.DataFrame()

    df = _ensure_unified_slopes(df)

    # Stage1 필터를 통과한 구간만 Stage2 대상으로 삼는다.
    if "signal_stage1" in df.columns:
        base_mask = df["signal_stage1"].astype(bool)
        if not base_mask.any():
            # Stage1 후보가 없다면 바로 반환
            df["signal_stage2"] = False
            return df
    else:
        # 방어적: signal_stage1이 없으면 전체를 대상으로 보지만,
        # 정상 파이프라인에서는 항상 Stage1 이후에만 호출된다.
        base_mask = pd.Series(True, index=df.index)

    # --- 신호 프리미티브 (Stage2용) ---
    cond_trend = (df["close"] > df["EMA60"]) & (df["TEMA20"] > df["DEMA20"])
    cond_macd = (df["MACD_OSC"] >= params.macd_osc_min) & (df["MACD_LINE"] > df["MACD_SIGNAL"])
    cond_rsi = (df["RSI_TEMA"] >= params.rsi_threshold) & (df["RSI_TEMA"] > df["RSI_DEMA"])
    cond_vol = (df["VOL_MA5"] > 0) & (df["volume"] >= params.vol_ma5_mult * df["VOL_MA5"])
    cond_vol_ma20 = (df["VOL_MA20"] > 0) & (
        df["volume"] >= params.vol_ma20_mult * df["VOL_MA20"]
    )

    df["cond_trend"] = cond_trend
    df["cond_macd"] = cond_macd
    df["cond_rsi"] = cond_rsi
    df["cond_vol"] = cond_vol
    df["cond_vol_ma20"] = cond_vol_ma20

    df["signals_true"] = (
        cond_trend.astype(int)
        + cond_macd.astype(int)
        + cond_rsi.astype(int)
        + cond_vol.astype(int)
    )

    df["min_signal_ok"] = df["signals_true"] >= params.min_signals

    # --- 과열 및 리스크 필터 ---
    df["overheat"] = (
        (df["RSI_TEMA"] >= params.overheat_rsi_tema)
        & (df["VOL_MA5"] > 0)
        & (df["volume"] >= params.overheat_vol_mult * df["VOL_MA5"])
    )

    # Trend score (max 3)
    trend_score = (
        (df["EMA60_SLOPE"] >= params.ema60_slope_min).astype(int)
        + (df["TEMA20_SLOPE"] >= params.tema20_slope_min).astype(int)
        + (df["DEMA20_SLOPE"] >= params.dema20_slope_min).astype(int)
    )

    # Momentum score (max 3)
    momentum_score = cond_macd.astype(int) + cond_rsi.astype(int) + (
        df["MACD_OSC"] > 0
    ).astype(int)

    # Volume score (max 2)
    volume_score = cond_vol.astype(int) + cond_vol_ma20.astype(int)

    # RiskVol (max 2, 값이 작을수록 안전)
    # - 과열이 아니고(0), ATR 필터 통과(0)일 때 risk_score가 가장 낮게 나오도록 구성
    risk_score = df["overheat"].astype(int) + (~df["atr_ok"]).astype(int)

    df["trend_score"] = trend_score
    df["momentum_score"] = momentum_score
    df["volume_score"] = volume_score
    df["risk_score"] = risk_score
    df["score"] = trend_score + momentum_score + volume_score + risk_score
    df["score_cut"] = params.score_cut
    df["total_signals"] = 4

    require_mode = str(params.require_dema_slope).lower()
    if require_mode == "required":
        base_mask &= df["DEMA20_SLOPE"] >= params.dema20_slope_min

    # 최종 Stage2 신호
    df["signal_stage2"] = (
        base_mask
        & df["min_signal_ok"]
        & (~df["overheat"])
        & (df["score"] >= params.score_cut)
    )

    return df


