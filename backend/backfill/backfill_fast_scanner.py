"""
백필용 고속 스캐너
- 스캐너 V2의 Stage1 + Score + Horizon 분류 경량화
- fallback 없음, 속도 최적화
- 로컬 캐시 기반
"""
import os
import pickle
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
try:
    from .backfill_fast_indicators import BackfillFastIndicators, calculate_indicators_batch
except ImportError:
    from backfill_fast_indicators import BackfillFastIndicators, calculate_indicators_batch

logger = logging.getLogger(__name__)

class BackfillFastScanner:
    """백필용 고속 스캐너"""
    
    def __init__(self, cache_dir: str = "data_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 레짐별 cutoff 설정 (scanner_v2/config_regime.py와 동일)
        self.regime_cutoffs = {
            'bull': {'swing': 6.0, 'position': 4.3, 'longterm': 5.0},
            'neutral': {'swing': 6.0, 'position': 4.5, 'longterm': 6.0},
            'bear': {'swing': 999.0, 'position': 5.5, 'longterm': 6.0},
            'crash': {'swing': 999.0, 'position': 999.0, 'longterm': 999.0}
        }
        
        # MAX_CANDIDATES 설정
        self.max_candidates = {
            'swing': 20,
            'position': 15,
            'longterm': 20
        }
        
        # 유니버스 캐시
        self.universe_cache = self.cache_dir / "universe_ohlcv.pkl"
        self.universe_data = {}
        self._load_universe_cache()
    
    def _load_universe_cache(self) -> None:
        """유니버스 캐시 로드"""
        try:
            if self.universe_cache.exists():
                with open(self.universe_cache, 'rb') as f:
                    self.universe_data = pickle.load(f)
                logger.info(f"유니버스 캐시 로드 완료: {len(self.universe_data)}개 종목")
            else:
                logger.warning("유니버스 캐시 파일이 없습니다")
        except Exception as e:
            logger.error(f"유니버스 캐시 로드 실패: {e}")
            self.universe_data = {}
    
    def scan_fast(self, date: str, final_regime: str, universe_codes: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        고속 스캔 실행
        
        Args:
            date: 스캔 날짜 (YYYYMMDD)
            final_regime: 글로벌 레짐 (bull/neutral/bear/crash)
            universe_codes: 스캔할 종목 코드 리스트 (None이면 전체)
            
        Returns:
            {horizon: [종목 리스트]} 딕셔너리
        """
        try:
            # crash인 경우 빈 결과 반환
            if final_regime == 'crash':
                return {'swing': [], 'position': [], 'longterm': []}
            
            # 유니버스 결정
            if universe_codes is None:
                universe_codes = list(self.universe_data.keys())[:200]  # 최대 200개
            
            # 해당 날짜의 데이터 추출
            date_data = self._extract_date_data(date, universe_codes)
            if not date_data:
                return {'swing': [], 'position': [], 'longterm': []}
            
            # Stage1 필터링
            stage1_candidates = self._apply_stage1_filters(date_data)
            
            # 점수 계산
            scored_candidates = self._calculate_scores(stage1_candidates)
            
            # Horizon 분류
            horizon_results = self._classify_horizons(scored_candidates, final_regime)
            
            logger.info(f"스캔 완료 ({date}): swing={len(horizon_results['swing'])}, position={len(horizon_results['position'])}, longterm={len(horizon_results['longterm'])}")
            
            return horizon_results
            
        except Exception as e:
            logger.error(f"고속 스캔 실패 ({date}): {e}")
            return {'swing': [], 'position': [], 'longterm': []}
    
    def _extract_date_data(self, date: str, universe_codes: List[str]) -> Dict[str, pd.DataFrame]:
        """해당 날짜의 데이터 추출"""
        date_data = {}
        target_date = pd.to_datetime(date, format='%Y%m%d')
        
        for code in universe_codes:
            if code not in self.universe_data:
                continue
                
            df = self.universe_data[code]
            if df.empty:
                continue
            
            # 해당 날짜까지의 데이터 필터링
            mask = df.index <= target_date
            if not mask.any():
                continue
                
            filtered_df = df[mask].tail(100)  # 최근 100일
            if len(filtered_df) >= 60:  # 최소 60일 필요
                date_data[code] = filtered_df
        
        return date_data
    
    def _apply_stage1_filters(self, date_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
        """Stage1 필터링 (turnover/price/ATR)"""
        candidates = {}
        
        for code, df in date_data.items():
            try:
                current = df.iloc[-1]
                
                # 기본 필터
                price = current['close']
                volume = current['volume']
                
                # 가격 필터 (1000원 이상)
                if price < 1000:
                    continue
                
                # 거래량 필터 (최소 거래량)
                if volume < 10000:
                    continue
                
                # ATR 필터 (변동성 체크)
                if len(df) >= 14:
                    atr_pct = self._calculate_simple_atr_pct(df)
                    if atr_pct < 1.0 or atr_pct > 15.0:  # 1~15% 범위
                        continue
                
                # 인디케이터 계산
                indicators = BackfillFastIndicators.calculate_indicators(df)
                
                candidates[code] = {
                    'code': code,
                    'price': price,
                    'volume': volume,
                    'indicators': indicators,
                    'df': df
                }
                
            except Exception as e:
                logger.debug(f"종목 {code} Stage1 필터링 실패: {e}")
                continue
        
        return candidates
    
    def _calculate_simple_atr_pct(self, df: pd.DataFrame, period: int = 14) -> float:
        """간단한 ATR 퍼센트 계산"""
        try:
            recent = df.tail(period + 1)
            if len(recent) < 2:
                return 2.0
            
            high = recent['high']
            low = recent['low']
            close = recent['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.mean()
            atr_pct = (atr / close.iloc[-1]) * 100
            
            return float(atr_pct)
        except:
            return 2.0
    
    def _calculate_scores(self, candidates: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """점수 계산 (스캐너 V2 로직 간소화)"""
        scored = {}
        
        for code, data in candidates.items():
            try:
                indicators = data['indicators']
                
                # 기본 점수
                score = 5.0
                
                # RSI 점수 (30-70 범위 선호)
                rsi = indicators['rsi']
                if 40 <= rsi <= 60:
                    score += 2.0
                elif 30 <= rsi <= 70:
                    score += 1.0
                elif rsi < 20 or rsi > 80:
                    score -= 1.0
                
                # MACD 점수
                macd = indicators['macd']
                if macd > 0:
                    score += 1.5
                elif macd < -0.5:
                    score -= 0.5
                
                # EMA60 대비 위치
                close = indicators['close']
                ema60 = indicators['ema60']
                if close > ema60 * 1.02:  # 2% 이상 위
                    score += 1.0
                elif close < ema60 * 0.98:  # 2% 이상 아래
                    score -= 0.5
                
                # ATR 점수 (적절한 변동성)
                atr_pct = indicators['atr_pct']
                if 2.0 <= atr_pct <= 5.0:
                    score += 1.0
                elif atr_pct > 8.0:
                    score -= 1.0
                
                # 최종 점수 범위 조정
                score = max(0.0, min(15.0, score))
                
                scored[code] = {
                    **data,
                    'score': score
                }
                
            except Exception as e:
                logger.debug(f"종목 {code} 점수 계산 실패: {e}")
                continue
        
        return scored
    
    def _classify_horizons(self, scored_candidates: Dict[str, Dict[str, Any]], 
                          final_regime: str) -> Dict[str, List[Dict[str, Any]]]:
        """Horizon 분류"""
        # 점수 순으로 정렬
        sorted_candidates = sorted(
            scored_candidates.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        # 레짐별 cutoff 가져오기
        cutoffs = self.regime_cutoffs.get(final_regime, self.regime_cutoffs['neutral'])
        
        # Horizon별 분류
        horizons = {'swing': [], 'position': [], 'longterm': []}
        
        for candidate in sorted_candidates:
            score = candidate['score']
            
            # 각 horizon 조건 체크
            if score >= cutoffs['swing'] and len(horizons['swing']) < self.max_candidates['swing']:
                horizons['swing'].append({
                    'code': candidate['code'],
                    'score': score,
                    'price': candidate['price'],
                    'volume': candidate['volume']
                })
            
            if score >= cutoffs['position'] and len(horizons['position']) < self.max_candidates['position']:
                horizons['position'].append({
                    'code': candidate['code'],
                    'score': score,
                    'price': candidate['price'],
                    'volume': candidate['volume']
                })
            
            if score >= cutoffs['longterm'] and len(horizons['longterm']) < self.max_candidates['longterm']:
                horizons['longterm'].append({
                    'code': candidate['code'],
                    'score': score,
                    'price': candidate['price'],
                    'volume': candidate['volume']
                })
        
        return horizons

# 전역 인스턴스
backfill_scanner = BackfillFastScanner()