from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List
import pandas as pd

from backend.config import config
from backend.kiwoom_api import KiwoomAPI
from backend.scanner import compute_indicators, match_condition, strategy_text
from backend.models import ScanResponse, ScanItem, IndicatorPayload, AnalyzeResponse, UniverseResponse, UniverseItem
from backend.utils import is_code


app = FastAPI(title='Stock Scanner API')

# CORS 설정 (프론트 개발 서버 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
api = KiwoomAPI()


@app.get('/')
def root():
    return {'status': 'running'}


@app.get('/scan', response_model=ScanResponse)
def scan():
    kospi = api.get_top_codes('KOSPI', config.universe_kospi)
    kosdaq = api.get_top_codes('KOSDAQ', config.universe_kosdaq)
    universe: List[str] = [*kospi, *kosdaq]

    items: List[ScanItem] = []
    for code in universe:
        try:
            df = api.get_ohlcv(code, config.ohlcv_count)
            if df.empty or len(df) < 21 or df[["open","high","low","close","volume"]].isna().any().any():
                continue
            df = compute_indicators(df)
            match = match_condition(df)
            cur = df.iloc[-1]
            item = ScanItem(
                ticker=code,
                name=api.get_stock_name(code),
                match=bool(match),
                indicators=IndicatorPayload(
                    TEMA=float(cur.TEMA20),
                    DEMA=float(cur.DEMA10),
                    MACD_OSC=float(cur.MACD_OSC),
                    RSI=float(cur.RSI),
                    RSI_TEMA=float(cur.RSI_TEMA),
                    RSI_DEMA=float(cur.RSI_DEMA),
                    OBV=float(cur.OBV),
                    VOL=int(cur.volume),
                    VOL_MA5=float(cur.VOL_MA5) if pd.notna(cur.VOL_MA5) else 0.0,
                ),
                strategy=strategy_text(df),
            )
            if item.match:
                items.append(item)
        except Exception:
            continue

    return ScanResponse(
        as_of=datetime.now().strftime('%Y-%m-%d'),
        universe_count=len(universe),
        matched_count=len(items),
        rsi_mode=config.rsi_mode,
        rsi_period=config.rsi_period,
        rsi_threshold=config.rsi_threshold,
        items=items,
    )


@app.get('/universe', response_model=UniverseResponse)
def universe():
    kospi = api.get_top_codes('KOSPI', config.universe_kospi)
    kosdaq = api.get_top_codes('KOSDAQ', config.universe_kosdaq)
    universe: List[str] = [*kospi, *kosdaq]

    items: List[UniverseItem] = []
    for code in universe:
        try:
            items.append(UniverseItem(ticker=code, name=api.get_stock_name(code)))
        except Exception:
            items.append(UniverseItem(ticker=code, name=code))

    return UniverseResponse(
        as_of=datetime.now().strftime('%Y-%m-%d'),
        items=items,
    )

@app.get('/analyze', response_model=AnalyzeResponse)
def analyze(name_or_code: str):
    code = name_or_code
    if not is_code(code):
        code = api.get_code_by_name(name_or_code)
        if not code:
            return AnalyzeResponse(ok=False, item=None, error='이름→코드 매핑 실패')

    df = api.get_ohlcv(code, config.ohlcv_count)
    if df.empty or len(df) < 21:
        return AnalyzeResponse(ok=False, item=None, error='데이터 부족')
    df = compute_indicators(df)
    match = match_condition(df)
    cur = df.iloc[-1]
    item = ScanItem(
        ticker=code,
        name=api.get_stock_name(code),
        match=bool(match),
        indicators=IndicatorPayload(
            TEMA=float(cur.TEMA20),
            DEMA=float(cur.DEMA10),
            MACD_OSC=float(cur.MACD_OSC),
            RSI=float(cur.RSI),
            RSI_TEMA=float(cur.RSI_TEMA),
            RSI_DEMA=float(cur.RSI_DEMA),
            OBV=float(cur.OBV),
            VOL=int(cur.volume),
            VOL_MA5=float(cur.VOL_MA5) if pd.notna(cur.VOL_MA5) else 0.0,
        ),
        strategy=strategy_text(df),
    )
    return AnalyzeResponse(ok=True, item=item)

