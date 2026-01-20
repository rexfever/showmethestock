"""
백필용 글로벌 레짐 v3 경량 분석기
- 로컬 캐시 기반 고속 처리
- 한국/미국 시장 데이터 결합
- 최소한의 API 호출
"""
import os
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BackfillMarketAnalyzerLight:
    """백필용 경량 시장 분석기"""
    
    def __init__(self, cache_dir: str = "data_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 캐시 파일 경로
        self.kospi_cache = self.cache_dir / "kospi200_ohlcv.pkl"
        self.spy_cache = self.cache_dir / "spy_ohlcv.pkl"
        self.qqq_cache = self.cache_dir / "qqq_ohlcv.pkl"
        self.vix_cache = self.cache_dir / "vix_ohlcv.pkl"
        
        # 데이터 로드
        self._load_cached_data()
    
    def _load_cached_data(self) -> None:
        """캐시된 데이터 로드"""
        try:
            if self.kospi_cache.exists():
                with open(self.kospi_cache, 'rb') as f:
                    self.kospi_data = pickle.load(f)
            else:
                self.kospi_data = pd.DataFrame()
                
            if self.spy_cache.exists():
                with open(self.spy_cache, 'rb') as f:
                    self.spy_data = pickle.load(f)
            else:
                self.spy_data = pd.DataFrame()
                
            if self.qqq_cache.exists():
                with open(self.qqq_cache, 'rb') as f:
                    self.qqq_data = pickle.load(f)
            else:
                self.qqq_data = pd.DataFrame()
                
            if self.vix_cache.exists():
                with open(self.vix_cache, 'rb') as f:
                    self.vix_data = pickle.load(f)
            else:
                self.vix_data = pd.DataFrame()
                
            logger.info(f"캐시 데이터 로드 완료: KOSPI={len(self.kospi_data)}, SPY={len(self.spy_data)}, QQQ={len(self.qqq_data)}, VIX={len(self.vix_data)}")
        except Exception as e:
            logger.error(f"캐시 데이터 로드 실패: {e}")
            self.kospi_data = pd.DataFrame()
            self.spy_data = pd.DataFrame()
            self.qqq_data = pd.DataFrame()
            self.vix_data = pd.DataFrame()
    
    def analyze_regime_light(self, date: str) -> Dict[str, Any]:
        """경량 레짐 분석"""
        try:
            # 한국 장세 점수 계산
            kr_scores = self._compute_kr_regime_light(date)
            
            # 미국 전일 장세 점수 계산
            us_prev_scores = self._compute_us_prev_light(date)
            
            # 미국 preopen 리스크 계산
            us_preopen_scores = self._compute_us_preopen_light(date)
            
            # 글로벌 레짐 조합
            final_regime_data = self._compose_global_regime_light(
                kr_scores, us_prev_scores, us_preopen_scores
            )
            
            return {
                "date": date,
                "final_regime": final_regime_data["final_regime"],
                "final_score": final_regime_data["final_score"],
                "kr_score": kr_scores["kr_score"],
                "us_prev_score": us_prev_scores["us_prev_score"],
                "us_preopen_score": us_preopen_scores["us_preopen_score"],
                "intraday_drop": kr_scores["intraday_drop"],
                "version": "v3-light"
            }
        except Exception as e:
            logger.error(f"레짐 분석 실패 ({date}): {e}")
            return {
                "date": date,
                "final_regime": "neutral",
                "final_score": 0.0,
                "kr_score": 0.0,
                "us_prev_score": 0.0,
                "us_preopen_score": 0.0,
                "intraday_drop": 0.0,
                "version": "v3-light"
            }
    
    def _compute_kr_regime_light(self, date: str) -> Dict[str, Any]:
        """한국 장세 점수 계산 (경량)"""
        try:
            if self.kospi_data.empty:
                return {"kr_score": 0.0, "intraday_drop": 0.0}
            
            # 날짜 변환
            target_date = pd.to_datetime(date, format='%Y%m%d')
            
            # 해당 날짜 데이터 찾기
            mask = self.kospi_data.index <= target_date
            if not mask.any():
                return {"kr_score": 0.0, "intraday_drop": 0.0}
            
            recent_data = self.kospi_data[mask].tail(10)  # 최근 10일
            if len(recent_data) < 2:
                return {"kr_score": 0.0, "intraday_drop": 0.0}
            
            current = recent_data.iloc[-1]
            prev = recent_data.iloc[-2]
            
            # r1, r3, r5 계산
            r1 = (current['close'] / prev['close'] - 1) if prev['close'] > 0 else 0.0
            
            r3 = 0.0
            if len(recent_data) >= 4:
                r3 = (current['close'] / recent_data.iloc[-4]['close'] - 1)
            
            r5 = 0.0
            if len(recent_data) >= 6:
                r5 = (current['close'] / recent_data.iloc[-6]['close'] - 1)
            
            # intraday drop 계산
            intraday_drop = (current['low'] / prev['close'] - 1) if prev['close'] > 0 else 0.0
            
            # 점수 계산
            kr_score = 0.0
            
            # Trend Score (-2 ~ +2)
            if r1 > 0.015: kr_score += 1.0
            if r1 > 0.025: kr_score += 1.0
            if r1 < -0.015: kr_score -= 1.0
            if r1 < -0.025: kr_score -= 1.0
            
            # Volatility Score (-1 ~ +1)
            volatility = (current['high'] - current['low']) / current['close'] if current['close'] > 0 else 0.0
            if volatility < 0.02: kr_score += 1.0
            elif volatility > 0.04: kr_score -= 1.0
            
            # Intraday Score (-1 ~ +1)
            if intraday_drop > -0.01: kr_score += 1.0
            elif intraday_drop < -0.025: kr_score -= 1.0
            
            return {
                "kr_score": kr_score,
                "intraday_drop": intraday_drop,
                "r1": r1,
                "r3": r3,
                "r5": r5
            }
        except Exception as e:
            logger.error(f"한국 장세 계산 실패: {e}")
            return {"kr_score": 0.0, "intraday_drop": 0.0}
    
    def _compute_us_prev_light(self, date: str) -> Dict[str, Any]:
        """미국 전일 장세 점수 계산 (경량)"""
        try:
            if self.spy_data.empty or self.qqq_data.empty or self.vix_data.empty:
                return {"us_prev_score": 0.0}
            
            # 날짜 변환 (미국 시장은 하루 뒤)
            target_date = pd.to_datetime(date, format='%Y%m%d') - timedelta(days=1)
            
            # SPY 데이터
            spy_mask = self.spy_data.index <= target_date
            if spy_mask.any():
                spy_recent = self.spy_data[spy_mask].tail(10)
                if len(spy_recent) >= 6:
                    spy_r3 = (spy_recent.iloc[-1]['close'] / spy_recent.iloc[-4]['close'] - 1)
                    spy_r5 = (spy_recent.iloc[-1]['close'] / spy_recent.iloc[-6]['close'] - 1)
                else:
                    spy_r3 = spy_r5 = 0.0
            else:
                spy_r3 = spy_r5 = 0.0
            
            # QQQ 데이터
            qqq_mask = self.qqq_data.index <= target_date
            if qqq_mask.any():
                qqq_recent = self.qqq_data[qqq_mask].tail(10)
                if len(qqq_recent) >= 6:
                    qqq_r3 = (qqq_recent.iloc[-1]['close'] / qqq_recent.iloc[-4]['close'] - 1)
                    qqq_r5 = (qqq_recent.iloc[-1]['close'] / qqq_recent.iloc[-6]['close'] - 1)
                else:
                    qqq_r3 = qqq_r5 = 0.0
            else:
                qqq_r3 = qqq_r5 = 0.0
            
            # VIX 데이터
            vix_mask = self.vix_data.index <= target_date
            if vix_mask.any():
                vix_recent = self.vix_data[vix_mask].tail(5)
                vix = vix_recent.iloc[-1]['close'] if len(vix_recent) > 0 else 20.0
            else:
                vix = 20.0
            
            # 점수 계산
            us_prev_score = 0.0
            
            # Trend Score
            if spy_r3 > 0.015: us_prev_score += 1.0
            if qqq_r3 > 0.020: us_prev_score += 1.0
            if spy_r5 < -0.03: us_prev_score -= 1.0
            if qqq_r5 < -0.04: us_prev_score -= 1.0
            
            # Vol Score
            if vix < 18: us_prev_score += 1.0
            if vix > 30: us_prev_score -= 1.0
            if vix > 35: us_prev_score -= 1.0
            
            return {
                "us_prev_score": us_prev_score,
                "spy_r3": spy_r3,
                "spy_r5": spy_r5,
                "qqq_r3": qqq_r3,
                "qqq_r5": qqq_r5,
                "vix": vix
            }
        except Exception as e:
            logger.error(f"미국 전일 장세 계산 실패: {e}")
            return {"us_prev_score": 0.0}
    
    def _compute_us_preopen_light(self, date: str) -> Dict[str, Any]:
        """미국 preopen 리스크 계산 (경량)"""
        try:
            # 백테스트에서는 preopen 데이터 없으므로 기본값
            return {
                "us_preopen_score": 0.0,
                "us_preopen_flag": "none"
            }
        except Exception as e:
            logger.error(f"미국 preopen 계산 실패: {e}")
            return {"us_preopen_score": 0.0, "us_preopen_flag": "none"}
    
    def _compose_global_regime_light(self, kr: Dict[str, Any], us_prev: Dict[str, Any], 
                                   us_preopen: Dict[str, Any]) -> Dict[str, Any]:
        """글로벌 레짐 조합 (경량)"""
        try:
            # 기본 점수 조합 (한국 60% + 미국 40%)
            base_score = 0.6 * kr.get("kr_score", 0.0) + 0.4 * us_prev.get("us_prev_score", 0.0)
            
            # preopen 리스크 페널티
            risk_penalty = 0.0
            preopen_flag = us_preopen.get("us_preopen_flag", "none")
            if preopen_flag == "watch":
                risk_penalty += 0.5
            elif preopen_flag == "danger":
                risk_penalty += 1.0
            
            final_score = base_score - risk_penalty
            
            # 레짐 결정
            # Crash 우선 규칙
            intraday_drop = kr.get("intraday_drop", 0.0)
            vix = us_prev.get("vix", 20.0)
            
            if vix > 35:
                final_regime = "crash"
            elif intraday_drop <= -0.025 and kr.get("kr_score", 0.0) < -1:
                final_regime = "crash"
            elif preopen_flag == "danger":
                final_regime = "crash"
            elif final_score >= 2.0:
                final_regime = "bull"
            elif final_score <= -2.0:
                final_regime = "bear"
            else:
                final_regime = "neutral"
            
            return {
                "final_score": final_score,
                "final_regime": final_regime
            }
        except Exception as e:
            logger.error(f"글로벌 레짐 조합 실패: {e}")
            return {"final_score": 0.0, "final_regime": "neutral"}

# 전역 인스턴스
backfill_analyzer = BackfillMarketAnalyzerLight()