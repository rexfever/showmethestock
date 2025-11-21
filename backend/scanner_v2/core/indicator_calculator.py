"""
지표 계산 모듈
"""
import pandas as pd
from indicators import (
    tema_smooth,
    dema_smooth,
    macd,
    rsi_tema,
    rsi_dema,
    obv,
    linreg_slope,
)


class IndicatorCalculator:
    """지표 계산기"""
    
    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        모든 지표 계산
        
        Args:
            df: OHLCV 데이터프레임
            
        Returns:
            지표가 추가된 데이터프레임
        """
        close = df["close"].astype(float)
        volume = df["volume"].astype(float)
        
        # 기본 지표
        df["TEMA20"] = tema_smooth(close, 20)
        df["DEMA10"] = dema_smooth(close, 10)
        
        # MACD
        macd_line, signal_line, osc = macd(close, 12, 26, 9)
        df["MACD_OSC"] = osc
        df["MACD_LINE"] = macd_line
        df["MACD_SIGNAL"] = signal_line
        
        # RSI
        df["RSI_TEMA"] = rsi_tema(close, 14)
        df["RSI_DEMA"] = rsi_dema(close, 14)
        
        # OBV
        df["OBV"] = obv(close, volume)
        
        # 거래량 이동평균
        df["VOL_MA5"] = volume.rolling(5).mean()
        
        # 추세 지표
        slope_lb = 20
        above_lb = 5
        df["TEMA20_SLOPE20"] = linreg_slope(df["TEMA20"], slope_lb)
        df["OBV_SLOPE20"] = linreg_slope(df["OBV"], slope_lb)
        df["DEMA10_SLOPE20"] = linreg_slope(df["DEMA10"], slope_lb)
        
        return df

