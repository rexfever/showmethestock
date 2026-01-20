"""
미국 주식 스캐너
기존 ScannerV2를 확장하여 미국 주식에 맞게 조정
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

from .core.indicator_calculator import IndicatorCalculator
from .core.us_filter_engine import USFilterEngine
from .core.us_scorer import USScorer
from .core.scanner import ScanResult
from market_analyzer import MarketCondition
from services.us_stocks_data import us_stocks_data
from services.us_stocks_universe import us_stocks_universe


class USScanner:
    """미국 주식 스캐너"""
    
    def __init__(self, config, market_analyzer=None):
        """
        Args:
            config: 설정 객체 (scanner_v2.config_v2.ScannerV2Config 또는 기존 config)
            market_analyzer: 시장 분석기 (선택)
        """
        self.config = config
        self.market_analyzer = market_analyzer
        self.indicator_calculator = IndicatorCalculator()
        # 미국용 FilterEngine과 Scorer 사용
        self.filter_engine = USFilterEngine(config)
        self.scorer = USScorer(config)
        
        # market_analysis_enable 설정 전달
        if hasattr(config, 'market_analysis_enable'):
            self.filter_engine.market_analysis_enable = config.market_analysis_enable
    
    def scan_one(self, symbol: str, date: str = None, market_condition: Optional[MarketCondition] = None) -> Optional[ScanResult]:
        """
        단일 종목 스캔
        
        Args:
            symbol: 종목 심볼 (예: "AAPL")
            date: 스캔 날짜 (YYYYMMDD 형식)
            market_condition: 시장 조건 (선택)
            
        Returns:
            ScanResult 또는 None (필터링된 경우)
        """
        try:
            # 1. 데이터 가져오기
            try:
                df = us_stocks_data.get_ohlcv(symbol, self.config.ohlcv_count, date)
            except Exception as e:
                logger.warning(f"{symbol} OHLCV 데이터 가져오기 실패: {e}")
                return None
            
            if df.empty or len(df) < 21:
                return None
            
            # 2. 기본 데이터 검증
            if df[["open", "high", "low", "close", "volume"]].isna().any().any():
                return None
            
            # 추가 데이터 검증: 음수 가격, 거래량 0, high < low 체크
            cur = df.iloc[-1]
            if (cur.get("close", 0) <= 0 or 
                cur.get("high", 0) <= 0 or 
                cur.get("low", 0) <= 0 or 
                cur.get("open", 0) <= 0 or
                cur.get("volume", 0) < 0 or
                cur.get("high", 0) < cur.get("low", 0) or
                cur.get("close", 0) > cur.get("high", 0) or
                cur.get("close", 0) < cur.get("low", 0)):
                return None
            
            # 3. 종목명 가져오기
            stock_info = us_stocks_universe.get_stock_info(symbol)
            stock_name = stock_info['name'] if stock_info and isinstance(stock_info, dict) else symbol
            
            # 4. 기본 하드 필터 적용 (지표 계산 전 - ETF, 유동성, 가격만)
            # USFilterEngine에서 처리하므로 여기서는 제거
            # (USFilterEngine.apply_hard_filters에서 USD 기준으로 체크)
            
            # 5. 지표 계산 (V1 지표 계산 사용)
            try:
                from scanner import compute_indicators
                df = compute_indicators(df)
                df['name'] = stock_name
            except Exception as e:
                logger.warning(f"{symbol} 지표 계산 실패: {e}")
                return None
            
            # 6. 지표 계산 후 하드 필터 적용 (RSI, 갭/이격, 과열 등)
            if not self.filter_engine.apply_hard_filters(df, stock_name, market_condition):
                return None
            
            # 7. 등락률 계산
            change_rate = self._calculate_change_rate(df)
            
            # 8. 소프트 필터 적용 (신호 충족 여부)
            matched, signals_count, signals_total = self.filter_engine.apply_soft_filters(
                df, market_condition, stock_name
            )
            
            if not matched:
                return None
            
            # 9. 점수 계산
            score, flags = self.scorer.calculate_score(df, market_condition)
            
            # 10. 전략 분류 (USScorer에서 이미 결정됨, flags에서 가져오기)
            strategy = flags.get("trading_strategy", "longterm")  # 기본값을 longterm으로 설정
            
            # 11. 레이블 결정
            score_label = flags.get("label", "후보 종목")
            
            # 12. 트렌드 정보 (TrendPayload 모델에 맞게 수정)
            cur = df.iloc[-1]
            above_cnt5 = int((df["TEMA20"] > df["DEMA10"]).tail(5).sum()) if len(df) >= 5 else 0
            trend = {
                "TEMA20_SLOPE20": float(cur.get("TEMA20_SLOPE20", 0)),
                "OBV_SLOPE20": float(cur.get("OBV_SLOPE20", 0)),
                "ABOVE_CNT5": above_cnt5,
                "DEMA10_SLOPE20": float(cur.get("DEMA10_SLOPE20", 0)),
            }
            
            # 13. 지표 정보 (IndicatorPayload 모델에 맞게 수정)
            indicators = {
                "TEMA": float(cur.get("TEMA20", 0)),
                "DEMA": float(cur.get("DEMA10", 0)),
                "MACD_OSC": float(cur.get("MACD_OSC", 0)),
                "MACD_LINE": float(cur.get("MACD_LINE", 0)),
                "MACD_SIGNAL": float(cur.get("MACD_SIGNAL", 0)),
                "RSI_TEMA": float(cur.get("RSI_TEMA", 0)),
                "RSI_DEMA": float(cur.get("RSI_DEMA", 0)),
                "OBV": float(cur.get("OBV", 0)),
                "VOL": int(cur.get("volume", 0)),
                "VOL_MA5": float(cur.get("VOL_MA5", 0)),
                "close": float(cur.get("close", 0)),
                "change_rate": change_rate,
            }
            
            return ScanResult(
                ticker=symbol,
                name=stock_name,
                match=True,
                score=score,
                indicators=indicators,
                trend=trend,
                strategy=strategy,
                flags=flags,
                score_label=score_label,
                market_condition=market_condition
            )
            
        except Exception as e:
            import traceback
            logger.error(f"{symbol} 스캔 오류: {e}\n{traceback.format_exc()}")
            return None
    
    def _calculate_change_rate(self, df: pd.DataFrame) -> float:
        """등락률 계산"""
        if len(df) < 2:
            return 0.0
        
        cur = df.iloc[-1]
        prev = df.iloc[-2]
        
        if prev.get("close", 0) > 0:
            return ((cur.get("close", 0) - prev.get("close", 0)) / prev.get("close", 0)) * 100
        return 0.0
    
    def scan(self, universe: List[str], date: str = None, market_condition: Optional[MarketCondition] = None) -> List[ScanResult]:
        """
        유니버스 전체 스캔
        
        Args:
            universe: 종목 심볼 리스트 (예: ["AAPL", "MSFT", ...])
            date: 스캔 날짜 (YYYYMMDD 형식)
            market_condition: 시장 조건 (선택)
            
        Returns:
            ScanResult 리스트
        """
        # 레짐별 필터 조건 적용 (약세장: 강화, 중립장: 중간, 강세장: 관대)
        # us_filter_engine.py에서 레짐별 조건이 자동으로 적용됨
        if market_condition:
            regime = getattr(market_condition, 'midterm_regime', None) or \
                     getattr(market_condition, 'final_regime', None) or \
                     getattr(market_condition, 'market_sentiment', 'neutral')
            logger.info(f"📊 시장 레짐: {regime} - 레짐별 필터 조건 적용")
        
        results = []
        passed_count = 0
        for symbol in universe:
            result = self.scan_one(symbol, date, market_condition)
            if result:
                results.append(result)
                passed_count += 1
                if passed_count <= 5:  # 처음 5개만 로그
                    logger.info(f"{symbol} 스캔 통과: 점수 {result.score:.2f}, 전략 {result.strategy}")
        
        if len(results) > 0:
            logger.info(f"스캔 완료: {len(universe)}개 중 {len(results)}개 종목 발견")
        
        # 점수 순으로 정렬
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Global Regime 기반 horizon cutoff 적용
        if market_condition:
            before_cutoff = len(results)
            results = self._apply_regime_cutoff(results, market_condition)
            after_cutoff = len(results)
            if before_cutoff > 0:
                logger.info(f"레짐 cutoff 적용: {before_cutoff}개 → {after_cutoff}개")
        
        return results
    
    def _apply_regime_cutoff(self, results: List[ScanResult], market_condition: MarketCondition) -> List[ScanResult]:
        """
        레짐 기반 cutoff 적용 (승률 우선 전략)
        - 강세장: 관대한 기준 (기본 cutoff - 1.0)
        - 중립장: 엄격한 기준 (6.0 이상만, 승률 46.7% → 높은 점수만 추천)
        - 약세장: 매우 엄격한 기준 (6.5 이상만, 승률 18.1% → 최고 점수만 추천)
        """
        from scanner_v2.config_regime import REGIME_CUTOFFS
        
        regime = getattr(market_condition, 'final_regime', 'neutral')
        cutoffs = REGIME_CUTOFFS.get(regime, REGIME_CUTOFFS['neutral'])
        
        filtered = []
        for result in results:
            # strategy가 None이거나 빈 문자열, "관찰"인 경우 처리
            if not result.strategy or result.strategy == "관찰":
                # "관찰" 전략은 longterm cutoff 사용
                strategy = "longterm"
            else:
                # 한국어 전략명을 영어로 변환
                strategy_map = {
                    "스윙": "swing",
                    "포지션": "position", 
                    "장기": "longterm"
                }
                strategy = strategy_map.get(result.strategy, result.strategy.lower())
            
            # cutoff 가져오기 (없으면 longterm 사용)
            cutoff = cutoffs.get(strategy, cutoffs.get('longterm', 6.0))
            
            # 레짐별 승률을 고려한 cutoff 조정 (승률 우선 전략)
            if regime == 'bull':
                # 강세장: 관대한 기준 (승률 88.1%로 매우 높음)
                cutoff_adjusted = cutoff - 1.0
            elif regime == 'neutral':
                # 중립장: 엄격한 기준 (전체 승률 46.7% → 4-6점 구간 승률 63.7%)
                # 4점 이상만 추천하여 승률 향상 (4-6점 구간이 최우수)
                cutoff_adjusted = max(4.0, cutoff)
            elif regime == 'bear':
                # 약세장: 매우 엄격한 기준 (전체 승률 18.1% → 최고 점수만 추천)
                # 6.5 이상만 추천하여 승률 향상 시도
                cutoff_adjusted = max(6.5, cutoff)
            else:
                # 기타: 기본 cutoff 사용
                cutoff_adjusted = cutoff
            
            if result.score >= cutoff_adjusted:
                filtered.append(result)
        
        return filtered

# 로거 설정
import logging
logger = logging.getLogger(__name__)

