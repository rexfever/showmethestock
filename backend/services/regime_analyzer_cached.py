"""
캐시 기반 레짐 분석기
"""
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, Any, Optional
from .regime_data_cache import regime_cache
from .us_futures_data_v8 import us_futures_data_v8

logger = logging.getLogger(__name__)

class RegimeAnalyzerCached:
    """캐시 기반 레짐 분석기"""
    
    def __init__(self):
        self.cache = regime_cache
        self.us_data = us_futures_data_v8
    
    def get_kospi_data(self, date: str = None) -> pd.DataFrame:
        """KOSPI 데이터 조회 (해당 날짜 기준) - pykrx 우선, FinanceDataReader fallback"""
        try:
            from utils.kospi_data_loader import get_kospi_data
            # pykrx 우선, FinanceDataReader fallback (당일 데이터 제공 가능)
            df = get_kospi_data(date=date, days=30)
            return df
        except Exception as e:
            logger.error(f"KOSPI 데이터 조회 실패: {e}")
            return pd.DataFrame()
    
    def get_kosdaq_data(self, date: str = None) -> pd.DataFrame:
        """KOSDAQ 데이터 조회 (해당 날짜 기준)"""
        try:
            # 캐시 파일 우선 확인
            import os
            cache_path = os.path.join(os.path.dirname(__file__), '..', 'data_cache', 'ohlcv', '229200.csv')
            if os.path.exists(cache_path):
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                if date:
                    target_date = pd.to_datetime(date, format='%Y%m%d')
                    df = df[df.index <= target_date].tail(30)
                return df
            
            # 캐시 없으면 API 호출
            from kiwoom_api import api
            df = api.get_ohlcv("229200", 30, date)  # KOSDAQ 지수 (30일)
            
            return df
        except Exception as e:
            logger.error(f"KOSDAQ 데이터 조회 실패: {e}")
            return pd.DataFrame()
    
    def analyze_regime_v4_cached(self, date: str = None) -> Dict[str, Any]:
        """캐시 기반 레짐 v4 분석"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        try:
            # 캐시에서 먼저 조회
            cached_result = self.cache.get_regime_result(date, 'v4')
            if cached_result is not None:
                logger.debug(f"레짐 v4 캐시 히트: {date}")
                return cached_result
            
            # 캐시 미스 시 새로 분석
            logger.info(f"레짐 v4 분석 시작: {date}")
            
            # 데이터 수집
            df_kospi = self.get_kospi_data(date)
            df_kosdaq = self.get_kosdaq_data(date)
            df_spy = self.us_data.fetch_data("SPY")
            df_qqq = self.us_data.fetch_data("QQQ")
            df_es = self.us_data.fetch_data("ES=F")
            df_nq = self.us_data.fetch_data("NQ=F")
            df_vix = self.us_data.fetch_data("^VIX")
            df_dxy = self.us_data.fetch_data("DX-Y.NYB")
            
            # 날짜 필터링 - 해당 날짜까지의 데이터만 사용
            target_date = pd.to_datetime(date, format='%Y%m%d')
            
            # 각 데이터프레임을 해당 날짜까지 필터링
            if not df_kosdaq.empty:
                df_kosdaq = df_kosdaq[df_kosdaq.index <= target_date].tail(30)
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
            
            # 점수 계산 (KOSPI + KOSDAQ)
            kr_result = self._compute_kr_score_v4(df_kospi, df_kosdaq)
            us_prev_result = self._compute_us_prev_score_v4(df_spy, df_qqq, df_vix)
            us_futures_result = self._compute_us_futures_score_v4(df_es, df_nq, df_vix, df_dxy)
            
            # 글로벌 조합
            global_result = self._combine_global_regime_v4(kr_result, us_prev_result, us_futures_result)
            
            # 결과 통합
            result = {
                **kr_result,
                **us_prev_result,
                **us_futures_result,
                **global_result,
                "date": date,
                "version": "regime_v4"
            }
            
            # 캐시에 저장
            self.cache.set_regime_result(date, result, 'v4')
            
            logger.info(f"레짐 v4 분석 완료: {date} -> {result['final_regime']} (점수: {result['final_score']:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"레짐 v4 분석 실패: {e}")
            return self._get_default_result(date)
    
    def _compute_kr_score_v4(self, df_kospi: pd.DataFrame, df_kosdaq: pd.DataFrame = None) -> Dict[str, Any]:
        """한국 장세 점수 계산 v4 (KOSPI + KOSDAQ)"""
        # KOSPI 점수 계산
        kospi_score = self._compute_single_market_score(df_kospi)
        
        # KOSDAQ 점수 계산
        kosdaq_score = self._compute_single_market_score(df_kosdaq if df_kosdaq is not None else pd.DataFrame())
        
        # 통합 점수 (KOSPI 70%, KOSDAQ 30%)
        if df_kospi.empty and (df_kosdaq is None or df_kosdaq.empty):
            return {"kr_score": -1.0, "kr_regime": "neutral"}
        
        if df_kospi.empty:
            # KOSPI 없으면 KOSDAQ만 사용
            final_score = kosdaq_score["score"]
        elif df_kosdaq is None or df_kosdaq.empty:
            # KOSDAQ 없으면 KOSPI만 사용
            final_score = kospi_score["score"]
        else:
            # 둘 다 있으면 가중 평균
            final_score = 0.7 * kospi_score["score"] + 0.3 * kosdaq_score["score"]
        
        # 레짐 결정
        if final_score >= 2.0:
            regime = "bull"
        elif final_score <= -2.0:
            regime = "bear"
        else:
            regime = "neutral"
        
        return {"kr_score": final_score, "kr_regime": regime}
    
    def _compute_single_market_score(self, df: pd.DataFrame) -> Dict[str, float]:
        """단일 시장(KOSPI 또는 KOSDAQ)의 점수 계산"""
        if df.empty or len(df) < 2:
            return {"score": 0.0}
        
        try:
            # 수익률 계산
            if len(df) >= 2:
                r1 = df['close'].iloc[-1] / df['close'].iloc[-2] - 1
            else:
                r1 = 0.0
            
            # 3일 EMA 변화율
            if len(df) >= 4:
                ema3 = df['close'].ewm(span=3).mean()
                r3 = ema3.iloc[-1] / ema3.iloc[-4] - 1
            else:
                r3 = 0.0
            
            # 5일 평균 수익률
            if len(df) >= 5:
                r5 = df['close'].pct_change().tail(5).mean()
            else:
                r5 = 0.0
            
            # 점수 계산
            score = 0.0
            if r1 > 0.015: score += 2.0
            elif r1 > 0.005: score += 1.0
            elif r1 < -0.015: score -= 2.0
            elif r1 < -0.005: score -= 1.0
            
            if r3 > 0.02: score += 1.0
            elif r3 < -0.02: score -= 1.0
            
            if r5 > 0.01: score += 1.0
            elif r5 < -0.01: score -= 1.0
            
            return {"score": score}
            
        except Exception as e:
            logger.error(f"단일 시장 점수 계산 실패: {e}")
            return {"score": 0.0}
    
    def _compute_us_prev_score_v4(self, df_spy: pd.DataFrame, df_qqq: pd.DataFrame, df_vix: pd.DataFrame) -> Dict[str, Any]:
        """미국 전일 장세 점수 계산 v4"""
        try:
            score = 0.0
            
            # SPY 수익률
            if not df_spy.empty and len(df_spy) >= 2:
                spy_r1 = df_spy['Close'].iloc[-1] / df_spy['Close'].iloc[-2] - 1
                logger.debug(f"SPY 수익률: {spy_r1*100:.2f}%")
                if spy_r1 > 0.01: score += 1.0
                elif spy_r1 < -0.01: score -= 1.0
            else:
                logger.warning("SPY 데이터 부족")
            
            # QQQ 수익률
            if not df_qqq.empty and len(df_qqq) >= 2:
                qqq_r1 = df_qqq['Close'].iloc[-1] / df_qqq['Close'].iloc[-2] - 1
                logger.debug(f"QQQ 수익률: {qqq_r1*100:.2f}%")
                if qqq_r1 > 0.012: score += 1.0
                elif qqq_r1 < -0.012: score -= 1.0
            else:
                logger.warning("QQQ 데이터 부족")
            
            # VIX 변화율
            if not df_vix.empty and len(df_vix) >= 2:
                vix_change = df_vix['Close'].iloc[-1] / df_vix['Close'].iloc[-2] - 1
                logger.debug(f"VIX 변화율: {vix_change*100:.2f}%")
                if vix_change < -0.05: score += 1.0
                elif vix_change > 0.1: score -= 2.0
                elif vix_change > 0.05: score -= 1.0
            else:
                logger.warning("VIX 데이터 부족")
                score += 1.0  # VIX 없으면 기본 점수
            
            # 레짐 결정
            if score >= 2.0:
                regime = "bull"
            elif score <= -2.0:
                regime = "bear"
            else:
                regime = "neutral"
            
            return {"us_prev_score": score, "us_prev_regime": regime}
            
        except Exception as e:
            logger.error(f"미국 전일 점수 계산 실패: {e}")
            return {"us_prev_score": 1.0, "us_prev_regime": "neutral"}
    
    def _compute_us_futures_score_v4(self, df_es: pd.DataFrame, df_nq: pd.DataFrame, 
                                   df_vx: pd.DataFrame, df_dxy: pd.DataFrame) -> Dict[str, Any]:
        """미국 선물 점수 계산 v4"""
        try:
            score = 0.0
            
            # ES=F 변화율
            if not df_es.empty and len(df_es) >= 2:
                es_change = df_es['Close'].iloc[-1] / df_es['Close'].iloc[-2] - 1
                if es_change > 0.008: score += 1.5
                elif es_change > 0.003: score += 0.5
                elif es_change < -0.008: score -= 1.5
                elif es_change < -0.003: score -= 0.5
            
            # NQ=F 변화율
            if not df_nq.empty and len(df_nq) >= 2:
                nq_change = df_nq['Close'].iloc[-1] / df_nq['Close'].iloc[-2] - 1
                if nq_change > 0.01: score += 1.5
                elif nq_change > 0.004: score += 0.5
                elif nq_change < -0.01: score -= 1.5
                elif nq_change < -0.004: score -= 0.5
            
            # VX=F 변화율 (VIX 사용)
            if not df_vx.empty and len(df_vx) >= 2:
                vx_change = df_vx['Close'].iloc[-1] / df_vx['Close'].iloc[-2] - 1
                if vx_change < -0.03: score += 1.0
                elif vx_change > 0.05: score -= 1.5
                elif vx_change > 0.02: score -= 0.5
            
            # DXY 변화율
            if not df_dxy.empty and len(df_dxy) >= 2:
                dxy_change = df_dxy['Close'].iloc[-1] / df_dxy['Close'].iloc[-2] - 1
                if dxy_change > 0.005: score -= 0.5  # 달러 강세는 위험 신호
                elif dxy_change < -0.005: score += 0.5
            
            # 레짐 결정
            if score >= 2.0:
                regime = "bull"
            elif score <= -2.0:
                regime = "bear"
            else:
                regime = "neutral"
            
            return {"us_futures_score": score, "us_futures_regime": regime}
            
        except Exception as e:
            logger.error(f"미국 선물 점수 계산 실패: {e}")
            return {"us_futures_score": 0.0, "us_futures_regime": "neutral"}
    
    def _combine_global_regime_v4(self, kr_result: Dict, us_prev_result: Dict, us_futures_result: Dict) -> Dict[str, Any]:
        """글로벌 레짐 v4 조합"""
        try:
            # 가중 평균 점수
            final_score = (0.6 * kr_result["kr_score"] + 
                          0.2 * us_prev_result["us_prev_score"] + 
                          0.2 * us_futures_result["us_futures_score"])
            
            # 최종 레짐 결정
            if final_score < -2.0:
                final_regime = "crash"
            elif final_score < -0.3:
                final_regime = "bear"
            elif final_score > 0.3:
                final_regime = "bull"
            else:
                final_regime = "neutral"
            
            # 특별 규칙: 개별 레짐이 crash면 최종도 crash
            if (kr_result["kr_regime"] == "crash" or 
                us_prev_result["us_prev_regime"] == "crash" or 
                us_futures_result["us_futures_regime"] == "crash"):
                final_regime = "crash"
            
            return {
                "final_score": final_score,
                "final_regime": final_regime
            }
            
        except Exception as e:
            logger.error(f"글로벌 레짐 조합 실패: {e}")
            return {"final_score": 0.0, "final_regime": "neutral"}
    
    def _get_default_result(self, date: str) -> Dict[str, Any]:
        """기본 결과 반환"""
        return {
            "kr_score": 0.0, "kr_regime": "neutral",
            "us_prev_score": 0.0, "us_prev_regime": "neutral", 
            "us_futures_score": 0.0, "us_futures_regime": "neutral",
            "final_score": 0.0, "final_regime": "neutral",
            "date": date, "version": "regime_v4"
        }
    
    def clear_cache(self) -> None:
        """캐시 클리어"""
        self.cache.clear_cache()
        logger.info("레짐 분석 캐시 클리어 완료")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        return self.cache.get_cache_stats()

# 전역 인스턴스
regime_analyzer_cached = RegimeAnalyzerCached()