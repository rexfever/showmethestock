"""
스캐너 V2 전용 설정
환경 변수에서 SCANNER_V2_ 접두사로 시작하는 값들을 로드
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


def _get_env_with_fallback(v2_key: str, v1_key: str, default: str):
    """V2 전용 설정이 있으면 사용, 없으면 V1 설정을 fallback으로 사용"""
    v2_value = os.getenv(v2_key)
    if v2_value is not None:
        return v2_value
    return os.getenv(v1_key, default)


@dataclass
class ScannerV2Config:
    """스캐너 V2 전용 설정
    SCANNER_V2_ 접두사가 있으면 우선 사용, 없으면 V1 설정(접두사 없음)을 fallback으로 사용
    """
    
    # === 신호 설정 ===
    min_signals: int = int(_get_env_with_fallback("SCANNER_V2_MIN_SIGNALS", "MIN_SIGNALS", "3"))
    macd_osc_min: float = float(_get_env_with_fallback("SCANNER_V2_MACD_OSC_MIN", "MACD_OSC_MIN", "0.0"))
    rsi_threshold: float = float(_get_env_with_fallback("SCANNER_V2_RSI_THRESHOLD", "RSI_THRESHOLD", "58"))
    rsi_upper_limit: float = float(_get_env_with_fallback("SCANNER_V2_RSI_UPPER_LIMIT", "RSI_UPPER_LIMIT", "83"))
    rsi_upper_limit_offset: float = float(os.getenv("SCANNER_V2_RSI_UPPER_LIMIT_OFFSET", "25.0"))  # V2 전용
    
    # === 갭/이격 필터 ===
    gap_min: float = float(_get_env_with_fallback("SCANNER_V2_GAP_MIN", "GAP_MIN", "0.002"))
    gap_max: float = float(_get_env_with_fallback("SCANNER_V2_GAP_MAX", "GAP_MAX", "0.015"))
    ext_from_tema20_max: float = float(_get_env_with_fallback("SCANNER_V2_EXT_FROM_TEMA20_MAX", "EXT_FROM_TEMA20_MAX", "0.015"))
    
    # === 거래량/유동성 ===
    vol_ma5_mult: float = float(_get_env_with_fallback("SCANNER_V2_VOL_MA5_MULT", "VOL_MA5_MULT", "2.5"))
    vol_ma20_mult: float = float(_get_env_with_fallback("SCANNER_V2_VOL_MA20_MULT", "VOL_MA20_MULT", "1.2"))
    min_turnover_krw: int = int(_get_env_with_fallback("SCANNER_V2_MIN_TURNOVER_KRW", "MIN_TURNOVER_KRW", "1000000000"))
    
    # === 변동성 필터 ===
    use_atr_filter: bool = _get_env_with_fallback("SCANNER_V2_USE_ATR_FILTER", "USE_ATR_FILTER", "false").lower() == "true"
    atr_pct_max: float = float(_get_env_with_fallback("SCANNER_V2_ATR_PCT_MAX", "ATR_PCT_MAX", "0.04"))
    atr_pct_min: float = float(_get_env_with_fallback("SCANNER_V2_ATR_PCT_MIN", "ATR_PCT_MIN", "0.01"))
    
    # === 가격 필터 ===
    min_price: int = int(_get_env_with_fallback("SCANNER_V2_MIN_PRICE", "MIN_PRICE", "2000"))
    
    # === 과열 필터 ===
    overheat_rsi_tema: int = int(_get_env_with_fallback("SCANNER_V2_OVERHEAT_RSI_TEMA", "OVERHEAT_RSI_TEMA", "70"))
    overheat_vol_mult: float = float(_get_env_with_fallback("SCANNER_V2_OVERHEAT_VOL_MULT", "OVERHEAT_VOL_MULT", "3.0"))
    
    # === 위험도 필터 ===
    risk_score_threshold: int = int(_get_env_with_fallback("SCANNER_V2_RISK_SCORE_THRESHOLD", "RISK_SCORE_THRESHOLD", "4"))
    
    # === 데이터 설정 ===
    ohlcv_count: int = int(_get_env_with_fallback("SCANNER_V2_OHLCV_COUNT", "OHLCV_COUNT", "120"))
    
    # === 기타 V1 호환성 ===
    rsi_setup_min: float = float(_get_env_with_fallback("SCANNER_V2_RSI_SETUP_MIN", "RSI_SETUP_MIN", "57"))
    market_analysis_enable: bool = _get_env_with_fallback("SCANNER_V2_MARKET_ANALYSIS_ENABLE", "MARKET_ANALYSIS_ENABLE", "true").lower() == "true"
    score_level_strong: int = int(_get_env_with_fallback("SCANNER_V2_SCORE_LEVEL_STRONG", "SCORE_LEVEL_STRONG", "10"))
    score_level_watch: int = int(_get_env_with_fallback("SCANNER_V2_SCORE_LEVEL_WATCH", "SCORE_LEVEL_WATCH", "7"))
    
    # === 점수 가중치 ===
    score_w_cross: int = int(_get_env_with_fallback("SCANNER_V2_SCORE_W_CROSS", "SCORE_W_CROSS", "3"))
    score_w_vol: int = int(_get_env_with_fallback("SCANNER_V2_SCORE_W_VOL", "SCORE_W_VOL", "2"))
    score_w_macd: int = int(_get_env_with_fallback("SCANNER_V2_SCORE_W_MACD", "SCORE_W_MACD", "1"))
    score_w_rsi: int = int(_get_env_with_fallback("SCANNER_V2_SCORE_W_RSI", "SCORE_W_RSI", "1"))
    score_w_tema_slope: int = int(_get_env_with_fallback("SCANNER_V2_SCORE_W_TEMA_SLOPE", "SCORE_W_TEMA_SLOPE", "2"))
    score_w_obv_slope: int = int(_get_env_with_fallback("SCANNER_V2_SCORE_W_OBV_SLOPE", "SCORE_W_OBV_SLOPE", "2"))
    score_w_above_cnt: int = int(_get_env_with_fallback("SCANNER_V2_SCORE_W_ABOVE_CNT", "SCORE_W_ABOVE_CNT", "2"))
    score_w_dema_slope: int = int(_get_env_with_fallback("SCANNER_V2_SCORE_W_DEMA_SLOPE", "SCORE_W_DEMA_SLOPE", "2"))
    
    # === 추세 필터 ===
    trend_slope_lookback: int = int(_get_env_with_fallback("SCANNER_V2_TREND_SLOPE_LOOKBACK", "TREND_SLOPE_LOOKBACK", "20"))
    trend_above_lookback: int = int(_get_env_with_fallback("SCANNER_V2_TREND_ABOVE_LOOKBACK", "TREND_ABOVE_LOOKBACK", "5"))
    require_dema_slope: str = _get_env_with_fallback("SCANNER_V2_REQUIRE_DEMA_SLOPE", "REQUIRE_DEMA_SLOPE", "optional")  # required, optional, off
    
    # === ETF 필터 ===
    inverse_etf_keywords: list = None
    bond_etf_keywords: list = None
    
    # === 미국 주식 전용 설정 (SCANNER_V2_US_ 접두사) ===
    # 변동성 필터 (미국 주식은 변동성이 크므로 범위 확대)
    us_atr_pct_min: float = float(os.getenv("SCANNER_V2_US_ATR_PCT_MIN", "0.005"))
    us_atr_pct_max: float = float(os.getenv("SCANNER_V2_US_ATR_PCT_MAX", "0.06"))
    
    # 갭/이격 필터 (미국 주식은 큰 갭이 흔함)
    us_gap_max: float = float(os.getenv("SCANNER_V2_US_GAP_MAX", "0.03"))
    us_ext_from_tema20_max: float = float(os.getenv("SCANNER_V2_US_EXT_FROM_TEMA20_MAX", "0.05"))
    
    # 거래량 필터 (미국 주식은 거래량 패턴이 다름)
    us_vol_ma5_mult: float = float(os.getenv("SCANNER_V2_US_VOL_MA5_MULT", "2.0"))
    us_vol_ma20_mult: float = float(os.getenv("SCANNER_V2_US_VOL_MA20_MULT", "1.0"))
    
    # RSI 필터 (미국 주식은 모멘텀 지속력이 강함)
    us_rsi_threshold: float = float(os.getenv("SCANNER_V2_US_RSI_THRESHOLD", "60"))
    us_rsi_upper_limit: float = float(os.getenv("SCANNER_V2_US_RSI_UPPER_LIMIT", "85"))
    us_rsi_setup_min: float = float(os.getenv("SCANNER_V2_US_RSI_SETUP_MIN", "60"))
    
    # 과열 필터 (미국 주식은 모멘텀 지속력이 강함)
    us_overheat_rsi_tema: int = int(os.getenv("SCANNER_V2_US_OVERHEAT_RSI_TEMA", "75"))
    us_overheat_vol_mult: float = float(os.getenv("SCANNER_V2_US_OVERHEAT_VOL_MULT", "4.0"))
    
    # 유동성/가격 필터 (미국 대형주 중심)
    us_min_turnover_usd: int = int(os.getenv("SCANNER_V2_US_MIN_TURNOVER_USD", "2000000"))
    us_min_price_usd: float = float(os.getenv("SCANNER_V2_US_MIN_PRICE_USD", "5.0"))
    
    def __post_init__(self):
        """초기화 후 처리"""
        if self.inverse_etf_keywords is None:
            self.inverse_etf_keywords = ["인버스", "레버리지", "2X", "3X"]
        if self.bond_etf_keywords is None:
            self.bond_etf_keywords = ["국채", "채권", "회사채", "머니마켓", "금리"]
    
    def get_weights(self) -> dict:
        """점수 가중치 반환"""
        return {
            'cross': self.score_w_cross,
            'volume': self.score_w_vol,
            'macd': self.score_w_macd,
            'rsi': self.score_w_rsi,
            'tema_slope': self.score_w_tema_slope,
            'dema_slope': self.score_w_dema_slope,
            'obv_slope': self.score_w_obv_slope,
            'above_cnt5': self.score_w_above_cnt,
        }


# 전역 설정 인스턴스
scanner_v2_config = ScannerV2Config()

