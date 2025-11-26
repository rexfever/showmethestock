"""
시장 상황 분석 및 동적 조건 조정 모듈
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
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
    institution_flow: str  # 'buy', 'sell', 'neutral' - 기관 수급
    volume_trend: str      # 'high', 'normal', 'low'
    
    # 동적 조정된 조건들
    rsi_threshold: float
    min_signals: int
    macd_osc_min: float
    vol_ma5_mult: float
    gap_max: float
    ext_from_tema20_max: float
    sentiment_score: float = 0.0
    trend_metrics: Dict[str, Any] = field(default_factory=dict)
    breadth_metrics: Dict[str, Any] = field(default_factory=dict)
    flow_metrics: Dict[str, Any] = field(default_factory=dict)
    sector_metrics: Dict[str, Any] = field(default_factory=dict)
    volatility_metrics: Dict[str, Any] = field(default_factory=dict)
    foreign_flow_label: str = ""
    institution_flow_label: str = ""
    volume_trend_label: str = ""
    adjusted_params: Dict[str, Any] = field(default_factory=dict)
    analysis_notes: Optional[str] = None
    
    # Global Regime v3/v4 필드들
    final_regime: Optional[str] = None
    final_score: float = 0.0
    kr_score: float = 0.0
    us_prev_score: float = 0.0
    us_preopen_risk_score: float = 0.0
    kr_regime: str = ""
    us_prev_regime: str = ""
    us_preopen_flag: str = ""
    intraday_drop: float = 0.0
    version: str = "regime_v1"  # v1(기존), regime_v3, regime_v4
    
    # Global Regime v4 추가 필드들
    global_trend_score: float = 0.0
    global_risk_score: float = 0.0
    kr_trend_score: float = 0.0
    us_trend_score: float = 0.0
    kr_risk_score: float = 0.0
    us_risk_score: float = 0.0

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
        
    def analyze_market_condition(self, date: str = None, regime_version: str = None) -> MarketCondition:
        """
        시장 상황 분석 (레짐 버전에 따라 자동 선택)
        
        Args:
            date: 분석 날짜 (YYYYMMDD)
            regime_version: 레짐 분석 버전 (v1, v3, v4). None이면 config에서 읽음
        
        Returns:
            MarketCondition 객체
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        # 레짐 버전 결정
        if regime_version is None:
            try:
                from config import config
                regime_version = getattr(config, 'regime_version', 'v1')
            except Exception:
                regime_version = 'v1'
        
        # 레짐 버전에 따라 적절한 메서드 호출
        if regime_version == 'v4':
            return self.analyze_market_condition_v4(date, mode="production")
        elif regime_version == 'v3':
            return self.analyze_market_condition_v3(date, mode="production")
        else:
            # v1 (기본 장세 분석)
            return self._analyze_market_condition_v1(date)
    
    def _analyze_market_condition_v1(self, date: str = None) -> MarketCondition:
        """시장 상황 분석 v1 (기본 장세 분석)"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        # 거래일 체크
        try:
            from main import is_trading_day
            if not is_trading_day(date):
                logger.warning(f"거래일이 아닙니다: {date}, 기본 조건 반환")
                return self._get_default_condition(date)
        except Exception as e:
            logger.warning(f"거래일 체크 실패: {e}")
        
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
            universe_return, sample_size = self._get_universe_return(date)
            
            # effective_return 계산 로직 개선
            # 당일 수익률이 크게 변동한 경우(±2% 이상) 당일 수익률 우선 사용
            # 며칠간의 추세를 반영한 kospi_return은 가중 평균으로 계산됨
            # 당일 수익률 가져오기 (가중 평균 전 원본 값)
            daily_return_raw = self._get_daily_return_raw(date)
            
            # effective_return 계산 로직
            if kospi_return < -0.025:  # -2.5% 미만 (crash 판단 기준)
                # 급락장 판단을 위해 가장 낮은 수익률 사용
                candidates = [kospi_return]  # 추세 반영 수익률
                if kospi_low_return is not None:
                    candidates.append(kospi_low_return)
                if universe_return is not None:
                    candidates.append(universe_return)
                effective_return = min(candidates)
                
                # 로그 출력
                if kospi_low_return is not None and kospi_low_return < kospi_return:
                    logger.info(f"급락장 판단: 저가 기준 사용 - 추세 {kospi_return*100:.2f}%, 저가 {kospi_low_return*100:.2f}%")
                if universe_return is not None and universe_return < kospi_return:
                    logger.info(f"급락장 판단: 유니버스 기준 사용 - 추세 {kospi_return*100:.2f}%, 유니버스 평균 {universe_return*100:.2f}%")
            elif daily_return_raw is not None and abs(daily_return_raw) >= 0.02:  # ±2% 이상 변동
                # 큰 변동일 때는 당일 수익률 우선 사용 (가중 평균보다 정확)
                effective_return = daily_return_raw
                logger.info(f"큰 변동 감지: 당일 수익률 사용 - 당일 {daily_return_raw*100:.2f}%, 가중평균 {kospi_return*100:.2f}%")
            else:
                # 일반적인 경우 추세 반영 수익률 사용
                effective_return = kospi_return
            
            logger.info(f"KOSPI 종가 수익률: {kospi_return*100:.2f}%, 최종 effective_return: {effective_return*100:.2f}%")
            
            # 시장 상황 판단
            market_sentiment = self._determine_market_sentiment(effective_return, volatility)
            sector_rotation = self._analyze_sector_rotation(date)
            foreign_flow = self._analyze_foreign_flow(date)
            institution_flow = self._analyze_institution_flow(date)
            volume_trend = self._analyze_volume_trend(date)
            
            # 동적 조건 조정
            adjusted_conditions = self._adjust_conditions(
                market_sentiment, kospi_return, volatility, volume_trend
            )

            sentiment_score = {
                "bull": 2.0,
                "neutral": 0.0,
                "bear": -1.0,
                "crash": -2.0,
            }.get(market_sentiment, 0.0)

            trend_metrics = {
                "kospi_return_close": kospi_return,
                "kospi_return_low": kospi_low_return,
                "universe_return": universe_return,
                "effective_return": effective_return,
            }

            breadth_metrics = {
                "average_return": universe_return,
                "sample_size": sample_size,
            }

            flow_metrics = {
                "foreign_flow_raw": foreign_flow,
                "institution_flow_raw": institution_flow,
            }

            sector_metrics = {
                "primary_rotation": sector_rotation,
            }

            volatility_metrics = {
                "intraday_range_ratio": volatility,
            }

            condition = MarketCondition(
                date=date,
                kospi_return=effective_return,  # 유효 수익률 사용 (KOSPI 또는 유니버스 평균)
                volatility=volatility,
                market_sentiment=market_sentiment,
                sector_rotation=sector_rotation,
                foreign_flow=foreign_flow,
                institution_flow=institution_flow,
                volume_trend=volume_trend,
                sentiment_score=sentiment_score,
                trend_metrics={k: v for k, v in trend_metrics.items()},
                breadth_metrics={k: v for k, v in breadth_metrics.items()},
                flow_metrics={k: v for k, v in flow_metrics.items()},
                sector_metrics={k: v for k, v in sector_metrics.items()},
                volatility_metrics={k: v for k, v in volatility_metrics.items()},
                foreign_flow_label=foreign_flow or "neutral",
                institution_flow_label=institution_flow or "neutral",
                volume_trend_label=volume_trend or "normal",
                adjusted_params=dict(adjusted_conditions),
                analysis_notes=f"effective={effective_return:.4f}, vol={volatility:.4f}, sample={sample_size}",
                version="regime_v1",  # v1 기본 장세 분석
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
    
    def _get_daily_return_raw(self, date: str) -> Optional[float]:
        """당일 수익률만 가져오기 (가중 평균 전 원본 값)"""
        try:
            from kiwoom_api import api
            from main import is_trading_day
            
            if not is_trading_day(date):
                return None
            
            df = api.get_ohlcv("069500", 2, date)
            if df.empty or len(df) < 2:
                return None
            
            prev_close = df.iloc[-2]['close']
            curr_close = df.iloc[-1]['close']
            if prev_close > 0:
                return (curr_close / prev_close - 1)
            return None
        except Exception:
            return None
    
    def _get_kospi_data(self, date: str) -> Tuple[float, float, Optional[float]]:
        """KOSPI 지수 데이터 가져오기 - 며칠간의 추세를 반영한 종가, 변동성, 저가 기준 수익률 반환"""
        try:
            from kiwoom_api import api
            from main import is_trading_day
            import numpy as np
            
            # 거래일 체크
            if not is_trading_day(date):
                logger.warning(f"거래일이 아닙니다: {date}, 장세 분석 건너뜀")
                return 0.0, 0.02, None
            
            # KOSPI 200 지수 (069500) 데이터 가져오기
            # 며칠간의 추세를 분석하기 위해 최근 5일 데이터 사용
            lookback_days = 5
            df = api.get_ohlcv("069500", lookback_days, date)
            if df.empty or len(df) < 2:
                # 데이터가 없으면 기본값 반환
                return 0.0, 0.02, None
            
            # 마지막 행이 당일
            current_idx = len(df) - 1
            current_close = df.iloc[current_idx]['close']
            current_high = df.iloc[current_idx]['high']
            current_low = df.iloc[current_idx]['low']
            
            # 며칠간의 추세 분석
            # 1. 단기 추세 (최근 3일 평균 수익률)
            # 2. 중기 추세 (최근 5일 평균 수익률)
            # 3. 당일 수익률 (전일 대비)
            
            # 전일 종가 (당일 수익률 계산용)
            if len(df) >= 2:
                prev_close = df.iloc[current_idx - 1]['close']
                daily_return = (current_close / prev_close - 1) if prev_close > 0 else 0.0
            else:
                daily_return = 0.0
                prev_close = current_close
            
            # 며칠간의 수익률 계산
            returns_3d = []  # 최근 3일
            returns_5d = []  # 최근 5일
            
            for i in range(max(0, current_idx - 4), current_idx):
                if i + 1 < len(df):
                    prev = df.iloc[i]['close']
                    curr = df.iloc[i + 1]['close']
                    if prev > 0:
                        ret = (curr / prev - 1)
                        returns_5d.append(ret)
                        if i >= current_idx - 2:  # 최근 3일
                            returns_3d.append(ret)
            
            # 평균 수익률 계산 (가중 평균: 최근일수록 높은 가중치)
            if returns_3d:
                # 최근 3일: 가중치 [0.2, 0.3, 0.5]
                weights_3d = [0.2, 0.3, 0.5][-len(returns_3d):]
                weighted_3d = sum(r * w for r, w in zip(returns_3d, weights_3d)) / sum(weights_3d)
            else:
                weighted_3d = daily_return
            
            if returns_5d:
                # 최근 5일: 가중치 [0.1, 0.15, 0.2, 0.25, 0.3]
                weights_5d = [0.1, 0.15, 0.2, 0.25, 0.3][-len(returns_5d):]
                weighted_5d = sum(r * w for r, w in zip(returns_5d, weights_5d)) / sum(weights_5d)
            else:
                weighted_5d = daily_return
            
            # 최종 수익률: 단기 추세(50%) + 중기 추세(30%) + 당일(20%) 가중 평균
            close_return = (weighted_3d * 0.5 + weighted_5d * 0.3 + daily_return * 0.2)
            
            # 저가 기준 수익률 (급락장 판단용)
            low_return = None
            if current_low > 0 and prev_close > 0:
                low_return = (current_low / prev_close - 1)
            
            # 변동성 계산 (며칠간의 평균 변동성)
            volatilities = []
            for i in range(max(0, current_idx - 4), current_idx + 1):
                if i < len(df):
                    high = df.iloc[i]['high']
                    low = df.iloc[i]['low']
                    close = df.iloc[i]['close']
                    if close > 0:
                        vol = (high - low) / close
                        volatilities.append(vol)
            
            volatility = sum(volatilities) / len(volatilities) if volatilities else 0.02
            
            logger.info(f"KOSPI 추세 분석: 당일={daily_return*100:+.2f}%, 3일평균={weighted_3d*100:+.2f}%, 5일평균={weighted_5d*100:+.2f}%, 최종={close_return*100:+.2f}%")
            
            return close_return, volatility, low_return
            
        except Exception as e:
            logger.warning(f"KOSPI 데이터 가져오기 실패: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            # 실패 시 기본값 반환
            return 0.0, 0.02, None
    
    def _get_universe_return(self, date: str) -> Tuple[Optional[float], int]:
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
                return None, 0
            
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
            
            sample_count = len(returns)
            if not returns:
                return None, 0
            
            # 평균 등락률 계산
            avg_return = sum(returns) / sample_count
            
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
                    logger.info(f"유니버스 분석 (다중 샘플링): {sample_count}개 + 추가 샘플, 평균 등락률 {avg_return*100:.2f}%")
                else:
                    logger.info(f"유니버스 분석: {sample_count}개 종목, 평균 등락률 {avg_return*100:.2f}%")
            else:
                logger.info(f"유니버스 분석: {sample_count}개 종목, 평균 등락률 {avg_return*100:.2f}%")
            
            return avg_return, sample_count
            
        except Exception as e:
            logger.warning(f"유니버스 평균 등락률 계산 실패: {e}")
            return None, 0
    
    def _determine_market_sentiment(self, kospi_return: float, volatility: float) -> str:
        """시장 심리 판단 (며칠간의 추세 반영)"""
        # 며칠간의 추세를 반영했으므로 기준을 약간 완화
        if kospi_return > 0.010:  # +1.0% 이상 (완화: 하루 기준 +1.5% → 며칠 추세 +1.0%)
            return 'bull'
        elif kospi_return < -0.025:  # -2.5% 미만 (완화: 하루 기준 -3% → 며칠 추세 -2.5%)
            return 'crash'
        elif kospi_return < -0.010:  # -1.0% 미만 (완화: 하루 기준 -1.5% → 며칠 추세 -1.0%)
            return 'bear'
        else:
            return 'neutral'
    
    def _analyze_sector_rotation(self, date: str) -> str:
        """섹터 로테이션 분석 - 주요 섹터 대표 종목 수익률 비교"""
        try:
            from kiwoom_api import api
            
            # 주요 섹터 대표 종목 (코드: 섹터명)
            sector_representatives = {
                '005930': 'tech',      # 삼성전자 (반도체/IT)
                '000660': 'tech',      # SK하이닉스 (반도체)
                '035420': 'tech',      # NAVER (인터넷)
                '051910': 'value',     # LG화학 (화학)
                '005380': 'value',     # 현대차 (자동차)
                '055550': 'value',     # 신한지주 (금융)
                '105560': 'value',     # KB금융 (금융)
            }
            
            sector_returns = {'tech': [], 'value': []}
            
            # 각 섹터 대표 종목의 수익률 계산
            for code, sector in sector_representatives.items():
                try:
                    df = api.get_ohlcv(code, 2, date)
                    if df.empty or len(df) < 2:
                        continue
                    
                    prev_close = df.iloc[-2]['close']
                    current_close = df.iloc[-1]['close']
                    
                    if prev_close > 0:
                        stock_return = (current_close / prev_close - 1)
                        sector_returns[sector].append(stock_return)
                except Exception:
                    continue
            
            # 섹터별 평균 수익률 계산
            tech_avg = sum(sector_returns['tech']) / len(sector_returns['tech']) if sector_returns['tech'] else 0
            value_avg = sum(sector_returns['value']) / len(sector_returns['value']) if sector_returns['value'] else 0
            
            # 섹터 로테이션 판단
            diff = tech_avg - value_avg
            if abs(diff) < 0.005:  # 0.5% 미만 차이
                return 'mixed'
            elif diff > 0:
                return 'tech'
            else:
                return 'value'
                
        except Exception as e:
            logger.warning(f"섹터 로테이션 분석 실패: {e}")
            return 'mixed'  # 기본값
    
    def _analyze_foreign_flow(self, date: str) -> str:
        """외국인 자금 흐름 분석 - 대형주 수익률로 간접 추정"""
        try:
            from kiwoom_api import api
            
            # 외국인 선호 대형주 (시총 상위 + 외국인 보유 비중 높은 종목)
            large_caps = [
                '005930',  # 삼성전자
                '000660',  # SK하이닉스
                '207940',  # 삼성바이오로직스
                '005380',  # 현대차
                '035420',  # NAVER
            ]
            
            returns = []
            for code in large_caps:
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
                return 'neutral'
            
            # 대형주 평균 수익률로 외국인 수급 추정
            avg_return = sum(returns) / len(returns)
            
            if avg_return > 0.01:  # +1% 이상
                return 'buy'
            elif avg_return < -0.01:  # -1% 이하
                return 'sell'
            else:
                return 'neutral'
                
        except Exception as e:
            logger.warning(f"외국인 수급 분석 실패: {e}")
            return 'neutral'  # 기본값
    
    def _analyze_institution_flow(self, date: str) -> str:
        """기관 자금 흐름 분석 - 중대형주 수익률로 간접 추정"""
        try:
            from kiwoom_api import api
            
            # 기관 선호 중대형주 (안정적 배당주 + 우량주)
            institution_favorites = [
                '005930',  # 삼성전자
                '055550',  # 신한지주
                '105560',  # KB금융
                '086790',  # 하나금융지주
                '032830',  # 삼성생명
                '000810',  # 삼성화재
            ]
            
            returns = []
            for code in institution_favorites:
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
                return 'neutral'
            
            # 중대형주 평균 수익률로 기관 수급 추정
            avg_return = sum(returns) / len(returns)
            
            if avg_return > 0.008:  # +0.8% 이상 (기관은 외국인보다 보수적)
                return 'buy'
            elif avg_return < -0.008:  # -0.8% 이하
                return 'sell'
            else:
                return 'neutral'
                
        except Exception as e:
            logger.warning(f"기관 수급 분석 실패: {e}")
            return 'neutral'  # 기본값
    
    def _analyze_volume_trend(self, date: str) -> str:
        """거래량 추세 분석 - 유니버스 종목 거래량 이동평균 비교"""
        try:
            from kiwoom_api import api
            import config
            
            # 유니버스 종목 샘플링 (최대 30개)
            universe_kospi = getattr(config, 'universe_kospi', 100)
            universe_kosdaq = getattr(config, 'universe_kosdaq', 100)
            kospi = api.get_top_codes('KOSPI', universe_kospi)
            kosdaq = api.get_top_codes('KOSDAQ', universe_kosdaq)
            universe = [*kospi, *kosdaq]
            
            if not universe:
                return 'normal'
            
            import random
            sample_size = min(30, len(universe))
            sampled_universe = random.sample(universe, sample_size) if len(universe) > sample_size else universe
            
            volume_ratios = []
            for code in sampled_universe:
                try:
                    # 최근 20일 데이터 가져오기 (거래량 이동평균 계산용)
                    df = api.get_ohlcv(code, 20, date)
                    if df.empty or len(df) < 6:
                        continue
                    
                    # 현재 거래량
                    current_volume = df.iloc[-1]['volume']
                    
                    # 5일 평균 거래량 (최근 5일)
                    avg_volume_5d = df.iloc[-6:-1]['volume'].mean()
                    
                    if avg_volume_5d > 0:
                        volume_ratio = current_volume / avg_volume_5d
                        volume_ratios.append(volume_ratio)
                except Exception:
                    continue
            
            if not volume_ratios:
                return 'normal'
            
            # 평균 거래량 비율 계산
            avg_ratio = sum(volume_ratios) / len(volume_ratios)
            
            logger.info(f"거래량 추세 분석: {len(volume_ratios)}개 종목, 평균 비율 {avg_ratio:.2f}")
            
            # 거래량 추세 판단
            if avg_ratio > 1.3:  # 평균 대비 30% 이상
                return 'high'
            elif avg_ratio < 0.7:  # 평균 대비 30% 이하
                return 'low'
            else:
                return 'normal'
                
        except Exception as e:
            logger.warning(f"거래량 추세 분석 실패: {e}")
            return 'normal'  # 기본값
    
    def _adjust_conditions(self, market_sentiment: str, kospi_return: float, 
                          volatility: float, volume_trend: str) -> Dict:
        """시장 상황에 따른 조건 조정"""
        
        # 기본값 (Tight Preset) - 갭/이격 필터 완화
        base_conditions = {
            'rsi_threshold': 58.0,
            'min_signals': 3,
            'macd_osc_min': 0.0,
            'vol_ma5_mult': 1.8,
            'gap_max': 0.025,  # 1.5% -> 2.5% (완화)
            'ext_from_tema20_max': 0.025  # 1.5% -> 2.5% (완화)
        }
        
        # 시장 상황별 조정
        if market_sentiment == 'bull':
            # 강세장: 높은 RSI 허용 (과매수 구간까지 상승 가능)
            base_conditions.update({
                'rsi_threshold': 65.0,  # 58 -> 65 (높은 RSI 허용)
                'min_signals': 2,       # 3 -> 2
                'macd_osc_min': -5.0,   # 0 -> -5
                'vol_ma5_mult': 1.5,    # 1.8 -> 1.5
                'gap_max': 0.030,       # 3.0% (강세장: 추세 강하므로 갭 완화)
                'ext_from_tema20_max': 0.025  # 2.5% (통일: 과매수는 장세 무관)
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
                'gap_max': 0.015,       # 1.5% (약세장: 추세 약하므로 갭 엄격)
                'ext_from_tema20_max': 0.025  # 2.5% (통일: 과매수는 장세 무관)
            })
            
        else:  # neutral
            # 중립장: 기본 조건 유지
            base_conditions.update({
                'rsi_threshold': 58.0,  # 기본값 유지
                'min_signals': 3,       # 유지
                'macd_osc_min': 0.0,    # 유지
                'vol_ma5_mult': 1.6,    # 1.8 -> 1.6
                'gap_max': 0.025,       # 2.5% (중립장: 기본값)
                'ext_from_tema20_max': 0.025  # 2.5% (통일: 과매수는 장세 무관)
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
        base_params = {
            'rsi_threshold': 58.0,
            'min_signals': 3,
            'macd_osc_min': 0.0,
            'vol_ma5_mult': 1.8,
            'gap_max': 0.025,  # 1.5% -> 2.5% (완화)
            'ext_from_tema20_max': 0.025,  # 1.5% -> 2.5% (완화)
        }
        return MarketCondition(
            date=date,
            kospi_return=0.0,
            volatility=0.03,
            market_sentiment='neutral',
            sector_rotation='mixed',
            foreign_flow='neutral',
            volume_trend='normal',
            foreign_flow_label='neutral',
            volume_trend_label='normal',
            adjusted_params=dict(base_params),
            **base_params
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

    def compute_kr_regime_score_v3(self, date: str) -> Dict[str, Any]:
        """
        한국 장세 점수 계산 (Global Regime v3)
        - 기존 analyze_market_condition에서 사용하는 데이터를 재사용
        - KOSPI200 r1, r5, 20MA 대비 위치, intraday drop 등을 조합
        """
        try:
            # 기존 KOSPI 데이터 가져오기 재사용
            kospi_return, volatility, kospi_low_return = self._get_kospi_data(date)
            universe_return, sample_size = self._get_universe_return(date)
            
            # intraday drop 계산 (저가 기준)
            intraday_drop = kospi_low_return if kospi_low_return is not None else kospi_return
            
            # 1. Trend Score (-2 ~ +2)
            kr_trend_score = 0.0
            if kospi_return > 0.015: kr_trend_score += 1.0
            if kospi_return > 0.025: kr_trend_score += 1.0
            if kospi_return < -0.015: kr_trend_score -= 1.0
            if kospi_return < -0.025: kr_trend_score -= 1.0
            
            # 2. Volatility Score (-1 ~ +1)
            kr_vol_score = 0.0
            if volatility < 0.02: kr_vol_score += 1.0
            elif volatility > 0.04: kr_vol_score -= 1.0
            
            # 3. Breadth Score (-1 ~ +1) - 유니버스 평균 활용
            kr_breadth_score = 0.0
            if universe_return is not None:
                if universe_return > 0.01: kr_breadth_score += 1.0
                elif universe_return < -0.01: kr_breadth_score -= 1.0
            
            # 4. Intraday Score (-1 ~ +1)
            kr_intraday_score = 0.0
            if intraday_drop > -0.01: kr_intraday_score += 1.0
            elif intraday_drop < -0.025: kr_intraday_score -= 1.0
            
            # 총 점수
            kr_score = kr_trend_score + kr_vol_score + kr_breadth_score + kr_intraday_score
            
            # Crash 판단 (우선)
            if intraday_drop <= -0.025 and kospi_return < -0.02:
                kr_regime = "crash"
            elif kr_score >= 2:
                kr_regime = "bull"
            elif kr_score <= -2:
                kr_regime = "bear"
            else:
                kr_regime = "neutral"
            
            return {
                "kr_trend_score": kr_trend_score,
                "kr_vol_score": kr_vol_score,
                "kr_breadth_score": kr_breadth_score,
                "kr_intraday_score": kr_intraday_score,
                "kr_score": kr_score,
                "kr_regime": kr_regime,
                "intraday_drop": intraday_drop,
            }
            
        except Exception as e:
            logger.error(f"한국 장세 점수 계산 실패: {e}")
            return {
                "kr_trend_score": 0.0, "kr_vol_score": 0.0,
                "kr_breadth_score": 0.0, "kr_intraday_score": 0.0,
                "kr_score": 0.0, "kr_regime": "neutral", "intraday_drop": 0.0
            }
    
    def compute_us_prev_score(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        미국 전일 장세 점수 계산
        """
        # 데이터 검증
        required_keys = ["spy_r3", "qqq_r3", "spy_r5", "qqq_r5", "vix", "ust10y_change"]
        if not snapshot.get("valid", False) or not all(key in snapshot for key in required_keys):
            return {
                "us_prev_trend_score": 0.0, "us_prev_vol_score": 0.0,
                "us_prev_macro_score": 0.0, "us_prev_score": 0.0,
                "us_prev_regime": "neutral"
            }
        
        # Trend Score
        trend = 0.0
        spy_r3 = snapshot.get("spy_r3", 0) or 0
        qqq_r3 = snapshot.get("qqq_r3", 0) or 0
        spy_r5 = snapshot.get("spy_r5", 0) or 0
        qqq_r5 = snapshot.get("qqq_r5", 0) or 0
        
        if spy_r3 > 0.015: trend += 1.0
        if qqq_r3 > 0.020: trend += 1.0
        if spy_r5 < -0.03: trend -= 1.0
        if qqq_r5 < -0.04: trend -= 1.0
        
        # Vol Score
        vol = 0.0
        vix = snapshot.get("vix", 20) or 20
        if vix < 18: vol += 1.0
        if vix > 30: vol -= 1.0
        if vix > 35: vol -= 1.0
        
        # Macro Score
        macro = 0.0
        ust10y_change = snapshot.get("ust10y_change", 0) or 0
        if ust10y_change > 0.10: macro -= 1.0
        if ust10y_change < -0.10: macro += 1.0
        
        us_prev_score = trend + vol + macro
        
        # Regime 결정
        if vix > 35:
            us_prev_regime = "crash"
        elif us_prev_score >= 2:
            us_prev_regime = "bull"
        elif us_prev_score <= -2:
            us_prev_regime = "bear"
        else:
            us_prev_regime = "neutral"
        
        return {
            "us_prev_trend_score": trend,
            "us_prev_vol_score": vol,
            "us_prev_macro_score": macro,
            "us_prev_score": us_prev_score,
            "us_prev_regime": us_prev_regime,
        }
    
    def compute_us_preopen_risk(self, pre: Dict[str, Any]) -> Dict[str, Any]:
        """
        미국 pre-open 리스크 점수 계산
        """
        if not pre.get("valid", False):
            return {"us_preopen_risk_score": 0.0, "us_preopen_flag": "none"}
        
        risk = 0.0
        if pre["es_change"] < -0.01: risk += 1.0
        if pre["es_change"] < -0.02: risk += 1.0
        if pre["nq_change"] < -0.015: risk += 1.0
        if pre["nq_change"] < -0.03: risk += 1.0
        if pre["vix_fut_change"] > 0.05: risk += 1.0
        if pre["vix_fut_change"] > 0.10: risk += 1.0
        if pre["usdkrw_change"] > 0.005: risk += 1.0
        
        if risk <= 1:
            flag = "calm"
        elif risk <= 3:
            flag = "watch"
        else:
            flag = "danger"
        
        return {
            "us_preopen_risk_score": risk,
            "us_preopen_flag": flag,
        }
    
    def compose_global_regime_v3(self, kr: Dict[str, Any], us_prev: Dict[str, Any], 
                                us_preopen: Dict[str, Any], mode: str = "backtest") -> Dict[str, Any]:
        """
        글로벌 레짐 조합 함수
        """
        base_score = 0.6 * kr["kr_score"] + 0.4 * us_prev["us_prev_score"]
        
        risk_penalty = 0.0
        if us_preopen.get("us_preopen_flag") == "watch":
            risk_penalty += 0.5
        elif us_preopen.get("us_preopen_flag") == "danger":
            risk_penalty += 1.0
        
        final_score = base_score - risk_penalty
        
        # Crash 우선 규칙
        if us_prev["us_prev_regime"] == "crash":
            final_regime = "crash"
        elif kr["kr_regime"] == "crash":
            final_regime = "crash"
        elif mode == "live" and us_preopen.get("us_preopen_flag") == "danger":
            final_regime = "crash"
        elif final_score >= 2.0:
            final_regime = "bull"
        elif final_score <= -2.0:
            final_regime = "bear"
        else:
            final_regime = "neutral"
        
        return {
            "final_score": final_score,
            "final_regime": final_regime,
        }
    
    def analyze_market_condition_v3(self, date: Optional[str] = None, mode: str = "backtest") -> MarketCondition:
        """
        Global Regime Model v3 장세 분석
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        try:
            # 미국 데이터 로드
            from services.us_market_data import get_us_prev_snapshot, get_us_preopen_snapshot
            
            us_prev_snapshot = get_us_prev_snapshot(date)
            us_prev_scores = self.compute_us_prev_score(us_prev_snapshot)
            
            # 한국 데이터 계산
            kr_scores = self.compute_kr_regime_score_v3(date)
            
            # Pre-open 리스크 (live 모드에서만)
            if mode == "live":
                pre_snapshot = get_us_preopen_snapshot(date)
                us_preopen_scores = self.compute_us_preopen_risk(pre_snapshot)
            else:
                us_preopen_scores = {"us_preopen_risk_score": 0.0, "us_preopen_flag": "none"}
            
            # 글로벌 레짐 조합
            global_regime = self.compose_global_regime_v3(kr_scores, us_prev_scores, us_preopen_scores, mode)
            
            # 기존 분석도 실행 (호환성)
            base_condition = self.analyze_market_condition(date)
            
            # v3 필드 업데이트
            base_condition.final_regime = global_regime["final_regime"]
            base_condition.final_score = global_regime["final_score"]
            base_condition.kr_score = kr_scores["kr_score"]
            base_condition.us_prev_score = us_prev_scores["us_prev_score"]
            base_condition.us_preopen_risk_score = us_preopen_scores["us_preopen_risk_score"]
            base_condition.kr_regime = kr_scores["kr_regime"]
            base_condition.us_prev_regime = us_prev_scores["us_prev_regime"]
            base_condition.us_preopen_flag = us_preopen_scores["us_preopen_flag"]
            base_condition.intraday_drop = kr_scores["intraday_drop"]
            base_condition.version = "regime_v3"
            
            # DB 저장
            try:
                from services.regime_storage import upsert_regime
                regime_data = {
                    'final_regime': global_regime["final_regime"],
                    'kr_regime': kr_scores["kr_regime"],
                    'us_prev_regime': us_prev_scores["us_prev_regime"],
                    'us_preopen_flag': us_preopen_scores["us_preopen_flag"],
                    'us_metrics': us_prev_snapshot,
                    'kr_metrics': kr_scores,
                    'us_preopen_metrics': us_preopen_scores
                }
                upsert_regime(date, regime_data)
            except Exception as db_error:
                logger.warning(f"DB 저장 실패, 계속 진행: {db_error}")
                # DB 저장 실패해도 분석 결과는 반환
            
            logger.info(f"Global Regime v3 분석 완료: {date} -> {global_regime['final_regime']} (점수: {global_regime['final_score']:.2f})")
            return base_condition
            
        except Exception as e:
            logger.error(f"Global Regime v3 분석 실패: {e}")
            # Fallback to v1
            base_condition = self.analyze_market_condition(date)
            base_condition.version = "regime_v1"
            return base_condition
    
    def analyze_market_condition_v4(self, date: Optional[str] = None, mode: str = "backtest") -> MarketCondition:
        """
        Global Regime Model v4 장세 분석 (미국 선물 데이터 포함)
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        try:
            from scanner_v2.regime_v4 import analyze_regime_v4
            from services.regime_storage import upsert_regime
            
            # v4 분석 실행
            v4_result = analyze_regime_v4(date)
            
            # 기존 분석도 실행 (호환성)
            base_condition = self.analyze_market_condition(date)
            
            # v4 필드 업데이트
            base_condition.final_regime = v4_result["final_regime"]
            base_condition.final_score = v4_result["final_score"]
            base_condition.kr_score = v4_result["kr_trend_score"]
            base_condition.us_prev_score = v4_result["us_trend_score"]
            base_condition.kr_regime = v4_result["kr_regime"]
            base_condition.us_prev_regime = v4_result["us_prev_regime"]
            base_condition.global_trend_score = v4_result["global_trend_score"]
            base_condition.global_risk_score = v4_result["global_risk_score"]
            base_condition.kr_trend_score = v4_result["kr_trend_score"]
            base_condition.us_trend_score = v4_result["us_trend_score"]
            base_condition.kr_risk_score = v4_result["kr_risk_score"]
            base_condition.us_risk_score = v4_result["us_risk_score"]
            base_condition.version = "regime_v4"
            
            # DB 저장
            try:
                regime_data = {
                    'final_regime': v4_result["final_regime"],
                    'kr_regime': v4_result["kr_regime"],
                    'us_prev_regime': v4_result["us_prev_regime"],
                    'global_trend_score': v4_result["global_trend_score"],
                    'global_risk_score': v4_result["global_risk_score"],
                    'kr_trend_score': v4_result["kr_trend_score"],
                    'us_trend_score': v4_result["us_trend_score"],
                    'kr_risk_score': v4_result["kr_risk_score"],
                    'us_risk_score': v4_result["us_risk_score"],
                    'version': 'regime_v4'
                }
                upsert_regime(date, regime_data)
            except Exception as db_error:
                logger.warning(f"DB 저장 실패, 계속 진행: {db_error}")
            
            logger.info(f"Global Regime v4 분석 완료: {date} -> {v4_result['final_regime']} (trend: {v4_result['global_trend_score']:.2f}, risk: {v4_result['global_risk_score']:.2f})")
            return base_condition
            
        except Exception as e:
            logger.error(f"Global Regime v4 분석 실패: {e}")
            # Fallback to v3
            return self.analyze_market_condition_v3(date, mode)

# 전역 인스턴스
market_analyzer = MarketAnalyzer()

