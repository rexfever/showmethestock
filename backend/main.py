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
from backend.models import ScanResponse, ScanItem, IndicatorPayload, TrendPayload, AnalyzeResponse, UniverseResponse, UniverseItem, ScoreFlags, PositionResponse, PositionItem, AddPositionRequest, UpdatePositionRequest
from backend.utils import is_code, normalize_code_or_name
import sqlite3
from backend.kakao import send_alert, format_scan_message


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

def _as_score_flags(f: dict):
    if not isinstance(f, dict):
        return None
    try:
        return ScoreFlags(
            cross=bool(f.get('cross')),
            vol_expand=bool(f.get('vol_expand')),
            macd_ok=bool(f.get('macd_ok')),
            rsi_ok=bool(f.get('rsi_ok')),
            tema_slope_ok=bool(f.get('tema_slope_ok')),
            obv_slope_ok=bool(f.get('obv_slope_ok')),
            above_cnt5_ok=bool(f.get('above_cnt5_ok')),
            dema_slope_ok=bool(f.get('dema_slope_ok')),
            details=f.get('details') if isinstance(f.get('details'), dict) else None,
        )
    except Exception:
        return None

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

def _log_send(to: str, matched_count: int):
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS send_logs(ts TEXT, to_no TEXT, matched_count INTEGER)")
        cur.execute("INSERT INTO send_logs(ts,to_no,matched_count) VALUES (?,?,?)", (datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), to, int(matched_count)))
        conn.commit(); conn.close()
    except Exception:
        pass

def _init_positions_table():
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS positions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                name TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                exit_date TEXT,
                exit_price REAL,
                current_price REAL,
                return_pct REAL,
                return_amount REAL,
                status TEXT DEFAULT 'open',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
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
    today_as_of = datetime.now().strftime('%Y-%m-%d')
    # 과거 재등장 이력 조회를 위한 DB 연결(가능하면 재사용)
    conn_hist = None
    cur_hist = None
    try:
        conn_hist = sqlite3.connect(_db_path())
        cur_hist = conn_hist.cursor()
        cur_hist.execute("CREATE TABLE IF NOT EXISTS scan_rank(date TEXT, code TEXT, score REAL, flags TEXT, score_label TEXT, close_price REAL, PRIMARY KEY(date, code))")
    except Exception:
        conn_hist = None
        cur_hist = None
    for code in universe:
        try:
            df = api.get_ohlcv(code, config.ohlcv_count)
            if df.empty or len(df) < 21 or df[["open","high","low","close","volume"]].isna().any().any():
                continue
            df = compute_indicators(df)
            matched, sig_true, sig_total = match_stats(df)
            score, flags = score_conditions(df)
            cur = df.iloc[-1]
            # 재등장 메타 계산
            recurrence = None
            if cur_hist is not None:
                try:
                    prev_dates = []
                    for row in cur_hist.execute("SELECT date FROM scan_rank WHERE code=? ORDER BY date DESC", (code,)):
                        d = str(row[0])
                        if d and d < today_as_of:
                            prev_dates.append(d)
                    if prev_dates:
                        last_as_of = prev_dates[0]
                        first_as_of = prev_dates[-1]
                        try:
                            days_since_last = int((pd.to_datetime(today_as_of) - pd.to_datetime(last_as_of)).days)
                        except Exception:
                            days_since_last = None
                        recurrence = {
                            'appeared_before': True,
                            'appear_count': len(prev_dates),
                            'last_as_of': last_as_of,
                            'first_as_of': first_as_of,
                            'days_since_last': days_since_last,
                        }
                    else:
                        recurrence = {
                            'appeared_before': False,
                            'appear_count': 0,
                            'last_as_of': None,
                            'first_as_of': today_as_of,
                            'days_since_last': None,
                        }
                except Exception:
                    recurrence = None
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
                flags=_as_score_flags(flags),
                score_label=str(flags.get("label")) if isinstance(flags, dict) else None,
                details={**(flags.get("details", {}) if isinstance(flags, dict) else {}), "close": float(cur.close), "recurrence": recurrence},
                strategy=strategy_text(df),
            )
            if item.match:
                items.append(item)
        except Exception:
            continue
    try:
        if conn_hist is not None:
            conn_hist.close()
    except Exception:
        pass

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
        # SQLite 합치기
        try:
            conn = sqlite3.connect(_db_path())
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS scan_rank(date TEXT, code TEXT, score REAL, flags TEXT, score_label TEXT, close_price REAL, PRIMARY KEY(date, code))")
            for row in cur.execute("SELECT date, COUNT(1) FROM scan_rank GROUP BY date"):
                date, cnt = row
                # 이미 파일 항목이 있으면 rank_count만 업데이트
                hit = next((x for x in files if x.get('as_of') == date), None)
                if hit:
                    hit['rank_count'] = max(hit.get('rank_count') or 0, int(cnt))
                else:
                    files.append({'file': f"db:{date}", 'as_of': date, 'created_at': '', 'matched_count': None, 'rank_count': int(cnt)})
            conn.close()
        except Exception:
            pass
        files.sort(key=lambda x: x.get('as_of') or '', reverse=True)
    except Exception:
        files = []
    return {'count': len(files), 'items': files}


@app.post('/_backfill_snapshots')
def backfill_snapshots():
    """기존 JSON 스냅샷 파일을 SQLite scan_rank 테이블로 백필한다."""
    inserted = 0
    updated = 0
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS scan_rank(date TEXT, code TEXT, score REAL, flags TEXT, score_label TEXT, close_price REAL, PRIMARY KEY(date, code))")
        for fn in os.listdir(SNAPSHOT_DIR):
            if not fn.startswith('scan-') or not fn.endswith('.json'):
                continue
            path = os.path.join(SNAPSHOT_DIR, fn)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    snap = json.load(f)
                as_of = snap.get('as_of')
                rank = snap.get('rank', [])
                if not as_of or not isinstance(rank, list):
                    continue
                for it in rank:
                    code = it.get('ticker') or it.get('code')
                    if not code:
                        continue
                    score = float(it.get('score') or 0.0)
                    label = it.get('score_label') or ''
                    try:
                        cur.execute("INSERT OR IGNORE INTO scan_rank(date, code, score, flags, score_label, close_price) VALUES (?,?,?,?,?,?)",
                                    (as_of, code, score, json.dumps({}, ensure_ascii=False), label, 0.0))
                        if cur.rowcount == 1:
                            inserted += 1
                        else:
                            cur.execute("UPDATE scan_rank SET score=?, score_label=? WHERE date=? AND code=?",
                                        (score, label, as_of, code))
                            if cur.rowcount == 1:
                                updated += 1
                    except Exception:
                        continue
            except Exception:
                continue
        conn.commit(); conn.close()
    except Exception as e:
        return {'ok': False, 'error': str(e), 'inserted': inserted, 'updated': updated}
    return {'ok': True, 'inserted': inserted, 'updated': updated}

@app.get('/validate_from_snapshot')
def validate_from_snapshot(as_of: str, top_k: int = 20):
    # 당일 스냅샷은 검증 불가(장중 변동/오류 방지)
    today = datetime.now().strftime('%Y-%m-%d')
    if as_of == today:
        return {
            'error': 'today snapshot not allowed',
            'as_of': today,
            'items': [],
            'count': 0,
        }
    """스냅샷(as_of=YYYY-MM-DD) 상위 목록 기준으로 현재 수익률 검증"""
    # 1) DB 우선
    rank = []
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        for row in cur.execute("SELECT code, score, score_label FROM scan_rank WHERE date=? ORDER BY score DESC LIMIT ?", (as_of, int(top_k))):
            rank.append({'ticker': row[0], 'score': row[1], 'score_label': row[2]})
        conn.close()
    except Exception:
        rank = []
    # 2) JSON 스냅샷 보조
    if not rank:
        fname = f"scan-{as_of.replace('-', '')}.json"
        path = os.path.join(SNAPSHOT_DIR, fname)
        if not os.path.exists(path):
            return {'error': 'snapshot not found', 'as_of': as_of, 'items': []}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                snap = json.load(f)
            rank = snap.get('rank', [])
            rank.sort(key=lambda x: x.get('score', 0), reverse=True)
        except Exception as e:
            return {'error': str(e), 'as_of': as_of, 'items': []}
    base_dt = as_of.replace('-', '')
    results = []
    rets = []
    max_rets = []
    for it in rank[:max(0, top_k)]:
        code = it.get('ticker')
        try:
            df_then = api.get_ohlcv(code, config.ohlcv_count, base_dt=base_dt)
            if df_then.empty:
                continue
            # 스캔 당시 전략 산출(당일 종가 기준 인디케이터 계산 후 전략 텍스트 생성)
            try:
                df_then_ci = compute_indicators(df_then)
                strategy_then = strategy_text(df_then_ci)
            except Exception:
                strategy_then = '-'
            # 기준일 종가 사용(장중가격(cur_prc) 배제)
            price_then = float(df_then.iloc[-1].close)
            # 현재가(종가 기준) 및 이후 최대 수익률 계산
            df_now = api.get_ohlcv(code, 5)
            if df_now.empty:
                continue
            price_now = float(df_now.iloc[-1].close)
            ret = (price_now / price_then - 1.0) * 100.0
            rets.append(ret)
            # 이후 구간 최대 종가 기준 최대 수익률
            df_since = api.get_ohlcv(code, config.ohlcv_count)
            max_ret_pct = 0.0
            try:
                if not df_since.empty:
                    sub = df_since[df_since['date'] >= base_dt]
                    if not sub.empty:
                        peak = float(sub['close'].max())
                        max_ret_pct = round((peak / price_then - 1.0) * 100.0, 2)
            except Exception:
                max_ret_pct = 0.0
            max_rets.append(max_ret_pct)
            results.append({
                'ticker': code,
                'name': api.get_stock_name(code),
                'score_then': it.get('score'),
                'score_label_then': it.get('score_label'),
                'strategy_then': strategy_then,
                'price_then': price_then,
                'price_now': price_now,
                'return_pct': round(ret, 2),
                'max_return_pct': max_ret_pct,
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
        'avg_max_return_pct': round(sum(max_rets)/len(max_rets), 2) if max_rets else 0.0,
        'max_max_return_pct': round(max(max_rets), 2) if max_rets else 0.0,
        'items': results,
    }


@app.post('/send_scan_result')
def send_scan_result(to: str, top_n: int = 5):
    """현재 /scan 결과 요약을 카카오 알림톡으로 발송하고 로그에 남긴다"""
    # 최신 스캔 실행
    resp = scan(save_snapshot=True)
    msg = format_scan_message(resp.items, resp.matched_count, top_n=top_n)
    result = send_alert(to, msg)
    _log_send(to, resp.matched_count)
    return {"status": "ok" if result.get('ok') else "fail", "matched_count": resp.matched_count, "sent_to": to, "provider": result}


@app.post('/kakao_webhook')
def kakao_webhook(body: dict):
    """카카오 오픈빌더 Webhook: 사용자가 종목명/코드를 말하면 분석 요약을 반환"""
    utterance = (body.get('utterance') or body.get('userRequest', {}).get('utterance') or '').strip()
    if not utterance:
        text = "분석할 종목명을 입력해 주세요. 예) 삼성전자"
    else:
        # analyze 호출
        res = analyze(utterance)
        if not res.ok:
            text = f"분석 실패: {res.error}"
        else:
            it = res.item
            text = f"{it.name}({it.ticker}) 분석: 점수 {int(it.score)} ({it.score_label or '-'})\n전략: {it.strategy}"
    # 카카오 응답 포맷(간단 텍스트)
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {"simpleText": {"text": text}}
            ]
        }
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
        flags=_as_score_flags(flags),
        score_label=str(flags.get("label")) if isinstance(flags, dict) else None,
        strategy=strategy_text(df),
    )
    return AnalyzeResponse(ok=True, item=item)


@app.get('/positions', response_model=PositionResponse)
def get_positions():
    """포지션 목록 조회 (현재가 및 수익률 계산 포함)"""
    _init_positions_table()
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        rows = cur.execute("SELECT * FROM positions ORDER BY created_at DESC").fetchall()
        conn.close()
        
        items = []
        total_return_amount = 0.0
        total_investment = 0.0
        
        for row in rows:
            id_, ticker, name, entry_date, entry_price, quantity, exit_date, exit_price, current_price, return_pct, return_amount, status, created_at, updated_at = row
            
            # 현재가 조회 (오픈 포지션만)
            if status == 'open':
                try:
                    df = api.get_ohlcv(ticker, 5)
                    if not df.empty:
                        current_price = float(df.iloc[-1].close)
                        return_pct = (current_price / entry_price - 1.0) * 100.0
                        return_amount = (current_price - entry_price) * quantity
                    else:
                        current_price = None
                        return_pct = None
                        return_amount = None
                except Exception:
                    current_price = None
                    return_pct = None
                    return_amount = None
            else:
                # 종료된 포지션
                if exit_price:
                    return_pct = (exit_price / entry_price - 1.0) * 100.0
                    return_amount = (exit_price - entry_price) * quantity
                else:
                    return_pct = None
                    return_amount = None
            
            # 총 수익률 계산용
            if return_amount is not None:
                total_return_amount += return_amount
            total_investment += entry_price * quantity
            
            items.append(PositionItem(
                id=id_,
                ticker=ticker,
                name=name,
                entry_date=entry_date,
                entry_price=entry_price,
                quantity=quantity,
                exit_date=exit_date,
                exit_price=exit_price,
                current_price=current_price,
                return_pct=return_pct,
                return_amount=return_amount,
                status=status
            ))
        
        total_return_pct = (total_return_amount / total_investment * 100.0) if total_investment > 0 else 0.0
        
        return PositionResponse(
            items=items,
            total_return_pct=round(total_return_pct, 2),
            total_return_amount=round(total_return_amount, 2)
        )
    except Exception as e:
        return PositionResponse(items=[], total_return_pct=0.0, total_return_amount=0.0)


@app.post('/positions', response_model=dict)
def add_position(request: AddPositionRequest):
    """새 포지션 추가"""
    _init_positions_table()
    try:
        # 종목명 조회
        name = api.get_stock_name(request.ticker)
        if not name or name == request.ticker:
            return {"ok": False, "error": "종목명 조회 실패"}
        
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO positions (ticker, name, entry_date, entry_price, quantity, status)
            VALUES (?, ?, ?, ?, ?, 'open')
        """, (request.ticker, name, request.entry_date, request.entry_price, request.quantity))
        conn.commit()
        conn.close()
        
        return {"ok": True, "id": cur.lastrowid}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get('/scan_positions')
def get_scan_positions():
    """스캔된 종목들 중 포지션이 있는 종목들의 수익률 조회"""
    _init_positions_table()
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        
        # 오픈 포지션만 조회
        rows = cur.execute("SELECT * FROM positions WHERE status = 'open' ORDER BY created_at DESC").fetchall()
        conn.close()
        
        items = []
        for row in rows:
            id_, ticker, name, entry_date, entry_price, quantity, exit_date, exit_price, current_price, return_pct, return_amount, status, created_at, updated_at = row
            
            # 현재가 조회
            try:
                df = api.get_ohlcv(ticker, 5)
                if not df.empty:
                    current_price = float(df.iloc[-1].close)
                    return_pct = (current_price / entry_price - 1.0) * 100.0
                    return_amount = (current_price - entry_price) * quantity
                else:
                    current_price = None
                    return_pct = None
                    return_amount = None
            except Exception:
                current_price = None
                return_pct = None
                return_amount = None
            
            items.append({
                'ticker': ticker,
                'name': name,
                'entry_date': entry_date,
                'entry_price': entry_price,
                'quantity': quantity,
                'current_price': current_price,
                'return_pct': return_pct,
                'return_amount': return_amount,
                'position_id': id_
            })
        
        return {'items': items, 'count': len(items)}
    except Exception as e:
        return {'items': [], 'count': 0, 'error': str(e)}


@app.post('/auto_add_positions')
def auto_add_positions(score_threshold: int = 8, default_quantity: int = 10, entry_date: str = None):
    """스캔 결과에서 조건을 만족하는 종목들을 자동으로 포지션에 추가"""
    _init_positions_table()
    try:
        # 최신 스캔 결과 조회
        kp = config.universe_kospi
        kd = config.universe_kosdaq
        kospi = api.get_top_codes('KOSPI', kp)
        kosdaq = api.get_top_codes('KOSDAQ', kd)
        universe = [*kospi, *kosdaq]

        added_positions = []
        entry_dt = entry_date or datetime.now().strftime('%Y-%m-%d')

        for code in universe:
            try:
                df = api.get_ohlcv(code, config.ohlcv_count)
                if df.empty or len(df) < 21:
                    continue
                df = compute_indicators(df)
                matched, sig_true, sig_total = match_stats(df)
                score, flags = score_conditions(df)
                
                # 조건 확인: 점수가 임계값 이상이고 매치된 경우
                if matched and score >= score_threshold:
                    # 이미 포지션이 있는지 확인
                    conn = sqlite3.connect(_db_path())
                    cur = conn.cursor()
                    existing = cur.execute("SELECT id FROM positions WHERE ticker = ? AND status = 'open'", (code,)).fetchone()
                    
                    if not existing:  # 기존 포지션이 없으면 추가
                        name = api.get_stock_name(code)
                        current_price = float(df.iloc[-1].close)
                        
                        cur.execute("""
                            INSERT INTO positions (ticker, name, entry_date, entry_price, quantity, status)
                            VALUES (?, ?, ?, ?, ?, 'open')
                        """, (code, name, entry_dt, current_price, default_quantity))
                        conn.commit()
                        
                        added_positions.append({
                            'ticker': code,
                            'name': name,
                            'entry_price': current_price,
                            'quantity': default_quantity,
                            'score': score
                        })
                    
                    conn.close()
            except Exception:
                continue

        return {
            'ok': True,
            'added_count': len(added_positions),
            'positions': added_positions,
            'criteria': {
                'score_threshold': score_threshold,
                'default_quantity': default_quantity,
                'entry_date': entry_dt
            }
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@app.put('/positions/{position_id}', response_model=dict)
def update_position(position_id: int, request: UpdatePositionRequest):
    """포지션 업데이트 (청산 처리)"""
    _init_positions_table()
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        
        # 기존 포지션 조회
        row = cur.execute("SELECT * FROM positions WHERE id = ?", (position_id,)).fetchone()
        if not row:
            conn.close()
            return {"ok": False, "error": "포지션을 찾을 수 없습니다"}
        
        id_, ticker, name, entry_date, entry_price, quantity, exit_date, exit_price, current_price, return_pct, return_amount, status, created_at, updated_at = row
        
        # 청산 처리
        if request.exit_date and request.exit_price:
            return_pct = (request.exit_price / entry_price - 1.0) * 100.0
            return_amount = (request.exit_price - entry_price) * quantity
            
            cur.execute("""
                UPDATE positions 
                SET exit_date = ?, exit_price = ?, return_pct = ?, return_amount = ?, status = 'closed', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (request.exit_date, request.exit_price, return_pct, return_amount, position_id))
        else:
            # 현재가만 업데이트
            cur.execute("""
                UPDATE positions 
                SET current_price = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (request.exit_price, position_id))
        
        conn.commit()
        conn.close()
        
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get('/scan_positions')
def get_scan_positions():
    """스캔된 종목들 중 포지션이 있는 종목들의 수익률 조회"""
    _init_positions_table()
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        
        # 오픈 포지션만 조회
        rows = cur.execute("SELECT * FROM positions WHERE status = 'open' ORDER BY created_at DESC").fetchall()
        conn.close()
        
        items = []
        for row in rows:
            id_, ticker, name, entry_date, entry_price, quantity, exit_date, exit_price, current_price, return_pct, return_amount, status, created_at, updated_at = row
            
            # 현재가 조회
            try:
                df = api.get_ohlcv(ticker, 5)
                if not df.empty:
                    current_price = float(df.iloc[-1].close)
                    return_pct = (current_price / entry_price - 1.0) * 100.0
                    return_amount = (current_price - entry_price) * quantity
                else:
                    current_price = None
                    return_pct = None
                    return_amount = None
            except Exception:
                current_price = None
                return_pct = None
                return_amount = None
            
            items.append({
                'ticker': ticker,
                'name': name,
                'entry_date': entry_date,
                'entry_price': entry_price,
                'quantity': quantity,
                'current_price': current_price,
                'return_pct': return_pct,
                'return_amount': return_amount,
                'position_id': id_
            })
        
        return {'items': items, 'count': len(items)}
    except Exception as e:
        return {'items': [], 'count': 0, 'error': str(e)}


@app.post('/auto_add_positions')
def auto_add_positions(score_threshold: int = 8, default_quantity: int = 10, entry_date: str = None):
    """스캔 결과에서 조건을 만족하는 종목들을 자동으로 포지션에 추가"""
    _init_positions_table()
    try:
        # 최신 스캔 결과 조회
        kp = config.universe_kospi
        kd = config.universe_kosdaq
        kospi = api.get_top_codes('KOSPI', kp)
        kosdaq = api.get_top_codes('KOSDAQ', kd)
        universe = [*kospi, *kosdaq]

        added_positions = []
        entry_dt = entry_date or datetime.now().strftime('%Y-%m-%d')

        for code in universe:
            try:
                df = api.get_ohlcv(code, config.ohlcv_count)
                if df.empty or len(df) < 21:
                    continue
                df = compute_indicators(df)
                matched, sig_true, sig_total = match_stats(df)
                score, flags = score_conditions(df)
                
                # 조건 확인: 점수가 임계값 이상이고 매치된 경우
                if matched and score >= score_threshold:
                    # 이미 포지션이 있는지 확인
                    conn = sqlite3.connect(_db_path())
                    cur = conn.cursor()
                    existing = cur.execute("SELECT id FROM positions WHERE ticker = ? AND status = 'open'", (code,)).fetchone()
                    
                    if not existing:  # 기존 포지션이 없으면 추가
                        name = api.get_stock_name(code)
                        current_price = float(df.iloc[-1].close)
                        
                        cur.execute("""
                            INSERT INTO positions (ticker, name, entry_date, entry_price, quantity, status)
                            VALUES (?, ?, ?, ?, ?, 'open')
                        """, (code, name, entry_dt, current_price, default_quantity))
                        conn.commit()
                        
                        added_positions.append({
                            'ticker': code,
                            'name': name,
                            'entry_price': current_price,
                            'quantity': default_quantity,
                            'score': score
                        })
                    
                    conn.close()
            except Exception:
                continue

        return {
            'ok': True,
            'added_count': len(added_positions),
            'positions': added_positions,
            'criteria': {
                'score_threshold': score_threshold,
                'default_quantity': default_quantity,
                'entry_date': entry_dt
            }
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@app.delete('/positions/{position_id}', response_model=dict)
def delete_position(position_id: int):
    """포지션 삭제"""
    _init_positions_table()
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        cur.execute("DELETE FROM positions WHERE id = ?", (position_id,))
        conn.commit()
        conn.close()
        
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get('/scan_positions')
def get_scan_positions():
    """스캔된 종목들 중 포지션이 있는 종목들의 수익률 조회"""
    _init_positions_table()
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        
        # 오픈 포지션만 조회
        rows = cur.execute("SELECT * FROM positions WHERE status = 'open' ORDER BY created_at DESC").fetchall()
        conn.close()
        
        items = []
        for row in rows:
            id_, ticker, name, entry_date, entry_price, quantity, exit_date, exit_price, current_price, return_pct, return_amount, status, created_at, updated_at = row
            
            # 현재가 조회
            try:
                df = api.get_ohlcv(ticker, 5)
                if not df.empty:
                    current_price = float(df.iloc[-1].close)
                    return_pct = (current_price / entry_price - 1.0) * 100.0
                    return_amount = (current_price - entry_price) * quantity
                else:
                    current_price = None
                    return_pct = None
                    return_amount = None
            except Exception:
                current_price = None
                return_pct = None
                return_amount = None
            
            items.append({
                'ticker': ticker,
                'name': name,
                'entry_date': entry_date,
                'entry_price': entry_price,
                'quantity': quantity,
                'current_price': current_price,
                'return_pct': return_pct,
                'return_amount': return_amount,
                'position_id': id_
            })
        
        return {'items': items, 'count': len(items)}
    except Exception as e:
        return {'items': [], 'count': 0, 'error': str(e)}


@app.post('/auto_add_positions')
def auto_add_positions(score_threshold: int = 8, default_quantity: int = 10, entry_date: str = None):
    """스캔 결과에서 조건을 만족하는 종목들을 자동으로 포지션에 추가"""
    _init_positions_table()
    try:
        # 최신 스캔 결과 조회
        kp = config.universe_kospi
        kd = config.universe_kosdaq
        kospi = api.get_top_codes('KOSPI', kp)
        kosdaq = api.get_top_codes('KOSDAQ', kd)
        universe = [*kospi, *kosdaq]

        added_positions = []
        entry_dt = entry_date or datetime.now().strftime('%Y-%m-%d')

        for code in universe:
            try:
                df = api.get_ohlcv(code, config.ohlcv_count)
                if df.empty or len(df) < 21:
                    continue
                df = compute_indicators(df)
                matched, sig_true, sig_total = match_stats(df)
                score, flags = score_conditions(df)
                
                # 조건 확인: 점수가 임계값 이상이고 매치된 경우
                if matched and score >= score_threshold:
                    # 이미 포지션이 있는지 확인
                    conn = sqlite3.connect(_db_path())
                    cur = conn.cursor()
                    existing = cur.execute("SELECT id FROM positions WHERE ticker = ? AND status = 'open'", (code,)).fetchone()
                    
                    if not existing:  # 기존 포지션이 없으면 추가
                        name = api.get_stock_name(code)
                        current_price = float(df.iloc[-1].close)
                        
                        cur.execute("""
                            INSERT INTO positions (ticker, name, entry_date, entry_price, quantity, status)
                            VALUES (?, ?, ?, ?, ?, 'open')
                        """, (code, name, entry_dt, current_price, default_quantity))
                        conn.commit()
                        
                        added_positions.append({
                            'ticker': code,
                            'name': name,
                            'entry_price': current_price,
                            'quantity': default_quantity,
                            'score': score
                        })
                    
                    conn.close()
            except Exception:
                continue

        return {
            'ok': True,
            'added_count': len(added_positions),
            'positions': added_positions,
            'criteria': {
                'score_threshold': score_threshold,
                'default_quantity': default_quantity,
                'entry_date': entry_dt
            }
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}

