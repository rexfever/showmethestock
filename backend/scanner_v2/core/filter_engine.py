"""
필터링 엔진 모듈
"""
import pandas as pd
from typing import Tuple, Optional
from market_analyzer import MarketCondition
from indicators import atr


class FilterEngine:
    """필터링 엔진"""
    
    def __init__(self, config):
        self.config = config
        # market_analysis_enable 체크용
        self.market_analysis_enable = getattr(config, 'market_analysis_enable', True)
    
    def apply_hard_filters(self, df: pd.DataFrame, stock_name: str, market_condition: Optional[MarketCondition] = None) -> bool:
        """
        하드 필터 적용 (통과/실패)
        
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
        
        # 1. 인버스 ETF 필터링
        if any(keyword in stock_name for keyword in self.config.inverse_etf_keywords):
            return False
        
        # 2. 금리/채권 ETF 필터링
        if any(keyword in stock_name for keyword in self.config.bond_etf_keywords):
            return False
        
        # 3. RSI 상한선 필터링
        if market_condition and self.config.market_analysis_enable:
            rsi_upper_limit = market_condition.rsi_threshold + 25.0
        else:
            rsi_upper_limit = self.config.rsi_upper_limit
        
        if cur.RSI_TEMA > rsi_upper_limit:
            return False
        
        # 4. 유동성 필터
        if len(df) >= 20:
            avg_turnover = (df["close"].iloc[-20:] * df["volume"].iloc[-20:]).mean()
            if avg_turnover < self.config.min_turnover_krw:
                return False
        
        # 5. 가격 하한
        if cur.close < self.config.min_price:
            return False
        
        # 6. 과열 필터
        overheat = (
            (cur.RSI_TEMA >= self.config.overheat_rsi_tema) and
            (cur.VOL_MA5 and cur.volume >= self.config.overheat_vol_mult * cur.VOL_MA5)
        )
        if overheat:
            return False
        
        # 7. 갭/이격 필터
        gap_now = (cur.TEMA20 - cur.DEMA10) / cur.close if cur.close else 0.0
        ext_pct = (cur.close - cur.TEMA20) / cur.TEMA20 if cur.TEMA20 else 0.0
        
        if market_condition and self.market_analysis_enable:
            gap_max = market_condition.gap_max
            ext_max = market_condition.ext_from_tema20_max
        else:
            gap_max = getattr(self.config, 'gap_max', 0.015)
            ext_max = getattr(self.config, 'ext_from_tema20_max', 0.015)
        
        gap_ok = (max(gap_now, 0.0) >= self.config.gap_min) and (gap_now <= gap_max)
        ext_ok = (ext_pct <= ext_max)
        if not (gap_ok and ext_ok):
            return False
        
        # 8. ATR 필터 (활성화된 경우)
        if getattr(self.config, 'use_atr_filter', False):
            _atr = atr(df["high"], df["low"], df["close"], 14).iloc[-1]
            if cur.close:
                atr_pct = _atr / cur.close
                atr_min = getattr(self.config, 'atr_pct_min', 0.01)
                atr_max = getattr(self.config, 'atr_pct_max', 0.04)
                if not (atr_min <= atr_pct <= atr_max):
                    return False
        
        return True
    
    def apply_soft_filters(self, df: pd.DataFrame, market_condition: Optional[MarketCondition] = None, stock_name: str = None) -> Tuple[bool, int, int]:
        """
        소프트 필터 적용 (신호 충족 여부)
        
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
            if (a_prev.TEMA20 <= a_prev.DEMA10) and (a_cur.TEMA20 > a_cur.DEMA10):
                crossed_recently = True
                break
        
        above_cnt = int((df["TEMA20"] > df["DEMA10"]).tail(5).sum()) if len(df) >= 5 else 0
        
        # 기본 신호 4개
        cond_gc = (crossed_recently or (cur.TEMA20 > cur.DEMA10)) and (df.iloc[-1]["TEMA20_SLOPE20"] > 0)
        cond_macd = (cur.MACD_LINE > cur.MACD_SIGNAL) or (cur.MACD_OSC > 0)
        rsi_momentum = (cur.RSI_TEMA > cur.RSI_DEMA) or (abs(cur.RSI_TEMA - cur.RSI_DEMA) < 3 and cur.RSI_TEMA > rsi_threshold)
        cond_rsi = rsi_momentum
        cond_vol = (cur.VOL_MA5 and cur.volume >= vol_ma5_mult * cur.VOL_MA5)
        
        basic_signals = sum([bool(cond_gc), bool(cond_macd), bool(cond_rsi), bool(cond_vol)])
        
        # 추가 신호 3개
        obv_slope_ok = df.iloc[-1]["OBV_SLOPE20"] > 0.001
        tema_slope_ok = (df.iloc[-1]["TEMA20_SLOPE20"] > 0.001) and (cur.close > cur.TEMA20)
        above_ok = above_cnt >= 3
        
        additional_signals = sum([bool(obv_slope_ok), bool(tema_slope_ok), bool(above_ok)])
        
        # 총 신호 개수
        signals_true = basic_signals + additional_signals
        
        # 추세 조건
        trend_ok = (
            (df.iloc[-1]["TEMA20_SLOPE20"] > 0) and
            (df.iloc[-1]["OBV_SLOPE20"] > 0) and
            (above_cnt >= 3)
        )
        
        # DEMA 슬로프 조건 (설정에 따라)
        require_dema = getattr(self.config, 'require_dema_slope', 'optional')
        if require_dema == "required":
            trend_ok = trend_ok and (df.iloc[-1]["DEMA10_SLOPE20"] > 0)
        
        # 최종 매칭: 신호 요건 충족 + 추세
        matched = (signals_true >= min_signals) and trend_ok
        
        return matched, int(signals_true), 7

