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


config = Config()


