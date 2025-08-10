import os
from dataclasses import dataclass
from dotenv import load_dotenv


# 1) 루트 .env 로드
load_dotenv()
# 2) backend/.env 로드(있으면 우선 적용)
backend_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(backend_env_path):
    load_dotenv(dotenv_path=backend_env_path, override=True)


@dataclass
class Config:
    app_key: str = os.getenv("APP_KEY", "")
    app_secret: str = os.getenv("APP_SECRET", "")
    api_base: str = os.getenv("API_BASE", "https://api.kiwoom.com")
    # 키움 REST 토큰 경로
    token_path: str = os.getenv("TOKEN_PATH", "/oauth2/token")

    universe_kospi: int = int(os.getenv("UNIVERSE_KOSPI", "100"))
    universe_kosdaq: int = int(os.getenv("UNIVERSE_KOSDAQ", "100"))
    ohlcv_count: int = int(os.getenv("OHLCV_COUNT", "220"))

    macd_osc_min: float = float(os.getenv("MACD_OSC_MIN", "-10"))
    rsi_mode: str = os.getenv("RSI_MODE", "hybrid")  # standard|tema|dema|hybrid
    rsi_period: int = int(os.getenv("RSI_PERIOD", "14"))
    rsi_threshold: float = float(os.getenv("RSI_THRESHOLD", "55"))
    vol_ma5_mult: float = float(os.getenv("VOL_MA5_MULT", "1.2"))

    rate_limit_delay_ms: int = int(os.getenv("RATE_LIMIT_DELAY_MS", "250"))

    # 콤마로 구분된 유니버스 고정 코드 목록 (예: "005930,000660,051910")
    universe_codes: str = os.getenv("UNIVERSE_CODES", "")

    # 실데이터 실패 시 모의 폴백 허용 여부 (기본: 0=비허용)
    use_mock_fallback: bool = os.getenv("USE_MOCK_FALLBACK", "0").lower() in ("1", "true", "yes")

    # 매칭에 필요한 최소 신호 개수(골든크로스/모멘텀/RSI/거래량 중)
    min_signals: int = int(os.getenv("MIN_SIGNALS", "2"))

    # Kiwoom REST TR 설정 (필요 시 .env에서 오버라이드)
    kiwoom_tr_topvalue_id: str = os.getenv("KIWOOM_TR_TOPVALUE_ID", "ka10032")
    kiwoom_tr_topvalue_path: str = os.getenv(
        "KIWOOM_TR_TOPVALUE_PATH",
        "/api/dostk/krinfo",
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

    # 심볼 프리로드 설정
    preload_symbols: bool = os.getenv("PRELOAD_SYMBOLS", "1").lower() in ("1", "true", "yes")
    # 프리로드할 시장 코드(쉼표구분): 001=코스피, 101=코스닥 등 문서 기준
    kiwoom_symbol_markets: str = os.getenv("KIWOOM_SYMBOL_MARKETS", "001,101")


config = Config()


