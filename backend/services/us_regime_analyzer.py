"""
미국 시장 전용 레짐 분석기
한국 시장 데이터 없이 미국 시장만으로 레짐 분석
"""
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, Any, Optional
from .us_futures_data_v8 import us_futures_data_v8
from .regime_data_cache import regime_cache

logger = logging.getLogger(__name__)


class USRegimeAnalyzer:
    """미국 시장 전용 레짐 분석기"""
    
    def __init__(self):
        self.us_data = us_futures_data_v8
        self.cache = regime_cache
    
    def analyze_us_market(self, date: str = None) -> Dict[str, Any]:
        """
        미국 시장 전용 레짐 분석
        
        Args:
            date: 분석 날짜 (YYYYMMDD 형식)
        
        Returns:
            {
                "us_equity_score": float,      # 미국 주식 점수
                "us_equity_regime": str,       # bull/bear/neutral
                "us_futures_score": float,     # 미국 선물 점수
                "us_futures_regime": str,      # bull/bear/neutral
                "us_volatility_score": float,  # 변동성 점수
                "final_score": float,          # 최종 점수
                "final_regime": str,           # 최종 레짐
                "spy_change": float,           # SPY 변화율
                "qqq_change": float,           # QQQ 변화율
                "vix_level": float,            # VIX 수준
                "date": str,
                "version": "us_regime_v1"
            }
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        try:
            # 캐시 확인
            cache_key = f"us_regime_{date}"
            cached_result = self.cache.get_regime_result(date, 'us_v1')
            if cached_result is not None:
                logger.debug(f"미국 레짐 캐시 히트: {date}")
                return cached_result
            
            logger.info(f"미국 레짐 분석 시작: {date}")
            
            # 데이터 수집
            df_spy = self.us_data.fetch_data("SPY")
            df_qqq = self.us_data.fetch_data("QQQ")
            df_es = self.us_data.fetch_data("ES=F")
            df_nq = self.us_data.fetch_data("NQ=F")
            df_vix = self.us_data.fetch_data("^VIX")
            df_dxy = self.us_data.fetch_data("DX-Y.NYB")
            
            # 날짜 필터링
            target_date = pd.to_datetime(date, format='%Y%m%d')
            
            if not df_spy.empty:
                df_spy = df_spy[df_spy.index <= target_date].tail(30)
            if not df_qqq.empty:
                df_qqq = df_qqq[df_qqq.index <= target_date].tail(30)
            if not df_es.empty:
                df_es = df_es[df_es.index <= target_date].tail(30)
            if not df_nq.empty:
                df_nq = df_nq[df_nq.index <= target_date].tail(30)
            if not df_vix.empty:
                df_vix = df_vix[df_vix.index <= target_date].tail(30)
            if not df_dxy.empty:
                df_dxy = df_dxy[df_dxy.index <= target_date].tail(30)
            
            # 1. 미국 주식 점수 (SPY + QQQ)
            equity_result = self._compute_us_equity_score(df_spy, df_qqq, df_vix)
            
            # 2. 미국 선물 점수 (ES + NQ)
            futures_result = self._compute_us_futures_score(df_es, df_nq, df_vix, df_dxy)
            
            # 3. 변동성 점수 (VIX)
            volatility_result = self._compute_volatility_score(df_vix)
            
            # 4. 최종 레짐 결정
            final_result = self._combine_us_regime(equity_result, futures_result, volatility_result)
            
            # 결과 통합
            result = {
                **equity_result,
                **futures_result,
                **volatility_result,
                **final_result,
                "date": date,
                "version": "us_regime_v1"
            }
            
            # 캐시 저장
            self.cache.set_regime_result(date, result, 'us_v1')
            
            logger.info(f"미국 레짐 분석 완료: {date} -> {result['final_regime']} (점수: {result['final_score']:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"미국 레짐 분석 실패: {e}")
            return self._get_default_result(date)
    
    def _compute_us_equity_score(self, df_spy: pd.DataFrame, df_qqq: pd.DataFrame, 
                                 df_vix: pd.DataFrame) -> Dict[str, Any]:
        """미국 주식 점수 계산 (SPY 50% + QQQ 50%)"""
        try:
            score = 0.0
            spy_change = 0.0
            qqq_change = 0.0
            
            # SPY 분석
            if not df_spy.empty and len(df_spy) >= 2:
                spy_change = df_spy['Close'].iloc[-1] / df_spy['Close'].iloc[-2] - 1
                
                # 1일 수익률
                if spy_change > 0.015:
                    score += 2.0
                elif spy_change > 0.005:
                    score += 1.0
                elif spy_change < -0.015:
                    score -= 2.0
                elif spy_change < -0.005:
                    score -= 1.0
                
                # 5일 추세
                if len(df_spy) >= 5:
                    spy_5d = df_spy['Close'].iloc[-1] / df_spy['Close'].iloc[-5] - 1
                    if spy_5d > 0.03:
                        score += 1.5
                    elif spy_5d > 0.01:
                        score += 0.5
                    elif spy_5d < -0.03:
                        score -= 1.5
                    elif spy_5d < -0.01:
                        score -= 0.5
                
                # 20일 이동평균 대비
                if len(df_spy) >= 20:
                    ma20 = df_spy['Close'].tail(20).mean()
                    if df_spy['Close'].iloc[-1] > ma20:
                        score += 1.0
                    else:
                        score -= 1.0
            
            # QQQ 분석
            if not df_qqq.empty and len(df_qqq) >= 2:
                qqq_change = df_qqq['Close'].iloc[-1] / df_qqq['Close'].iloc[-2] - 1
                
                # 1일 수익률 (기술주는 변동성이 크므로 가중치 높임)
                if qqq_change > 0.02:
                    score += 2.0
                elif qqq_change > 0.01:
                    score += 1.0
                elif qqq_change < -0.02:
                    score -= 2.0
                elif qqq_change < -0.01:
                    score -= 1.0
                
                # 5일 추세
                if len(df_qqq) >= 5:
                    qqq_5d = df_qqq['Close'].iloc[-1] / df_qqq['Close'].iloc[-5] - 1
                    if qqq_5d > 0.04:
                        score += 1.5
                    elif qqq_5d > 0.015:
                        score += 0.5
                    elif qqq_5d < -0.04:
                        score -= 1.5
                    elif qqq_5d < -0.015:
                        score -= 0.5
            
            # VIX 영향 (공포 지수)
            if not df_vix.empty and len(df_vix) >= 2:
                vix_change = df_vix['Close'].iloc[-1] / df_vix['Close'].iloc[-2] - 1
                vix_level = df_vix['Close'].iloc[-1]
                
                # VIX 하락은 긍정
                if vix_change < -0.1:
                    score += 1.5
                elif vix_change < -0.05:
                    score += 0.5
                elif vix_change > 0.15:
                    score -= 2.0
                elif vix_change > 0.1:
                    score -= 1.0
                
                # VIX 절대 수준
                if vix_level < 15:
                    score += 1.0
                elif vix_level > 30:
                    score -= 2.0
                elif vix_level > 25:
                    score -= 1.0
            
            # 레짐 결정
            if score >= 3.0:
                regime = "bull"
            elif score <= -3.0:
                regime = "bear"
            else:
                regime = "neutral"
            
            return {
                "us_equity_score": score,
                "us_equity_regime": regime,
                "spy_change": spy_change * 100,
                "qqq_change": qqq_change * 100
            }
            
        except Exception as e:
            logger.error(f"미국 주식 점수 계산 실패: {e}")
            return {
                "us_equity_score": 0.0,
                "us_equity_regime": "neutral",
                "spy_change": 0.0,
                "qqq_change": 0.0
            }
    
    def _compute_us_futures_score(self, df_es: pd.DataFrame, df_nq: pd.DataFrame,
                                  df_vix: pd.DataFrame, df_dxy: pd.DataFrame) -> Dict[str, Any]:
        """미국 선물 점수 계산"""
        try:
            score = 0.0
            
            # ES (S&P 500 선물)
            if not df_es.empty and len(df_es) >= 2:
                es_change = df_es['Close'].iloc[-1] / df_es['Close'].iloc[-2] - 1
                if es_change > 0.01:
                    score += 1.5
                elif es_change > 0.005:
                    score += 0.5
                elif es_change < -0.01:
                    score -= 1.5
                elif es_change < -0.005:
                    score -= 0.5
            
            # NQ (NASDAQ 선물)
            if not df_nq.empty and len(df_nq) >= 2:
                nq_change = df_nq['Close'].iloc[-1] / df_nq['Close'].iloc[-2] - 1
                if nq_change > 0.012:
                    score += 1.5
                elif nq_change > 0.006:
                    score += 0.5
                elif nq_change < -0.012:
                    score -= 1.5
                elif nq_change < -0.006:
                    score -= 0.5
            
            # VIX 선물 영향
            if not df_vix.empty and len(df_vix) >= 2:
                vix_change = df_vix['Close'].iloc[-1] / df_vix['Close'].iloc[-2] - 1
                if vix_change < -0.05:
                    score += 1.0
                elif vix_change > 0.1:
                    score -= 1.5
            
            # DXY (달러 인덱스) - 달러 강세는 주식에 부정적
            if not df_dxy.empty and len(df_dxy) >= 2:
                dxy_change = df_dxy['Close'].iloc[-1] / df_dxy['Close'].iloc[-2] - 1
                if dxy_change > 0.008:
                    score -= 1.0
                elif dxy_change > 0.004:
                    score -= 0.5
                elif dxy_change < -0.008:
                    score += 1.0
                elif dxy_change < -0.004:
                    score += 0.5
            
            # 레짐 결정
            if score >= 2.0:
                regime = "bull"
            elif score <= -2.0:
                regime = "bear"
            else:
                regime = "neutral"
            
            return {
                "us_futures_score": score,
                "us_futures_regime": regime
            }
            
        except Exception as e:
            logger.error(f"미국 선물 점수 계산 실패: {e}")
            return {
                "us_futures_score": 0.0,
                "us_futures_regime": "neutral"
            }
    
    def _compute_volatility_score(self, df_vix: pd.DataFrame) -> Dict[str, Any]:
        """변동성 점수 계산"""
        try:
            score = 0.0
            vix_level = 0.0
            
            if not df_vix.empty:
                vix_level = df_vix['Close'].iloc[-1]
                
                # VIX 절대 수준에 따른 점수
                if vix_level < 12:
                    score = 2.0  # 매우 안정
                elif vix_level < 15:
                    score = 1.0  # 안정
                elif vix_level < 20:
                    score = 0.0  # 중립
                elif vix_level < 25:
                    score = -1.0  # 불안
                elif vix_level < 30:
                    score = -2.0  # 매우 불안
                else:
                    score = -3.0  # 공포
            
            return {
                "us_volatility_score": score,
                "vix_level": vix_level
            }
            
        except Exception as e:
            logger.error(f"변동성 점수 계산 실패: {e}")
            return {
                "us_volatility_score": 0.0,
                "vix_level": 0.0
            }
    
    def _combine_us_regime(self, equity_result: Dict, futures_result: Dict, 
                          volatility_result: Dict) -> Dict[str, Any]:
        """미국 레짐 통합"""
        try:
            # 가중 평균: 주식 50%, 선물 30%, 변동성 20%
            final_score = (0.5 * equity_result["us_equity_score"] +
                          0.3 * futures_result["us_futures_score"] +
                          0.2 * volatility_result["us_volatility_score"])
            
            # 최종 레짐 결정
            if final_score >= 2.5:
                final_regime = "bull"
            elif final_score >= 0.5:
                final_regime = "neutral_bull"
            elif final_score <= -2.5:
                final_regime = "bear"
            elif final_score <= -0.5:
                final_regime = "neutral_bear"
            else:
                final_regime = "neutral"
            
            # 특별 규칙: VIX가 35 이상이면 무조건 bear
            if volatility_result.get("vix_level", 0) > 35:
                final_regime = "bear"
                final_score = min(final_score, -2.5)
            
            # 투자 조언 생성
            advice = self._generate_advice(final_regime, final_score, 
                                          equity_result, volatility_result)
            
            return {
                "final_score": final_score,
                "final_regime": final_regime,
                "market_sentiment": final_regime,
                "advice": advice,
                # 동적 필터 값 설정
                "rsi_threshold": self._get_rsi_threshold(final_regime),
                "min_signals": self._get_min_signals(final_regime),
                "vol_ma5_mult": self._get_vol_mult(final_regime),
                "gap_max": self._get_gap_max(final_regime),
                "ext_from_tema20_max": self._get_ext_max(final_regime)
            }
            
        except Exception as e:
            logger.error(f"미국 레짐 통합 실패: {e}")
            return {
                "final_score": 0.0,
                "final_regime": "neutral",
                "market_sentiment": "neutral",
                "advice": "시장 상황을 주의 깊게 관찰하세요.",
                "rsi_threshold": 58,
                "min_signals": 3,
                "vol_ma5_mult": 2.5,
                "gap_max": 0.015,
                "ext_from_tema20_max": 0.015
            }
    
    def _generate_advice(self, regime: str, score: float, 
                        equity_result: Dict, volatility_result: Dict) -> str:
        """투자 조언 생성"""
        spy_change = equity_result.get("spy_change", 0)
        vix_level = volatility_result.get("vix_level", 0)
        
        if regime == "bull":
            return f"미국 시장이 강세입니다. SPY {spy_change:+.2f}%, VIX {vix_level:.1f}. 적극적인 투자를 고려하세요."
        elif regime == "neutral_bull":
            return f"미국 시장이 약한 강세입니다. SPY {spy_change:+.2f}%. 선별적 투자를 권장합니다."
        elif regime == "bear":
            return f"미국 시장이 약세입니다. SPY {spy_change:+.2f}%, VIX {vix_level:.1f}. 보수적 접근이 필요합니다."
        elif regime == "neutral_bear":
            return f"미국 시장이 약한 약세입니다. SPY {spy_change:+.2f}%. 신중한 투자가 필요합니다."
        else:
            return f"미국 시장이 중립입니다. SPY {spy_change:+.2f}%. 관망하며 기회를 찾으세요."
    
    def _get_rsi_threshold(self, regime: str) -> int:
        """레짐별 RSI 임계값"""
        thresholds = {
            "bull": 55,
            "neutral_bull": 57,
            "neutral": 58,
            "neutral_bear": 60,
            "bear": 62
        }
        return thresholds.get(regime, 58)
    
    def _get_min_signals(self, regime: str) -> int:
        """레짐별 최소 신호 개수"""
        signals = {
            "bull": 2,
            "neutral_bull": 3,
            "neutral": 3,
            "neutral_bear": 4,
            "bear": 4
        }
        return signals.get(regime, 3)
    
    def _get_vol_mult(self, regime: str) -> float:
        """레짐별 거래량 배수"""
        mults = {
            "bull": 2.0,
            "neutral_bull": 2.3,
            "neutral": 2.5,
            "neutral_bear": 2.8,
            "bear": 3.0
        }
        return mults.get(regime, 2.5)
    
    def _get_gap_max(self, regime: str) -> float:
        """레짐별 갭 최대값"""
        gaps = {
            "bull": 0.020,
            "neutral_bull": 0.018,
            "neutral": 0.015,
            "neutral_bear": 0.012,
            "bear": 0.010
        }
        return gaps.get(regime, 0.015)
    
    def _get_ext_max(self, regime: str) -> float:
        """레짐별 이격 최대값"""
        exts = {
            "bull": 0.020,
            "neutral_bull": 0.018,
            "neutral": 0.015,
            "neutral_bear": 0.012,
            "bear": 0.010
        }
        return exts.get(regime, 0.015)
    
    def _get_default_result(self, date: str) -> Dict[str, Any]:
        """기본 결과 반환"""
        return {
            "us_equity_score": 0.0,
            "us_equity_regime": "neutral",
            "us_futures_score": 0.0,
            "us_futures_regime": "neutral",
            "us_volatility_score": 0.0,
            "vix_level": 0.0,
            "final_score": 0.0,
            "final_regime": "neutral",
            "market_sentiment": "neutral",
            "spy_change": 0.0,
            "qqq_change": 0.0,
            "advice": "데이터를 불러올 수 없습니다.",
            "date": date,
            "version": "us_regime_v1",
            "rsi_threshold": 58,
            "min_signals": 3,
            "vol_ma5_mult": 2.5,
            "gap_max": 0.015,
            "ext_from_tema20_max": 0.015
        }
    
    def clear_cache(self) -> None:
        """캐시 클리어"""
        self.cache.clear_cache()
        logger.info("미국 레짐 분석 캐시 클리어 완료")


# 전역 인스턴스
us_regime_analyzer = USRegimeAnalyzer()
