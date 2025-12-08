"""
미국 주식 점수 계산 모듈
USD 기준으로 점수 계산
"""
import pandas as pd
from typing import Dict, Tuple, Optional
from market_analyzer import MarketCondition


class USScorer:
    """미국 주식 점수 계산기 (USD 기준)"""
    
    def __init__(self, config):
        self.config = config
        # USD 기준 필터 값
        self.min_turnover_usd = getattr(config, 'min_turnover_usd', 1000000)  # $1M
        self.min_price_usd = getattr(config, 'min_price_usd', 5.0)  # $5
    
    def calculate_score(self, df: pd.DataFrame, market_condition: Optional[MarketCondition] = None) -> Tuple[float, Dict]:
        """
        점수 계산 - USD 기준
        
        Args:
            df: 지표가 계산된 데이터프레임
            market_condition: 시장 조건 (선택)
            
        Returns:
            (score: float, flags: Dict)
        """
        if len(df) < 21:
            return 0, {}
        
        cur = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 하드 필터 재확인 (점수 계산 단계) - USD 기준
        # 유동성
        if len(df) >= 20:
            # USD 기준 거래대금 계산
            avg_turnover = (df["close"].iloc[-20:] * df["volume"].iloc[-20:]).mean()
            if avg_turnover < self.min_turnover_usd:
                return 0, {"label": "유동성부족", "match": False}
        
        # 가격 하한 (USD 기준)
        if cur.get("close", 0) < self.min_price_usd:
            return 0, {"label": "저가종목", "match": False}
        
        # 과열
        overheat = (
            (cur.get("RSI_TEMA", 0) >= self.config.overheat_rsi_tema) and
            (cur.get("VOL_MA5", 0) and cur.get("volume", 0) >= self.config.overheat_vol_mult * cur.get("VOL_MA5", 0))
        )
        if overheat:
            return 0, {"label": "과열", "match": False}
        
        # 갭/이격
        gap_now = (cur.get("TEMA20", 0) - cur.get("DEMA10", 0)) / cur.get("close", 1) if cur.get("close", 0) else 0.0
        ext_pct = (cur.get("close", 0) - cur.get("TEMA20", 0)) / cur.get("TEMA20", 1) if cur.get("TEMA20", 0) else 0.0
        
        if market_condition and getattr(self.config, 'market_analysis_enable', True):
            gap_max = market_condition.gap_max
            ext_max = market_condition.ext_from_tema20_max
        else:
            gap_max = getattr(self.config, 'gap_max', 0.015)
            ext_max = getattr(self.config, 'ext_from_tema20_max', 0.015)
        
        # 갭 필터: 음수 갭 허용 (최대값만 체크)
        gap_ok = (gap_now <= gap_max)
        ext_ok = (ext_pct <= ext_max)
        if not (gap_ok and ext_ok):
            return 0, {"label": "갭/이격불량", "match": False}
        
        # 점수 계산 (한국형 Scorer와 동일한 로직)
        flags = {}
        score = 0
        details = {}
        
        # 가중치
        W = self._get_weights()
        
        # 1) 골든크로스
        cross = (cur.get("TEMA20", 0) > cur.get("DEMA10", 0)) and (prev.get("TEMA20", 0) <= prev.get("DEMA10", 0))
        flags["cross"] = bool(cross)
        if cross:
            score += W['cross']
        details['cross'] = {'ok': bool(cross), 'w': W['cross'], 'gain': W['cross'] if cross else 0}
        
        # 2) 거래량
        vol_ma5_mult = getattr(self.config, 'vol_ma5_mult', 2.5)
        vol_ma20_mult = getattr(self.config, 'vol_ma20_mult', 1.2)
        volx = (cur.get("VOL_MA5", 0) and cur.get("volume", 0) >= vol_ma5_mult * cur.get("VOL_MA5", 0)) and \
               (df["volume"].iloc[-20:].mean() > 0 and cur.get("volume", 0) >= vol_ma20_mult * df["volume"].iloc[-20:].mean())
        flags["vol_expand"] = bool(volx)
        if volx:
            score += W['volume']
        details['volume'] = {'ok': bool(volx), 'w': W['volume'], 'gain': W['volume'] if volx else 0}
        
        # 3) MACD
        macd_golden_cross = (cur.get("MACD_LINE", 0) > cur.get("MACD_SIGNAL", 0)) and (prev.get("MACD_LINE", 0) <= prev.get("MACD_SIGNAL", 0))
        macd_line_up = cur.get("MACD_LINE", 0) > cur.get("MACD_SIGNAL", 0)
        market_analysis_enable = getattr(self.config, 'market_analysis_enable', True)
        macd_osc_min = market_condition.macd_osc_min if market_condition and market_analysis_enable else getattr(self.config, 'macd_osc_min', 0.0)
        macd_osc_ok = cur.get("MACD_OSC", 0) > macd_osc_min
        macd_ok = macd_golden_cross or macd_line_up or macd_osc_ok
        flags["macd_ok"] = bool(macd_ok)
        if macd_ok:
            score += W['macd']
        details['macd'] = {'ok': bool(macd_ok), 'w': W['macd'], 'gain': W['macd'] if macd_ok else 0}
        
        # 4) RSI
        if market_condition and market_analysis_enable:
            rsi_threshold = market_condition.rsi_threshold
        else:
            rsi_threshold = getattr(self.config, 'rsi_threshold', 58)
        
        rsi_momentum = (cur.get("RSI_TEMA", 0) > cur.get("RSI_DEMA", 0)) or (abs(cur.get("RSI_TEMA", 0) - cur.get("RSI_DEMA", 0)) < 3 and cur.get("RSI_TEMA", 0) > rsi_threshold)
        flags["rsi_ok"] = bool(rsi_momentum)
        if rsi_momentum:
            score += W['rsi']
        details['rsi'] = {'ok': bool(rsi_momentum), 'w': W['rsi'], 'gain': W['rsi'] if rsi_momentum else 0}
        
        # 5) 추세 지표
        tema_slope_ok = (df.iloc[-1].get("TEMA20_SLOPE20", 0) > 0.001) and (cur.get("close", 0) > cur.get("TEMA20", 0))
        flags["tema_slope_ok"] = bool(tema_slope_ok)
        if tema_slope_ok:
            score += W['tema_slope']
        details['tema_slope'] = {'ok': bool(tema_slope_ok), 'w': W['tema_slope'], 'gain': W['tema_slope'] if tema_slope_ok else 0}
        
        obv_slope_ok = df.iloc[-1]["OBV_SLOPE20"] > 0.001
        flags["obv_slope_ok"] = bool(obv_slope_ok)
        if obv_slope_ok:
            score += W['obv_slope']
        details['obv_slope'] = {'ok': bool(obv_slope_ok), 'w': W['obv_slope'], 'gain': W['obv_slope'] if obv_slope_ok else 0}
        
        above_cnt = int((df["TEMA20"] > df["DEMA10"]).tail(5).sum())
        above_cnt5_ok = above_cnt >= 3
        flags["above_cnt5_ok"] = bool(above_cnt5_ok)
        if above_cnt5_ok:
            score += W['above_cnt5']
        details['above_cnt5'] = {'ok': bool(above_cnt5_ok), 'w': W['above_cnt5'], 'gain': W['above_cnt5'] if above_cnt5_ok else 0}
        
        dema_slope_ok = df.iloc[-1]["DEMA10_SLOPE20"] > 0.001
        flags["dema_slope_ok"] = bool(dema_slope_ok)
        if dema_slope_ok:
            score += W['dema_slope']
        details['dema_slope'] = {'ok': bool(dema_slope_ok), 'w': W['dema_slope'], 'gain': W['dema_slope'] if dema_slope_ok else 0}
        
        # 신호 충족 여부 확인
        basic_signals = sum([
            bool(flags.get("cross")),
            bool(flags.get("vol_expand")),
            bool(flags.get("macd_ok")),
            bool(flags.get("rsi_ok"))
        ])
        
        additional_signals = sum([
            bool(flags.get("tema_slope_ok")),
            bool(flags.get("obv_slope_ok")),
            bool(flags.get("above_cnt5_ok"))
        ])
        
        signals_true = basic_signals + additional_signals
        
        # min_signals 가져오기
        if market_condition and market_analysis_enable:
            min_signals = market_condition.min_signals
        else:
            min_signals = getattr(self.config, 'min_signals', 3)
        
        signals_sufficient = signals_true >= min_signals
        
        # 신호 우선 원칙: 신호 충족 = 후보군 (점수 무관)
        flags["match"] = signals_sufficient
        flags["signals_count"] = signals_true
        flags["signals_basic"] = basic_signals
        flags["signals_additional"] = additional_signals
        flags["min_signals_required"] = min_signals
        
        # 위험도 점수 계산
        risk_score, risk_flags = self._calculate_risk_score(df)
        
        # 위험도 차감
        adjusted_score = score - risk_score
        
        # 전략 결정
        from .strategy import determine_trading_strategy
        strategy, target_profit, stop_loss, holding_period = determine_trading_strategy(flags, adjusted_score)
        
        # 레이블 설정
        if adjusted_score >= 10:
            flags["label"] = "강한 매수"
        elif adjusted_score >= 8:
            flags["label"] = "매수 후보"
        elif adjusted_score >= 6:
            flags["label"] = "관심 종목"
        else:
            flags["label"] = "후보 종목"
        
        # 전략 정보
        flags["trading_strategy"] = strategy
        flags["target_profit"] = target_profit
        flags["stop_loss"] = stop_loss
        flags["holding_period"] = holding_period
        
        # 디버깅 정보
        flags["momentum_score"] = sum([
            3 if flags.get("cross") else 0,
            2 if flags.get("vol_expand") else 0,
            1 if flags.get("macd_ok") else 0,
            1 if flags.get("rsi_ok") else 0
        ])
        flags["trend_score"] = sum([
            2 if flags.get("tema_slope_ok") else 0,
            2 if flags.get("obv_slope_ok") else 0,
            2 if flags.get("above_cnt5_ok") else 0,
            2 if flags.get("dema_slope_ok") else 0
        ])
        
        flags["details"] = details
        flags["risk_score"] = risk_score
        
        return adjusted_score, flags
    
    def _get_weights(self) -> Dict[str, float]:
        """점수 가중치 가져오기"""
        if hasattr(self.config, 'get_weights'):
            return self.config.get_weights()
        elif hasattr(self.config, 'dynamic_score_weights'):
            return self.config.dynamic_score_weights()
        else:
            return {
                'cross': getattr(self.config, 'score_w_cross', 3),
                'volume': getattr(self.config, 'score_w_vol', 2),
                'macd': getattr(self.config, 'score_w_macd', 1),
                'rsi': getattr(self.config, 'score_w_rsi', 1),
                'tema_slope': getattr(self.config, 'score_w_tema_slope', 2),
                'dema_slope': getattr(self.config, 'score_w_dema_slope', 2),
                'obv_slope': getattr(self.config, 'score_w_obv_slope', 2),
                'above_cnt5': getattr(self.config, 'score_w_above_cnt', 2),
            }
    
    def _calculate_risk_score(self, df: pd.DataFrame) -> Tuple[int, Dict]:
        """위험도 점수 계산 (한국형과 동일)"""
        if len(df) < 21:
            return 0, {}
        
        cur = df.iloc[-1]
        risk_score = 0
        risk_flags = {}
        
        # 1. 과매수 구간 위험 (RSI_TEMA > 80)
        rsi_overbought = cur.get("RSI_TEMA", 0) > 80
        risk_flags["rsi_overbought"] = rsi_overbought
        if rsi_overbought:
            risk_score += 2
        
        # 2. 거래량 급증 위험 (평균 대비 3배 이상)
        vol_spike_threshold = getattr(self.config, 'vol_spike_threshold', 3.0)
        vol_spike = cur.get("volume", 0) > (cur.get("VOL_MA5", 0) * vol_spike_threshold if cur.get("VOL_MA5", 0) else cur.get("volume", 0))
        risk_flags["vol_spike"] = vol_spike
        if vol_spike:
            risk_score += 2
        
        # 3. 모멘텀 지속성 부족 위험 (MACD 상승 기간이 짧음)
        macd_trend_duration = 0
        for i in range(min(10, len(df) - 1)):
            if df.iloc[-(i+1)].get("MACD_OSC", 0) > df.iloc[-(i+2)].get("MACD_OSC", 0):
                macd_trend_duration += 1
            else:
                break
        
        momentum_duration_min = getattr(self.config, 'momentum_duration_min', 3)
        momentum_weak = macd_trend_duration < momentum_duration_min
        risk_flags["momentum_weak"] = momentum_weak
        if momentum_weak:
            risk_score += 1
        
        # 4. 가격 급등 후 조정 위험 (최근 5일 중 4일 이상 상승)
        recent_up_days = 0
        for i in range(min(5, len(df) - 1)):
            if df.iloc[-(i+1)].get("close", 0) > df.iloc[-(i+2)].get("close", 0):
                recent_up_days += 1
        
        price_exhaustion = recent_up_days >= 4
        risk_flags["price_exhaustion"] = price_exhaustion
        if price_exhaustion:
            risk_score += 1
        
        return risk_score, risk_flags

