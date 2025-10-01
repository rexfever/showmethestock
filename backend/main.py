from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import os
import json
from typing import List, Optional
import pandas as pd

from config import config, reload_from_env
from environment import get_environment_info
from kiwoom_api import KiwoomAPI
from scanner import compute_indicators, match_condition, match_stats, strategy_text, score_conditions
from models import ScanResponse, ScanItem, IndicatorPayload, TrendPayload, AnalyzeResponse, UniverseResponse, UniverseItem, ScoreFlags, PositionResponse, PositionItem, AddPositionRequest, UpdatePositionRequest, PortfolioResponse, PortfolioItem, AddToPortfolioRequest, UpdatePortfolioRequest
from utils import is_code, normalize_code_or_name
import sqlite3
from kakao import send_alert, format_scan_message, format_scan_alert_message
import glob

# 인증 관련 import
from auth_models import User, Token, SocialLoginRequest, EmailSignupRequest, EmailLoginRequest, EmailVerificationRequest, PasswordResetRequest, PasswordResetConfirmRequest, PaymentRequest, PaymentResponse, AdminUserUpdateRequest, AdminUserDeleteRequest, AdminStatsResponse
from auth_service import auth_service
from social_auth import social_auth_service
from subscription_service import subscription_service
from payment_service import kakao_pay_service
from subscription_plans import get_all_plans, get_plan
from admin_service import admin_service
import httpx

# 포트폴리오 관련 import
from portfolio_service import portfolio_service


app = FastAPI(title='Stock Scanner API')

# CORS 설정 (환경별 동적 설정)
def get_cors_origins():
    """환경에 따른 CORS origins 설정"""
    env_info = get_environment_info()
    if env_info['is_local']:
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    else:
        return [
            "https://sohntech.ai.kr",
            "https://www.sohntech.ai.kr",
        ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
api = KiwoomAPI()


@app.get('/')
def root():
    return {'status': 'running'}


@app.get('/environment')
def get_environment():
    """현재 실행 환경 정보 반환"""
    env_info = get_environment_info()
    return {
        'environment': env_info['environment'],
        'is_local': env_info['is_local'],
        'is_server': env_info['is_server'],
        'hostname': env_info['hostname'],
        'local_ip': env_info['local_ip'],
        'working_directory': env_info['working_directory'],
        'user': env_info['user'],
        'config': {
            'environment': config.environment,
            'is_local': config.is_local,
            'is_server': config.is_server,
            'universe_kospi': config.universe_kospi,
            'universe_kosdaq': config.universe_kosdaq,
        }
    }


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


def calculate_returns(ticker: str, scan_date: str, current_date: str = None) -> dict:
    """특정 종목의 수익률 계산
    
    Args:
        ticker: 종목 코드
        scan_date: 스캔 날짜 (YYYY-MM-DD)
        current_date: 현재 날짜 (YYYY-MM-DD), None이면 오늘
        
    Returns:
        dict: {
            'current_return': float,  # 현재 수익률
            'max_return': float,      # 기간 내 최고 수익률
            'min_return': float,      # 기간 내 최저 수익률
            'scan_price': float,      # 스캔 시점 가격
            'current_price': float,   # 현재 가격
            'max_price': float,       # 기간 내 최고가
            'min_price': float,       # 기간 내 최저가
            'days_elapsed': int       # 경과 일수
        }
    """
    try:
        if current_date is None:
            current_date = datetime.now().strftime('%Y-%m-%d')
        
        # 스캔 날짜의 데이터 조회
        scan_date_formatted = scan_date.replace('-', '')
        df_scan = api.get_ohlcv(ticker, 1, scan_date_formatted)
        
        if df_scan.empty:
            print(f"스캔 날짜 데이터 없음: {ticker} {scan_date}")
            return None
            
        scan_price = float(df_scan.iloc[-1]['close'])
        
        # 현재까지의 데이터 조회 (스캔 날짜부터)
        df_current = api.get_ohlcv(ticker, 100)  # 충분한 기간
        
        if df_current.empty:
            return None
            
        # 스캔 날짜 이후 데이터만 필터링
        scan_date_dt = pd.to_datetime(scan_date)
        df_current['date_dt'] = pd.to_datetime(df_current['date'])
        df_period = df_current[df_current['date_dt'] >= scan_date_dt]
        
        if df_period.empty:
            return None
            
        current_price = float(df_period.iloc[-1]['close'])
        
        # high/low가 0인 경우 close 가격을 기준으로 추정
        high_prices = df_period['high'].where(df_period['high'] > 0, df_period['close'])
        low_prices = df_period['low'].where(df_period['low'] > 0, df_period['close'])
        
        max_price = float(high_prices.max())
        min_price = float(low_prices.min())
        
        # 수익률 계산
        current_return = ((current_price - scan_price) / scan_price) * 100
        max_return = ((max_price - scan_price) / scan_price) * 100
        min_return = ((min_price - scan_price) / scan_price) * 100
        
        # 경과 일수
        days_elapsed = (pd.to_datetime(current_date) - scan_date_dt).days
        
        return {
            'current_return': round(current_return, 2),
            'max_return': round(max_return, 2),
            'min_return': round(min_return, 2),
            'scan_price': scan_price,
            'current_price': current_price,
            'max_price': max_price,
            'min_price': min_price,
            'days_elapsed': days_elapsed
        }
        
    except Exception as e:
        print(f"수익률 계산 오류 ({ticker}): {e}")
        return None


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
            rsi_dema_setup=bool(f.get('rsi_dema_setup')),
            rsi_tema_trigger=bool(f.get('rsi_tema_trigger')),
            rsi_dema_value=f.get('rsi_dema_value'),
            rsi_tema_value=f.get('rsi_tema_value'),
            overheated_rsi_tema=bool(f.get('overheated_rsi_tema')),
            tema_slope_ok=bool(f.get('tema_slope_ok')),
            obv_slope_ok=bool(f.get('obv_slope_ok')),
            above_cnt5_ok=bool(f.get('above_cnt5_ok')),
            dema_slope_ok=bool(f.get('dema_slope_ok')),
            details=f.get('details') if isinstance(f.get('details'), dict) else None,
            label=f.get('label'),
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
                quantity INTEGER NOT NULL,
                score INTEGER,
                strategy TEXT,
                current_return_pct REAL,
                max_return_pct REAL,
                exit_date TEXT,
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
def scan(kospi_limit: int = None, kosdaq_limit: int = None, save_snapshot: bool = True, sort_by: str = 'score', date: str = None):
    kp = kospi_limit or config.universe_kospi
    kd = kosdaq_limit or config.universe_kosdaq
    kospi = api.get_top_codes('KOSPI', kp)
    kosdaq = api.get_top_codes('KOSDAQ', kd)
    universe: List[str] = [*kospi, *kosdaq]

    # 날짜 처리
    if date:
        try:
            # YYYYMMDD 형식으로 입력된 날짜를 YYYY-MM-DD로 변환
            scan_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            today_as_of = scan_date
        except:
            raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. YYYYMMDD 형식으로 입력해주세요.")
    else:
        today_as_of = datetime.now().strftime('%Y-%m-%d')
    
    # Fallback 로직 적용
    from scanner import scan_with_preset
    
    chosen_step = None
    if not config.fallback_enable:
        # Fallback 비활성화 시 기존 로직
        items = scan_with_preset(universe, {}, date)
        items = items[:config.top_k]
    else:
        # Fallback 활성화 시 단계별 완화
        final_items = []
        chosen_step = 0
        
        for step, overrides in enumerate(config.fallback_presets):
            items = scan_with_preset(universe, overrides, date)
            # 하드 컷은 scan_one_symbol 내부에서 이미 처리되어야 함(과열/유동성/가격 등)
            if len(items) >= config.fallback_target_min:
                chosen_step = step
                final_items = items[:min(config.top_k, config.fallback_target_max)]
                break
        
        # 만약 모든 단계에서도 0개라면, 마지막 단계 결과에서 score 상위 TOP_K만 가져오되,
        # 하드 컷(과열/유동성/가격)만 적용된 집합이어야 함.
        if not final_items:
            # 가장 완화된 단계의 결과를 그대로 사용(이미 하드 컷 적용됨)
            final_items = items[:min(config.top_k, config.fallback_target_max)]
        
        items = final_items
    
    # ScanItem 객체로 변환
    scan_items: List[ScanItem] = []
    for item in items:
        try:
            # 재등장 메타 계산
            recurrence = None
            # 과거 재등장 이력 조회를 위한 DB 연결(가능하면 재사용)
            conn_hist = None
            cur_hist = None
            try:
                conn_hist = sqlite3.connect(_db_path())
                cur_hist = conn_hist.cursor()
                cur_hist.execute("CREATE TABLE IF NOT EXISTS scan_rank(date TEXT, code TEXT, score REAL, flags TEXT, score_label TEXT, close_price REAL, PRIMARY KEY(date, code))")
                
                prev_dates = []
                for row in cur_hist.execute("SELECT date FROM scan_rank WHERE code=? ORDER BY date DESC", (item["ticker"],)):
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
            finally:
                if conn_hist is not None:
                    conn_hist.close()
            
            scan_item = ScanItem(
                ticker=item["ticker"],
                name=item["name"],
                match=item["match"],
                score=item["score"],
                indicators=IndicatorPayload(
                    TEMA=item["indicators"]["TEMA"],
                    DEMA=item["indicators"]["DEMA"],
                    MACD_OSC=item["indicators"]["MACD_OSC"],
                    MACD_LINE=item["indicators"]["MACD_LINE"],
                    MACD_SIGNAL=item["indicators"]["MACD_SIGNAL"],
                    RSI_TEMA=item["indicators"]["RSI_TEMA"],
                    RSI_DEMA=item["indicators"]["RSI_DEMA"],
                    OBV=item["indicators"]["OBV"],
                    VOL=item["indicators"]["VOL"],
                    VOL_MA5=item["indicators"]["VOL_MA5"],
                    close=item["indicators"]["close"],
                ),
                trend=TrendPayload(
                    TEMA20_SLOPE20=item["trend"]["TEMA20_SLOPE20"],
                    OBV_SLOPE20=item["trend"]["OBV_SLOPE20"],
                    ABOVE_CNT5=item["trend"]["ABOVE_CNT5"],
                    DEMA10_SLOPE20=item["trend"]["DEMA10_SLOPE20"],
                ),
                flags=_as_score_flags(item["flags"]),
                score_label=item["score_label"],
                details={**item["flags"].get("details", {}), "close": item["indicators"]["close"], "recurrence": recurrence},
                strategy=item["strategy"],
                # 수익률 계산 (과거 스캔인 경우)
                returns=calculate_returns(item["ticker"], today_as_of) if date else None,
            )
            scan_items.append(scan_item)
        except Exception:
            continue

    resp = ScanResponse(
        as_of=today_as_of,
        universe_count=len(universe),
        matched_count=len(scan_items),
        rsi_mode="tema_dema",  # 새로운 RSI 모드
        rsi_period=14,  # 고정값
        rsi_threshold=config.rsi_setup_min,  # 새로운 RSI 임계값 사용
        items=scan_items,
        fallback_step=chosen_step if config.fallback_enable else None,
        score_weights=getattr(config, 'dynamic_score_weights')() if hasattr(config, 'dynamic_score_weights') else {},
        score_level_strong=config.score_level_strong,
        score_level_watch=config.score_level_watch,
        require_dema_slope=getattr(config, 'require_dema_slope', 'required'),
    )
    if save_snapshot:
        # 스냅샷에는 핵심 메타/랭킹만 저장(용량 절약)
        # 스냅샷에 종가, 거래량, 변동률 추가
        enhanced_rank = []
        for it in scan_items:
            try:
                # 최신 OHLCV 데이터 가져오기 (스냅샷 생성 시점)
                df = api.get_ohlcv(it.ticker, 2)  # 최근 2일 데이터 (전일 대비 변동률 계산용)
                if not df.empty:
                    latest = df.iloc[-1]
                    prev_close = df.iloc[-2]["close"] if len(df) > 1 else latest["open"]
                    
                    # 변동률 계산 (전일 종가 대비)
                    if prev_close != 0:
                        change_rate = round(((latest["close"] - prev_close) / prev_close) * 100, 2)
                    else:
                        change_rate = 0
                    
                    enhanced_item = {
                        'ticker': it.ticker,
                        'name': it.name,
                        'score': it.score,
                        'score_label': it.score_label,
                        'close_price': int(latest["close"]),  # 종가
                        'volume': int(latest["volume"]),      # 거래량
                        'change_rate': change_rate,           # 변동률
                    }
                else:
                    # 데이터 없을 때 기본값
                    enhanced_item = {
                        'ticker': it.ticker,
                        'name': it.name,
                        'score': it.score,
                        'score_label': it.score_label,
                        'close_price': 0,
                        'volume': 0,
                        'change_rate': 0,
                    }
            except Exception as e:
                # API 호출 실패시 기본값
                enhanced_item = {
                    'ticker': it.ticker,
                    'name': it.name,
                    'score': it.score,
                    'score_label': it.score_label,
                    'close_price': 0,
                    'volume': 0,
                    'change_rate': 0,
                }
            enhanced_rank.append(enhanced_item)
        
        snapshot = {
            'as_of': resp.as_of,
            'created_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'universe_count': resp.universe_count,
            'matched_count': resp.matched_count,
            'rsi_mode': resp.rsi_mode,
            'rsi_period': resp.rsi_period,
            'rsi_threshold': resp.rsi_threshold,
            'rank': enhanced_rank,
        }
        _save_scan_snapshot(snapshot)
        _save_snapshot_db(resp.as_of, items)
    return resp


@app.get('/scan/historical', response_model=ScanResponse)
def scan_historical(date: str, kospi_limit: int = None, kosdaq_limit: int = None):
    """과거 날짜로 스캔하고 성과를 측정하는 엔드포인트
    
    Args:
        date: 스캔할 날짜 (YYYYMMDD 형식)
        kospi_limit: KOSPI 종목 수 제한
        kosdaq_limit: KOSDAQ 종목 수 제한
        
    Returns:
        ScanResponse: 스캔 결과와 각 종목의 현재까지의 성과
    """
    return scan(
        kospi_limit=kospi_limit,
        kosdaq_limit=kosdaq_limit,
        save_snapshot=False,  # 과거 스캔은 스냅샷 저장하지 않음
        sort_by='score',
        date=date
    )


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
    """현재 /scan 결과 요약을 솔라피 알림톡으로 발송하고 로그에 남긴다"""
    # 최신 스캔 실행
    resp = scan(save_snapshot=True)
    
    # 솔라피 알림톡 템플릿 변수 생성
    from datetime import datetime
    scan_date = datetime.now().strftime("%Y년 %m월 %d일")
    template_data = format_scan_alert_message(
        matched_count=resp.matched_count,
        scan_date=scan_date,
        user_name="고객님"
    )
    
    result = send_alert(to, template_data)
    _log_send(to, resp.matched_count)
    
    return {
        "status": "ok" if result.get('ok') else "fail", 
        "matched_count": resp.matched_count, 
        "sent_to": to, 
        "template_data": template_data,
        "provider": result
    }


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
        match=flags.get("match", bool(matched)),
        score=float(score),
        indicators=IndicatorPayload(
            TEMA=float(cur.TEMA20),
            DEMA=float(cur.DEMA10),
            MACD_OSC=float(cur.MACD_OSC),
            MACD_LINE=float(cur.MACD_LINE),
            MACD_SIGNAL=float(cur.MACD_SIGNAL),
            RSI_TEMA=float(cur.RSI_TEMA),
            RSI_DEMA=float(cur.RSI_DEMA),
            OBV=float(cur.OBV),
            VOL=int(cur.volume),
            VOL_MA5=float(cur.VOL_MA5) if pd.notna(cur.VOL_MA5) else 0.0,
            close=float(cur.close),
        ),
        trend=TrendPayload(
            TEMA20_SLOPE20=float(df.iloc[-1].get("TEMA20_SLOPE20", 0.0)) if "TEMA20_SLOPE20" in df.columns else 0.0,
            OBV_SLOPE20=float(df.iloc[-1].get("OBV_SLOPE20", 0.0)) if "OBV_SLOPE20" in df.columns else 0.0,
            ABOVE_CNT5=int(((df["TEMA20"] > df["DEMA10"]).tail(5).sum()) if ("TEMA20" in df.columns and "DEMA10" in df.columns) else 0),
            DEMA10_SLOPE20=float(df.iloc[-1].get("DEMA10_SLOPE20", 0.0)) if "DEMA10_SLOPE20" in df.columns else 0.0,
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
            id_, ticker, name, entry_date, quantity, score, strategy, current_return_pct, max_return_pct, exit_date, status, created_at, updated_at = row
            
            # 현재 수익률과 최대 수익률 계산 (오픈 포지션만)
            if status == 'open':
                try:
                    # 진입일부터 현재까지의 데이터 조회
                    from datetime import datetime, timedelta
                    entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
                    days_diff = (datetime.now() - entry_dt).days
                    lookback_days = min(days_diff + 10, 100)  # 여유분 포함
                    
                    df = api.get_ohlcv(ticker, lookback_days)
                    if not df.empty and len(df) > 1:
                        # 진입일 이후 데이터만 필터링
                        df['date'] = pd.to_datetime(df.index)
                        entry_date_dt = pd.to_datetime(entry_date)
                        df = df[df['date'] >= entry_date_dt]
                        
                        if len(df) > 0:
                            # 진입가 (첫 번째 종가)
                            entry_price = float(df.iloc[0].close)
                            # 현재가 (마지막 종가)
                            current_price = float(df.iloc[-1].close)
                            # 현재 수익률
                            current_return_pct = (current_price / entry_price - 1.0) * 100.0
                            # 기간내 최대 수익률
                            max_price = float(df['close'].max())
                            max_return_pct = (max_price / entry_price - 1.0) * 100.0
                        else:
                            current_return_pct = None
                            max_return_pct = None
                    else:
                        current_return_pct = None
                        max_return_pct = None
                except Exception:
                    current_return_pct = None
                    max_return_pct = None
            else:
                # 종료된 포지션은 기존 값 유지
                pass
            
            items.append(PositionItem(
                id=id_,
                ticker=ticker,
                name=name,
                entry_date=entry_date,
                quantity=quantity,
                score=score,
                strategy=strategy,
                current_return_pct=current_return_pct,
                max_return_pct=max_return_pct,
                exit_date=exit_date,
                status=status
            ))
        
        # 전체 수익률 계산 (현재 수익률 기준)
        total_return_pct = 0.0
        valid_positions = [item for item in items if item.current_return_pct is not None]
        if valid_positions:
            total_return_pct = sum(item.current_return_pct for item in valid_positions) / len(valid_positions)
        
        return PositionResponse(
            items=items,
            total_return_pct=round(total_return_pct, 2)
        )
    except Exception as e:
        return PositionResponse(items=[], total_return_pct=0.0)


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
            INSERT INTO positions (ticker, name, entry_date, quantity, score, strategy, status)
            VALUES (?, ?, ?, ?, ?, ?, 'open')
        """, (request.ticker, name, request.entry_date, request.quantity, request.score, request.strategy))
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
            id_, ticker, name, entry_date, quantity, score, strategy, current_return_pct, max_return_pct, exit_date, status, created_at, updated_at = row
            
            # 현재 수익률과 최대 수익률 계산
            try:
                # 진입일부터 현재까지의 데이터 조회
                from datetime import datetime, timedelta
                entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
                days_diff = (datetime.now() - entry_dt).days
                lookback_days = min(days_diff + 10, 100)  # 여유분 포함
                
                df = api.get_ohlcv(ticker, lookback_days)
                if not df.empty and len(df) > 1:
                    # 진입일 이후 데이터만 필터링
                    df['date'] = pd.to_datetime(df.index)
                    entry_date_dt = pd.to_datetime(entry_date)
                    df = df[df['date'] >= entry_date_dt]
                    
                    if len(df) > 0:
                        # 진입가 (첫 번째 종가)
                        entry_price = float(df.iloc[0].close)
                        # 현재가 (마지막 종가)
                        current_price = float(df.iloc[-1].close)
                        # 현재 수익률
                        current_return_pct = (current_price / entry_price - 1.0) * 100.0
                        # 기간내 최대 수익률
                        max_price = float(df['close'].max())
                        max_return_pct = (max_price / entry_price - 1.0) * 100.0
                    else:
                        current_return_pct = None
                        max_return_pct = None
                else:
                    current_return_pct = None
                    max_return_pct = None
            except Exception:
                current_return_pct = None
                max_return_pct = None
            
            items.append({
                'ticker': ticker,
                'name': name,
                'entry_date': entry_date,
                'quantity': quantity,
                'score': score,
                'strategy': strategy,
                'current_return_pct': current_return_pct,
                'max_return_pct': max_return_pct,
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
                            INSERT INTO positions (ticker, name, entry_date, quantity, score, strategy, status)
                            VALUES (?, ?, ?, ?, ?, ?, 'open')
                        """, (code, name, entry_dt, default_quantity, score, flags.get('label', '')))
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
        
        id_, ticker, name, entry_date, quantity, score, strategy, current_return_pct, max_return_pct, exit_date, status, created_at, updated_at = row
        
        # 청산 처리
        if request.exit_date:
            cur.execute("""
                UPDATE positions 
                SET exit_date = ?, status = 'closed', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (request.exit_date, position_id))
        
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
            id_, ticker, name, entry_date, quantity, score, strategy, current_return_pct, max_return_pct, exit_date, status, created_at, updated_at = row
            
            # 현재 수익률과 최대 수익률 계산
            try:
                # 진입일부터 현재까지의 데이터 조회
                from datetime import datetime, timedelta
                entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
                days_diff = (datetime.now() - entry_dt).days
                lookback_days = min(days_diff + 10, 100)  # 여유분 포함
                
                df = api.get_ohlcv(ticker, lookback_days)
                if not df.empty and len(df) > 1:
                    # 진입일 이후 데이터만 필터링
                    df['date'] = pd.to_datetime(df.index)
                    entry_date_dt = pd.to_datetime(entry_date)
                    df = df[df['date'] >= entry_date_dt]
                    
                    if len(df) > 0:
                        # 진입가 (첫 번째 종가)
                        entry_price = float(df.iloc[0].close)
                        # 현재가 (마지막 종가)
                        current_price = float(df.iloc[-1].close)
                        # 현재 수익률
                        current_return_pct = (current_price / entry_price - 1.0) * 100.0
                        # 기간내 최대 수익률
                        max_price = float(df['close'].max())
                        max_return_pct = (max_price / entry_price - 1.0) * 100.0
                    else:
                        current_return_pct = None
                        max_return_pct = None
                else:
                    current_return_pct = None
                    max_return_pct = None
            except Exception:
                current_return_pct = None
                max_return_pct = None
            
            items.append({
                'ticker': ticker,
                'name': name,
                'entry_date': entry_date,
                'quantity': quantity,
                'score': score,
                'strategy': strategy,
                'current_return_pct': current_return_pct,
                'max_return_pct': max_return_pct,
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
                            INSERT INTO positions (ticker, name, entry_date, quantity, score, strategy, status)
                            VALUES (?, ?, ?, ?, ?, ?, 'open')
                        """, (code, name, entry_dt, default_quantity, score, flags.get('label', '')))
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
            id_, ticker, name, entry_date, quantity, score, strategy, current_return_pct, max_return_pct, exit_date, status, created_at, updated_at = row
            
            # 현재 수익률과 최대 수익률 계산
            try:
                # 진입일부터 현재까지의 데이터 조회
                from datetime import datetime, timedelta
                entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
                days_diff = (datetime.now() - entry_dt).days
                lookback_days = min(days_diff + 10, 100)  # 여유분 포함
                
                df = api.get_ohlcv(ticker, lookback_days)
                if not df.empty and len(df) > 1:
                    # 진입일 이후 데이터만 필터링
                    df['date'] = pd.to_datetime(df.index)
                    entry_date_dt = pd.to_datetime(entry_date)
                    df = df[df['date'] >= entry_date_dt]
                    
                    if len(df) > 0:
                        # 진입가 (첫 번째 종가)
                        entry_price = float(df.iloc[0].close)
                        # 현재가 (마지막 종가)
                        current_price = float(df.iloc[-1].close)
                        # 현재 수익률
                        current_return_pct = (current_price / entry_price - 1.0) * 100.0
                        # 기간내 최대 수익률
                        max_price = float(df['close'].max())
                        max_return_pct = (max_price / entry_price - 1.0) * 100.0
                    else:
                        current_return_pct = None
                        max_return_pct = None
                else:
                    current_return_pct = None
                    max_return_pct = None
            except Exception:
                current_return_pct = None
                max_return_pct = None
            
            items.append({
                'ticker': ticker,
                'name': name,
                'entry_date': entry_date,
                'quantity': quantity,
                'score': score,
                'strategy': strategy,
                'current_return_pct': current_return_pct,
                'max_return_pct': max_return_pct,
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
                            INSERT INTO positions (ticker, name, entry_date, quantity, score, strategy, status)
                            VALUES (?, ?, ?, ?, ?, ?, 'open')
                        """, (code, name, entry_dt, default_quantity, score, flags.get('label', '')))
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


@app.get("/available-scan-dates")
async def get_available_scan_dates():
    """사용 가능한 스캔 날짜 목록을 가져옵니다."""
    try:
        # 스냅샷 파일들에서 날짜 추출
        snapshot_files = glob.glob("snapshots/scan-*.json")
        auto_scan_files = glob.glob("snapshots/auto-scan-*.json")
        
        all_files = snapshot_files + auto_scan_files
        
        if not all_files:
            return {"ok": False, "error": "스캔 결과가 없습니다."}
        
        # 날짜 추출 및 중복 제거
        import re
        dates = set()
        for file in all_files:
            date_match = re.search(r'(\d{8})', file)
            if date_match:
                dates.add(date_match.group(1))
        
        # 날짜 정렬 (최신순)
        sorted_dates = sorted(list(dates), reverse=True)
        
        return {"ok": True, "dates": sorted_dates}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/scan-by-date/{date}")
async def get_scan_by_date(date: str):
    """특정 날짜의 스캔 결과를 가져옵니다. (YYYYMMDD 형식)"""
    try:
        # 날짜 형식 검증
        if len(date) != 8 or not date.isdigit():
            return {"ok": False, "error": "날짜 형식이 올바르지 않습니다. YYYYMMDD 형식을 사용해주세요."}
        
        # 해당 날짜의 스캔 파일 찾기
        snapshot_files = glob.glob(f"snapshots/scan-{date}.json")
        auto_scan_files = glob.glob(f"snapshots/auto-scan-{date}_*.json")
        
        all_files = snapshot_files + auto_scan_files
        
        if not all_files:
            return {"ok": False, "error": f"{date} 날짜의 스캔 결과가 없습니다."}
        
        # 가장 최신 파일 선택 (auto-scan이 있으면 우선)
        target_file = max(all_files, key=lambda x: x.split("-")[-1].replace(".json", ""))
        
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 스캔 날짜 정보 추가
        data["scan_date"] = date
        data["is_latest"] = False
        
        # 사용자 화면에 필요한 정보 추가 (latest-scan과 동일한 로직)
        enhanced_items = []
        
        # rank 배열이 있는 경우 (일반 스캔 파일)
        if data.get("rank"):
            for item in data["rank"]:
                ticker = item.get("ticker")
                score_label = item.get("score_label", "")
                if ticker and score_label != "제외":
                    # 기본 정보
                    enhanced_item = {
                        "ticker": ticker,
                        "name": item.get("name", ""),
                        "score": item.get("score", 0),
                        "score_label": item.get("score_label", ""),
                        "match": True,
                    }
                    
                    # 시장 구분
                    market = "코스피" if ticker.startswith(("00", "01", "02", "03", "04", "05", "06", "07", "08", "09")) else "코스닥"
                    enhanced_item["market"] = market
                    
                    # 매매전략과 평가 항목
                    enhanced_item["strategy"] = "상승추세정착" if item.get("score", 0) >= 10 else "상승시작"
                    enhanced_item["evaluation"] = {"total_score": item.get("score", 0)}
                    
                    # 현재가, 변동률, 거래량 (스냅샷 데이터에서)
                    enhanced_item["current_price"] = item.get("close_price", 0)
                    enhanced_item["change_rate"] = item.get("change_rate", 0)
                    enhanced_item["volume"] = item.get("volume", 0)
                    
                    # 수익률 정보 계산 (과거 스캔 결과이므로)
                    scan_date_formatted = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                    returns_info = calculate_returns(ticker, scan_date_formatted)
                    if returns_info:
                        enhanced_item["returns"] = returns_info
                    else:
                        enhanced_item["returns"] = {
                            "current_return": 0,
                            "max_return": 0,
                            "min_return": 0,
                            "scan_price": 0,
                            "current_price": 0,
                            "max_price": 0,
                            "min_price": 0,
                            "days_elapsed": 0
                        }
                    
                    # 시장 관심도 (거래량 기반)
                    if item.get("volume", 0) > 1000000:
                        enhanced_item["market_interest"] = "높음"
                    elif item.get("volume", 0) > 500000:
                        enhanced_item["market_interest"] = "보통"
                    else:
                        enhanced_item["market_interest"] = "낮음"
                    
                    enhanced_items.append(enhanced_item)
        
        # items 배열이 있는 경우 (auto-scan 파일)
        elif data.get("items"):
            for item in data["items"]:
                ticker = item.get("ticker")
                if ticker:
                    # 기본 정보
                    enhanced_item = {
                        "ticker": ticker,
                        "name": item.get("name", ""),
                        "score": item.get("score", 0),
                        "score_label": item.get("score_label", ""),
                        "match": item.get("match", True),
                    }
                    
                    # 사용자 화면에 필요한 추가 정보 생성
                    # 시장 구분
                    market = "코스피" if ticker.startswith(("00", "01", "02", "03", "04", "05", "06", "07", "08", "09")) else "코스닥"
                    enhanced_item["market"] = market
                    
                    # 매매전략과 평가 항목
                    score = item.get("score", 0)
                    score_label = item.get("score_label", "관심")
                    
                    # 점수 기반으로 전략 설정
                    if score >= 10:
                        enhanced_item["strategy"] = "상승추세정착"
                    elif score >= 8:
                        enhanced_item["strategy"] = "상승시작"
                    elif score >= 6:
                        enhanced_item["strategy"] = "관심증가"
                    else:
                        enhanced_item["strategy"] = "관심"
                    
                    # 스냅샷 데이터 활용
                    enhanced_item["score_label"] = score_label
                    enhanced_item["evaluation"] = {
                        "total_score": score
                    }
                    
                    # auto-scan 파일에서 종가, 거래량, 변동률 가져오기
                    indicators = item.get("indicators", {})
                    details = item.get("details", {})
                    
                    enhanced_item["current_price"] = details.get("close", 0)  # details.close
                    enhanced_item["volume"] = indicators.get("VOL", 0)        # indicators.VOL
                    enhanced_item["change_rate"] = 0  # auto-scan에는 변동률이 없음
                    
                    # 수익률 정보 계산 (과거 스캔 결과이므로)
                    scan_date_formatted = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                    returns_info = calculate_returns(ticker, scan_date_formatted)
                    if returns_info:
                        enhanced_item["returns"] = returns_info
                    else:
                        enhanced_item["returns"] = {
                            "current_return": 0,
                            "max_return": 0,
                            "min_return": 0,
                            "scan_price": 0,
                            "current_price": 0,
                            "max_price": 0,
                            "min_price": 0,
                            "days_elapsed": 0
                        }
                    
                    # 거래금액 기반 시장 관심도 설정
                    volume = enhanced_item["volume"]
                    current_price = enhanced_item["current_price"]
                    trade_amount = volume * current_price  # 거래금액 (원)
                    
                    if trade_amount > 100000000000:  # 1,000억원 이상
                        enhanced_item["market_interest"] = "높음"
                    elif trade_amount > 50000000000:  # 500억원 이상
                        enhanced_item["market_interest"] = "보통"
                    else:
                        enhanced_item["market_interest"] = "낮음"
                    
                    enhanced_items.append(enhanced_item)
        
        # items 필드에 향상된 데이터 추가
        data["items"] = enhanced_items
        
        return {"ok": True, "data": data, "file": target_file}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/latest-scan")
async def get_latest_scan():
    """최신 스캔 결과를 가져옵니다."""
    try:
        # 스냅샷 파일들 중에서 가장 최신 파일 찾기
        snapshot_files = glob.glob("snapshots/scan-*.json")
        auto_scan_files = glob.glob("snapshots/auto-scan-*.json")
        
        all_files = snapshot_files + auto_scan_files
        
        if not all_files:
            return {"ok": False, "error": "스캔 결과가 없습니다."}
        
        # 파일명에서 날짜 추출하여 정렬
        latest_file = max(all_files, key=lambda x: x.split("-")[-1].replace(".json", ""))
        
        # 파일명에서 날짜 추출
        import re
        date_match = re.search(r'(\d{8})', latest_file)
        scan_date = date_match.group(1) if date_match else "알 수 없음"
        
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 스캔 날짜 정보 추가
        data["scan_date"] = scan_date
        data["is_latest"] = True
        
        # 사용자 화면에 필요한 정보 추가
        enhanced_items = []
        
        # rank 배열이 있는 경우 (일반 스캔 파일)
        if data.get("rank"):
            for item in data["rank"]:
                ticker = item.get("ticker")
                score_label = item.get("score_label", "")
                if ticker and score_label != "제외":
                    # 기본 정보
                    enhanced_item = {
                        "ticker": ticker,
                        "name": item.get("name", ""),
                        "score": item.get("score", 0),
                        "score_label": item.get("score_label", ""),
                        "match": True,  # rank에 있는 것은 모두 매칭된 것
                    }
                    
                    # 사용자 화면에 필요한 추가 정보 생성
                    # 시장 구분
                    market = "코스피" if ticker.startswith(("00", "01", "02", "03", "04", "05", "06", "07", "08", "09")) else "코스닥"
                    enhanced_item["market"] = market
                    
                    # 매매전략과 평가 항목 (스냅샷 데이터 기반, 성능 최적화)
                    score = item.get("score", 0)
                    score_label = item.get("score_label", "관심")
                    
                    # 점수 기반으로 전략 설정 (API 호출 없음)
                    if score >= 10:
                        enhanced_item["strategy"] = "상승추세정착"
                    elif score >= 8:
                        enhanced_item["strategy"] = "상승시작"
                    elif score >= 6:
                        enhanced_item["strategy"] = "관심증가"
                    else:
                        enhanced_item["strategy"] = "관심"
                    
                    # 스냅샷 데이터 활용
                    enhanced_item["score_label"] = score_label
                    enhanced_item["evaluation"] = {
                        "total_score": score
                    }
                    
                    # 스냅샷에서 종가, 거래량, 변동률 가져오기
                    enhanced_item["current_price"] = item.get("close_price", 0)  # 스냅샷의 종가
                    enhanced_item["change_rate"] = item.get("change_rate", 0)    # 스냅샷의 변동률
                    enhanced_item["volume"] = item.get("volume", 0)             # 스냅샷의 거래량
                    
                    # 거래금액 기반 시장 관심도 설정
                    volume = enhanced_item["volume"]
                    current_price = enhanced_item["current_price"]
                    trade_amount = volume * current_price  # 거래금액 (원)
                    
                    if trade_amount > 100000000000:  # 1,000억원 이상
                        enhanced_item["market_interest"] = "높음"
                    elif trade_amount > 50000000000:  # 500억원 이상
                        enhanced_item["market_interest"] = "보통"
                    else:
                        enhanced_item["market_interest"] = "낮음"
                    
                    enhanced_items.append(enhanced_item)
        
        # items 배열이 있는 경우 (auto-scan 파일)
        elif data.get("items"):
            for item in data["items"]:
                ticker = item.get("ticker")
                if ticker:
                    # 기본 정보
                    enhanced_item = {
                        "ticker": ticker,
                        "name": item.get("name", ""),
                        "score": item.get("score", 0),
                        "score_label": item.get("score_label", ""),
                        "match": item.get("match", True),
                    }
                    
                    # 사용자 화면에 필요한 추가 정보 생성
                    # 시장 구분
                    market = "코스피" if ticker.startswith(("00", "01", "02", "03", "04", "05", "06", "07", "08", "09")) else "코스닥"
                    enhanced_item["market"] = market
                    
                    # 매매전략과 평가 항목
                    score = item.get("score", 0)
                    score_label = item.get("score_label", "관심")
                    
                    # 점수 기반으로 전략 설정
                    if score >= 10:
                        enhanced_item["strategy"] = "상승추세정착"
                    elif score >= 8:
                        enhanced_item["strategy"] = "상승시작"
                    elif score >= 6:
                        enhanced_item["strategy"] = "관심증가"
                    else:
                        enhanced_item["strategy"] = "관심"
                    
                    # 스냅샷 데이터 활용
                    enhanced_item["score_label"] = score_label
                    enhanced_item["evaluation"] = {
                        "total_score": score
                    }
                    
                    # auto-scan 파일에서 종가, 거래량, 변동률 가져오기
                    indicators = item.get("indicators", {})
                    details = item.get("details", {})
                    
                    enhanced_item["current_price"] = details.get("close", 0)  # details.close
                    enhanced_item["volume"] = indicators.get("VOL", 0)        # indicators.VOL
                    enhanced_item["change_rate"] = 0  # auto-scan에는 변동률이 없음
                    
                    # 수익률 정보 계산 (과거 스캔 결과이므로)
                    scan_date_formatted = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                    returns_info = calculate_returns(ticker, scan_date_formatted)
                    if returns_info:
                        enhanced_item["returns"] = returns_info
                    else:
                        enhanced_item["returns"] = {
                            "current_return": 0,
                            "max_return": 0,
                            "min_return": 0,
                            "scan_price": 0,
                            "current_price": 0,
                            "max_price": 0,
                            "min_price": 0,
                            "days_elapsed": 0
                        }
                    
                    # 거래금액 기반 시장 관심도 설정
                    volume = enhanced_item["volume"]
                    current_price = enhanced_item["current_price"]
                    trade_amount = volume * current_price  # 거래금액 (원)
                    
                    if trade_amount > 100000000000:  # 1,000억원 이상
                        enhanced_item["market_interest"] = "높음"
                    elif trade_amount > 50000000000:  # 500억원 이상
                        enhanced_item["market_interest"] = "보통"
                    else:
                        enhanced_item["market_interest"] = "낮음"
                    
                    enhanced_items.append(enhanced_item)
        
        # items 필드에 향상된 데이터 추가
        data["items"] = enhanced_items
        
        return {"ok": True, "data": data, "file": latest_file}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==================== 인증 관련 엔드포인트 ====================

# JWT 토큰 검증을 위한 의존성
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """현재 로그인한 사용자 정보 가져오기"""
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 유효하지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = auth_service.get_user_by_email(token_data.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

@app.post("/auth/social-login", response_model=Token)
async def social_login(request: SocialLoginRequest):
    """소셜 로그인 (카카오, 네이버, 토스)"""
    try:
        # 소셜 로그인 토큰 검증
        social_user_info = await social_auth_service.verify_social_token(
            request.provider, request.access_token
        )
        
        if not social_user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="소셜 로그인 토큰이 유효하지 않습니다"
            )
        
        # 사용자 생성 또는 조회
        user_create = social_auth_service.create_user_from_social(social_user_info)
        user = auth_service.create_user(user_create)
        
        # 마지막 로그인 시간 업데이트
        auth_service.update_last_login(user.id)
        
        # JWT 토큰 생성
        access_token_expires = timedelta(minutes=30)
        access_token = auth_service.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그인 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 조회"""
    return current_user

@app.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """로그아웃 (클라이언트에서 토큰 삭제)"""
    return {"message": "로그아웃되었습니다"}

@app.get("/auth/check")
async def check_auth(current_user: User = Depends(get_current_user)):
    """인증 상태 확인"""
    return {
        "authenticated": True,
        "user": current_user
    }

# ===== 이메일 가입/로그인 API =====

@app.post("/auth/email/signup")
async def email_signup(request: EmailSignupRequest):
    """이메일 회원가입"""
    try:
        # 사용자 생성
        success = auth_service.create_email_user(request)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 이메일입니다"
            )
        
        # 인증 이메일 발송
        email_sent = auth_service.send_verification_email(request.email)
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="인증 이메일 발송에 실패했습니다"
            )
        
        return {"message": "회원가입이 완료되었습니다. 이메일을 확인하여 인증을 완료해주세요."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원가입 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/auth/email/verify")
async def verify_email(request: EmailVerificationRequest):
    """이메일 인증"""
    try:
        success = auth_service.verify_email_code(request.email, request.verification_code)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="인증 코드가 올바르지 않거나 만료되었습니다"
            )
        
        return {"message": "이메일 인증이 완료되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이메일 인증 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/auth/email/login", response_model=Token)
async def email_login(request: EmailLoginRequest):
    """이메일 로그인"""
    try:
        user = auth_service.verify_email_user(request.email, request.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다"
            )
        
        # JWT 토큰 생성
        access_token_expires = timedelta(minutes=30)
        access_token = auth_service.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # 마지막 로그인 시간 업데이트
        auth_service.update_last_login(user.id)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그인 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/auth/email/resend-verification")
async def resend_verification_email(request: PasswordResetRequest):
    """인증 이메일 재발송"""
    try:
        success = auth_service.send_verification_email(request.email)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="인증 이메일 발송에 실패했습니다"
            )
        
        return {"message": "인증 이메일이 재발송되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이메일 재발송 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/auth/email/password-reset")
async def request_password_reset(request: PasswordResetRequest):
    """비밀번호 재설정 요청"""
    try:
        success = auth_service.send_password_reset_email(request.email)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="등록되지 않은 이메일이거나 이메일 발송에 실패했습니다"
            )
        
        return {"message": "비밀번호 재설정 이메일이 발송되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"비밀번호 재설정 요청 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/auth/email/password-reset/confirm")
async def confirm_password_reset(request: PasswordResetConfirmRequest):
    """비밀번호 재설정 확인"""
    try:
        success = auth_service.reset_password(request.email, request.verification_code, request.new_password)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="인증 코드가 올바르지 않거나 만료되었습니다"
            )
        
        return {"message": "비밀번호가 성공적으로 재설정되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"비밀번호 재설정 중 오류가 발생했습니다: {str(e)}"
        )


@app.post("/auth/kakao/callback", response_model=Token)
async def kakao_callback(request: dict):
    """카카오 OAuth 콜백 처리"""
    try:
        print(f"카카오 콜백 요청: {request}")
        code = request.get("code")
        redirect_uri = request.get("redirect_uri")
        
        if not code:
            print("인증 코드가 없습니다")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="인증 코드가 없습니다"
            )
        
        # 카카오에서 액세스 토큰 요청
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": "4eb579e52709ea64e8b941b9c95d20da",
                    "redirect_uri": redirect_uri,
                    "code": code
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            print(f"카카오 토큰 응답 상태: {token_response.status_code}")
            print(f"카카오 토큰 응답 내용: {token_response.text}")
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="카카오 토큰 요청에 실패했습니다"
                )
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="카카오 액세스 토큰을 받지 못했습니다"
                )
            
            # 카카오에서 사용자 정보 요청
            user_response = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            print(f"카카오 사용자 정보 응답 상태: {user_response.status_code}")
            print(f"카카오 사용자 정보 응답 내용: {user_response.text}")
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="카카오 사용자 정보 요청에 실패했습니다"
                )
            
            user_data = user_response.json()
            kakao_account = user_data.get("kakao_account", {})
            profile = kakao_account.get("profile", {})
            
            # 사용자 정보 구성
            social_user_info = {
                "provider": "kakao",
                "provider_id": str(user_data.get("id")),
                "email": kakao_account.get("email", ""),
                "name": profile.get("nickname", ""),
                "profile_image": profile.get("profile_image_url", ""),
                "phone_number": kakao_account.get("phone_number", ""),
                "gender": kakao_account.get("gender", ""),
                "age_range": kakao_account.get("age_range", ""),
                "birthday": kakao_account.get("birthday", "")
            }
            
            print(f"사용자 정보 구성: {social_user_info}")
            
            # 사용자 생성 또는 조회
            try:
                user_create = social_auth_service.create_user_from_social(social_user_info)
                print(f"사용자 생성 요청: {user_create}")
                user = auth_service.create_user(user_create)
                print(f"사용자 생성 완료: {user}")
                
                # 마지막 로그인 시간 업데이트
                auth_service.update_last_login(user.id)
                print("마지막 로그인 시간 업데이트 완료")
            except Exception as e:
                print(f"사용자 생성 오류: {e}")
                raise
            
            # JWT 토큰 생성
            access_token_expires = timedelta(minutes=30)
            jwt_token = auth_service.create_access_token(
                data={"sub": user.email}, expires_delta=access_token_expires
            )
            
            return {
                "access_token": jwt_token,
                "token_type": "bearer",
                "user": user
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"카카오 로그인 처리 중 오류가 발생했습니다: {str(e)}"
        )


# ===== 포트폴리오 API =====

@app.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """포트폴리오 조회"""
    try:
        portfolio = portfolio_service.get_portfolio(current_user.id, status)
        return portfolio
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 조회 중 오류가 발생했습니다: {str(e)}"
        )


@app.post("/portfolio/add", response_model=PortfolioItem)
async def add_to_portfolio(
    request: AddToPortfolioRequest,
    current_user: User = Depends(get_current_user)
):
    """포트폴리오에 종목 추가"""
    try:
        portfolio_item = portfolio_service.add_to_portfolio(current_user.id, request)
        return portfolio_item
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 추가 중 오류가 발생했습니다: {str(e)}"
        )


@app.put("/portfolio/{ticker}", response_model=PortfolioItem)
async def update_portfolio(
    ticker: str,
    request: UpdatePortfolioRequest,
    current_user: User = Depends(get_current_user)
):
    """포트폴리오 항목 업데이트"""
    try:
        portfolio_item = portfolio_service.update_portfolio(current_user.id, ticker, request)
        if not portfolio_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포트폴리오에서 해당 종목을 찾을 수 없습니다"
            )
        return portfolio_item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 업데이트 중 오류가 발생했습니다: {str(e)}"
        )


@app.delete("/portfolio/{ticker}")
async def remove_from_portfolio(
    ticker: str,
    current_user: User = Depends(get_current_user)
):
    """포트폴리오에서 종목 제거"""
    try:
        success = portfolio_service.remove_from_portfolio(current_user.id, ticker)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포트폴리오에서 해당 종목을 찾을 수 없습니다"
            )
        return {"message": "포트폴리오에서 종목이 제거되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 제거 중 오류가 발생했습니다: {str(e)}"
        )


@app.get("/portfolio/summary")
async def get_portfolio_summary(current_user: User = Depends(get_current_user)):
    """포트폴리오 요약 정보"""
    try:
        portfolio = portfolio_service.get_portfolio(current_user.id)
        
        # 상태별 통계
        watching_count = len([item for item in portfolio.items if item.status == "watching"])
        holding_count = len([item for item in portfolio.items if item.status == "holding"])
        sold_count = len([item for item in portfolio.items if item.status == "sold"])
        
        # 수익률별 통계
        profitable_count = len([item for item in portfolio.items if item.profit_loss_pct and item.profit_loss_pct > 0])
        loss_count = len([item for item in portfolio.items if item.profit_loss_pct and item.profit_loss_pct < 0])
        
        return {
            "total_items": len(portfolio.items),
            "watching_count": watching_count,
            "holding_count": holding_count,
            "sold_count": sold_count,
            "profitable_count": profitable_count,
            "loss_count": loss_count,
            "total_investment": portfolio.total_investment,
            "total_current_value": portfolio.total_current_value,
            "total_profit_loss": portfolio.total_profit_loss,
            "total_profit_loss_pct": portfolio.total_profit_loss_pct
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 요약 조회 중 오류가 발생했습니다: {str(e)}"
        )


# ==================== 구독 및 결제 API ====================

@app.get("/subscription/plans")
async def get_subscription_plans():
    """구독 플랜 목록 조회"""
    try:
        plans = get_all_plans()
        return {"plans": [plan.dict() for plan in plans]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"구독 플랜 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/subscription/status")
async def get_subscription_status(current_user: User = Depends(get_current_user)):
    """사용자 구독 상태 조회"""
    try:
        status = subscription_service.check_subscription_status(current_user.id)
        permissions = subscription_service.get_user_permissions(current_user.id)
        
        return {
            "subscription": status,
            "permissions": permissions
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"구독 상태 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/payment/create")
async def create_payment(
    request: PaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """결제 생성"""
    try:
        # 플랜 확인
        plan = get_plan(request.plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="존재하지 않는 플랜입니다"
            )
        
        # 카카오페이 결제 생성
        payment_response = await kakao_pay_service.create_payment(
            user_id=current_user.id,
            plan_id=request.plan_id,
            return_url=request.return_url,
            cancel_url=request.cancel_url,
            fail_url=request.cancel_url  # 실패 시에도 취소 URL로
        )
        
        if not payment_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="결제 생성에 실패했습니다"
            )
        
        return payment_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"결제 생성 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/payment/approve")
async def approve_payment(
    payment_id: str,
    pg_token: str,
    plan_id: str,
    current_user: User = Depends(get_current_user)
):
    """결제 승인"""
    try:
        # 카카오페이 결제 승인
        approval_data = await kakao_pay_service.approve_payment(
            payment_id=payment_id,
            pg_token=pg_token,
            user_id=current_user.id,
            plan_id=plan_id
        )
        
        if not approval_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="결제 승인에 실패했습니다"
            )
        
        # 구독 생성
        success = subscription_service.create_subscription(
            user_id=current_user.id,
            plan_id=plan_id,
            payment_id=payment_id,
            amount=approval_data["amount"],
            expires_at=approval_data["expires_at"]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="구독 생성에 실패했습니다"
            )
        
        return {
            "message": "결제가 완료되었습니다",
            "subscription": subscription_service.get_user_subscription(current_user.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"결제 승인 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/subscription/cancel")
async def cancel_subscription(current_user: User = Depends(get_current_user)):
    """구독 취소"""
    try:
        success = subscription_service.cancel_subscription(current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="구독 취소에 실패했습니다"
            )
        
        return {"message": "구독이 취소되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"구독 취소 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/subscription/history")
async def get_subscription_history(current_user: User = Depends(get_current_user)):
    """구독 내역 조회"""
    try:
        # 실제로는 데이터베이스에서 구독 내역을 조회해야 함
        subscription = subscription_service.get_user_subscription(current_user.id)
        
        return {
            "current_subscription": subscription,
            "history": []  # TODO: 구독 내역 테이블에서 조회
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"구독 내역 조회 중 오류가 발생했습니다: {str(e)}"
        )


# ==================== 관리자 API ====================

def get_admin_user(current_user: User = Depends(get_current_user)):
    """관리자 권한 확인"""
    if not admin_service.is_admin(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    return current_user

@app.get("/admin/stats")
async def get_admin_stats(admin_user: User = Depends(get_admin_user)):
    """관리자 통계 조회"""
    try:
        stats = admin_service.get_admin_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"관리자 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/admin/users")
async def get_all_users(
    limit: int = 100,
    offset: int = 0,
    admin_user: User = Depends(get_admin_user)
):
    """모든 사용자 조회"""
    try:
        users = admin_service.get_all_users(limit, offset)
        return {"users": users, "total": len(users)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/admin/users/{user_id}")
async def get_user_by_id(
    user_id: int,
    admin_user: User = Depends(get_admin_user)
):
    """특정 사용자 조회"""
    try:
        user = admin_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.put("/admin/users/{user_id}")
async def update_user(
    user_id: int,
    request: AdminUserUpdateRequest,
    admin_user: User = Depends(get_admin_user)
):
    """사용자 정보 업데이트"""
    try:
        # 요청 데이터 구성
        updates = {}
        if request.membership_tier is not None:
            updates["membership_tier"] = request.membership_tier.value
        if request.subscription_status is not None:
            updates["subscription_status"] = request.subscription_status.value
        if request.subscription_expires_at is not None:
            updates["subscription_expires_at"] = request.subscription_expires_at.isoformat()
        if request.is_admin is not None:
            updates["is_admin"] = request.is_admin
        
        success = admin_service.update_user(user_id, updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="사용자 정보 업데이트에 실패했습니다"
            )
        
        # 업데이트된 사용자 정보 반환
        updated_user = admin_service.get_user_by_id(user_id)
        return {"message": "사용자 정보가 업데이트되었습니다", "user": updated_user}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 정보 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    request: AdminUserDeleteRequest,
    admin_user: User = Depends(get_admin_user)
):
    """사용자 삭제"""
    try:
        if not request.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="사용자 삭제를 확인해주세요"
            )
        
        # 자기 자신 삭제 방지
        if user_id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="자기 자신을 삭제할 수 없습니다"
            )
        
        success = admin_service.delete_user(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="사용자 삭제에 실패했습니다"
            )
        
        return {"message": "사용자가 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 삭제 중 오류가 발생했습니다: {str(e)}"
        )
