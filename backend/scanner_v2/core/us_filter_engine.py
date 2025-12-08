"""
미국 주식 필터링 엔진 모듈
USD 기준으로 필터링
"""
import pandas as pd
from typing import Tuple, Optional
from market_analyzer import MarketCondition
from indicators import atr


class USFilterEngine:
    """미국 주식 필터링 엔진 (USD 기준)"""
    
    def __init__(self, config):
        self.config = config
        # market_analysis_enable 체크용
        self.market_analysis_enable = getattr(config, 'market_analysis_enable', True)
        
        # USD 기준 필터 값 (환율 1300 기준)
        # 한국: 10억원 → 미국: 약 $770K (더 보수적으로 $1M)
        # 한국: 2,000원 → 미국: $5
        self.min_turnover_usd = getattr(config, 'min_turnover_usd', 1000000)  # $1M
        self.min_price_usd = getattr(config, 'min_price_usd', 5.0)  # $5
    
    def apply_hard_filters(self, df: pd.DataFrame, stock_name: str, market_condition: Optional[MarketCondition] = None) -> bool:
        """
        하드 필터 적용 (통과/실패) - USD 기준
        
        Args:
            df: OHLCV 데이터프레임
            stock_name: 종목명
            market_condition: 시장 조건 (선택)
            
        Returns:
            True: 통과, False: 제외
        """
        if len(df) < 21:
            return False
        
        cur = df.iloc[-1]
        
        # 1. 인버스 ETF 필터링 (미국 ETF 키워드)
        us_inverse_keywords = ["inverse", "short", "bear", "2x", "3x", "leveraged"]
        if any(keyword.lower() in stock_name.lower() for keyword in us_inverse_keywords):
            return False
        
        # 2. 금리/채권 ETF 필터링 (미국 ETF 키워드)
        us_bond_keywords = ["bond", "treasury", "treasuries", "corporate bond"]
        if any(keyword.lower() in stock_name.lower() for keyword in us_bond_keywords):
            return False
        
        # 3. RSI 상한선 필터링
        if market_condition and self.market_analysis_enable:
            rsi_upper_limit = market_condition.rsi_threshold + 25.0
        else:
            rsi_upper_limit = self.config.rsi_upper_limit
        
        if cur.get("RSI_TEMA", 0) > rsi_upper_limit:
            return False
        
        # 4. 유동성 필터 (USD 기준)
        if len(df) >= 20:
            # USD 기준 거래대금 계산 (close * volume)
            avg_turnover = (df["close"].iloc[-20:] * df["volume"].iloc[-20:]).mean()
            if avg_turnover < self.min_turnover_usd:
                return False
        
        # 5. 가격 하한 (USD 기준)
        if cur.get("close", 0) < self.min_price_usd:
            return False
        
        # 6. 과열 필터
        overheat = (
            (cur.get("RSI_TEMA", 0) >= self.config.overheat_rsi_tema) and
            (cur.get("VOL_MA5", 0) and cur.get("volume", 0) >= self.config.overheat_vol_mult * cur.get("VOL_MA5", 0))
        )
        if overheat:
            return False
        
        # 7. 갭/이격 필터
        gap_now = (cur.get("TEMA20", 0) - cur.get("DEMA10", 0)) / cur.get("close", 1) if cur.get("close", 0) else 0.0
        ext_pct = (cur.get("close", 0) - cur.get("TEMA20", 0)) / cur.get("TEMA20", 1) if cur.get("TEMA20", 0) else 0.0
        
        if market_condition and self.market_analysis_enable:
            gap_max = market_condition.gap_max
            ext_max = market_condition.ext_from_tema20_max
        else:
            gap_max = getattr(self.config, 'gap_max', 0.015)
            ext_max = getattr(self.config, 'ext_from_tema20_max', 0.015)
        
        # 갭 필터: 음수 갭도 허용 (하락 후 반등 가능)
        gap_ok = (gap_now <= gap_max)  # 최대값만 체크 (음수 갭 허용)
        ext_ok = (ext_pct <= ext_max)
        if not (gap_ok and ext_ok):
            return False
        
        # 8. ATR 필터 (활성화된 경우)
        if getattr(self.config, 'use_atr_filter', False):
            _atr = atr(df["high"], df["low"], df["close"], 14).iloc[-1]
            if cur.get("close", 0):
                atr_pct = _atr / cur.get("close", 1)
                atr_min = getattr(self.config, 'atr_pct_min', 0.01)
                atr_max = getattr(self.config, 'atr_pct_max', 0.04)
                if not (atr_min <= atr_pct <= atr_max):
                    return False
        
        return True
    
    def apply_soft_filters(self, df: pd.DataFrame, market_condition: Optional[MarketCondition] = None, stock_name: str = None) -> Tuple[bool, int, int]:
        """
        소프트 필터 적용 (신호 충족 여부) - 한국형과 동일한 로직
        
        Args:
            df: 지표가 계산된 데이터프레임
            market_condition: 시장 조건 (선택)
            stock_name: 종목명 (선택)
            
        Returns:
            (matched: bool, signals_true: int, total_signals: int)
        """
        if len(df) < 21:
            return False, 0, 7
        
        cur = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 동적 조건 가져오기
        if market_condition and self.market_analysis_enable:
            rsi_threshold = market_condition.rsi_threshold
            min_signals = market_condition.min_signals
            vol_ma5_mult = market_condition.vol_ma5_mult
        else:
            rsi_threshold = getattr(self.config, 'rsi_threshold', 58)
            min_signals = getattr(self.config, 'min_signals', 3)
            vol_ma5_mult = getattr(self.config, 'vol_ma5_mult', 2.5)
        
        # 골든크로스 확인
        lookback = min(5, len(df) - 1)
        crossed_recently = False
        for i in range(lookback):
            a_prev = df.iloc[-2 - i]
            a_cur = df.iloc[-1 - i]
            if (a_prev.get("TEMA20", 0) <= a_prev.get("DEMA10", 0)) and (a_cur.get("TEMA20", 0) > a_cur.get("DEMA10", 0)):
                crossed_recently = True
                break
        
        above_cnt = int((df["TEMA20"] > df["DEMA10"]).tail(5).sum()) if len(df) >= 5 else 0
        
        # 기본 신호 4개
        cond_gc = (crossed_recently or (cur.get("TEMA20", 0) > cur.get("DEMA10", 0))) and (df.iloc[-1].get("TEMA20_SLOPE20", 0) > 0)
        cond_macd = (cur.get("MACD_LINE", 0) > cur.get("MACD_SIGNAL", 0)) or (cur.get("MACD_OSC", 0) > 0)
        rsi_momentum = (cur.get("RSI_TEMA", 0) > cur.get("RSI_DEMA", 0)) or (abs(cur.get("RSI_TEMA", 0) - cur.get("RSI_DEMA", 0)) < 3 and cur.get("RSI_TEMA", 0) > rsi_threshold)
        cond_rsi = rsi_momentum
        cond_vol = (cur.get("VOL_MA5", 0) and cur.get("volume", 0) >= vol_ma5_mult * cur.get("VOL_MA5", 0))
        
        basic_signals = sum([bool(cond_gc), bool(cond_macd), bool(cond_rsi), bool(cond_vol)])
        
        # 추가 신호 3개
        obv_slope_ok = df.iloc[-1].get("OBV_SLOPE20", 0) > 0.001
        tema_slope_ok = (df.iloc[-1].get("TEMA20_SLOPE20", 0) > 0.001) and (cur.get("close", 0) > cur.get("TEMA20", 0))
        above_ok = above_cnt >= 3
        
        additional_signals = sum([bool(obv_slope_ok), bool(tema_slope_ok), bool(above_ok)])
        
        # 총 신호 개수
        signals_true = basic_signals + additional_signals
        
        # 추세 조건 (시장 상황에 따라 완화)
        if market_condition and self.market_analysis_enable:
            market_sentiment = getattr(market_condition, 'market_sentiment', 'neutral')
            final_regime = getattr(market_condition, 'final_regime', 'neutral')
            global_trend_score = getattr(market_condition, 'global_trend_score', 0.0)
            
            is_bull_market = (
                (market_sentiment == 'bull') or 
                (final_regime == 'bull') or 
                (global_trend_score > 1.0)
            )
        else:
            is_bull_market = False
        
        if is_bull_market:
            # 강세장: 조건 완화
            tema_slope_ok = df.iloc[-1]["TEMA20_SLOPE20"] > 0
            obv_slope_ok = df.iloc[-1]["OBV_SLOPE20"] > 0
            above_ok = above_cnt >= 2
            golden_cross_ok = cur.get("TEMA20", 0) > cur.get("DEMA10", 0)
            
            trend_conditions = [tema_slope_ok, obv_slope_ok, above_ok, golden_cross_ok]
            trend_ok = sum(trend_conditions) >= 2
            
            require_dema = getattr(self.config, 'require_dema_slope', 'optional')
            if require_dema == "required":
                dema_slope_ok = df.iloc[-1]["DEMA10_SLOPE20"] > 0
                if not dema_slope_ok:
                    trend_ok = trend_ok or (sum(trend_conditions) >= 3)
        else:
            # 약세장/중립장: 미국 주식은 조건 완화 (4개 중 2개 이상)
            tema_slope_ok = df.iloc[-1]["TEMA20_SLOPE20"] > 0
            obv_slope_ok = df.iloc[-1]["OBV_SLOPE20"] > 0
            above_ok = above_cnt >= 2  # 3에서 2로 완화
            golden_cross_ok = cur.get("TEMA20", 0) > cur.get("DEMA10", 0)
            
            trend_conditions = [tema_slope_ok, obv_slope_ok, above_ok, golden_cross_ok]
            trend_ok = sum(trend_conditions) >= 2  # 4개 중 2개 이상
            
            require_dema = getattr(self.config, 'require_dema_slope', 'optional')
            if require_dema == "required":
                dema_slope_ok = df.iloc[-1]["DEMA10_SLOPE20"] > 0
                if not dema_slope_ok:
                    trend_ok = trend_ok or (sum(trend_conditions) >= 3)
        
        # 최종 매칭: 신호 요건 충족 + 추세
        matched = (signals_true >= min_signals) and trend_ok
        
        return matched, int(signals_true), 7

