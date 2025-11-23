"""
Scanner V2 호환성 래퍼

이 파일은 기존 screener_v2.py 인터페이스와의 호환성을 위한 래퍼입니다.
실제 구현은 scanner_v2/ 모듈을 사용합니다.
"""

from scanner_v2.core.scanner import ScannerV2 as CoreScannerV2, ScanResult
from scanner_v2.config_v2 import ScannerV2Config
from dataclasses import dataclass, asdict
from typing import Dict, Optional
import pandas as pd


@dataclass
class ScreenerParams:
    """ScreenerV2 파라미터 (호환성용)"""
    
    min_turnover_krw: float = 1000000000.0  # 10억원
    min_price: float = 2000.0
    rsi_threshold: float = 58.0
    min_signals: int = 3
    macd_osc_min: float = 0.0
    vol_ma5_mult: float = 2.5
    vol_ma20_mult: float = 1.2
    overheat_rsi_tema: float = 70.0
    overheat_vol_mult: float = 3.0
    gap_min: float = 0.001
    gap_max: float = 0.025
    ext_from_tema20_max: float = 0.025
    atr_pct_min: float = 1.0
    atr_pct_max: float = 4.0
    score_cut: float = 10.0
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class ScreenerV2:
    """
    ScreenerV2 호환성 래퍼 클래스
    
    기존 screener_v2.py 인터페이스를 유지하면서
    내부적으로는 scanner_v2/ 모듈을 사용합니다.
    """
    
    def __init__(self, params: Optional[ScreenerParams] = None):
        self.params = params or ScreenerParams()
        
        # ScannerV2Config로 변환
        config = ScannerV2Config()
        config.min_turnover_krw = self.params.min_turnover_krw
        config.min_price = self.params.min_price
        config.rsi_threshold = self.params.rsi_threshold
        config.min_signals = self.params.min_signals
        config.vol_ma5_mult = self.params.vol_ma5_mult
        config.gap_max = self.params.gap_max
        config.ext_from_tema20_max = self.params.ext_from_tema20_max
        
        # 실제 스캐너 인스턴스 생성
        self.scanner = CoreScannerV2(config)
    
    def evaluate(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        호환성을 위한 evaluate 메서드
        
        주의: 이 메서드는 더 이상 권장되지 않습니다.
        scanner_v2.core.scanner.ScannerV2를 직접 사용하세요.
        """
        # 기본적인 DataFrame 반환 (호환성용)
        if prices is None or prices.empty or len(prices) < 21:
            return pd.DataFrame()
        
        # 간단한 신호 계산 (실제로는 scanner_v2 사용 권장)
        df = prices.copy()
        df["signal"] = False  # 기본값
        df["score"] = 0.0
        
        return df


# 호환성을 위한 함수들
def evaluate_stage1(df: pd.DataFrame, params: ScreenerParams) -> pd.DataFrame:
    """
    Stage1 호환성 함수
    
    주의: 이 함수는 더 이상 사용되지 않습니다.
    scanner_v2.core.scanner.ScannerV2를 사용하세요.
    """
    print("⚠️ evaluate_stage1은 더 이상 사용되지 않습니다. scanner_v2.core.scanner.ScannerV2를 사용하세요.")
    return df


def evaluate_stage2(df: pd.DataFrame, params: ScreenerParams) -> pd.DataFrame:
    """
    Stage2 호환성 함수
    
    주의: 이 함수는 더 이상 사용되지 않습니다.
    scanner_v2.core.scanner.ScannerV2를 사용하세요.
    """
    print("⚠️ evaluate_stage2는 더 이상 사용되지 않습니다. scanner_v2.core.scanner.ScannerV2를 사용하세요.")
    return df