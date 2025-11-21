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
            
            # 4. 하드 필터 적용 (ETF 등)
            if not self.filter_engine.apply_hard_filters(df, stock_name, market_condition):
                return None
            
            # 5. 지표 계산
            df = self.indicator_calculator.compute_all(df)
            df['name'] = stock_name
            
            # 6. 등락률 계산
            change_rate = self._calculate_change_rate(df)
            
            # 7. 소프트 필터 적용 (신호 충족 여부)
            matched, signals_count, signals_total = self.filter_engine.apply_soft_filters(
                df, market_condition, stock_name
            )
            
            if not matched:
                return None
            
            # 8. 점수 계산
            score, flags = self.scorer.calculate_score(df, market_condition)
            
            # 9. 전략 결정
            from .strategy import determine_trading_strategy
            strategy_tuple = determine_trading_strategy(flags, score)
            strategy = strategy_tuple[0] if isinstance(strategy_tuple, tuple) else "관찰"
            
            # 10. 결과 생성
            cur = df.iloc[-1]
            return ScanResult(
                ticker=code,
                name=stock_name,
                match=True,
                score=score,
                indicators={
                    "TEMA": cur.TEMA20,
                    "DEMA": cur.DEMA10,
                    "MACD_OSC": cur.MACD_OSC,
                    "MACD_LINE": cur.MACD_LINE,
                    "MACD_SIGNAL": cur.MACD_SIGNAL,
                    "RSI_TEMA": cur.RSI_TEMA,
                    "RSI_DEMA": cur.RSI_DEMA,
                    "OBV": cur.OBV,
                    "VOL": cur.volume,
                    "VOL_MA5": cur.VOL_MA5,
                    "close": cur.close,
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
        return results
    
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

