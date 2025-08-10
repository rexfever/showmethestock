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


class ScanItem(BaseModel):
    ticker: str
    name: str
    match: bool
    indicators: IndicatorPayload
    strategy: str


class ScanResponse(BaseModel):
    as_of: str
    universe_count: int
    matched_count: int
    rsi_mode: str
    rsi_period: int
    rsi_threshold: float
    items: List[ScanItem]


class AnalyzeResponse(BaseModel):
    ok: bool
    item: Optional[ScanItem]
    error: Optional[str] = None


