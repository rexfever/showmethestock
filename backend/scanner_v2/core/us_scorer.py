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
        # USD 기준 필터 값 (미국 주식 전용 설정 우선 사용)
        self.min_turnover_usd = getattr(config, 'us_min_turnover_usd', 2000000)  # $2M
        self.min_price_usd = getattr(config, 'us_min_price_usd', 5.0)  # $5
    
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
        
        # 과열 (미국 주식 전용 설정 사용)
        overheat_rsi = getattr(self.config, 'us_overheat_rsi_tema', 75)
        overheat_vol_mult = getattr(self.config, 'us_overheat_vol_mult', 4.0)
        overheat = (
            (cur.get("RSI_TEMA", 0) >= overheat_rsi) and
            (cur.get("VOL_MA5", 0) and cur.get("volume", 0) >= overheat_vol_mult * cur.get("VOL_MA5", 0))
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
            # 미국 주식 전용 설정 사용
            gap_max = getattr(self.config, 'us_gap_max', 0.03)
            ext_max = getattr(self.config, 'us_ext_from_tema20_max', 0.05)
        
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
        
        # 2) 거래량 (미국 주식 전용 설정 사용)
        vol_ma5_mult = getattr(self.config, 'us_vol_ma5_mult', 2.0)
        vol_ma20_mult = getattr(self.config, 'us_vol_ma20_mult', 1.0)
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
        
        # 4) RSI (미국 주식 전용 설정 사용)
        if market_condition and market_analysis_enable:
            rsi_threshold = market_condition.rsi_threshold
        else:
            rsi_threshold = getattr(self.config, 'us_rsi_threshold', 60)
        
        rsi_momentum = (cur.get("RSI_TEMA", 0) > cur.get("RSI_DEMA", 0)) or (abs(cur.get("RSI_TEMA", 0) - cur.get("RSI_DEMA", 0)) < 3 and cur.get("RSI_TEMA", 0) > rsi_threshold)
        flags["rsi_ok"] = bool(rsi_momentum)
        flags["rsi_tema"] = cur.get("RSI_TEMA", 0)  # 전략 분류에 사용
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
        # 단, 저점수 종목은 기본 신호 최소 2개 추가 요구
        if signals_sufficient and score < 4:
            # 저점수 종목은 기본 신호 최소 2개 추가 요구
            if basic_signals < 2:
                signals_sufficient = False
        
        flags["match"] = signals_sufficient
        flags["signals_count"] = signals_true
        flags["signals_basic"] = basic_signals
        flags["signals_additional"] = additional_signals
        flags["min_signals_required"] = min_signals
        
        # 위험도 점수 계산
        risk_score, risk_flags = self._calculate_risk_score(df)
        
        # 6점 이상 종목에 추가 필터링 (점수 = 위험도 역설 해결)
        # 고점수 = 높은 위험도이므로, 더 강한 위험도 차감 필요
        if score >= 6:
            cur = df.iloc[-1]
            additional_risk = 0
            
            # RSI 70 이상 추가 차감 (강화)
            rsi_tema = cur.get("RSI_TEMA", 0)
            if rsi_tema >= 75:
                additional_risk += 3  # RSI 75 이상: 3점 추가 차감 (강화)
            elif rsi_tema >= 70:
                additional_risk += 2  # RSI 70 이상: 2점 추가 차감 (강화)
            
            # 거래량 급증 추가 차감 (강화)
            vol_ma5 = cur.get("VOL_MA5", 0)
            if vol_ma5 > 0:
                vol_ratio = cur.get("volume", 0) / vol_ma5
                if vol_ratio >= 3.0:
                    additional_risk += 3  # 거래량 3배 이상: 3점 추가 차감 (강화)
                elif vol_ratio >= 2.5:
                    additional_risk += 2  # 거래량 2.5배 이상: 2점 추가 차감 (강화)
            
            # 이격률 과도 추가 차감 (강화)
            tema20 = cur.get("TEMA20", 0)
            if tema20 > 0:
                ext_pct = (cur.get("close", 0) - tema20) / tema20
                if ext_pct >= 0.08:
                    additional_risk += 3  # 8% 이상 이격: 3점 추가 차감 (강화)
                elif ext_pct >= 0.05:
                    additional_risk += 2  # 5% 이상 이격: 2점 추가 차감 (강화)
            
            # 과열 상태 종합 판단: 여러 위험 신호가 동시에 있으면 추가 차감
            overheat_count = sum([
                rsi_tema >= 70,
                vol_ratio >= 2.5 if vol_ma5 > 0 else False,
                ext_pct >= 0.05 if tema20 > 0 else False
            ])
            if overheat_count >= 2:  # 2개 이상 위험 신호
                additional_risk += 2  # 과열 상태 추가 차감
            
            risk_score += additional_risk
            risk_flags["additional_risk_6plus"] = additional_risk
        
        # 위험도 차감 (점수 = 위험도 역설 해결: 고점수 = 높은 위험도)
        # 점수가 높을수록 위험도가 높으므로, 위험도 차감을 더 강하게 적용
        risk_multiplier = 1.0
        if score >= 8:
            # 고점수 종목은 위험도 차감을 2.0배 적용 (고점수 = 높은 위험도)
            risk_multiplier = 2.0
        elif score >= 6:
            # 중고점수 종목은 위험도 차감을 1.5배 적용 (고점수 = 높은 위험도)
            risk_multiplier = 1.5
        
        adjusted_risk_score = int(risk_score * risk_multiplier)
        adjusted_score = score - adjusted_risk_score
        
        # 저점수 종목 품질 검증 강화 (0-4점 구간 성과 악화 해결)
        # 기본 신호(골든크로스, 거래량, MACD, RSI) 중 최소 2개 이상 요구
        if adjusted_score < 4:
            basic_signals_count = sum([
                bool(flags.get("cross")),
                bool(flags.get("vol_expand")),
                bool(flags.get("macd_ok")),
                bool(flags.get("rsi_ok"))
            ])
            # 기본 신호가 2개 미만이면 점수를 0으로 조정 (필터링)
            if basic_signals_count < 2:
                adjusted_score = 0
                flags["low_score_filtered"] = True
                flags["low_score_reason"] = f"기본 신호 부족 ({basic_signals_count}개)"
        
        # 위험도 차감 정보 저장
        flags["risk_score"] = risk_score
        flags["risk_multiplier"] = risk_multiplier
        flags["adjusted_risk_score"] = adjusted_risk_score
        
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
        """위험도 점수 계산 (과매수 상태 강화 차감)"""
        if len(df) < 21:
            return 0, {}
        
        cur = df.iloc[-1]
        risk_score = 0
        risk_flags = {}
        
        # 1. 과매수 구간 위험 (최적화: 위험도 차감 완화 - 성과 분석 기반)
        rsi_tema = cur.get("RSI_TEMA", 0)
        if rsi_tema > 80:
            # RSI 80 이상: 1점 차감 (최적화: 2점 → 1점, 성과 개선을 위해 완화)
            risk_score += 1
            risk_flags["rsi_overbought"] = True
        elif rsi_tema > 75:
            # RSI 75-80: 0점 차감 (최적화: 1점 → 0점, 과도한 차감 방지)
            risk_flags["rsi_overbought"] = False
        elif rsi_tema > 70:
            # RSI 70-75: 0점 차감 (과도한 차감 방지)
            risk_flags["rsi_elevated"] = False
        else:
            risk_flags["rsi_overbought"] = False
            risk_flags["rsi_elevated"] = False
        
        # 2. 거래량 급증 위험 (강화: 더 엄격한 기준)
        vol_spike_threshold = getattr(self.config, 'vol_spike_threshold', 3.0)
        vol_ma5 = cur.get("VOL_MA5", 0)
        if vol_ma5 > 0:
            vol_ratio = cur.get("volume", 0) / vol_ma5
            if vol_ratio >= vol_spike_threshold * 1.5:
                # 거래량이 평균의 4.5배 이상: 1점 차감 (최적화: 2점 → 1점, 성과 개선을 위해 완화)
                risk_score += 1
                risk_flags["vol_spike"] = True
            elif vol_ratio >= vol_spike_threshold:
                # 거래량이 평균의 3배 이상: 0점 차감 (최적화: 1점 → 0점, 과도한 차감 방지)
                risk_flags["vol_spike"] = False
            else:
                risk_flags["vol_spike"] = False
        else:
            risk_flags["vol_spike"] = False
        
        # 3. 모멘텀 지속성 부족 위험 (강화)
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
            # 모멘텀 약화: 1점 차감 (최적화: 2점 → 1점, 성과 개선을 위해 완화)
            risk_score += 1
        
        # 4. 가격 급등 후 조정 위험 (강화)
        recent_up_days = 0
        for i in range(min(5, len(df) - 1)):
            if df.iloc[-(i+1)].get("close", 0) > df.iloc[-(i+2)].get("close", 0):
                recent_up_days += 1
        
        price_exhaustion = recent_up_days >= 4
        risk_flags["price_exhaustion"] = price_exhaustion
        if price_exhaustion:
            # 가격 고갈: 1점 차감 (최적화: 2점 → 1점, 성과 개선을 위해 완화)
            risk_score += 1
        
        # 5. 신규: 이격률 과도 위험 (TEMA20 대비 가격 상승률)
        tema20 = cur.get("TEMA20", 0)
        if tema20 > 0:
            ext_pct = (cur.get("close", 0) - tema20) / tema20
            if ext_pct > 0.08:  # 8% 이상 이격
                risk_score += 0  # 최적화: 1점 → 0점 (과도한 차감 방지)
                risk_flags["extreme_extension"] = False
            elif ext_pct > 0.05:  # 5-8% 이격
                risk_score += 0  # 과도한 차감 방지
                risk_flags["extreme_extension"] = False
            else:
                risk_flags["extreme_extension"] = False
        
        # 6. 신규: 점수와 RSI 불일치 위험 (점수가 높은데 RSI도 높으면 위험)
        # 이건 점수 계산 후에 체크해야 하므로 별도 로직으로 처리
        
        return risk_score, risk_flags

