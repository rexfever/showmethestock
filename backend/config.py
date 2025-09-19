import os
from dataclasses import dataclass
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

    # 심볼 프리로드 설정
    preload_symbols: bool = os.getenv("PRELOAD_SYMBOLS", "1").lower() in ("1", "true", "yes")
    # 프리로드할 시장 코드(쉼표구분): 001=코스피, 101=코스닥 등 문서 기준
    kiwoom_symbol_markets: str = os.getenv("KIWOOM_SYMBOL_MARKETS", "0,10")

    # 추세 파라미터
    trend_above_lookback: int = int(os.getenv("TREND_ABOVE_LOOKBACK", "5"))
    trend_slope_lookback: int = int(os.getenv("TREND_SLOPE_LOOKBACK", "20"))
    # dema 기울기 모드: required|optional|off
    require_dema_slope: str = os.getenv("REQUIRE_DEMA_SLOPE", "optional").lower()

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
    rsi_overbought_threshold: float = float(os.getenv("RSI_OVERBOUGHT_THRESHOLD", "80"))
    vol_spike_threshold: float = float(os.getenv("VOL_SPIKE_THRESHOLD", "3.0"))
    momentum_duration_min: int = int(os.getenv("MOMENTUM_DURATION_MIN", "3"))
    risk_score_threshold: int = int(os.getenv("RISK_SCORE_THRESHOLD", "3"))

    def dynamic_score_weights(self) -> dict:
        raw = os.getenv("SCORE_WEIGHTS", "")
        if not raw:
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
        try:
            data = json.loads(raw)
            # 기본값과 병합
            base = {
                "cross": self.score_w_cross,
                "volume": self.score_w_vol,
                "macd": self.score_w_macd,
                "rsi": self.score_w_rsi,
                "tema_slope": self.score_w_tema_slope,
                "dema_slope": self.score_w_dema_slope,
                "obv_slope": self.score_w_obv_slope,
                "above_cnt5": self.score_w_above_cnt,
            }
            base.update({k:int(v) for k,v in data.items() if isinstance(v,(int,float))})
            return base
        except Exception:
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


config = Config()


def reload_from_env() -> None:
    """.env를 다시 로드하고 config 인스턴스 값을 갱신한다 (서버 재시작 없이 적용)."""
    # 루트와 backend/.env 재적용
    load_dotenv()
    backend_env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(backend_env_path):
        load_dotenv(dotenv_path=backend_env_path, override=True)

    # 필드 업데이트
    for field in [
        'app_key','app_secret','api_base','token_path',
        'universe_kospi','universe_kosdaq','ohlcv_count',
        'macd_osc_min','rsi_mode','rsi_period','rsi_threshold','vol_ma5_mult',
        'rate_limit_delay_ms','universe_codes','use_mock_fallback','min_signals',
        'kiwoom_tr_topvalue_id','kiwoom_tr_topvalue_path','kiwoom_tr_ohlcv_id','kiwoom_tr_ohlcv_path',
        'kiwoom_tr_stockinfo_id','kiwoom_tr_stockinfo_path','preload_symbols','kiwoom_symbol_markets',
        'trend_above_lookback','trend_slope_lookback','require_dema_slope',
        'score_w_cross','score_w_vol','score_w_macd','score_w_rsi','score_w_tema_slope','score_w_dema_slope','score_w_obv_slope','score_w_above_cnt',
        'score_level_strong','score_level_watch',
    ]:
        # 각 필드 타입에 맞춰 변환
        val = os.getenv(field.upper())
        if val is None:
            continue
        try:
            cur = getattr(config, field)
            if isinstance(cur, bool):
                setattr(config, field, val.lower() in ("1","true","yes"))
            elif isinstance(cur, int):
                setattr(config, field, int(val))
            elif isinstance(cur, float):
                setattr(config, field, float(val))
            else:
                setattr(config, field, val)
        except Exception:
            setattr(config, field, val)


