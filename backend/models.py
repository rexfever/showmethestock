from pydantic import BaseModel
from typing import List, Optional


class IndicatorPayload(BaseModel):
    TEMA: float
    DEMA: float
    MACD_OSC: float
    RSI: float
    RSI_TEMA: float
    RSI_DEMA: float
    OBV: float
    VOL: int
    VOL_MA5: float


class TrendPayload(BaseModel):
    TEMA20_SLOPE20: float
    OBV_SLOPE20: float
    ABOVE_CNT5: int


class ScoreFlags(BaseModel):
    cross: bool
    vol_expand: bool
    macd_ok: bool
    rsi_ok: bool
    tema_slope_ok: bool
    obv_slope_ok: bool
    above_cnt5_ok: bool
    dema_slope_ok: bool = False
    details: Optional[dict] = None


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


class ScanResponse(BaseModel):
    as_of: str
    universe_count: int
    matched_count: int
    rsi_mode: str
    rsi_period: int
    rsi_threshold: float
    items: List[ScanItem]
    # meta
    score_weights: Optional[dict] = None
    score_level_strong: Optional[int] = None
    score_level_watch: Optional[int] = None
    require_dema_slope: Optional[str] = None


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


