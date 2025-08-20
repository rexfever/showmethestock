from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import json
from typing import List
import pandas as pd

from backend.config import config, reload_from_env
from backend.kiwoom_api import KiwoomAPI
from backend.scanner import compute_indicators, match_condition, match_stats, strategy_text, score_conditions
from backend.models import ScanResponse, ScanItem, IndicatorPayload, TrendPayload, AnalyzeResponse, UniverseResponse, UniverseItem
from backend.utils import is_code, normalize_code_or_name
import sqlite3


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


@app.post('/_reload_config')
def _reload_config():
    reload_from_env()
    return {
        'ok': True,
        'score_weights': getattr(config, 'dynamic_score_weights')(),
        'score_level_strong': config.score_level_strong,
        'score_level_watch': config.score_level_watch,
        'require_dema_slope': getattr(config, 'require_dema_slope', 'required'),
    }


SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), 'snapshots')
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def _save_scan_snapshot(payload: dict) -> str:
    try:
        as_of = payload.get('as_of') or datetime.now().strftime('%Y-%m-%d')
        fname = f"scan-{as_of.replace('-', '')}.json"
        path = os.path.join(SNAPSHOT_DIR, fname)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False)
        return path
    except Exception:
        return ''

def _db_path() -> str:
    return os.path.join(os.path.dirname(__file__), 'snapshots.db')

def _save_snapshot_db(as_of: str, items: List[ScanItem]):
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS scan_rank(date TEXT, code TEXT, score REAL, flags TEXT, score_label TEXT, close_price REAL, PRIMARY KEY(date, code))")
        rows = []
        for it in items:
            rows.append((as_of, it.ticker, float(it.score), json.dumps(it.flags or {} , ensure_ascii=False), it.score_label or '', float(it.indicators.VOL if hasattr(it.indicators,'VOL') else 0)))
        cur.executemany("INSERT OR REPLACE INTO scan_rank(date, code, score, flags, score_label, close_price) VALUES (?,?,?,?,?,?)", rows)
        conn.commit()
        conn.close()
    except Exception:
        pass


@app.get('/scan', response_model=ScanResponse)
def scan(kospi_limit: int = None, kosdaq_limit: int = None, save_snapshot: bool = True, sort_by: str = 'score'):
    kp = kospi_limit or config.universe_kospi
    kd = kosdaq_limit or config.universe_kosdaq
    kospi = api.get_top_codes('KOSPI', kp)
    kosdaq = api.get_top_codes('KOSDAQ', kd)
    universe: List[str] = [*kospi, *kosdaq]

    items: List[ScanItem] = []
    for code in universe:
        try:
            df = api.get_ohlcv(code, config.ohlcv_count)
            if df.empty or len(df) < 21 or df[["open","high","low","close","volume"]].isna().any().any():
                continue
            df = compute_indicators(df)
            matched, sig_true, sig_total = match_stats(df)
            score, flags = score_conditions(df)
            cur = df.iloc[-1]
            item = ScanItem(
                ticker=code,
                name=api.get_stock_name(code),
                match=bool(matched),
                score=float(score),
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
                trend=TrendPayload(
                    TEMA20_SLOPE20=float(df.iloc[-1].get("TEMA20_SLOPE20", 0.0)) if "TEMA20_SLOPE20" in df.columns else 0.0,
                    OBV_SLOPE20=float(df.iloc[-1].get("OBV_SLOPE20", 0.0)) if "OBV_SLOPE20" in df.columns else 0.0,
                    ABOVE_CNT5=int(((df["TEMA20"] > df["DEMA10"]).tail(5).sum()) if ("TEMA20" in df.columns and "DEMA10" in df.columns) else 0),
                ),
                flags=flags,
                score_label=str(flags.get("label")) if isinstance(flags, dict) else None,
                details={**(flags.get("details", {}) if isinstance(flags, dict) else {}), "close": float(cur.close)},
                strategy=strategy_text(df),
            )
            if item.match:
                items.append(item)
        except Exception:
            continue

    # 정렬: score | volume (VOL) | change_rate(추후)
    if sort_by == 'volume':
        items = sorted(items, key=lambda x: getattr(x.indicators, 'VOL', 0), reverse=True)
    else:
        items = sorted(items, key=lambda x: x.score, reverse=True)

    resp = ScanResponse(
        as_of=datetime.now().strftime('%Y-%m-%d'),
        universe_count=len(universe),
        matched_count=len(items),
        rsi_mode=config.rsi_mode,
        rsi_period=config.rsi_period,
        rsi_threshold=config.rsi_threshold,
        items=items,
        score_weights=getattr(config, 'dynamic_score_weights')() if hasattr(config, 'dynamic_score_weights') else {},
        score_level_strong=config.score_level_strong,
        score_level_watch=config.score_level_watch,
        require_dema_slope=getattr(config, 'require_dema_slope', 'required'),
    )
    if save_snapshot:
        # 스냅샷에는 핵심 메타/랭킹만 저장(용량 절약)
        snapshot = {
            'as_of': resp.as_of,
            'created_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'universe_count': resp.universe_count,
            'matched_count': resp.matched_count,
            'rsi_mode': resp.rsi_mode,
            'rsi_period': resp.rsi_period,
            'rsi_threshold': resp.rsi_threshold,
            'rank': [
                {
                    'ticker': it.ticker,
                    'name': it.name,
                    'score': it.score,
                    'score_label': it.score_label,
                }
                for it in items
            ],
        }
        _save_scan_snapshot(snapshot)
        _save_snapshot_db(resp.as_of, items)
    return resp


@app.get('/universe', response_model=UniverseResponse)
def universe(apply_scan: bool = False, kospi_limit: int = None, kosdaq_limit: int = None):
    kp = kospi_limit or config.universe_kospi
    kd = kosdaq_limit or config.universe_kosdaq
    kospi = api.get_top_codes('KOSPI', kp)
    kosdaq = api.get_top_codes('KOSDAQ', kd)
    universe: List[str] = [*kospi, *kosdaq]

    items: List[UniverseItem] = []
    for code in universe:
        try:
            if apply_scan:
                df = api.get_ohlcv(code, config.ohlcv_count)
                if df.empty or len(df) < 21 or df[["open","high","low","close","volume"]].isna().any().any():
                    continue
                df = compute_indicators(df)
                if not match_condition(df):
                    continue
            items.append(UniverseItem(ticker=code, name=api.get_stock_name(code)))
        except Exception:
            if not apply_scan:
                items.append(UniverseItem(ticker=code, name=code))

    return UniverseResponse(
        as_of=datetime.now().strftime('%Y-%m-%d'),
        items=items,
    )


@app.get('/_debug/topvalue')
def _debug_topvalue(market: str = 'KOSPI'):
    return api.debug_call_topvalue_once(market)


@app.get('/_debug/stockinfo')
def _debug_stockinfo(market_tp: str = '001'):
    return api.debug_call_stockinfo_once(market_tp)


# 기존 /validate 제거 → 스냅샷 기반 검증만 유지


@app.get('/snapshots')
def list_snapshots():
    files = []
    try:
        for fn in os.listdir(SNAPSHOT_DIR):
            if not fn.startswith('scan-') or not fn.endswith('.json'):
                continue
            path = os.path.join(SNAPSHOT_DIR, fn)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                files.append({
                    'file': fn,
                    'as_of': meta.get('as_of'),
                    'created_at': meta.get('created_at'),
                    'matched_count': meta.get('matched_count'),
                    'rank_count': len(meta.get('rank', [])),
                })
            except Exception:
                continue
        files.sort(key=lambda x: x.get('as_of') or '', reverse=True)
    except Exception:
        files = []
    return {'count': len(files), 'items': files}


@app.get('/validate_from_snapshot')
def validate_from_snapshot(as_of: str, top_k: int = 20):
    """스냅샷(as_of=YYYY-MM-DD) 상위 목록 기준으로 현재 수익률 검증"""
    fname = f"scan-{as_of.replace('-', '')}.json"
    path = os.path.join(SNAPSHOT_DIR, fname)
    if not os.path.exists(path):
        return {'error': 'snapshot not found', 'as_of': as_of, 'items': []}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            snap = json.load(f)
    except Exception as e:
        return {'error': str(e), 'as_of': as_of, 'items': []}
    rank = snap.get('rank', [])
    rank.sort(key=lambda x: x.get('score', 0), reverse=True)
    base_dt = as_of.replace('-', '')
    results = []
    rets = []
    for it in rank[:max(0, top_k)]:
        code = it.get('ticker')
        try:
            df_then = api.get_ohlcv(code, config.ohlcv_count, base_dt=base_dt)
            if df_then.empty:
                continue
            price_then = float(df_then.iloc[-1].close)
            df_now = api.get_ohlcv(code, 5)
            if df_now.empty:
                continue
            price_now = float(df_now.iloc[-1].close)
            ret = (price_now / price_then - 1.0) * 100.0
            rets.append(ret)
            results.append({
                'ticker': code,
                'name': api.get_stock_name(code),
                'score_then': it.get('score'),
                'price_then': price_then,
                'price_now': price_now,
                'return_pct': round(ret, 2),
            })
        except Exception:
            continue
    win = sum(1 for r in rets if r > 0)
    win_rate = round((win / len(rets) * 100.0), 2) if rets else 0.0
    avg_ret = round((sum(rets) / len(rets)), 2) if rets else 0.0
    # 최대낙폭(MDD) 계산(단순 종가만, 선정일→오늘까지 단일 구간 수익률 리스트 기준)
    # 여기선 리턴 배열 rets로 근사: 누적 곱 대신 최소값 사용(정밀도 낮음)
    mdd = round(min(rets) if rets else 0.0, 2)
    return {
        'as_of': datetime.now().strftime('%Y-%m-%d'),
        'snapshot_as_of': as_of,
        'top_k': top_k,
        'count': len(results),
        'win_rate_pct': win_rate,
        'avg_return_pct': avg_ret,
        'mdd_pct': mdd,
        'items': results,
    }

@app.get('/analyze', response_model=AnalyzeResponse)
def analyze(name_or_code: str):
    code = normalize_code_or_name(name_or_code)
    if not is_code(code):
        code = api.get_code_by_name(code)
        if not code:
            return AnalyzeResponse(ok=False, item=None, error='이름→코드 매핑 실패')

    df = api.get_ohlcv(code, config.ohlcv_count)
    if df.empty or len(df) < 21:
        return AnalyzeResponse(ok=False, item=None, error='데이터 부족')
    df = compute_indicators(df)
    matched, sig_true, sig_total = match_stats(df)
    score, flags = score_conditions(df)
    cur = df.iloc[-1]
    item = ScanItem(
        ticker=code,
        name=api.get_stock_name(code),
        match=bool(matched),
        score=float(score),
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
        trend=TrendPayload(
            TEMA20_SLOPE20=float(df.iloc[-1].get("TEMA20_SLOPE20", 0.0)) if "TEMA20_SLOPE20" in df.columns else 0.0,
            OBV_SLOPE20=float(df.iloc[-1].get("OBV_SLOPE20", 0.0)) if "OBV_SLOPE20" in df.columns else 0.0,
            ABOVE_CNT5=int(((df["TEMA20"] > df["DEMA10"]).tail(5).sum()) if ("TEMA20" in df.columns and "DEMA10" in df.columns) else 0),
        ),
        flags=flags,
        score_label=str(flags.get("label")) if isinstance(flags, dict) else None,
        strategy=strategy_text(df),
    )
    return AnalyzeResponse(ok=True, item=item)

