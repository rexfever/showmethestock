import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass
class Config:
    app_key: str = os.getenv("APP_KEY", "")
    app_secret: str = os.getenv("APP_SECRET", "")
    api_base: str = os.getenv("API_BASE", "https://api.kiwoom.com")

    universe_kospi: int = int(os.getenv("UNIVERSE_KOSPI", "100"))
    universe_kosdaq: int = int(os.getenv("UNIVERSE_KOSDAQ", "100"))
    ohlcv_count: int = int(os.getenv("OHLCV_COUNT", "220"))

    macd_osc_min: float = float(os.getenv("MACD_OSC_MIN", "-50"))
    rsi_mode: str = os.getenv("RSI_MODE", "hybrid")  # standard|tema|dema|hybrid
    rsi_period: int = int(os.getenv("RSI_PERIOD", "14"))
    rsi_threshold: float = float(os.getenv("RSI_THRESHOLD", "55"))
    vol_ma5_mult: float = float(os.getenv("VOL_MA5_MULT", "1.5"))

    rate_limit_delay_ms: int = int(os.getenv("RATE_LIMIT_DELAY_MS", "250"))


config = Config()


