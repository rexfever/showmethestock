"""
스캐너 V2 메인 클래스
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

from ..core.indicator_calculator import IndicatorCalculator
from ..core.filter_engine import FilterEngine
from ..core.scorer import Scorer
from market_analyzer import MarketCondition


@dataclass
class ScanResult:
    """스캔 결과 데이터 클래스"""
    ticker: str
    name: str
    match: bool
    score: float
    indicators: Dict[str, Any]
    trend: Dict[str, Any]
    strategy: str
    flags: Dict[str, Any]
    score_label: str
    market_condition: Optional[MarketCondition] = None


class ScannerV2:
    """스캐너 V2 메인 클래스"""
    
    def __init__(self, config, market_analyzer=None):
        """
        Args:
            config: 설정 객체 (scanner_v2.config_v2.ScannerV2Config 또는 기존 config)
            market_analyzer: 시장 분석기 (선택)
        """
        self.config = config
        self.market_analyzer = market_analyzer
        self.indicator_calculator = IndicatorCalculator()
        self.filter_engine = FilterEngine(config)
        self.scorer = Scorer(config)
        
        # market_analysis_enable 설정 전달
        if hasattr(config, 'market_analysis_enable'):
            self.filter_engine.market_analysis_enable = config.market_analysis_enable
    
    def scan_one(self, code: str, date: str = None, market_condition: Optional[MarketCondition] = None) -> Optional[ScanResult]:
        """
        단일 종목 스캔
        
        Args:
            code: 종목 코드
            date: 스캔 날짜 (YYYYMMDD 형식)
            market_condition: 시장 조건 (선택)
            
        Returns:
            ScanResult 또는 None (필터링된 경우)
        """
        try:
            from kiwoom_api import api
            
            # 1. 데이터 가져오기
            df = api.get_ohlcv(code, self.config.ohlcv_count, date)
            if df.empty or len(df) < 21:
                return None
            
            # 2. 기본 데이터 검증
            if df[["open", "high", "low", "close", "volume"]].isna().any().any():
                return None
            
            # 3. 종목명 가져오기
            stock_name = api.get_stock_name(code)
            
            # 4. 기본 하드 필터 적용 (지표 계산 전 - ETF, 유동성, 가격만)
            # 인버스 ETF 필터링
            if any(keyword in stock_name for keyword in self.config.inverse_etf_keywords):
                return None
            
            # 금리/채권 ETF 필터링
            if any(keyword in stock_name for keyword in self.config.bond_etf_keywords):
                return None
            
            # 유동성 필터 (지표 계산 전)
            if len(df) >= 20:
                avg_turnover = (df["close"].iloc[-20:] * df["volume"].iloc[-20:]).mean()
                if avg_turnover < self.config.min_turnover_krw:
                    return None
            
            # 가격 하한
            if df.iloc[-1].get("close", 0) < self.config.min_price:
                return None
            
            # 5. 지표 계산 (V1 지표 계산 사용)
            from scanner import compute_indicators
            df = compute_indicators(df)
            df['name'] = stock_name
            
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
            
            # 9-1. 시장 분리 신호 시 가산점 적용 (양방향)
            if market_condition and hasattr(market_condition, 'market_divergence') and market_condition.market_divergence:
                divergence_type = getattr(market_condition, 'divergence_type', '')
                try:
                    # 케이스 1: KOSPI 상승 + KOSDAQ 하락 → KOSPI 종목 가산점
                    if divergence_type == 'kospi_up_kosdaq_down':
                        if hasattr(market_condition, 'kospi_universe') and market_condition.kospi_universe:
                            if code in market_condition.kospi_universe:
                                score += 1.0
                                flags['kospi_bonus'] = True
                        else:
                            # Fallback: 캐시가 없으면 API 호출
                            from kiwoom_api import api
                            kospi_codes = api.get_top_codes('KOSPI', 200)
                            if code in kospi_codes:
                                score += 1.0
                                flags['kospi_bonus'] = True
                    # 케이스 2: KOSPI 하락 + KOSDAQ 상승 → KOSDAQ 종목 가산점
                    elif divergence_type == 'kospi_down_kosdaq_up':
                        if hasattr(market_condition, 'kosdaq_universe') and market_condition.kosdaq_universe:
                            if code in market_condition.kosdaq_universe:
                                score += 1.0
                                flags['kosdaq_bonus'] = True
                        else:
                            # Fallback: 캐시가 없으면 API 호출
                            from kiwoom_api import api
                            kosdaq_codes = api.get_top_codes('KOSDAQ', 200)
                            if code in kosdaq_codes:
                                score += 1.0
                                flags['kosdaq_bonus'] = True
                except Exception as e:
                    # 에러 발생 시 로깅
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"가산점 적용 실패: {e}")
            
            # 10. 전략 결정
            from .strategy import determine_trading_strategy
            strategy_tuple = determine_trading_strategy(flags, score)
            strategy = strategy_tuple[0] if isinstance(strategy_tuple, tuple) else "관찰"
            
            # 11. 결과 생성
            cur = df.iloc[-1]
            return ScanResult(
                ticker=code,
                name=stock_name,
                match=True,
                score=score,
                indicators={
                    "TEMA": cur["TEMA20"] if "TEMA20" in cur else cur.get("TEMA20", 0.0),
                    "DEMA": cur["DEMA10"] if "DEMA10" in cur else cur.get("DEMA10", 0.0),
                    "MACD_OSC": cur["MACD_OSC"] if "MACD_OSC" in cur else cur.get("MACD_OSC", 0.0),
                    "MACD_LINE": cur["MACD_LINE"] if "MACD_LINE" in cur else cur.get("MACD_LINE", 0.0),
                    "MACD_SIGNAL": cur["MACD_SIGNAL"] if "MACD_SIGNAL" in cur else cur.get("MACD_SIGNAL", 0.0),
                    "RSI_TEMA": cur["RSI_TEMA"] if "RSI_TEMA" in cur else cur.get("RSI_TEMA", 0.0),
                    "RSI_DEMA": cur["RSI_DEMA"] if "RSI_DEMA" in cur else cur.get("RSI_DEMA", 0.0),
                    "OBV": cur["OBV"] if "OBV" in cur else cur.get("OBV", 0.0),
                    "VOL": cur["volume"] if "volume" in cur else cur.get("volume", 0),
                    "VOL_MA5": cur["VOL_MA5"] if "VOL_MA5" in cur else cur.get("VOL_MA5", 0.0),
                    "close": cur["close"] if "close" in cur else cur.get("close", 0.0),
                    "change_rate": change_rate,
                },
                trend={
                    "TEMA20_SLOPE20": df.iloc[-1].get("TEMA20_SLOPE20", 0),
                    "OBV_SLOPE20": df.iloc[-1].get("OBV_SLOPE20", 0),
                    "ABOVE_CNT5": int((df["TEMA20"] > df["DEMA10"]).tail(5).sum()),
                    "DEMA10_SLOPE20": df.iloc[-1].get("DEMA10_SLOPE20", 0),
                },
                strategy=strategy,
                flags=flags,
                score_label=flags.get("label", "제외"),
                market_condition=market_condition
            )
        except Exception as e:
            print(f"스캔 오류 ({code}): {e}")
            return None
    
    def scan(self, universe: List[str], date: str = None, market_condition: Optional[MarketCondition] = None) -> List[ScanResult]:
        """
        유니버스 전체 스캔
        
        Args:
            universe: 종목 코드 리스트
            date: 스캔 날짜 (YYYYMMDD 형식)
            market_condition: 시장 조건 (선택)
            
        Returns:
            ScanResult 리스트
        """
        results = []
        for code in universe:
            result = self.scan_one(code, date, market_condition)
            if result:
                results.append(result)
        
        # 점수 순으로 정렬
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Global Regime v3 기반 horizon cutoff 적용
        if market_condition:
            results = self._apply_regime_cutoff(results, market_condition)
        
        return results
    
    def _apply_regime_cutoff(self, results: List[ScanResult], market_condition: MarketCondition) -> List[ScanResult]:
        """
        장세별 horizon cutoff 및 max candidates 적용
        
        v4 구조: midterm_regime을 사용하여 cutoff 결정 (단기 변동에 영향받지 않음)
        """
        # v4 구조: midterm_regime 우선 사용 (스캔 조건의 핵심)
        regime = None
        if market_condition is not None:
            if getattr(market_condition, "midterm_regime", None):
                regime = market_condition.midterm_regime
            elif getattr(market_condition, "final_regime", None):
                regime = market_condition.final_regime
            else:
                regime = getattr(market_condition, "market_sentiment", None)
        
        if regime is None:
            regime = "neutral"
        
        # 설정 파일에서 cutoff 및 max_candidates 로드
        try:
            from .config_regime import REGIME_CUTOFFS, MAX_CANDIDATES
            cutoffs = REGIME_CUTOFFS
            max_candidates = MAX_CANDIDATES
        except ImportError:
            # fallback to hardcoded values
            cutoffs = {
                'bull': {'swing': 6.0, 'position': 4.3, 'longterm': 5.0},
                'neutral': {'swing': 6.0, 'position': 4.5, 'longterm': 6.0},
                'bear': {'swing': 999.0, 'position': 5.5, 'longterm': 6.0},
                'crash': {'swing': 999.0, 'position': 999.0, 'longterm': 999.0}
            }
            max_candidates = {'swing': 20, 'position': 15, 'longterm': 20}
        
        regime_cutoffs = cutoffs.get(regime, cutoffs['neutral'])
        
        # horizon별 필터링
        # v4 구조: (score - risk_score) >= cutoff 기준 사용
        filtered_results = {'swing': [], 'position': [], 'longterm': []}
        
        for result in results:
            score = result.score
            # risk_score는 flags에서 가져오기 (scorer에서 계산된 값)
            risk_score = result.flags.get("risk_score", 0) if hasattr(result, 'flags') and result.flags else 0
            
            # effective_score = score - risk_score
            effective_score = (score or 0) - (risk_score or 0)
            
            # swing (단기)
            if effective_score >= regime_cutoffs['swing']:
                filtered_results['swing'].append(result)
            
            # position (중기)
            if effective_score >= regime_cutoffs['position']:
                filtered_results['position'].append(result)
            
            # longterm (장기)
            if effective_score >= regime_cutoffs['longterm']:
                filtered_results['longterm'].append(result)
        
        # max candidates 적용
        for horizon in filtered_results:
            if len(filtered_results[horizon]) > max_candidates[horizon]:
                filtered_results[horizon] = filtered_results[horizon][:max_candidates[horizon]]
        
        # 통합 결과 (중복 제거)
        final_results = []
        seen_tickers = set()
        
        # 우선순위: swing > position > longterm
        for horizon in ['swing', 'position', 'longterm']:
            for result in filtered_results[horizon]:
                if result.ticker not in seen_tickers:
                    final_results.append(result)
                    seen_tickers.add(result.ticker)
        
        print(f"🎯 장세별 필터링 ({regime}): swing={len(filtered_results['swing'])}, position={len(filtered_results['position'])}, longterm={len(filtered_results['longterm'])}, 최종={len(final_results)}개")
        
        return final_results
    
    def _calculate_change_rate(self, df: pd.DataFrame) -> float:
        """등락률 계산"""
        if len(df) < 2:
            return 0.0
        
        current_close = float(df.iloc[-1]["close"])
        # 유효한 전일 종가 찾기 (최대 5일 전까지)
        prev_close = 0
        for i in range(2, min(6, len(df) + 1)):
            candidate_close = float(df.iloc[-i]["close"])
            if candidate_close > 0:
                prev_close = candidate_close
                break
        
        if prev_close > 0:
            return round(((current_close - prev_close) / prev_close) * 100, 2)
        return 0.0

