from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class IndicatorPayload(BaseModel):
    TEMA20: float  # TEMA20 (20일 삼중지수이동평균)
    DEMA10: float  # DEMA10 (10일 이중지수이동평균)
    MACD_OSC: float
    MACD_LINE: float
    MACD_SIGNAL: float
    RSI_TEMA: float
    RSI_DEMA: float
    OBV: float
    VOL: int
    VOL_MA5: float
    close: float
    change_rate: Optional[float] = 0.0


class TrendPayload(BaseModel):
    TEMA20_SLOPE20: float
    OBV_SLOPE20: float
    ABOVE_CNT5: int
    DEMA10_SLOPE20: float


class User(BaseModel):
    """사용자 모델"""
    id: Optional[int] = None
    email: str
    phone: Optional[str] = None
    notification_enabled: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MaintenanceSettings(BaseModel):
    """메인트넌스 설정 모델"""
    id: Optional[int] = None
    is_enabled: bool = False
    end_date: Optional[str] = None
    message: str = "서비스 점검 중입니다."
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MaintenanceSettingsRequest(BaseModel):
    """메인트넌스 설정 요청 모델"""
    is_enabled: bool
    end_date: Optional[str] = None
    message: Optional[str] = None


class ScoreFlags(BaseModel):
    cross: bool
    vol_expand: bool
    macd_ok: bool
    rsi_dema_setup: bool = False
    rsi_tema_trigger: bool = False
    rsi_dema_value: Optional[float] = None
    rsi_tema_value: Optional[float] = None
    overheated_rsi_tema: bool = False
    tema_slope_ok: bool
    obv_slope_ok: bool
    above_cnt5_ok: bool
    dema_slope_ok: bool = False
    details: Optional[dict] = None
    recurrence: Optional[dict] = None
    label: Optional[str] = None


class ScanItem(BaseModel):
    ticker: str
    name: str
    match: bool
    score: float
    indicators: IndicatorPayload
    trend: Optional[TrendPayload] = None
    strategy: str
    flags: Optional[ScoreFlags] = None
    score_label: Optional[str] = None
    details: Optional[dict] = None
    recurrence: Optional[dict] = None
    # 수익률 정보 (과거 스캔 검증용)
    returns: Optional[dict] = None


class ScanResponse(BaseModel):
    as_of: str
    universe_count: int
    matched_count: int
    rsi_mode: str
    rsi_period: int
    rsi_threshold: float
    items: List[ScanItem]
    # fallback info
    fallback_step: Optional[int] = None
    # meta
    score_weights: Optional[dict] = None
    score_level_strong: Optional[int] = None
    score_level_watch: Optional[int] = None
    require_dema_slope: Optional[str] = None
    # market guide
    market_guide: Optional[dict] = None


class AnalyzeResponse(BaseModel):
    ok: bool
    item: Optional[ScanItem]
    error: Optional[str] = None


class UniverseItem(BaseModel):
    ticker: str
    name: str


class UniverseResponse(BaseModel):
    as_of: str
    items: List[UniverseItem]


class ValidateItem(BaseModel):
    ticker: str
    name: str
    score_then: float
    price_then: float
    price_now: float
    return_pct: float
    max_return_pct: float
    score_label_then: Optional[str] = None
    strategy_then: Optional[str] = None


class ValidateResponse(BaseModel):
    as_of: str
    snapshot_as_of: str
    top_k: int
    count: int
    win_rate_pct: float
    avg_return_pct: float
    mdd_pct: float
    avg_max_return_pct: float
    max_max_return_pct: float
    items: List[ValidateItem]


class PositionItem(BaseModel):
    id: Optional[int] = None
    ticker: str
    name: str
    entry_date: str
    quantity: int
    score: Optional[int] = None
    strategy: Optional[str] = None
    current_return_pct: Optional[float] = None
    max_return_pct: Optional[float] = None
    exit_date: Optional[str] = None
    status: str  # 'open' | 'closed'


class PositionResponse(BaseModel):
    items: List[PositionItem]
    total_return_pct: Optional[float] = None


class AddPositionRequest(BaseModel):
    ticker: str
    entry_date: str
    quantity: int
    score: Optional[int] = None
    strategy: Optional[str] = None


class UpdatePositionRequest(BaseModel):
    exit_date: Optional[str] = None


class PortfolioItem(BaseModel):
    """포트폴리오 아이템 모델"""
    id: Optional[int] = None
    user_id: int
    ticker: str
    name: str
    entry_price: Optional[float] = None  # 매수가
    quantity: Optional[int] = None  # 수량
    entry_date: Optional[str] = None  # 매수일
    current_price: Optional[float] = None  # 현재가
    total_investment: Optional[float] = None  # 총 투자금
    current_value: Optional[float] = None  # 현재 평가금액
    profit_loss: Optional[float] = None  # 손익
    profit_loss_pct: Optional[float] = None  # 손익률
    status: str = "watching"  # 'watching' | 'holding' | 'sold'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PortfolioResponse(BaseModel):
    """포트폴리오 응답 모델"""
    items: List[PortfolioItem]
    total_investment: Optional[float] = None
    total_current_value: Optional[float] = None
    total_profit_loss: Optional[float] = None
    total_profit_loss_pct: Optional[float] = None


class AddToPortfolioRequest(BaseModel):
    """포트폴리오 추가 요청"""
    ticker: str
    name: str
    entry_price: Optional[float] = None
    quantity: Optional[int] = None
    entry_date: Optional[str] = None


class AddTradingRequest(BaseModel):
    """매매 내역 추가 요청 모델"""
    ticker: str
    name: str
    trade_type: str  # 'buy' | 'sell'
    quantity: int
    price: float
    trade_date: str
    notes: Optional[str] = None


class TradingHistory(BaseModel):
    """매매 내역 모델"""
    id: Optional[int] = None
    user_id: int
    ticker: str
    name: str
    trade_type: str  # 'buy' | 'sell'
    quantity: int
    price: float
    trade_date: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TradingHistoryResponse(BaseModel):
    """매매 내역 응답 모델"""
    items: List[TradingHistory]
    total_buy_amount: float
    total_sell_amount: float
    net_amount: float


class UpdatePortfolioRequest(BaseModel):
    """포트폴리오 업데이트 요청"""
    entry_price: Optional[float] = None
    quantity: Optional[int] = None
    entry_date: Optional[str] = None
    status: Optional[str] = None


