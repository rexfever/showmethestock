import os
from dataclasses import dataclass, field
import json
from dotenv import load_dotenv
from environment import env_detector, get_config_overrides


# 1) 루트 .env 로드
load_dotenv()
# 2) backend/.env 로드(있으면 우선 적용)
backend_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(backend_env_path):
    load_dotenv(dotenv_path=backend_env_path, override=True)


@dataclass
class Config:
    # 환경 정보
    environment: str = env_detector.environment
    is_local: bool = env_detector.is_local
    is_server: bool = env_detector.is_server
    
    app_key: str = os.getenv("APP_KEY", "")
    app_secret: str = os.getenv("APP_SECRET", "")
    api_base: str = os.getenv("API_BASE", "https://api.kiwoom.com")
    # 키움 REST 토큰 경로
    token_path: str = os.getenv("TOKEN_PATH", "/oauth2/token")

    # 환경별 기본값 적용
    _env_overrides = get_config_overrides()
    universe_kospi: int = int(os.getenv("UNIVERSE_KOSPI", str(_env_overrides.get("universe_kospi", 25))))
    universe_kosdaq: int = int(os.getenv("UNIVERSE_KOSDAQ", str(_env_overrides.get("universe_kosdaq", 25))))
    ohlcv_count: int = int(os.getenv("OHLCV_COUNT", "220"))

    # === Tight preset ===
    min_signals: int = int(os.getenv("MIN_SIGNALS", "2"))              # 3 -> 2 (현실적)
    macd_osc_min: float = float(os.getenv("MACD_OSC_MIN", "0.0"))        # -10 -> 0 (음모멘텀 제외)
    rsi_mode: str = os.getenv("RSI_MODE", "tema")              # hybrid -> tema
    rsi_threshold: float = float(os.getenv("RSI_THRESHOLD", "58"))       # 55 -> 58
    
    # 교차/이격 타이트
    gap_min: float = float(os.getenv("GAP_MIN", "0.002"))                # 0.1% -> 0.2%
    gap_max: float = float(os.getenv("GAP_MAX", "0.015"))                # 2.0% -> 1.5%
    ext_from_tema20_max: float = float(os.getenv("EXT_FROM_TEMA20_MAX", "0.015"))  # 2% -> 1.5%
    
    # 거래량·유동성
    vol_ma5_mult: float = float(os.getenv("VOL_MA5_MULT", "1.8"))        # 2.0 -> 1.8 (현실적)
    vol_ma20_mult: float = float(os.getenv("VOL_MA20_MULT", "1.2"))      # 신규: MA20도 함께 요구
    min_turnover_krw: int = int(os.getenv("MIN_TURNOVER_KRW", "1000000000"))  # 10억 이상
    
    # 변동성 컷
    use_atr_filter: bool = os.getenv("USE_ATR_FILTER", "true").lower() == "true"
    atr_pct_max: float = float(os.getenv("ATR_PCT_MAX", "0.04"))         # <= 4%
    atr_pct_min: float = float(os.getenv("ATR_PCT_MIN", "0.01"))         # >= 1% (너무 잠잠한 종목 배제)
    
    # 가격/연속신호 억제
    min_price: int = int(os.getenv("MIN_PRICE", "2000"))               # 2,000원 미만 제외
    entry_cooldown_days: int = int(os.getenv("ENTRY_COOLDOWN_DAYS", "3"))
    
    # 과열 컷(유지)
    overheat_rsi_tema: int = int(os.getenv("OVERHEAT_RSI_TEMA", "70"))
    overheat_vol_mult: float = float(os.getenv("OVERHEAT_VOL_MULT", "3.0"))
    
    # 반환 상한
    top_k: int = int(os.getenv("TOP_K", "5"))                          # 15 -> 5
    
    # === Auto Fallback 설정 ===
    fallback_enable: bool = os.getenv("FALLBACK_ENABLE", "true").lower() == "true"  # false -> true (안전한 Fallback 활성화)
    fallback_target_min: int = int(os.getenv("FALLBACK_TARGET_MIN", "1"))  # 최소 확보 개수
    fallback_target_max: int = int(os.getenv("FALLBACK_TARGET_MAX", "5"))  # 최대 반환 개수(=TOP_K와 동일 권장)
    
    # === 시장 상황 연동 설정 ===
    market_analysis_enable: bool = os.getenv("MARKET_ANALYSIS_ENABLE", "true").lower() == "true"
    market_analysis_interval: int = int(os.getenv("MARKET_ANALYSIS_INTERVAL", "60"))  # 분 단위
    market_analysis_cache_ttl: int = int(os.getenv("MARKET_ANALYSIS_CACHE_TTL", "300"))  # 초 단위
    
    # 시장 상황별 기본 프리셋 (RSI 기준 수정)
    market_preset_bull_rsi: float = float(os.getenv("MARKET_PRESET_BULL_RSI", "65.0"))  # 강세장: 높은 RSI 허용
    market_preset_neutral_rsi: float = float(os.getenv("MARKET_PRESET_NEUTRAL_RSI", "58.0"))  # 중립장: 기본값
    market_preset_bear_rsi: float = float(os.getenv("MARKET_PRESET_BEAR_RSI", "45.0"))  # 약세장: 낮은 RSI 허용
    
    # KOSPI 임계값 (시장 상황 판단용)
    kospi_bull_threshold: float = float(os.getenv("KOSPI_BULL_THRESHOLD", "0.02"))  # +2% (0.02 -> 0.02)
    kospi_bear_threshold: float = float(os.getenv("KOSPI_BEAR_THRESHOLD", "-0.02"))  # -2% (0.02 -> 0.02)
    
    # === 필터링 설정 ===
    # RSI 상한선 (과매수 구간 진입 방지)
    rsi_upper_limit: float = float(os.getenv("RSI_UPPER_LIMIT", "70.0"))
    
    # 인버스 ETF 필터링 키워드
    inverse_etf_keywords: list = field(default_factory=lambda: os.getenv("INVERSE_ETF_KEYWORDS", "인버스,2X,레버리지,SHORT,BEAR,DOWN").split(","))
    
    # 금리/채권 ETF 필터링 키워드
    bond_etf_keywords: list = field(default_factory=lambda: os.getenv("BOND_ETF_KEYWORDS", "금리액티브,머니마켓액티브,CD금리,채권,국채,KRX금현물").split(","))
    
    # === RSI (TEMA/DEMA 기반) - 기존 로직 유지 ===
    rsi_setup_min: int = int(os.getenv("RSI_SETUP_MIN", "58"))   # RSI_DEMA Setup 구간 최소 (Tight preset)
    rsi_setup_max: int = int(os.getenv("RSI_SETUP_MAX", "75"))   # RSI_DEMA Setup 구간 최대
    rsi_trigger_min: int = int(os.getenv("RSI_TRIGGER_MIN", "50"))  # RSI_TEMA Trigger 기준
    rsi_overheat: int = int(os.getenv("RSI_OVERHEAT", "85"))     # RSI_TEMA 과열 컷

    rate_limit_delay_ms: int = int(os.getenv("RATE_LIMIT_DELAY_MS", "250"))

    # 콤마로 구분된 유니버스 고정 코드 목록 (예: "005930,000660,051910")
    universe_codes: str = os.getenv("UNIVERSE_CODES", "")

    # 실데이터 실패 시 모의 폴백 허용 여부 (기본: 0=비허용)
    use_mock_fallback: bool = os.getenv("USE_MOCK_FALLBACK", "1").lower() in ("1", "true", "yes")

    # 매칭에 필요한 최소 신호 개수(골든크로스/모멘텀/RSI/거래량 중) - 중복 제거됨

    # Kiwoom REST TR 설정 (필요 시 .env에서 오버라이드)
    kiwoom_tr_topvalue_id: str = os.getenv("KIWOOM_TR_TOPVALUE_ID", "ka10032")
    kiwoom_tr_topvalue_path: str = os.getenv(
        "KIWOOM_TR_TOPVALUE_PATH",
        "/api/dostk/rkinfo",
    )
    kiwoom_tr_ohlcv_id: str = os.getenv("KIWOOM_TR_OHLCV_ID", "ka10081")
    kiwoom_tr_ohlcv_path: str = os.getenv(
        "KIWOOM_TR_OHLCV_PATH",
        "/api/dostk/chart",
    )
    kiwoom_tr_stockinfo_id: str = os.getenv("KIWOOM_TR_STOCKINFO_ID", "ka10099")
    kiwoom_tr_stockinfo_path: str = os.getenv(
        "KIWOOM_TR_STOCKINFO_PATH",
        "/api/dostk/stkinfo",
    )
    kiwoom_tr_quote_id: str = os.getenv("KIWOOM_TR_QUOTE_ID", "FHKST01010100")
    kiwoom_tr_quote_path: str = os.getenv(
        "KIWOOM_TR_QUOTE_PATH",
        "/uapi/domestic-stock/v1/quotations/inquire-price",
    )

    # 심볼 프리로드 설정
    preload_symbols: bool = os.getenv("PRELOAD_SYMBOLS", "1").lower() in ("1", "true", "yes")
    # 프리로드할 시장 코드(쉼표구분): 001=코스피, 101=코스닥 등 문서 기준
    kiwoom_symbol_markets: str = os.getenv("KIWOOM_SYMBOL_MARKETS", "0,10")

    # 추세 파라미터
    trend_above_lookback: int = int(os.getenv("TREND_ABOVE_LOOKBACK", "5"))
    trend_slope_lookback: int = int(os.getenv("TREND_SLOPE_LOOKBACK", "20"))
    # dema 기울기 모드: required|optional|off
    require_dema_slope: str = os.getenv("REQUIRE_DEMA_SLOPE", "required").lower()  # optional -> required (DEMA 슬로프 하락 차단)

    # 점수 가중치
    score_w_cross: int = int(os.getenv("SCORE_W_CROSS", "3"))
    score_w_vol: int = int(os.getenv("SCORE_W_VOL", "2"))
    score_w_macd: int = int(os.getenv("SCORE_W_MACD", "1"))
    score_w_rsi: int = int(os.getenv("SCORE_W_RSI", "1"))
    score_w_tema_slope: int = int(os.getenv("SCORE_W_TEMA_SLOPE", "2"))
    score_w_dema_slope: int = int(os.getenv("SCORE_W_DEMA_SLOPE", "2"))
    score_w_obv_slope: int = int(os.getenv("SCORE_W_OBV_SLOPE", "2"))
    score_w_above_cnt: int = int(os.getenv("SCORE_W_ABOVE_CNT", "2"))
    score_level_strong: int = int(os.getenv("SCORE_LEVEL_STRONG", "8"))
    score_level_watch: int = int(os.getenv("SCORE_LEVEL_WATCH", "5"))
    
    # 위험도 필터링 설정
    # rsi_overbought_threshold: float = float(os.getenv("RSI_OVERBOUGHT_THRESHOLD", "80"))  # 비활성화
    vol_spike_threshold: float = float(os.getenv("VOL_SPIKE_THRESHOLD", "3.0"))
    momentum_duration_min: int = int(os.getenv("MOMENTUM_DURATION_MIN", "3"))
    risk_score_threshold: int = int(os.getenv("RISK_SCORE_THRESHOLD", "3"))

    def dynamic_score_weights(self) -> dict:
        # 타이트화된 기본값 반환 (환경변수 재로드 방지)
        return {
            "cross": self.score_w_cross,
            "volume": self.score_w_vol,
            "macd": self.score_w_macd,
            "rsi": self.score_w_rsi,
            "tema_slope": self.score_w_tema_slope,
            "dema_slope": self.score_w_dema_slope,
            "obv_slope": self.score_w_obv_slope,
            "above_cnt5": self.score_w_above_cnt,
        }
    
    # 단계별 완화 프리셋 (상수 테이블)
    @property
    def fallback_presets(self) -> list:
        return [
            # step 0: current strict (현 설정 그대로 사용)
            {},
            # step 1: 신호 및 거래량 약간 완화 (현재 강화된 파라미터 고려)
            {"min_signals": 3, "vol_ma5_mult": 2.0},  # 완화 (현재 5/2.2 → 3/2.0)
            # step 2: 추가 완화
            {"min_signals": 2, "vol_ma5_mult": 1.8},  # 더 완화
            # step 3: 거래량 현실적 완화
            {"min_signals": 2, "vol_ma5_mult": 1.5, "vol_ma20_mult": 1.1},  # 거래량 현실적 완화
            # step 4: 갭/이격 범위 완화
            {"min_signals": 2, "vol_ma5_mult": 1.5, "gap_max": 0.025, "ext_from_tema20_max": 0.025},  # 갭/이격 완화
            # step 5: 최종 현실적 완화 (DEMA 슬로프도 완화)
            {"min_signals": 1, "vol_ma5_mult": 1.3, "require_dema_slope": "optional"},  # 최종 완화
        ]


config = Config()


def reload_from_env() -> None:
    """.env를 다시 로드하고 config 인스턴스 값을 갱신한다 (서버 재시작 없이 적용)."""
    # 타이트화 설정 유지를 위해 비활성화
    pass


