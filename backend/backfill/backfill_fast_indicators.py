"""
백필용 고속 인디케이터 계산기
- 최소한의 인디케이터만 계산 (EMA60, RSI, MACD, ATR)
- Pandas vectorization 활용
- 로컬 캐시 기반
"""
import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BackfillFastIndicators:
    """백필용 고속 인디케이터 계산기"""
    
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> Dict[str, Any]:
        """
        최소한의 인디케이터 계산
        
        Args:
            df: OHLCV 데이터프레임 (최소 60일 필요)
            
        Returns:
            인디케이터 딕셔너리
        """
        try:
            if len(df) < 60:
                return BackfillFastIndicators._get_default_indicators()
            
            # 최신 데이터
            current = df.iloc[-1]
            
            # EMA60 계산
            ema60 = BackfillFastIndicators._calculate_ema(df['close'], 60)
            
            # RSI(14) 계산
            rsi = BackfillFastIndicators._calculate_rsi(df['close'], 14)
            
            # MACD(12, 26, 9) 계산
            macd = BackfillFastIndicators._calculate_macd(df['close'], 12, 26, 9)
            
            # ATR(14) 계산
            atr_pct = BackfillFastIndicators._calculate_atr_pct(df, 14)
            
            return {
                "close": float(current['close']),
                "ema60": float(ema60.iloc[-1]) if not ema60.empty else float(current['close']),
                "rsi": float(rsi.iloc[-1]) if not rsi.empty else 50.0,
                "macd": float(macd.iloc[-1]) if not macd.empty else 0.0,
                "atr_pct": float(atr_pct.iloc[-1]) if not atr_pct.empty else 2.0
            }
        except Exception as e:
            logger.error(f"인디케이터 계산 실패: {e}")
            return BackfillFastIndicators._get_default_indicators()
    
    @staticmethod
    def _calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """EMA 계산"""
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def _calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def _calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
        """MACD 계산"""
        ema_fast = series.ewm(span=fast).mean()
        ema_slow = series.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        macd_histogram = macd_line - signal_line
        return macd_histogram
    
    @staticmethod
    def _calculate_atr_pct(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR 퍼센트 계산"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        atr_pct = (atr / close) * 100
        
        return atr_pct
    
    @staticmethod
    def _get_default_indicators() -> Dict[str, Any]:
        """기본 인디케이터 값"""
        return {
            "close": 0.0,
            "ema60": 0.0,
            "rsi": 50.0,
            "macd": 0.0,
            "atr_pct": 2.0
        }

# 배치 처리용 함수
def calculate_indicators_batch(df_dict: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
    """
    여러 종목의 인디케이터를 배치로 계산
    
    Args:
        df_dict: {종목코드: OHLCV DataFrame} 딕셔너리
        
    Returns:
        {종목코드: 인디케이터 딕셔너리} 딕셔너리
    """
    results = {}
    
    for code, df in df_dict.items():
        try:
            results[code] = BackfillFastIndicators.calculate_indicators(df)
        except Exception as e:
            logger.error(f"종목 {code} 인디케이터 계산 실패: {e}")
            results[code] = BackfillFastIndicators._get_default_indicators()
    
    return results