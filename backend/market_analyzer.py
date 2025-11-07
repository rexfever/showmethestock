"""
시장 상황 분석 및 동적 조건 조정 모듈
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class MarketCondition:
    """시장 상황 정보"""
    date: str
    kospi_return: float
    volatility: float
    market_sentiment: str  # 'bull', 'neutral', 'bear'
    sector_rotation: str   # 'tech', 'value', 'mixed'
    foreign_flow: str      # 'buy', 'sell', 'neutral'
    volume_trend: str      # 'high', 'normal', 'low'
    
    # 동적 조정된 조건들
    rsi_threshold: float
    min_signals: int
    macd_osc_min: float
    vol_ma5_mult: float
    gap_max: float
    ext_from_tema20_max: float

class MarketAnalyzer:
    """시장 상황 분석기"""
    
    def __init__(self):
        self.kospi_data = None
        self.last_analysis = None
        self._cache = {}
        self._cache_ttl = 300  # 5분 캐시
    
    def clear_cache(self):
        """캐시 클리어"""
        self._cache.clear()
        logger.info("시장 분석 캐시 클리어됨")
        
    def analyze_market_condition(self, date: str = None) -> MarketCondition:
        """시장 상황 분석"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        # 캐시 확인
        cache_key = f"market_analysis_{date}"
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self._cache_ttl:
                logger.info(f"캐시된 시장 분석 사용: {date}")
                return cached_data
            
        try:
            # KOSPI 데이터 가져오기 (실제로는 API 호출) - 종가와 저가 기준 수익률 모두 반환
            kospi_return, volatility, kospi_low_return = self._get_kospi_data(date)
            
            # 유니버스 전체 종목 분석 (급락장 판단용)
            universe_return = self._get_universe_return(date)
            
            # 급락장 판단을 위해 가장 낮은 수익률 사용
            # 후보: KOSPI 종가, KOSPI 저가, 유니버스 평균
            candidates = [kospi_return]
            if kospi_low_return is not None:
                candidates.append(kospi_low_return)
            if universe_return is not None:
                candidates.append(universe_return)
            
            # 가장 낮은 값 사용
            effective_return = min(candidates)
            
            # 로그 출력
            if kospi_low_return is not None and kospi_low_return < kospi_return:
                logger.info(f"저가 기준 사용: 종가 {kospi_return*100:.2f}%, 저가 {kospi_low_return*100:.2f}%")
            if universe_return is not None and universe_return < kospi_return:
                logger.info(f"유니버스 기준 사용: KOSPI {kospi_return*100:.2f}%, 유니버스 평균 {universe_return*100:.2f}%")
            logger.info(f"최종 effective_return: {effective_return*100:.2f}%")
            
            # 시장 상황 판단
            market_sentiment = self._determine_market_sentiment(effective_return, volatility)
            sector_rotation = self._analyze_sector_rotation(date)
            foreign_flow = self._analyze_foreign_flow(date)
            volume_trend = self._analyze_volume_trend(date)
            
            # 동적 조건 조정
            adjusted_conditions = self._adjust_conditions(
                market_sentiment, kospi_return, volatility, volume_trend
            )
            
            condition = MarketCondition(
                date=date,
                kospi_return=effective_return,  # 유효 수익률 사용 (KOSPI 또는 유니버스 평균)
                volatility=volatility,
                market_sentiment=market_sentiment,
                sector_rotation=sector_rotation,
                foreign_flow=foreign_flow,
                volume_trend=volume_trend,
                **adjusted_conditions
            )
            
            # 캐시에 저장
            self._cache[cache_key] = (condition, datetime.now())
            self.last_analysis = condition
            logger.info(f"시장 상황 분석 완료: {market_sentiment} (유효 수익률: {effective_return*100:.2f}%), RSI 임계값: {condition.rsi_threshold}")
            
            return condition
            
        except Exception as e:
            logger.error(f"시장 상황 분석 실패: {e}")
            # 기본값 반환
            return self._get_default_condition(date)
    
    def _get_kospi_data(self, date: str) -> Tuple[float, float, Optional[float]]:
        """KOSPI 지수 데이터 가져오기 - 종가, 변동성, 저가 기준 수익률 반환"""
        try:
            from kiwoom_api import api
            
            # KOSPI 200 지수 (069500) 데이터 가져오기
            df = api.get_ohlcv("069500", 2, date)
            if df.empty or len(df) < 2:
                # 데이터가 없으면 기본값 반환
                return 0.0, 0.02, None
            
            # 전일 종가
            prev_close = df.iloc[-2]['close']
            current_close = df.iloc[-1]['close']
            current_high = df.iloc[-1]['high']
            current_low = df.iloc[-1]['low']
            
            # 종가 기준 수익률
            close_return = (current_close / prev_close - 1) if prev_close > 0 else 0.0
            
            # 저가 기준 수익률 (급락장 판단용)
            low_return = None
            if current_low > 0 and prev_close > 0:
                low_return = (current_low / prev_close - 1)
            
            # 변동성 계산 (간단한 ATR 기반)
            volatility = (current_high - current_low) / current_close if current_close > 0 else 0.02
            
            return close_return, volatility, low_return
            
        except Exception as e:
            logger.warning(f"KOSPI 데이터 가져오기 실패: {e}")
            # 실패 시 기본값 반환
            return 0.0, 0.02, None
    
    def _get_universe_return(self, date: str) -> Optional[float]:
        """유니버스 전체 종목의 평균 등락률 계산"""
        try:
            from kiwoom_api import api
            import config
            
            # 유니버스 종목 가져오기
            universe_kospi = getattr(config, 'universe_kospi', 100)
            universe_kosdaq = getattr(config, 'universe_kosdaq', 100)
            kospi = api.get_top_codes('KOSPI', universe_kospi)
            kosdaq = api.get_top_codes('KOSDAQ', universe_kosdaq)
            universe = [*kospi, *kosdaq]
            
            if not universe:
                return None
            
            # 샘플링 (전체 조회 시 시간이 오래 걸리므로 최대 100개 사용)
            # 급락장 판단 정확도를 위해 샘플 크기 증가
            import random
            sample_size = min(100, len(universe))
            sampled_universe = random.sample(universe, sample_size) if len(universe) > sample_size else universe
            
            returns = []
            for code in sampled_universe:
                try:
                    df = api.get_ohlcv(code, 2, date)
                    if df.empty or len(df) < 2:
                        continue
                    
                    prev_close = df.iloc[-2]['close']
                    current_close = df.iloc[-1]['close']
                    
                    if prev_close > 0:
                        stock_return = (current_close / prev_close - 1)
                        returns.append(stock_return)
                except Exception:
                    continue
            
            if not returns:
                return None
            
            # 평균 등락률 계산
            avg_return = sum(returns) / len(returns)
            
            # 추가: 여러 번 샘플링해서 더 안정적인 평균 계산 (시간이 허용되는 경우)
            # 첫 번째 샘플의 평균이 -2.5% 이하인 경우, 추가 샘플링으로 확인
            if avg_return < -0.025 and len(universe) > sample_size:
                # 추가 샘플링 (최대 3번 더)
                additional_samples = []
                for i in range(3):
                    additional_sampled = random.sample(universe, min(50, len(universe)))
                    additional_returns = []
                    for code in additional_sampled:
                        try:
                            df = api.get_ohlcv(code, 2, date)
                            if df.empty or len(df) < 2:
                                continue
                            prev_close = df.iloc[-2]['close']
                            current_close = df.iloc[-1]['close']
                            if prev_close > 0:
                                additional_returns.append((current_close / prev_close - 1))
                        except:
                            continue
                    if additional_returns:
                        additional_samples.append(sum(additional_returns) / len(additional_returns))
                
                # 모든 샘플의 평균 사용
                if additional_samples:
                    all_returns = [avg_return] + additional_samples
                    avg_return = sum(all_returns) / len(all_returns)
                    logger.info(f"유니버스 분석 (다중 샘플링): {len(returns)}개 + 추가 샘플, 평균 등락률 {avg_return*100:.2f}%")
                else:
                    logger.info(f"유니버스 분석: {len(returns)}개 종목, 평균 등락률 {avg_return*100:.2f}%")
            else:
                logger.info(f"유니버스 분석: {len(returns)}개 종목, 평균 등락률 {avg_return*100:.2f}%")
            
            return avg_return
            
        except Exception as e:
            logger.warning(f"유니버스 평균 등락률 계산 실패: {e}")
            return None
    
    def _determine_market_sentiment(self, kospi_return: float, volatility: float) -> str:
        """시장 심리 판단"""
        if kospi_return > 0.02:  # +2% 이상
            return 'bull'
        elif kospi_return < -0.03:  # -3% 미만 (급락장)
            return 'crash'
        elif kospi_return < -0.02:  # -2% 미만 (약세장)
            return 'bear'
        else:
            return 'neutral'
    
    def _analyze_sector_rotation(self, date: str) -> str:
        """섹터 로테이션 분석"""
        # 임시 로직 - 실제로는 섹터별 성과 분석
        import random
        sectors = ['tech', 'value', 'mixed']
        return random.choice(sectors)
    
    def _analyze_foreign_flow(self, date: str) -> str:
        """외국인 자금 흐름 분석"""
        # 임시 로직 - 실제로는 외국인 매매동향 분석
        import random
        flows = ['buy', 'sell', 'neutral']
        return random.choice(flows)
    
    def _analyze_volume_trend(self, date: str) -> str:
        """거래량 추세 분석"""
        # 임시 로직 - 실제로는 거래량 분석
        import random
        trends = ['high', 'normal', 'low']
        return random.choice(trends)
    
    def _adjust_conditions(self, market_sentiment: str, kospi_return: float, 
                          volatility: float, volume_trend: str) -> Dict:
        """시장 상황에 따른 조건 조정"""
        
        # 기본값 (Tight Preset)
        base_conditions = {
            'rsi_threshold': 58.0,
            'min_signals': 3,
            'macd_osc_min': 0.0,
            'vol_ma5_mult': 1.8,
            'gap_max': 0.015,
            'ext_from_tema20_max': 0.015
        }
        
        # 시장 상황별 조정
        if market_sentiment == 'bull':
            # 강세장: 높은 RSI 허용 (과매수 구간까지 상승 가능)
            base_conditions.update({
                'rsi_threshold': 65.0,  # 58 -> 65 (높은 RSI 허용)
                'min_signals': 2,       # 3 -> 2
                'macd_osc_min': -5.0,   # 0 -> -5
                'vol_ma5_mult': 1.5,    # 1.8 -> 1.5
                'gap_max': 0.02,        # 1.5% -> 2%
                'ext_from_tema20_max': 0.02
            })
            
        elif market_sentiment == 'crash':
            # 급락장: 추천하지 않음 (빈 리스트 반환을 위한 설정)
            # 실제로는 execute_scan_with_fallback에서 빈 리스트 반환
            base_conditions.update({
                'rsi_threshold': 40.0,   # 낮은 RSI 허용 (하지만 추천 안 함)
                'min_signals': 999,      # 거의 불가능한 조건 (추천 안 함)
                'macd_osc_min': 999.0,   # 거의 불가능한 조건
                'vol_ma5_mult': 999.0,   # 거의 불가능한 조건
                'gap_max': 0.001,        # 거의 불가능한 조건
                'ext_from_tema20_max': 0.001
            })
            
        elif market_sentiment == 'bear':
            # 약세장: 낮은 RSI 허용 (과매도 구간에서 반등 기대)
            base_conditions.update({
                'rsi_threshold': 45.0,  # 58 -> 45 (낮은 RSI 허용)
                'min_signals': 4,       # 3 -> 4
                'macd_osc_min': 5.0,    # 0 -> 5
                'vol_ma5_mult': 2.0,    # 1.8 -> 2.0
                'gap_max': 0.01,        # 1.5% -> 1%
                'ext_from_tema20_max': 0.01
            })
            
        else:  # neutral
            # 중립장: 기본 조건 유지
            base_conditions.update({
                'rsi_threshold': 58.0,  # 기본값 유지
                'min_signals': 3,       # 유지
                'macd_osc_min': 0.0,    # 유지
                'vol_ma5_mult': 1.6,    # 1.8 -> 1.6
                'gap_max': 0.018,       # 1.5% -> 1.8%
                'ext_from_tema20_max': 0.018
            })
        
        # 변동성 기반 추가 조정 (제한적)
        if volatility > 0.04:  # 고변동성
            base_conditions['rsi_threshold'] += 2.0  # 5.0 -> 2.0 (제한적)
            base_conditions['min_signals'] += 1
            
        elif volatility < 0.02:  # 저변동성
            base_conditions['rsi_threshold'] -= 1.0  # 3.0 -> 1.0 (제한적)
            
        # 거래량 추세 기반 조정
        if volume_trend == 'high':
            base_conditions['vol_ma5_mult'] -= 0.2  # 거래량이 많으면 완화
        elif volume_trend == 'low':
            base_conditions['vol_ma5_mult'] += 0.2  # 거래량이 적으면 강화
            
        return base_conditions
    
    def _get_default_condition(self, date: str) -> MarketCondition:
        """기본 조건 반환 (분석 실패 시)"""
        return MarketCondition(
            date=date,
            kospi_return=0.0,
            volatility=0.03,
            market_sentiment='neutral',
            sector_rotation='mixed',
            foreign_flow='neutral',
            volume_trend='normal',
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=1.8,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
    
    def get_market_preset(self, market_sentiment: str) -> Dict:
        """시장 상황별 프리셋 반환"""
        presets = {
            'bull': {
                'rsi_threshold': 65.0,  # 높은 RSI 허용
                'min_signals': 2,
                'macd_osc_min': -5.0,
                'vol_ma5_mult': 1.5,
                'gap_max': 0.02,
                'ext_from_tema20_max': 0.02,
                'description': '강세장: 높은 RSI 허용으로 상승 추세 포착'
            },
            'neutral': {
                'rsi_threshold': 58.0,  # 기본값 유지
                'min_signals': 3,
                'macd_osc_min': 0.0,
                'vol_ma5_mult': 1.6,
                'gap_max': 0.018,
                'ext_from_tema20_max': 0.018,
                'description': '중립장: 균형잡힌 조건 (9월 13일 스타일)'
            },
            'bear': {
                'rsi_threshold': 45.0,  # 낮은 RSI 허용
                'min_signals': 4,
                'macd_osc_min': 5.0,
                'vol_ma5_mult': 2.0,
                'gap_max': 0.01,
                'ext_from_tema20_max': 0.01,
                'description': '약세장: 엄격한 조건으로 리스크 관리'
            },
            'crash': {
                'rsi_threshold': 40.0,
                'min_signals': 999,  # 추천하지 않음
                'macd_osc_min': 999.0,
                'vol_ma5_mult': 999.0,
                'gap_max': 0.001,
                'ext_from_tema20_max': 0.001,
                'description': '급락장: 추천하지 않음 (안전 우선)'
            }
        }
        
        return presets.get(market_sentiment, presets['neutral'])

# 전역 인스턴스
market_analyzer = MarketAnalyzer()

