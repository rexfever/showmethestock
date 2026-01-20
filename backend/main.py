from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import os
import json
import sqlite3
from typing import List, Optional, Dict
import pandas as pd
import asyncio
import glob
import httpx
import threading
from contextlib import asynccontextmanager

try:
    from . import db_patch  # type: ignore  # noqa: F401
except ImportError:
    import db_patch  # type: ignore  # noqa: F401

from config import config, reload_from_env
from environment import get_environment_info
from kiwoom_api import KiwoomAPI
from scanner import compute_indicators, match_condition, match_stats, strategy_text, score_conditions
from market_analyzer import market_analyzer
from services.us_stocks_universe import us_stocks_universe
from services.us_stocks_data import us_stocks_data
from scanner_v2.us_scanner import USScanner
from scanner_v2.config_v2 import ScannerV2Config
from models import ScanResponse, ScanItem, IndicatorPayload, TrendPayload, AnalyzeResponse, UniverseResponse, UniverseItem, ScoreFlags, PositionResponse, PositionItem, AddPositionRequest, UpdatePositionRequest, PortfolioResponse, PortfolioItem, AddToPortfolioRequest, UpdatePortfolioRequest, MaintenanceSettingsRequest, TradingHistory, AddTradingRequest, TradingHistoryResponse
from utils import is_code, normalize_code_or_name
from date_helper import normalize_date, get_kst_now
from db_manager import db_manager
from security_utils import sanitize_file_path, escape_html
from kakao import send_alert, format_scan_message, format_scan_alert_message

# 공통 함수: scan_rank 테이블 생성
def create_scan_rank_table(cur):
    """scan_rank 테이블을 최신 스키마로 생성 (실제 DB 스키마와 일치: DATE 타입 사용)"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scan_rank(
            date DATE NOT NULL, 
            code TEXT NOT NULL, 
            name TEXT, 
            score REAL, 
            score_label TEXT,
            current_price REAL,
            volume INTEGER,
            change_rate REAL,
            market TEXT,
            strategy TEXT,
            indicators TEXT,
            trend TEXT,
            flags TEXT,
            details TEXT,
            returns TEXT,
            recurrence TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            close_price REAL,
            scanner_version TEXT NOT NULL DEFAULT 'v1',
            PRIMARY KEY(date, code, scanner_version)
        )
    """)

# 공통 함수: market_conditions 테이블 생성
def create_market_conditions_table(cur):
    """market_conditions 테이블 생성 (시장 상황 분석 결과 저장)"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_conditions(
            date TEXT NOT NULL PRIMARY KEY,
            market_sentiment TEXT NOT NULL,
            sentiment_score NUMERIC(5,2) DEFAULT 0,
            kospi_return REAL,
            volatility REAL,
            rsi_threshold REAL,
            sector_rotation TEXT,
            foreign_flow TEXT,
            volume_trend TEXT,
            min_signals INTEGER,
            macd_osc_min REAL,
            vol_ma5_mult REAL,
            gap_max REAL,
            ext_from_tema20_max REAL,
            trend_metrics JSONB DEFAULT '{}'::JSONB,
            breadth_metrics JSONB DEFAULT '{}'::JSONB,
            flow_metrics JSONB DEFAULT '{}'::JSONB,
            sector_metrics JSONB DEFAULT '{}'::JSONB,
            volatility_metrics JSONB DEFAULT '{}'::JSONB,
            foreign_flow_label TEXT,
            volume_trend_label TEXT,
            adjusted_params JSONB DEFAULT '{}'::JSONB,
            analysis_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

# 공통 함수: maintenance_settings 테이블 생성
def create_maintenance_settings_table(cur):
    """maintenance_settings 테이블 생성"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_settings(
            id SERIAL PRIMARY KEY,
            is_enabled BOOLEAN DEFAULT FALSE,
            end_date TIMESTAMP WITH TIME ZONE,
            message TEXT DEFAULT '서비스 점검 중입니다.',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    cur.execute("SELECT COUNT(*) FROM maintenance_settings")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO maintenance_settings (is_enabled, end_date, message)
            VALUES (FALSE, NULL, '서비스 점검 중입니다.')
        """)

def create_popup_notice_table(cur):
    """popup_notice 테이블 생성 (실제 DB 스키마와 일치)"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS popup_notice(
            id BIGSERIAL PRIMARY KEY,
            is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            start_date TIMESTAMP WITH TIME ZONE NOT NULL,
            end_date TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)

# 서비스 모듈 import
from services.returns_service import calculate_returns, calculate_returns_batch, clear_cache
from services.enhanced_report_generator import EnhancedReportGenerator
from services.scan_service import get_recurrence_data, save_scan_snapshot, execute_scan_with_fallback
from services.access_log_service import init_access_logs_table, log_access

# 향상된 보고서 생성기 인스턴스
report_generator = EnhancedReportGenerator()

from new_recurrence_api import router as recurrence_router
from market_guide import get_market_guide, get_detailed_stock_advice

# 인증 관련 import
from auth_models import User, Token, SocialLoginRequest, EmailSignupRequest, EmailLoginRequest, EmailVerificationRequest, PasswordResetRequest, PasswordResetConfirmRequest, PaymentRequest, PaymentResponse, AdminUserUpdateRequest, AdminUserDeleteRequest, AdminStatsResponse, MaintenanceSettingsRequest, PopupNoticeRequest
from auth_service import auth_service
from social_auth import social_auth_service
from subscription_service import subscription_service
from parameter_store import parameter_store
from payment_service import kakao_pay_service
from subscription_plans import get_all_plans, get_plan
from admin_service import admin_service

# 포트폴리오 관련 import
from portfolio_service import portfolio_service


# 스케줄러 백그라운드 스레드
scheduler_thread = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 앱 생명주기 관리"""
    # 시작 시
    global scheduler_thread
    from scheduler import run_scheduler
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 FastAPI 앱 시작 - 스케줄러 초기화 중...")
    
    # 접속 기록 테이블 초기화
    try:
        init_access_logs_table()
        logger.info("✅ 접속 기록 테이블 초기화 완료")
    except Exception as e:
        logger.warning(f"⚠️ 접속 기록 테이블 초기화 실패: {e}")
    
    # 스케줄러를 백그라운드 스레드로 실행
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("✅ 스케줄러 백그라운드 스레드 시작 완료")
    
    yield
    
    # 종료 시
    logger.info("🛑 FastAPI 앱 종료 중...")

app = FastAPI(title='Stock Scanner API', lifespan=lifespan)

# CORS 설정 (환경별 동적 설정)
def get_cors_origins():
    """환경에 따른 CORS origins 설정"""
    env_info = get_environment_info()
    if env_info['is_local']:
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",  # 추가 포트 지원
        ]
    else:
        return [
            "https://sohntech.ai.kr",
            "https://www.sohntech.ai.kr",
        ]

# 접속 기록 미들웨어
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time

class AccessLogMiddleware(BaseHTTPMiddleware):
    """접속 기록 미들웨어"""
    
    async def dispatch(self, request: Request, call_next):
        # 요청 시작 시간
        start_time = time.time()
        
        # IP 주소 가져오기
        ip_address = request.client.host if request.client else None
        if request.headers.get("x-forwarded-for"):
            # 프록시를 통한 경우 실제 IP 주소
            ip_address = request.headers.get("x-forwarded-for").split(",")[0].strip()
        
        # User-Agent
        user_agent = request.headers.get("user-agent", "")
        
        # 요청 경로 및 메서드
        request_path = request.url.path
        request_method = request.method
        
        # 사용자 정보 (토큰에서 추출)
        user_id = None
        email = None
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                from auth_service import auth_service
                token_data = auth_service.verify_token(token)
                if token_data:
                    user = auth_service.get_user_by_id(token_data.user_id)
                    if user:
                        user_id = user.id
                        email = user.email
        except Exception:
            # 인증 실패는 무시 (비로그인 사용자)
            pass
        
        # 요청 처리
        response = await call_next(request)
        
        # 응답 시간 계산
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # 상태 코드
        status_code = response.status_code
        
        # 접속 기록 저장 (비동기로 처리하여 응답 지연 최소화)
        # 정적 파일이나 헬스 체크는 제외
        if not request_path.startswith(("/static/", "/_next/", "/favicon.ico", "/health")):
            try:
                log_access(
                    user_id=user_id,
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_path=request_path,
                    request_method=request_method,
                    status_code=status_code,
                    response_time_ms=response_time_ms
                )
            except Exception as e:
                # 접속 기록 실패는 로그만 남기고 요청 처리는 계속
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"접속 기록 저장 실패: {e}")
        
        return response

# CORS 미들웨어 추가 (AccessLogMiddleware보다 먼저 실행되도록)
# FastAPI는 add_middleware를 역순으로 실행하므로, CORS를 나중에 추가해야 먼저 실행됨
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 접속 기록 미들웨어 (CORS 이후에 추가하여 CORS가 먼저 실행되도록)
app.add_middleware(AccessLogMiddleware)

api = KiwoomAPI()


@app.get('/')
def root():
    return {'status': 'running'}


@app.get('/health')
def health():
    """헬스 체크 엔드포인트"""
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}


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


# 수익률 계산 함수들은 services/returns_service.py로 이동됨


def _save_scan_snapshot(payload: dict) -> str:
    try:
        as_of = payload.get('as_of') or datetime.now().strftime('%Y%m%d')
        fname = f"scan-{as_of}.json"
        safe_path = sanitize_file_path(fname, SNAPSHOT_DIR)
        if not safe_path:
            return ''
        with open(safe_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False)
        return safe_path
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

def _save_snapshot_db(as_of: str, items: List[ScanItem], market_condition=None):
    try:
        print(f"💾 데이터베이스 저장 시작: {as_of}, {len(items)}개 항목")
        
        # 시장 상황 저장 (market_condition이 제공된 경우)
        if market_condition:
            try:
                with db_manager.get_cursor() as cur:
                    create_market_conditions_table(cur)
                    cur.execute("""
                        INSERT INTO market_conditions(
                            date, market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                            sector_rotation, foreign_flow, institution_flow, volume_trend,
                            min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                            trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                            foreign_flow_label, institution_flow_label, volume_trend_label, adjusted_params, analysis_notes
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (date) DO UPDATE SET
                            market_sentiment = EXCLUDED.market_sentiment,
                            sentiment_score = EXCLUDED.sentiment_score,
                            kospi_return = EXCLUDED.kospi_return,
                            volatility = EXCLUDED.volatility,
                            rsi_threshold = EXCLUDED.rsi_threshold,
                            sector_rotation = EXCLUDED.sector_rotation,
                            foreign_flow = EXCLUDED.foreign_flow,
                            institution_flow = EXCLUDED.institution_flow,
                            volume_trend = EXCLUDED.volume_trend,
                            min_signals = EXCLUDED.min_signals,
                            macd_osc_min = EXCLUDED.macd_osc_min,
                            vol_ma5_mult = EXCLUDED.vol_ma5_mult,
                            gap_max = EXCLUDED.gap_max,
                            ext_from_tema20_max = EXCLUDED.ext_from_tema20_max,
                            trend_metrics = EXCLUDED.trend_metrics,
                            breadth_metrics = EXCLUDED.breadth_metrics,
                            flow_metrics = EXCLUDED.flow_metrics,
                            sector_metrics = EXCLUDED.sector_metrics,
                            volatility_metrics = EXCLUDED.volatility_metrics,
                            foreign_flow_label = EXCLUDED.foreign_flow_label,
                            institution_flow_label = EXCLUDED.institution_flow_label,
                            volume_trend_label = EXCLUDED.volume_trend_label,
                            adjusted_params = EXCLUDED.adjusted_params,
                            analysis_notes = EXCLUDED.analysis_notes,
                            updated_at = NOW()
                    """, (
                        as_of,
                        market_condition.market_sentiment,
                        market_condition.sentiment_score,
                        market_condition.kospi_return,
                        market_condition.volatility,
                        market_condition.rsi_threshold,
                        market_condition.sector_rotation,
                        market_condition.foreign_flow,
                        market_condition.institution_flow,
                        market_condition.volume_trend,
                        market_condition.min_signals,
                        market_condition.macd_osc_min,
                        market_condition.vol_ma5_mult,
                        market_condition.gap_max,
                        market_condition.ext_from_tema20_max,
                        json.dumps(market_condition.trend_metrics) if market_condition.trend_metrics else None,
                        json.dumps(market_condition.breadth_metrics) if market_condition.breadth_metrics else None,
                        json.dumps(market_condition.flow_metrics) if market_condition.flow_metrics else None,
                        json.dumps(market_condition.sector_metrics) if market_condition.sector_metrics else None,
                        json.dumps(market_condition.volatility_metrics) if market_condition.volatility_metrics else None,
                        market_condition.foreign_flow_label,
                        market_condition.institution_flow_label,
                        market_condition.volume_trend_label,
                        json.dumps(market_condition.adjusted_params) if market_condition.adjusted_params else None,
                        market_condition.analysis_notes
                    ))
                print(f"✅ 시장 상황 저장 완료: {as_of} ({market_condition.market_sentiment})")
            except Exception as e:
                print(f"⚠️ 시장 상황 저장 실패: {e}")
        
        # 스캔 결과가 0개인 경우 NORESULT 레코드 추가
        if not items:
            print(f"📭 스캔 결과 0개 - NORESULT 레코드 저장: {as_of}")
            with db_manager.get_cursor() as cur:
                create_scan_rank_table(cur)
                # scanner_version을 확인하여 해당 버전만 삭제 (기본값: v1)
                try:
                    from scanner_settings_manager import get_scanner_version
                    scanner_version = get_scanner_version()
                except Exception:
                    from config import config
                    scanner_version = getattr(config, 'scanner_version', 'v1')
                cur.execute("DELETE FROM scan_rank WHERE date = %s AND scanner_version = %s", (as_of, scanner_version))
                cur.execute("""
                    INSERT INTO scan_rank(
                        date, code, name, score, score_label, current_price, volume, change_rate, 
                        market, strategy, indicators, trend, flags, details, returns, recurrence, close_price
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    as_of, "NORESULT", "추천종목 없음", 0.0, "추천종목 없음",
                    0.0, 0, 0.0, "", "",
                    json.dumps({}, ensure_ascii=False),
                    json.dumps({}, ensure_ascii=False),
                    json.dumps({"no_result": True}, ensure_ascii=False),
                    json.dumps({}, ensure_ascii=False),
                    json.dumps({}, ensure_ascii=False),
                    json.dumps({}, ensure_ascii=False),
                    0.0
                ))
            print(f"✅ NORESULT 저장 완료: {as_of}")
            return
        
        rows = []
        for it in items:
            # 각 필드를 indicators에서 일관되게 사용
            name = getattr(it, 'name', '') or ''
            current_price = float(getattr(it.indicators, 'close', 0) or 0.0)
            close_price = current_price  # 종가는 현재가와 동일
            volume = int(getattr(it.indicators, 'VOL', 0) or 0)
            change_rate = float(getattr(it.indicators, 'change_rate', 0.0) or 0.0)
            market = getattr(it, 'market', '') or ''
            strategy = getattr(it, 'strategy', '') or ''

            # JSON 필드들
            indicators_json = json.dumps(it.indicators.__dict__ if hasattr(it.indicators, '__dict__') else {}, ensure_ascii=False)
            trend_json = json.dumps(it.trend.__dict__ if hasattr(it.trend, '__dict__') else {}, ensure_ascii=False)
            flags_json = json.dumps(it.flags.__dict__ if hasattr(it.flags, '__dict__') else {}, ensure_ascii=False)
            details_json = json.dumps({}, ensure_ascii=False)  # 기본값
            returns_json = json.dumps({}, ensure_ascii=False)  # 기본값
            recurrence_json = json.dumps({}, ensure_ascii=False)  # 기본값
            
            rows.append((
                as_of, it.ticker, name, float(it.score), it.score_label or '', 
                current_price, volume, change_rate, market, strategy,
                indicators_json, trend_json, flags_json, details_json, 
                returns_json, recurrence_json, close_price
            ))
        
        if rows:
            with db_manager.get_cursor() as cur:
                # 테이블 생성 (없으면)
                create_scan_rank_table(cur)
                # scanner_version을 확인하여 해당 버전만 삭제 (기본값: v1)
                try:
                    from scanner_settings_manager import get_scanner_version
                    scanner_version = get_scanner_version()
                except Exception:
                    from config import config
                    scanner_version = getattr(config, 'scanner_version', 'v1')
                cur.execute("DELETE FROM scan_rank WHERE date = %s AND scanner_version = %s", (as_of, scanner_version))
                cur.executemany("""
                    INSERT INTO scan_rank(
                        date, code, name, score, score_label, current_price, volume, change_rate, 
                        market, strategy, indicators, trend, flags, details, returns, recurrence, close_price
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, rows)
        
        print(f"✅ 데이터베이스 저장 완료: {as_of}")
    except Exception as e:
        print(f"❌ 데이터베이스 저장 오류: {e}")
        import traceback
        traceback.print_exc()

def _log_send(to: str, matched_count: int):
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS send_logs(
                    id SERIAL PRIMARY KEY,
                    ts TIMESTAMP NOT NULL DEFAULT NOW(),
                    to_no TEXT,
                    matched_count INTEGER
                )
            """)
            cur.execute(
                "INSERT INTO send_logs(ts, to_no, matched_count) VALUES (NOW(), %s, %s)",
                (to, int(matched_count)),
            )
    except Exception:
        pass

def _init_positions_table():
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS positions(
                    id SERIAL PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    entry_date DATE NOT NULL,
                    quantity INTEGER NOT NULL,
                    score INTEGER,
                    strategy TEXT,
                    current_return_pct DOUBLE PRECISION,
                    max_return_pct DOUBLE PRECISION,
                    exit_date DATE,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
    except Exception:
        pass


def is_trading_day(check_date: str = None):
    """거래일인지 확인 (주말과 공휴일 제외)"""
    import pytz
    import holidays
    
    if check_date:
        # 지정된 날짜 확인
        try:
            if len(check_date) == 8 and check_date.isdigit():  # YYYYMMDD 형식
                date_str = f"{check_date[:4]}-{check_date[4:6]}-{check_date[6:8]}"
            elif len(check_date) == 10 and check_date.count('-') == 2:  # YYYY-MM-DD 형식
                date_str = check_date
            else:
                return False
            
            check_dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception as e:
            print(f"거래일 체크 오류: {check_date}, {e}")
            return False
    else:
        # 오늘 날짜 확인 (KST 통일)
        kst = pytz.timezone('Asia/Seoul')
        check_dt = datetime.now(kst).date()
    
    # 주말 체크
    if check_dt.weekday() >= 5:  # 토요일(5), 일요일(6)
        return False
    
    # 한국 공휴일 체크
    kr_holidays = holidays.SouthKorea()
    if check_dt in kr_holidays:
        return False
    
    return True

@app.get('/scan', response_model=ScanResponse)
def scan(kospi_limit: int = None, kosdaq_limit: int = None, save_snapshot: bool = True, sort_by: str = 'score', date: str = None, scanner_version: Optional[str] = None):
    # 날짜 처리 (통일된 형식 사용) - date가 없으면 현재 날짜를 YYYYMMDD 형식으로 명시
    try:
        today_as_of = normalize_date(date)  # date가 None이면 현재 날짜를 YYYYMMDD로 반환
    except Exception as e:
        print(f"날짜 파싱 오류: {e}")
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. YYYYMMDD 형식으로 입력해주세요.")

    # 거래일 체크 (정규화된 날짜로 확인)
    if not is_trading_day(today_as_of):
        raise HTTPException(
            status_code=400, 
            detail="오늘은 거래일이 아닙니다. 주말이나 공휴일에는 스캔을 실행할 수 없습니다."
        )
    
    # 미래 날짜 가드: today_as_of가 오늘보다 크면 오늘로 클램프
    try:
        _today = get_kst_now().strftime('%Y%m%d')
        if today_as_of > _today:
            today_as_of = _today
    except Exception:
        pass
    
    # 시장 상황 분석 (활성화된 경우) - DB에 저장된 결과를 먼저 확인
    market_condition = None
    if config.market_analysis_enable:
        try:
            # DB에서 장세 분석 결과 먼저 확인 (스케줄러에서 이미 완료했을 수 있음)
            from db_manager import db_manager
            from market_analyzer import MarketCondition
            from date_helper import yyyymmdd_to_date
            import json
            
            date_obj = yyyymmdd_to_date(today_as_of)
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                           sector_rotation, foreign_flow, institution_flow, volume_trend,
                           min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                           trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                           foreign_flow_label, institution_flow_label, volume_trend_label, adjusted_params, analysis_notes,
                           midterm_regime, short_term_risk_score, final_regime, longterm_regime
                    FROM market_conditions
                    WHERE date = %s
                """, (date_obj,))
                row = cur.fetchone()
            
            if row:
                # DB에 저장된 결과 사용 (스케줄러에서 이미 완료)
                values = dict(zip([
                    'market_sentiment', 'sentiment_score', 'kospi_return', 'volatility', 'rsi_threshold',
                    'sector_rotation', 'foreign_flow', 'institution_flow', 'volume_trend',
                    'min_signals', 'macd_osc_min', 'vol_ma5_mult', 'gap_max', 'ext_from_tema20_max',
                    'trend_metrics', 'breadth_metrics', 'flow_metrics', 'sector_metrics', 'volatility_metrics',
                    'foreign_flow_label', 'institution_flow_label', 'volume_trend_label', 'adjusted_params', 'analysis_notes',
                    'midterm_regime', 'short_term_risk_score', 'final_regime', 'longterm_regime'
                ], row))
                
                sentiment_score = float(values.get("sentiment_score", 0.0)) if values.get("sentiment_score") is not None else 0.0
                
                # JSON 필드 파싱 (이미 dict인 경우 처리)
                def _ensure_json(value):
                    if value is None:
                        return None
                    if isinstance(value, dict):
                        return value
                    if isinstance(value, str):
                        try:
                            return json.loads(value)
                        except:
                            return None
                    return None
                
                trend_metrics = _ensure_json(values.get("trend_metrics"))
                breadth_metrics = _ensure_json(values.get("breadth_metrics"))
                flow_metrics = _ensure_json(values.get("flow_metrics"))
                sector_metrics = _ensure_json(values.get("sector_metrics"))
                volatility_metrics = _ensure_json(values.get("volatility_metrics"))
                adjusted_params = _ensure_json(values.get("adjusted_params"))
                
                market_condition = MarketCondition(
                    date=today_as_of,
                    market_sentiment=values.get("market_sentiment"),
                    sentiment_score=sentiment_score,
                    kospi_return=values.get("kospi_return"),
                    volatility=values.get("volatility"),
                    rsi_threshold=values.get("rsi_threshold"),
                    sector_rotation=values.get("sector_rotation"),
                    foreign_flow=values.get("foreign_flow"),
                    institution_flow=values.get("institution_flow"),
                    volume_trend=values.get("volume_trend"),
                    min_signals=values.get("min_signals"),
                    macd_osc_min=values.get("macd_osc_min"),
                    vol_ma5_mult=values.get("vol_ma5_mult"),
                    gap_max=values.get("gap_max"),
                    ext_from_tema20_max=values.get("ext_from_tema20_max"),
                    trend_metrics=trend_metrics,
                    breadth_metrics=breadth_metrics,
                    flow_metrics=flow_metrics,
                    sector_metrics=sector_metrics,
                    volatility_metrics=volatility_metrics,
                    foreign_flow_label=values.get("foreign_flow_label"),
                    institution_flow_label=values.get("institution_flow_label"),
                    volume_trend_label=values.get("volume_trend_label"),
                    adjusted_params=adjusted_params,
                    analysis_notes=values.get("analysis_notes"),
                    midterm_regime=values.get("midterm_regime"),
                    short_term_risk_score=int(values.get("short_term_risk_score")) if values.get("short_term_risk_score") is not None else None,
                    final_regime=values.get("final_regime"),
                    longterm_regime=values.get("longterm_regime"),
                )
                print(f"📊 시장 상황 조회 (DB 재사용): {market_condition.market_sentiment} (유효 수익률: {market_condition.kospi_return*100:.2f}%, RSI 임계값: {market_condition.rsi_threshold})")
            else:
                # DB에 없으면 새로 분석 (수동 실행 등)
                print(f"📊 DB에 장세 분석 결과 없음, 새로 분석 수행...")
                market_analyzer.clear_cache()
                regime_version = getattr(config, 'regime_version', 'v1')
                market_condition = market_analyzer.analyze_market_condition(today_as_of, regime_version=regime_version)
                
                # 레짐 버전에 따른 로그 출력
                if hasattr(market_condition, 'version'):
                    if market_condition.version == 'regime_v4':
                        print(f"📊 Global Regime v4: {market_condition.final_regime} (trend: {market_condition.global_trend_score:.2f}, risk: {market_condition.global_risk_score:.2f})")
                    elif market_condition.version == 'regime_v3':
                        print(f"📊 Global Regime v3: {market_condition.final_regime} (점수: {market_condition.final_score:.2f})")
                    else:
                        print(f"📊 시장 상황 분석 v1: {market_condition.market_sentiment} (유효 수익률: {market_condition.kospi_return*100:.2f}%, RSI 임계값: {market_condition.rsi_threshold})")
                else:
                    print(f"📊 시장 상황 분석: {market_condition.market_sentiment} (유효 수익률: {market_condition.kospi_return*100:.2f}%, RSI 임계값: {market_condition.rsi_threshold})")
        except Exception as e:
            print(f"⚠️ 시장 분석 실패, 기본 조건 사용: {e}")
            import traceback
            traceback.print_exc()
    
    kp = kospi_limit or config.universe_kospi
    kd = kosdaq_limit or config.universe_kosdaq
    
    # 시장 분리 신호에 따라 Universe 비율 조정 (양방향)
    if market_condition and hasattr(market_condition, 'market_divergence') and market_condition.market_divergence:
        divergence_type = getattr(market_condition, 'divergence_type', '')
        if divergence_type == 'kospi_up_kosdaq_down':
            # KOSPI 상승·KOSDAQ 하락 시 KOSPI 비중 증가
            adjusted_kp = int(kp * 1.5)  # 100 -> 150
            adjusted_kd = int(kd * 0.5)  # 100 -> 50
            print(f"📊 시장 분리 신호 감지 (KOSPI↑ KOSDAQ↓) - Universe 조정: KOSPI {kp}→{adjusted_kp}, KOSDAQ {kd}→{adjusted_kd}")
            kp = adjusted_kp
            kd = adjusted_kd
        elif divergence_type == 'kospi_down_kosdaq_up':
            # KOSPI 하락·KOSDAQ 상승 시 KOSDAQ 비중 증가
            adjusted_kp = int(kp * 0.5)  # 100 -> 50
            adjusted_kd = int(kd * 1.5)  # 100 -> 150
            print(f"📊 시장 분리 신호 감지 (KOSPI↓ KOSDAQ↑) - Universe 조정: KOSPI {kp}→{adjusted_kp}, KOSDAQ {kd}→{adjusted_kd}")
            kp = adjusted_kp
            kd = adjusted_kd
    
    kospi = api.get_top_codes('KOSPI', kp)
    kosdaq = api.get_top_codes('KOSDAQ', kd)
    universe: List[str] = [*kospi, *kosdaq]
    
    # 성능 최적화: market_condition에 KOSPI/KOSDAQ 리스트 저장 (가산점 로직에서 재사용)
    if market_condition:
        market_condition.kospi_universe = kospi
        market_condition.kosdaq_universe = kosdaq
    
    # 스캐너 버전 결정: 파라미터 > DB 설정 > 기본값
    if scanner_version and scanner_version in ['v1', 'v2', 'v3']:
        target_engine = scanner_version
    else:
        # 파라미터가 없으면 기존 방식 (하위 호환성)
        from scanner_settings_manager import get_active_engine
        target_engine = get_active_engine()
    
    # 스캔 실행 (정규화된 날짜 YYYYMMDD 형식 사용)
    print(f"📅 스캔 날짜: {today_as_of} (YYYYMMDD 형식)")
    print(f"🔧 스캐너 버전: {target_engine} {'(파라미터 지정)' if scanner_version else '(DB 설정)'}")
    
    # V3 엔진 처리
    if target_engine == 'v3':
        from scanner_v3 import ScannerV3
        scanner_v3 = ScannerV3()
        v3_result = scanner_v3.scan(universe, today_as_of, market_condition)
        
        # V3 결과를 기존 형식으로 변환 (하위 호환성)
        items = []
        
        # midterm 결과 추가
        for candidate in v3_result.get("results", {}).get("midterm", {}).get("candidates", []):
            code = candidate.get("code")
            indicators = candidate.get("indicators", {})
            
            # 키움 API에서 실제 가격 데이터 및 종목명 가져오기
            stock_name = ""
            close_price = 0.0
            volume = 0
            change_rate = 0.0
            
            try:
                # 종목명 가져오기
                stock_name = api.get_stock_name(code) or ""
            except Exception as e:
                print(f"⚠️ {code} 종목명 가져오기 실패: {e}")
            
            try:
                df = api.get_ohlcv(code, 1, today_as_of)
                if not df.empty:
                    latest = df.iloc[-1]
                    close_price = float(latest["close"])
                    volume = int(latest["volume"])
                    # 전일 대비 등락률 계산
                    if len(df) >= 2:
                        prev_close = float(df.iloc[-2]["close"])
                        change_rate = ((close_price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
                    else:
                        change_rate = 0.0
                else:
                    close_price = indicators.get("close", 0.0)
                    volume = indicators.get("volume", 0)
                    change_rate = 0.0
            except Exception as e:
                print(f"⚠️ {code} 가격 데이터 가져오기 실패: {e}")
                close_price = indicators.get("close", 0.0)
                volume = indicators.get("volume", 0)
                change_rate = 0.0
            
            # midterm indicators를 표준 형식으로 변환
            standard_indicators = {
                "close": close_price,
                "TEMA": indicators.get("ema20", 0.0),  # TEMA로 매핑
                "DEMA": indicators.get("ema60", 0.0),  # DEMA로 매핑
                "MACD_OSC": 0.0,
                "MACD_LINE": 0.0,
                "MACD_SIGNAL": 0.0,
                "RSI_TEMA": indicators.get("rsi", 0.0),
                "RSI_DEMA": 0.0,
                "OBV": 0.0,
                "VOL": volume,
                "VOL_MA5": indicators.get("vma20", 0.0),
                "change_rate": change_rate
            }
            
            items.append({
                "ticker": code,
                "name": stock_name,  # 키움 API에서 가져온 종목명
                "match": True,
                "score": candidate.get("score", 0.0),
                "indicators": standard_indicators,
                "trend": {
                    "TEMA20_SLOPE20": 0.0,
                    "OBV_SLOPE20": 0.0,
                    "ABOVE_CNT5": 0,
                    "DEMA10_SLOPE20": 0.0
                },
                "flags": {
                    "cross": False,
                    "vol_expand": False,
                    "macd_ok": False,
                    "tema_slope_ok": False,
                    "obv_slope_ok": False,
                    "above_cnt5_ok": False,
                    "details": {
                        "engine": "midterm",
                        "pick_source": candidate.get("meta", {}).get("pick_source", "unknown")
                    }
                },
                "strategy": "midterm",
                "score_label": "midterm",
                "engine": "midterm"
            })
        
        # v2-lite 결과 추가 (neutral/normal일 때만)
        if v3_result.get("results", {}).get("v2_lite", {}).get("enabled", False):
            for candidate in v3_result.get("results", {}).get("v2_lite", {}).get("candidates", []):
                code = candidate.get("code")
                indicators = candidate.get("indicators", {})
                meta = candidate.get("meta", {})
                trend = meta.get("trend", {})
                flags = meta.get("flags", {})
                
                # v2-lite indicators는 이미 표준 형식
                items.append({
                    "ticker": code,
                    "name": candidate.get("name", ""),
                    "match": meta.get("match", True),
                    "score": 1.0,  # v2-lite는 score=1.0 (호환성)
                    "indicators": indicators,
                    "trend": trend,
                    "flags": flags,
                    "strategy": "v2_lite",  # v3에서는 항상 "v2_lite"로 저장 (원본 "눌림목" 무시)
                    "score_label": meta.get("score_label", "v2_lite"),
                    "engine": "v2_lite"
                })
        
        scanner_version = "v3"
        chosen_step = None
        
        midterm_count = len(v3_result.get('results', {}).get('midterm', {}).get('candidates', []))
        v2_lite_count = len(v3_result.get('results', {}).get('v2_lite', {}).get('candidates', []))
        print(f"📈 V3 스캔 완료: midterm {midterm_count}개, v2-lite {v2_lite_count}개 (레짐: {v3_result.get('regime', {}).get('final', 'unknown')}/{v3_result.get('regime', {}).get('risk', 'unknown')})")
    elif target_engine == 'v2':
        # V2 엔진 명시적 실행
        from scanner_factory import scan_with_scanner
        all_items = scan_with_scanner(universe, None, today_as_of, market_condition, version='v2')
        # V2 결과 정렬 및 상위 N개 선택 (점수 필터 없이)
        all_items.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_k = getattr(config, 'top_k', 50)
        items = all_items[:top_k]
        # V2는 fallback 없이 실행
        chosen_step = None
        scanner_version = 'v2'
        print(f"📈 V2 스캔 완료: {len(items)}개 종목 발견 (전체: {len(all_items)}개, 상위 {top_k}개 선택, 날짜: {today_as_of})")
    else:
        # V1 엔진 (기존 로직)
        result = execute_scan_with_fallback(universe, today_as_of, market_condition)
        if len(result) == 3:
            items, chosen_step, detected_version = result
            # 파라미터로 지정된 버전 우선, 없으면 감지된 버전 사용
            scanner_version = target_engine if scanner_version else detected_version
        else:
            # 하위 호환성: 기존 코드는 2개 값만 반환
            items, chosen_step = result
            # 파라미터로 지정된 버전 우선, 없으면 target_engine 사용
            scanner_version = target_engine if scanner_version else None
        print(f"📈 스캔 완료: {len(items)}개 종목 발견 (날짜: {today_as_of}, 버전: {scanner_version or 'auto'})")
    
    # 수익률 계산 (병렬 처리) - 모든 스캔에 대해 날짜 명시
    returns_data = {}
    tickers = [item["ticker"] for item in items]
    print(f"💰 수익률 계산 시작: {len(tickers)}개 종목, 날짜: {today_as_of}")
    
    # 현재 날짜와 비교하여 과거 스캔인지 확인
    _today = get_kst_now().strftime('%Y%m%d')
    if today_as_of < _today:  # 과거 스캔인 경우
        returns_data = calculate_returns_batch(tickers, today_as_of)
    else:  # 당일 스캔인 경우 - 당일 등락률 표시
        for ticker in tickers:
            try:
                # 키움 API에서 가져온 change_rate를 returns 형태로 변환
                item_data = next((item for item in items if item["ticker"] == ticker), None)
                if item_data and "change_rate" in item_data["indicators"]:
                    change_rate = item_data["indicators"]["change_rate"]
                    current_price = item_data["indicators"]["close"]
                    returns_data[ticker] = {
                        'current_return': change_rate,
                        'max_return': change_rate,  # 당일 최대 등락률은 현재와 동일
                        'min_return': change_rate,  # 당일 최소 등락률은 현재와 동일
                        'current_price': current_price,
                        'days_elapsed': 0
                    }
            except Exception as e:
                print(f"당일 등락률 처리 오류 ({ticker}): {e}")
    
    print(f"💰 수익률 계산 완료: {len(returns_data)}개 결과")
    for ticker, ret in returns_data.items():
        if ret:
            print(f"  {ticker}: {ret.get('current_return', 0):.2f}%")
    
    # 재등장 이력 조회 (배치 처리)
    tickers = [item["ticker"] for item in items]
    recurrence_data = get_recurrence_data(tickers, today_as_of)
    
    # ScanItem 객체로 변환
    scan_items: List[ScanItem] = []
    for item in items:
        try:
            ticker = item["ticker"]
            recurrence = recurrence_data.get(ticker)
            returns = returns_data.get(ticker)
            
            # 키움 API에서 가져온 등락률 사용
            cr = item["indicators"].get("change_rate", 0.0)

            # V1과 V2 호환성: TEMA20 (V1) 또는 TEMA (V2)
            tema_value = item["indicators"].get("TEMA") or item["indicators"].get("TEMA20", 0.0)
            dema_value = item["indicators"].get("DEMA") or item["indicators"].get("DEMA10", 0.0)
            
            # trend 처리 (V3의 midterm은 trend가 없을 수 있음)
            trend_data = item.get("trend", {})
            if trend_data and isinstance(trend_data, dict) and "TEMA20_SLOPE20" in trend_data:
                trend_payload = TrendPayload(
                    TEMA20_SLOPE20=trend_data.get("TEMA20_SLOPE20", 0.0),
                    OBV_SLOPE20=trend_data.get("OBV_SLOPE20", 0.0),
                    ABOVE_CNT5=trend_data.get("ABOVE_CNT5", 0),
                    DEMA10_SLOPE20=trend_data.get("DEMA10_SLOPE20", 0.0),
                )
            else:
                # V3 midterm 등 trend가 없는 경우 기본값
                trend_payload = TrendPayload(
                    TEMA20_SLOPE20=0.0,
                    OBV_SLOPE20=0.0,
                    ABOVE_CNT5=0,
                    DEMA10_SLOPE20=0.0,
                )
            
            # flags 처리
            flags_data = item.get("flags", {})
            if flags_data and isinstance(flags_data, dict):
                score_flags = _as_score_flags(flags_data)
            else:
                # 기본 ScoreFlags 생성
                from models import ScoreFlags
                score_flags = ScoreFlags(
                    cross=False,
                    vol_expand=False,
                    macd_ok=False,
                    tema_slope_ok=False,
                    obv_slope_ok=False,
                    above_cnt5_ok=False,
                    details=flags_data.get("details", {}) if isinstance(flags_data, dict) else {}
                )
            
            scan_item = ScanItem(
                ticker=ticker,
                name=item.get("name", ""),
                match=item.get("match", True),
                score=item.get("score", 0.0),
                indicators=IndicatorPayload(
                    TEMA=tema_value,
                    DEMA=dema_value,
                    MACD_OSC=item["indicators"].get("MACD_OSC", 0.0),
                    MACD_LINE=item["indicators"].get("MACD_LINE", 0.0),
                    MACD_SIGNAL=item["indicators"].get("MACD_SIGNAL", 0.0),
                    RSI_TEMA=item["indicators"].get("RSI_TEMA", 0.0),
                    RSI_DEMA=item["indicators"].get("RSI_DEMA", 0.0),
                    OBV=item["indicators"].get("OBV", 0.0),
                    VOL=item["indicators"].get("VOL", 0),
                    VOL_MA5=item["indicators"].get("VOL_MA5", 0.0),
                    close=item["indicators"].get("close", 0.0),
                    change_rate=cr,
                ),
                trend=trend_payload,
                flags=score_flags,
                score_label=item.get("score_label", ""),
                details={**(flags_data.get("details", {}) if isinstance(flags_data, dict) else {}), "close": item["indicators"].get("close", 0.0)},
                strategy=item.get("strategy", ""),
                recurrence=recurrence,  # recurrence 필드에 직접 할당
                returns=returns,
                current_price=item["indicators"].get("close", 0.0),  # 현재가
                change_rate=cr,  # 등락률
            )
            scan_items.append(scan_item)
        except Exception as e:
            print(f"ScanItem 생성 오류 ({item.get('ticker', 'unknown')}): {e}")
            continue
    
    # v2_lite 결과 필터링 (UI에서 숨김, 백데이터로만 저장)
    scan_items = [item for item in scan_items if item.strategy != "v2_lite"]
    
    # 시장 가이드 생성
    scan_result_dict = {
        'matched_count': len(scan_items),
        'rsi_threshold': market_condition.rsi_threshold if market_condition else config.rsi_setup_min,
        'items': [{
            'ticker': item.ticker,
            'indicators': {'change_rate': item.indicators.change_rate},
            'flags': {'vol_expand': item.flags.vol_expand if item.flags else False}
        } for item in scan_items],
        'market_sentiment': market_condition.market_sentiment if market_condition else None  # market_analyzer의 판단 결과 전달
    }
    market_guide = get_market_guide(scan_result_dict)
    
    resp = ScanResponse(
        as_of=today_as_of,
        universe_count=len(universe),
        matched_count=len(scan_items),
        rsi_mode="current_status",  # 현재 상태 분석 모드
        rsi_period=14,  # 고정값
        rsi_threshold=market_condition.rsi_threshold if market_condition else config.rsi_setup_min,  # 시장 상황 기반 RSI 임계값
        items=scan_items,
        fallback_step=chosen_step if config.fallback_enable else None,
        score_weights=getattr(config, 'dynamic_score_weights')() if hasattr(config, 'dynamic_score_weights') else {},
        score_level_strong=config.score_level_strong,
        score_level_watch=config.score_level_watch,
        require_dema_slope=getattr(config, 'require_dema_slope', 'required'),
        market_guide=market_guide,
        scanner_version=scanner_version or getattr(config, 'scanner_version', 'v1'),  # DB 설정 기반 버전 정보
    )
    if save_snapshot:
        # 스냅샷에는 핵심 메타/랭킹만 저장(용량 절약)
        # 스냅샷에 종가, 거래량, 변동률 추가
        enhanced_rank = []
        for it in scan_items:
            try:
                # 저장은 indicators 기반으로 일관 처리
                current_price = int(getattr(it.indicators, 'close', 0) or 0)
                volume = int(getattr(it.indicators, 'VOL', 0) or 0)
                change_rate = float(getattr(it.indicators, 'change_rate', 0.0) or 0.0)
                
                enhanced_item = {
                    'ticker': it.ticker,
                    'name': it.name,
                    'score': it.score,
                    'score_label': it.score_label,
                    'current_price': int(current_price),  # 현재가
                    'volume': int(volume),              # 거래량
                    'change_rate': change_rate,         # 변동률
                }
            except Exception as e:
                # API 호출 실패시 기본값
                enhanced_item = {
                    'ticker': it.ticker,
                    'name': it.name,
                    'score': it.score,
                    'score_label': it.score_label,
                    'current_price': 0,
                    'volume': 0,
                    'change_rate': 0,
                }
            enhanced_rank.append(enhanced_item)
        
        print(f"🔍 save_snapshot 조건 확인: {save_snapshot} (타입: {type(save_snapshot)})")
        print(f"✅ save_snapshot=True, 스냅샷 저장 시작")
        snapshot = {
            'as_of': resp.as_of,
            'created_at': datetime.now().strftime('%Y%m%d%H%M%S'),
            'universe_count': resp.universe_count,
            'matched_count': resp.matched_count,
            'rsi_mode': resp.rsi_mode,
            'rsi_period': resp.rsi_period,
            'rsi_threshold': resp.rsi_threshold,
            'rank': enhanced_rank,
        }
        try:
            # save_scan_snapshot 사용 (scanner_version 포함)
            # 원본 item["flags"]를 사용하여 trading_strategy 보존
            scan_items_dict = []
            for idx, it in enumerate(scan_items):
                # 원본 flags dict 가져오기 (ScanItem 변환 전)
                original_flags = items[idx]["flags"] if idx < len(items) else {}
                
                # strategy 추출: it.strategy > original_flags.trading_strategy (우선순위)
                strategy_value = None
                if hasattr(it, 'strategy') and it.strategy:
                    strategy_value = it.strategy
                elif isinstance(original_flags, dict) and original_flags.get("trading_strategy"):
                    strategy_value = original_flags.get("trading_strategy")
                elif hasattr(it, 'flags') and hasattr(it.flags, '__dict__'):
                    flags_dict = it.flags.__dict__
                    if isinstance(flags_dict, dict) and flags_dict.get("trading_strategy"):
                        strategy_value = flags_dict.get("trading_strategy")
                
                scan_items_dict.append({
                    'ticker': it.ticker,
                    'name': it.name,
                    'score': it.score,
                    'score_label': it.score_label,
                    'strategy': strategy_value,
                    'flags': original_flags if isinstance(original_flags, dict) else (it.flags.__dict__ if hasattr(it.flags, '__dict__') else {}),
                    'recurrence': it.recurrence if hasattr(it, 'recurrence') else None,
                    'returns': it.returns if hasattr(it, 'returns') else None,
                })
            save_scan_snapshot(scan_items_dict, resp.as_of, scanner_version)
            
            # 시장 상황도 함께 저장
            if market_condition:
                try:
                    from main import create_market_conditions_table
                    with db_manager.get_cursor() as cur:
                        create_market_conditions_table(cur)
                        cur.execute("""
                            INSERT INTO market_conditions(
                                date, market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                                sector_rotation, foreign_flow, institution_flow, volume_trend,
                                min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                                trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                                foreign_flow_label, institution_flow_label, volume_trend_label, adjusted_params, analysis_notes
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (date) DO UPDATE SET
                                market_sentiment = EXCLUDED.market_sentiment,
                                sentiment_score = EXCLUDED.sentiment_score,
                                kospi_return = EXCLUDED.kospi_return,
                                volatility = EXCLUDED.volatility,
                                rsi_threshold = EXCLUDED.rsi_threshold,
                                sector_rotation = EXCLUDED.sector_rotation,
                                foreign_flow = EXCLUDED.foreign_flow,
                                institution_flow = EXCLUDED.institution_flow,
                                volume_trend = EXCLUDED.volume_trend,
                                min_signals = EXCLUDED.min_signals,
                                macd_osc_min = EXCLUDED.macd_osc_min,
                                vol_ma5_mult = EXCLUDED.vol_ma5_mult,
                                gap_max = EXCLUDED.gap_max,
                                ext_from_tema20_max = EXCLUDED.ext_from_tema20_max,
                                trend_metrics = EXCLUDED.trend_metrics,
                                breadth_metrics = EXCLUDED.breadth_metrics,
                                flow_metrics = EXCLUDED.flow_metrics,
                                sector_metrics = EXCLUDED.sector_metrics,
                                volatility_metrics = EXCLUDED.volatility_metrics,
                                foreign_flow_label = EXCLUDED.foreign_flow_label,
                                institution_flow_label = EXCLUDED.institution_flow_label,
                                volume_trend_label = EXCLUDED.volume_trend_label,
                                adjusted_params = EXCLUDED.adjusted_params,
                                analysis_notes = EXCLUDED.analysis_notes,
                                updated_at = NOW()
                        """, (
                            resp.as_of,
                            market_condition.market_sentiment,
                            market_condition.sentiment_score,
                            market_condition.kospi_return,
                            market_condition.volatility,
                            market_condition.rsi_threshold,
                            market_condition.sector_rotation,
                            market_condition.foreign_flow,
                            market_condition.institution_flow,
                            market_condition.volume_trend,
                            market_condition.min_signals,
                            market_condition.macd_osc_min,
                            market_condition.vol_ma5_mult,
                            market_condition.gap_max,
                            market_condition.ext_from_tema20_max,
                            json.dumps(market_condition.trend_metrics) if market_condition.trend_metrics else None,
                            json.dumps(market_condition.breadth_metrics) if market_condition.breadth_metrics else None,
                            json.dumps(market_condition.flow_metrics) if market_condition.flow_metrics else None,
                            json.dumps(market_condition.sector_metrics) if market_condition.sector_metrics else None,
                            json.dumps(market_condition.volatility_metrics) if market_condition.volatility_metrics else None,
                            market_condition.foreign_flow_label,
                            market_condition.institution_flow_label,
                            market_condition.volume_trend_label,
                            json.dumps(market_condition.adjusted_params) if market_condition.adjusted_params else None,
                            market_condition.analysis_notes
                        ))
                    print(f"✅ 시장 상황 저장 완료: {resp.as_of} ({market_condition.market_sentiment}, {market_condition.kospi_return*100:.2f}%)")
                except Exception as e:
                    print(f"⚠️ 시장 상황 저장 실패: {e}")
            
            print(f"✅ DB 저장 성공: {resp.as_of} (버전: {scanner_version or 'auto'})")
        except Exception as e:
            print(f"❌ DB 저장 실패: {e}")
            # 실패해도 API 응답은 반환
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
        as_of=datetime.now().strftime('%Y%m%d'),
        items=items,
    )


@app.get('/scan/us-stocks', response_model=ScanResponse)
def scan_us_stocks(
    universe_type: str = 'sp500',  # 'sp500', 'nasdaq100', 'combined'
    limit: int = 500,
    date: str = None,
    save_snapshot: bool = True  # 한국 주식과 동일하게 기본값 True
):
    """
    미국 주식 스캔
    
    Args:
        universe_type: 유니버스 타입 ('sp500', 'nasdaq100', 'combined')
        limit: 최대 종목 수
        date: 스캔 날짜 (YYYYMMDD 형식, None이면 오늘)
        save_snapshot: 스캔 결과를 DB에 저장할지 여부
    """
    try:
        # 날짜 처리
        today_as_of = normalize_date(date) if date else get_kst_now().strftime('%Y%m%d')
        
        # 유니버스 가져오기
        try:
            if universe_type == 'sp500':
                stocks = us_stocks_universe.get_sp500_list()
                if not stocks:
                    raise HTTPException(status_code=500, detail="S&P 500 리스트를 가져올 수 없습니다")
                symbols = [s['symbol'] for s in stocks[:limit]]
            elif universe_type == 'nasdaq100':
                stocks = us_stocks_universe.get_nasdaq100_list()
                if not stocks:
                    raise HTTPException(status_code=500, detail="NASDAQ 100 리스트를 가져올 수 없습니다")
                symbols = [s['symbol'] for s in stocks[:limit]]
            elif universe_type == 'combined':
                symbols = us_stocks_universe.get_combined_universe(limit=limit)
                if not symbols:
                    raise HTTPException(status_code=500, detail="통합 유니버스를 가져올 수 없습니다")
            else:
                raise HTTPException(status_code=400, detail=f"지원하지 않는 유니버스 타입: {universe_type}")
        except HTTPException:
            raise
        except Exception as e:
            print(f"⚠️ 유니버스 가져오기 실패: {e}")
            raise HTTPException(status_code=500, detail=f"유니버스 가져오기 실패: {str(e)}")
        
        print(f"📊 미국 주식 스캔 시작: {len(symbols)}개 종목, 날짜: {today_as_of}")
        
        # 시장 조건 분석 (Global Regime v4 사용 - 한국+미국 통합 분석)
        market_condition = None
        if config.market_analysis_enable:
            try:
                # Global Regime v4 사용 (한국+미국 데이터를 모두 고려)
                # v4는 이미 SPY, QQQ, VIX 등 미국 데이터를 포함하므로 적합
                market_condition = market_analyzer.analyze_market_condition(
                    today_as_of, 
                    regime_version='v4'
                )
                print(f"✅ 레짐 분석 완료: {market_condition.final_regime if hasattr(market_condition, 'final_regime') else market_condition.market_sentiment}")
            except Exception as e:
                print(f"⚠️ 미국 시장 레짐 분석 실패: {e}")
                import traceback
                print(traceback.format_exc())
                # 레짐 분석 실패 시에도 스캔은 계속 진행 (market_condition = None)
        
        # 스캐너 설정
        scanner_config = ScannerV2Config()
        
        # 미국 주식 스캐너 생성
        us_scanner = USScanner(scanner_config, market_analyzer)
        
        # 스캔 실행
        results = us_scanner.scan(symbols, today_as_of, market_condition)
        
        print(f"✅ 미국 주식 스캔 완료: {len(results)}개 종목 발견")
        
        # ScanItem 리스트로 변환
        items: List[ScanItem] = []
        for result in results:
            try:
                # 등락률 및 현재가 가져오기
                quote = us_stocks_data.get_stock_quote(result.ticker)
                change_rate = quote.get('change_rate', 0.0) if quote else 0.0
                current_price = quote.get('current_price', 0.0) if quote else 0.0
                
                # OHLCV 데이터에서 close 가져오기 (fallback)
                if current_price == 0.0:
                    df = us_stocks_data.get_ohlcv(result.ticker, 1)
                    if not df.empty:
                        current_price = float(df.iloc[-1]['close'])
                
                items.append(ScanItem(
                    ticker=result.ticker,
                    name=result.name,
                    match=result.match,  # 필수 필드 추가
                    score=result.score,
                    score_label=result.score_label,
                    current_price=current_price,
                    change_rate=change_rate,
                    strategy=result.strategy,
                    indicators=IndicatorPayload(**result.indicators) if result.indicators else None,
                    trend=TrendPayload(**result.trend) if result.trend else None,
                    flags=ScoreFlags(**result.flags) if result.flags else None
                ))
            except Exception as e:
                print(f"⚠️ {result.ticker} 변환 오류: {e}")
                continue
        
        # DB 저장 (한국 주식과 동일한 방식)
        if save_snapshot:
            try:
                from services.scan_service import save_scan_snapshot
                scan_items_dict = []
                for idx, result in enumerate(results):
                    # flags를 dict로 변환
                    flags_dict = {}
                    if result.flags:
                        if isinstance(result.flags, dict):
                            flags_dict = result.flags
                        elif hasattr(result.flags, '__dict__'):
                            flags_dict = result.flags.__dict__
                    
                    # strategy 추출 (우선순위: result.strategy > flags.trading_strategy)
                    strategy_value = result.strategy
                    if not strategy_value and flags_dict.get("trading_strategy"):
                        strategy_value = flags_dict.get("trading_strategy")
                    
                    scan_items_dict.append({
                        'ticker': result.ticker,
                        'name': result.name,
                        'score': result.score,
                        'score_label': result.score_label,
                        'strategy': strategy_value,
                        'flags': flags_dict,
                    })
                
                # scanner_version을 'us_v2'로 저장 (한국 주식은 'v1' 또는 'v2')
                save_scan_snapshot(scan_items_dict, today_as_of, 'us_v2')
                print(f"✅ 미국 주식 스캔 결과 DB 저장 완료: {today_as_of} (버전: us_v2)")
            except Exception as e:
                print(f"⚠️ 미국 주식 스캔 결과 DB 저장 실패: {e}")
                import traceback
                traceback.print_exc()
        
        return ScanResponse(
            as_of=today_as_of,
            universe_count=len(symbols),
            matched_count=len(items),
            rsi_mode="current_status",
            rsi_period=14,
            rsi_threshold=getattr(scanner_config, 'us_rsi_setup_min', 60),  # 미국 주식용 RSI 임계값
            items=items,
            fallback_step=None,
            score_weights=scanner_config.get_weights(),
            score_level_strong=scanner_config.score_level_strong,
            score_level_watch=scanner_config.score_level_watch,
            market_guide=None,  # 미국 시장 가이드 (추후 구현)
            market_condition=market_condition
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ 미국 주식 스캔 오류: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"미국 주식 스캔 실패: {str(e)}")


@app.get('/_debug/topvalue')
def _debug_topvalue(market: str = 'KOSPI'):
    return api.debug_call_topvalue_once(market)


@app.get('/_debug/stockinfo')
def _debug_stockinfo(market_tp: str = '001'):
    return api.debug_call_stockinfo_once(market_tp)


# 기존 /validate 제거 → 스냅샷 기반 검증만 유지


@app.delete('/scan/{date}')
def delete_scan_result(date: str):
    """특정 날짜의 스캔 결과 삭제"""
    try:
        try:
            normalized = normalize_date(date)
        except ValueError:
            return {
                "ok": False,
                "error": "날짜 형식이 올바르지 않습니다. YYYYMMDD 형식을 사용해주세요."
            }
        formatted_date = normalized
        target_date = datetime.strptime(formatted_date, "%Y%m%d").date()
        
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute(
                "DELETE FROM scan_rank WHERE date = %s OR date = %s",
                (target_date, formatted_date),
            )
            deleted_count = cur.rowcount or 0
        
        # 2. JSON 스냅샷 파일 삭제 (경로 검증)
        safe_filename = f"scan-{formatted_date}.json"
        snapshot_file = sanitize_file_path(safe_filename, SNAPSHOT_DIR)
        file_deleted = False
        if snapshot_file and os.path.exists(snapshot_file):
            os.remove(snapshot_file)
            file_deleted = True
        
        return {
            "ok": True,
            "message": f"{formatted_date} 스캔 결과가 삭제되었습니다",
            "deleted_records": deleted_count,
            "file_deleted": file_deleted
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


@app.get('/snapshots')
def list_snapshots():
    files = []
    try:
        for fn in os.listdir(SNAPSHOT_DIR):
            if not fn.startswith('scan-') or not fn.endswith('.json'):
                continue
            safe_path = sanitize_file_path(fn, SNAPSHOT_DIR)
            if not safe_path:
                continue
            try:
                with open(safe_path, 'r', encoding='utf-8') as f:
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
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("SELECT date, COUNT(1) AS cnt FROM scan_rank GROUP BY date")
                rows = cur.fetchall()
            
            for row in rows:
                if isinstance(row, dict):
                    date_val = row.get('date')
                    cnt = row.get('cnt', 0)
                else:
                    date_val, cnt = row
                cnt = int(cnt or 0)
                date_iso = None
                date_compact = None
                if hasattr(date_val, 'strftime'):
                    date_iso = date_val.strftime('%Y-%m-%d')
                    date_compact = date_val.strftime('%Y%m%d')
                elif isinstance(date_val, str):
                    date_iso = date_val
                    date_compact = date_val.replace('-', '')
                else:
                    date_iso = str(date_val)
                    date_compact = str(date_val)
                
                # 이미 파일 항목이 있으면 rank_count만 업데이트
                hit = next(
                    (x for x in files if x.get('as_of') in {date_iso, date_compact}),
                    None
                )
                if hit:
                    hit['rank_count'] = max(hit.get('rank_count') or 0, cnt)
                else:
                    files.append({
                        'file': f"db:{date_compact}",
                        'as_of': date_compact,
                        'created_at': '',
                        'matched_count': None,
                        'rank_count': cnt
                    })
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
        with db_manager.get_cursor(commit=True) as cur:
            for fn in os.listdir(SNAPSHOT_DIR):
                if not fn.startswith('scan-') or not fn.endswith('.json'):
                    continue
                safe_path = sanitize_file_path(fn, SNAPSHOT_DIR)
                if not safe_path:
                    continue
                try:
                    with open(safe_path, 'r', encoding='utf-8') as f:
                        snap = json.load(f)
                except Exception:
                    continue
                
                as_of = snap.get('as_of')
                rank = snap.get('rank', [])
                if not as_of or not isinstance(rank, list):
                    continue
                
                try:
                    if len(as_of) == 8:
                        target_date = datetime.strptime(as_of, "%Y%m%d").date()
                    elif len(as_of) == 10 and as_of.count('-') == 2:
                        target_date = datetime.strptime(as_of, "%Y-%m-%d").date()
                        as_of = target_date.strftime("%Y%m%d")
                    else:
                        continue
                except Exception:
                    continue
                
                for it in rank:
                    code = it.get('ticker') or it.get('code')
                    if not code:
                        continue
                    name = it.get('name') or code
                    score = float(it.get('score') or 0.0)
                    label = it.get('score_label') or ''
                    current_price = it.get('current_price') or it.get('close_price') or 0.0
                    close_price = it.get('close_price') or current_price
                    volume = it.get('volume') or 0
                    change_rate = it.get('change_rate') or it.get('returns', {}).get('current_return')
                    market = it.get('market')
                    strategy = it.get('strategy')
                    indicators = it.get('indicators') or {}
                    trend = it.get('trend')
                    flags = it.get('flags') or {}
                    details = it.get('details') or {}
                    returns_data = it.get('returns') or {}
                    recurrence = it.get('recurrence') or {}
                    
                    try:
                        cur.execute("""
                            INSERT INTO scan_rank(
                                date, code, name, score, score_label, current_price, close_price,
                                volume, change_rate, market, strategy, indicators, trend, flags,
                                details, returns, recurrence
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s
                            )
                            ON CONFLICT (date, code) DO UPDATE SET
                                name = EXCLUDED.name,
                                score = EXCLUDED.score,
                                score_label = EXCLUDED.score_label,
                                current_price = EXCLUDED.current_price,
                                close_price = EXCLUDED.close_price,
                                volume = EXCLUDED.volume,
                                change_rate = EXCLUDED.change_rate,
                                market = EXCLUDED.market,
                                strategy = EXCLUDED.strategy,
                                indicators = EXCLUDED.indicators,
                                trend = EXCLUDED.trend,
                                flags = EXCLUDED.flags,
                                details = EXCLUDED.details,
                                returns = EXCLUDED.returns,
                                recurrence = EXCLUDED.recurrence
                        """, (
                            target_date,
                            code,
                            name,
                            score,
                            label,
                            current_price,
                            close_price,
                            volume,
                            change_rate,
                            market,
                            strategy,
                            indicators,
                            trend,
                            flags,
                            details,
                            returns_data,
                            recurrence,
                        ))
                        status = cur.statusmessage or ""
                        if status.startswith("INSERT"):
                            inserted += 1
                        elif status.startswith("UPDATE"):
                            updated += 1
                    except Exception:
                        continue
    except Exception as e:
        return {'ok': False, 'error': str(e), 'inserted': inserted, 'updated': updated}
    return {'ok': True, 'inserted': inserted, 'updated': updated}

@app.get('/validate_from_snapshot')
def validate_from_snapshot(as_of: str, top_k: int = 20):
    # 당일 스냅샷은 검증 불가(장중 변동/오류 방지)
    today = datetime.now().strftime('%Y%m%d')
    if as_of == today:
        return {
            'error': 'today snapshot not allowed',
            'as_of': today,
            'items': [],
            'count': 0,
        }
    """스냅샷(as_of=YYYY-MM-DD) 상위 목록 기준으로 현재 수익률 검증"""
    # 1) DB 우선 (두 날짜 형식 지원)
    rank = []
    try:
        try:
            normalized = normalize_date(as_of)
        except ValueError:
            normalized = as_of.replace('-', '')
        target_date = None
        try:
            target_date = datetime.strptime(normalized, "%Y%m%d").date()
        except Exception:
            target_date = None
        
        with db_manager.get_cursor(commit=False) as cur:
            if target_date:
                cur.execute(
                    """
                    SELECT code, score, score_label
                    FROM scan_rank
                    WHERE date = %s
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (target_date, int(top_k)),
                )
                rows = cur.fetchall()
            else:
                rows = []
            
            if not rows:
                cur.execute(
                    """
                    SELECT code, score, score_label
                    FROM scan_rank
                    WHERE date = %s
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (normalized, int(top_k)),
                )
                rows = cur.fetchall()
        
        for row in rows:
            if isinstance(row, dict):
                rank.append({
                    'ticker': row.get('code'),
                    'score': row.get('score'),
                    'score_label': row.get('score_label')
                })
            else:
                rank.append({'ticker': row[0], 'score': row[1], 'score_label': row[2]})
    except Exception:
        rank = []
    # 2) JSON 스냅샷 보조
    if not rank:
        fname = f"scan-{as_of}.json"
        safe_path = sanitize_file_path(fname, SNAPSHOT_DIR)
        if not safe_path or not os.path.exists(safe_path):
            return {'error': 'snapshot not found', 'as_of': as_of, 'items': []}
        try:
            with open(safe_path, 'r', encoding='utf-8') as f:
                snap = json.load(f)
            rank = snap.get('rank', [])
            rank.sort(key=lambda x: x.get('score', 0), reverse=True)
        except Exception as e:
            return {'error': str(e), 'as_of': as_of, 'items': []}
    base_dt = as_of
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
        'as_of': datetime.now().strftime('%Y%m%d'),
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
    """카카오 오픈빌더 Webhook: 사용자가 종목명/코드를 말하면 현재 상태 분석을 반환"""
    utterance = (body.get('utterance') or body.get('userRequest', {}).get('utterance') or '').strip()
    if not utterance:
        text = "분석할 종목명을 입력해 주세요. 예) 삼성전자"
    else:
        # analyze_friendly 호출
        res = analyze_friendly(utterance)
        if not res["ok"]:
            text = f"분석 실패: {res['error']}"
        else:
            analysis = res["analysis"]
            text = f"{res['name']}({res['ticker']})\n현재가: {res['current_price']:,.0f}원\n{analysis['summary']}\n상태: {analysis['current_status']}"
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
    """종목의 기술적 지표를 분석하여 현재 상태 제공 (내부용)"""
    code = normalize_code_or_name(name_or_code)
    if not is_code(code):
        code = api.get_code_by_name(code)
        if not code:
            return AnalyzeResponse(ok=False, item=None, error='이름→코드 매핑 실패')

    df = api.get_ohlcv(code, config.ohlcv_count)
    if df.empty or len(df) < 21:
        return AnalyzeResponse(ok=False, item=None, error='데이터 부족')
    
    df = compute_indicators(df)
    
    # 현재가 및 변동률 계산
    cur = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else cur
    change_rate = ((cur.close - prev.close) / prev.close * 100) if prev.close > 0 else 0.0
    
    # 기술적 지표 기반 현재 상태 분석 (스캔 조건 매칭 대신)
    score, flags = score_conditions(df)  # 기존 함수 활용하되 해석 방식 변경
    
    item = ScanItem(
        ticker=code,
        name=api.get_stock_name(code),
        match=True,  # 항상 True (현재 상태 분석이므로)
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
            change_rate=change_rate,
        ),
        trend=TrendPayload(
            TEMA20_SLOPE20=float(df.iloc[-1].get("TEMA20_SLOPE20", 0.0)) if "TEMA20_SLOPE20" in df.columns else 0.0,
            OBV_SLOPE20=float(df.iloc[-1].get("OBV_SLOPE20", 0.0)) if "OBV_SLOPE20" in df.columns else 0.0,
            ABOVE_CNT5=int(((df["TEMA20"] > df["DEMA10"]).tail(5).sum()) if ("TEMA20" in df.columns and "DEMA10" in df.columns) else 0),
            DEMA10_SLOPE20=float(df.iloc[-1].get("DEMA10_SLOPE20", 0.0)) if "DEMA10_SLOPE20" in df.columns else 0.0,
        ),
        flags=_as_score_flags(flags),
        score_label=f"현재 상태: {get_status_label(cur, flags)}",
        strategy=get_current_status_description(df, flags),
    )
    return AnalyzeResponse(ok=True, item=item)

def get_status_label(cur, flags):
    """현재 상태 라벨 생성"""
    rsi = cur.RSI_TEMA
    if rsi > 70:
        return "과매수 구간"
    elif rsi < 30:
        return "과매도 구간"
    elif flags.get('cross'):
        return "상승 신호"
    elif cur.MACD_OSC > 0:
        return "상승 추세"
    else:
        return "관찰 필요"

def get_current_status_description(df, flags):
    """현재 상태 설명 생성"""
    cur = df.iloc[-1]
    descriptions = []
    
    # RSI 상태
    rsi = cur.RSI_TEMA
    if rsi > 70:
        descriptions.append("과매수 상태로 조정 가능성")
    elif rsi < 30:
        descriptions.append("과매도 상태로 반등 가능성")
    
    # MACD 상태
    if cur.MACD_OSC > 0:
        descriptions.append("상승 모멘텀 유지")
    else:
        descriptions.append("하락 모멘텀 지속")
    
    # 거래량 상태
    vol_ratio = cur.volume / cur.VOL_MA5 if cur.VOL_MA5 > 0 else 1
    if vol_ratio > 2:
        descriptions.append("거래량 급증")
    elif vol_ratio < 0.5:
        descriptions.append("거래량 감소")
    
    return ", ".join(descriptions) if descriptions else "일반적인 상태"


@app.get('/analyze-friendly')
def analyze_friendly(name_or_code: str):
    """종목의 현재 상태를 분석하여 사용자 친화적으로 제공 (메인 분석 기능)"""
    try:
        # 기본 분석 실행
        analysis_result = analyze(name_or_code)
        
        if not analysis_result.ok:
            return {
                "ok": False,
                "error": analysis_result.error,
                "analysis": None
            }
        
        # 현재 상태 분석 생성
        from user_friendly_analysis import get_user_friendly_analysis
        current_analysis = get_user_friendly_analysis(analysis_result)
        
        return {
            "ok": True,
            "ticker": analysis_result.item.ticker,
            "name": analysis_result.item.name,
            "current_price": float(analysis_result.item.indicators.close),
            "change_rate": getattr(analysis_result.item.indicators, 'change_rate', 0.0),
            "analysis": current_analysis,
            "error": None
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"분석 중 오류가 발생했습니다: {str(e)}",
            "analysis": None
        }


@app.get('/positions', response_model=PositionResponse)
def get_positions():
    """포지션 목록 조회 (현재가 및 수익률 계산 포함)"""
    _init_positions_table()
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, ticker, name, entry_date, quantity, score, strategy,
                       current_return_pct, max_return_pct, exit_date, status, created_at, updated_at
                FROM positions
                ORDER BY created_at DESC
            """)
            rows = cur.fetchall()
        
        items = []
        for row in rows:
            if isinstance(row, dict):
                data = row
            else:
                columns = [
                    "id", "ticker", "name", "entry_date", "quantity", "score", "strategy",
                    "current_return_pct", "max_return_pct", "exit_date", "status",
                    "created_at", "updated_at"
                ]
                data = dict(zip(columns, row))
            
            id_ = data.get("id")
            ticker = data.get("ticker")
            name = data.get("name")
            entry_date = data.get("entry_date")
            quantity = data.get("quantity")
            score = data.get("score")
            strategy = data.get("strategy")
            current_return_pct = data.get("current_return_pct")
            max_return_pct = data.get("max_return_pct")
            exit_date = data.get("exit_date")
            status = data.get("status")
            
            entry_date_str = None
            if hasattr(entry_date, "strftime"):
                entry_date_str = entry_date.strftime('%Y%m%d')
            elif isinstance(entry_date, str):
                entry_date_str = entry_date.replace('-', '')
            else:
                entry_date_str = None
            
            if status == 'open':
                try:
                    returns_data = calculate_returns(ticker, entry_date_str) if entry_date_str else None
                    if returns_data:
                        current_return_pct = returns_data.get('current_return')
                        max_return_pct = returns_data.get('max_return')
                except Exception as e:
                    print(f"수익률 계산 오류 ({ticker}): {e}")
                    current_return_pct = None
                    max_return_pct = None
            
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
        
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO positions (ticker, name, entry_date, quantity, score, strategy, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'open')
                RETURNING id
            """, (
                request.ticker,
                name,
                request.entry_date,
                request.quantity,
                request.score,
                request.strategy,
            ))
            new_id_row = cur.fetchone()
            new_id = new_id_row['id'] if new_id_row and isinstance(new_id_row, dict) else (new_id_row[0] if new_id_row else None)
        
        return {"ok": True, "id": new_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get('/scan_positions')
def get_scan_positions():
    """스캔된 종목들 중 포지션이 있는 종목들의 수익률 조회"""
    _init_positions_table()
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, ticker, name, entry_date, quantity, score, strategy,
                       current_return_pct, max_return_pct, exit_date, status, created_at, updated_at
                FROM positions
                WHERE status = 'open'
                ORDER BY created_at DESC
            """)
            rows = cur.fetchall()
        
        items = []
        for row in rows:
            if isinstance(row, dict):
                data = row
            else:
                columns = [
                    "id", "ticker", "name", "entry_date", "quantity", "score", "strategy",
                    "current_return_pct", "max_return_pct", "exit_date", "status",
                    "created_at", "updated_at"
                ]
                data = dict(zip(columns, row))
            
            id_ = data.get("id")
            ticker = data.get("ticker")
            name = data.get("name")
            entry_date = data.get("entry_date")
            quantity = data.get("quantity")
            score = data.get("score")
            strategy = data.get("strategy")
            current_return_pct = data.get("current_return_pct")
            max_return_pct = data.get("max_return_pct")
            
            entry_date_str = None
            if hasattr(entry_date, "strftime"):
                entry_date_str = entry_date.strftime('%Y%m%d')
                entry_date_display = entry_date.strftime('%Y-%m-%d')
            elif isinstance(entry_date, str):
                entry_date_str = entry_date.replace('-', '')
                entry_date_display = entry_date
            else:
                entry_date_display = entry_date
            
            # 현재 수익률과 최대 수익률 계산
            try:
                returns_data = calculate_returns(ticker, entry_date_str) if entry_date_str else None
                if returns_data:
                    current_return_pct = returns_data.get('current_return')
                    max_return_pct = returns_data.get('max_return')
            except Exception:
                current_return_pct = None
                max_return_pct = None
            
            items.append({
                'ticker': ticker,
                'name': name,
                'entry_date': entry_date_display,
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
        entry_dt = entry_date or datetime.now().strftime('%Y%m%d')
        try:
            entry_date_obj = datetime.strptime(entry_dt, "%Y%m%d").date()
        except Exception:
            entry_date_obj = datetime.now().date()
            entry_dt = entry_date_obj.strftime("%Y%m%d")

        with db_manager.get_cursor(commit=True) as cur:
            for code in universe:
                try:
                    df = api.get_ohlcv(code, config.ohlcv_count)
                    if df.empty or len(df) < 21:
                        continue
                    df = compute_indicators(df)
                    matched, sig_true, sig_total = match_stats(df)
                    score, flags = score_conditions(df)
                    
                    if matched and score >= score_threshold:
                        cur.execute(
                            "SELECT id FROM positions WHERE ticker = %s AND status = 'open'",
                            (code,),
                        )
                        existing = cur.fetchone()
                        if existing:
                            continue
                        
                        name = api.get_stock_name(code)
                        current_price = float(df.iloc[-1].close)
                        strategy_label = flags.get('label', '') if isinstance(flags, dict) else ''
                        
                        cur.execute("""
                            INSERT INTO positions (ticker, name, entry_date, quantity, score, strategy, status)
                            VALUES (%s, %s, %s, %s, %s, %s, 'open')
                        """, (
                            code,
                            name,
                            entry_date_obj,
                            default_quantity,
                            score,
                            strategy_label,
                        ))
                        
                        if cur.rowcount:
                            added_positions.append({
                                'ticker': code,
                                'name': name,
                                'entry_price': current_price,
                                'quantity': default_quantity,
                                'score': score
                            })
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
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("SELECT id FROM positions WHERE id = %s", (position_id,))
            row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "포지션을 찾을 수 없습니다"}
            
            if request.exit_date:
                cur.execute("""
                    UPDATE positions
                    SET exit_date = %s,
                        status = 'closed',
                        updated_at = NOW()
                    WHERE id = %s
                """, (request.exit_date, position_id))
        
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_position(position_id: int):
    """포지션 삭제"""
    _init_positions_table()
    try:
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM positions WHERE id = %s", (position_id,))
        
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def get_available_scan_dates():
    """사용 가능한 스캔 날짜 목록을 가져옵니다."""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("SELECT DISTINCT date FROM scan_rank ORDER BY date DESC")
            rows = cur.fetchall()
        
        if not rows:
            return {"ok": False, "error": "스캔 결과가 없습니다."}
        
        # 날짜 형식을 YYYYMMDD로 통일
        normalized_dates = []
        for row in rows:
            raw_date = row.get('date') if isinstance(row, dict) else row[0]
            try:
                if hasattr(raw_date, "strftime"):
                    formatted_date = raw_date.strftime('%Y%m%d')
                else:
                    date_str = str(raw_date)
                    if len(date_str) == 8 and date_str.isdigit():
                        formatted_date = date_str
                    elif len(date_str) == 10 and date_str.count('-') == 2:
                        formatted_date = date_str.replace('-', '')
                    else:
                        continue
                normalized_dates.append(formatted_date)
            except:
                continue
        
        # 중복 제거 및 정렬 (최신순)
        unique_dates = sorted(list(set(normalized_dates)), reverse=True)
        
        return {"ok": True, "dates": unique_dates}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/scan-by-date/{date}")
async def get_scan_by_date(date: str, scanner_version: Optional[str] = None):
    """특정 날짜의 스캔 결과를 가져옵니다. (YYYYMMDD 형식)
    
    Args:
        date: 날짜 (YYYYMMDD 형식)
        scanner_version: 스캐너 버전 ('v1', 'v2', 또는 'v2-lite'). None이면 DB 설정 사용
    """
    try:
        from datetime import datetime

        def _row_to_dict(row):
            if isinstance(row, dict):
                return row
            keys = [
                "code", "name", "score", "score_label", "current_price", "volume",
                "change_rate", "market", "strategy", "indicators", "trend",
                "flags", "details", "returns", "recurrence", "scanner_version",
                "anchor_date", "anchor_close", "anchor_price_type", "anchor_source"
            ]
            return dict(zip(keys, row))
        
        try:
            formatted_date = normalize_date(date)
        except ValueError:
            return {"ok": False, "error": "날짜 형식이 올바르지 않습니다. YYYYMMDD 형식을 사용해주세요."}
        
        from date_helper import yyyymmdd_to_date
        target_date = yyyymmdd_to_date(formatted_date)
        
        # 스캐너 버전 결정: 파라미터 > DB 설정 > 기본값
        # 'us_v2', 'v3'도 허용 (미국 주식 스캔, v3 엔진)
        if scanner_version and scanner_version in ['v1', 'v2', 'us_v2', 'v3']:
            target_scanner_version = scanner_version
        else:
            # DB 설정에서 읽기
            try:
                from scanner_settings_manager import get_scanner_version
                target_scanner_version = get_scanner_version()
            except Exception:
                from config import config
                target_scanner_version = getattr(config, 'scanner_version', 'v1')
        
        with db_manager.get_cursor(commit=False) as cur:
            # us_v2, v2-lite, v3는 절대 다른 버전으로 fallback하지 않음
            if target_scanner_version == 'v3':
                # v3는 strategy로 구분 (v2_lite는 UI에서 숨김, 백데이터로만 저장)
                cur.execute("""
                    SELECT code, name, score, score_label, close_price AS current_price, volume,
                           change_rate, market, strategy, indicators, trend, flags, details, returns, recurrence,
                           scanner_version, anchor_date, anchor_close, anchor_price_type, anchor_source
                    FROM scan_rank
                    WHERE date = %s AND scanner_version = 'v3' 
                      AND strategy != 'v2_lite'
                      AND ((score >= 1 AND score <= 10) OR code = 'NORESULT')
                    ORDER BY 
                        CASE WHEN code = 'NORESULT' THEN 0 ELSE 1 END,
                        CASE strategy
                            WHEN 'midterm' THEN 1
                            ELSE 2
                        END,
                        CASE WHEN code = 'NORESULT' THEN 0 ELSE score END DESC
                """, (target_date,))
                rows = cur.fetchall()
                detected_version = 'v3'
            elif target_scanner_version == 'us_v2':
                cur.execute("""
                    SELECT code, name, score, score_label, close_price AS current_price, volume,
                           change_rate, market, strategy, indicators, trend, flags, details, returns, recurrence,
                           scanner_version, anchor_date, anchor_close, anchor_price_type, anchor_source
                    FROM scan_rank
                    WHERE date = %s AND scanner_version = 'us_v2'
                    ORDER BY CASE WHEN code = 'NORESULT' THEN 0 ELSE score END DESC
                """, (target_date,))
                rows = cur.fetchall()
                detected_version = 'us_v2'
            elif target_scanner_version == 'v2-lite':
                cur.execute("""
                    SELECT code, name, score, score_label, close_price AS current_price, volume,
                           change_rate, market, strategy, indicators, trend, flags, details, returns, recurrence,
                           scanner_version, anchor_date, anchor_close, anchor_price_type, anchor_source
                    FROM scan_rank
                    WHERE date = %s AND scanner_version = 'v2-lite'
                    ORDER BY CASE WHEN code = 'NORESULT' THEN 0 ELSE score END DESC
                """, (target_date,))
                rows = cur.fetchall()
                detected_version = 'v2-lite'
            else:
                # v1/v2는 서로 fallback 가능
                cur.execute("""
                    WITH version_check AS (
                        SELECT scanner_version
                        FROM scan_rank
                        WHERE date = %s AND scanner_version = %s
                        LIMIT 1
                    ),
                    fallback_version AS (
                        SELECT scanner_version
                        FROM scan_rank
                        WHERE date = %s AND scanner_version IN ('v1', 'v2')
                        ORDER BY scanner_version DESC
                        LIMIT 1
                    )
                    SELECT code, name, score, score_label, close_price AS current_price, volume,
                           change_rate, market, strategy, indicators, trend, flags, details, returns, recurrence,
                           scanner_version, anchor_date, anchor_close, anchor_price_type, anchor_source
                    FROM scan_rank
                    WHERE date = %s 
                    AND scanner_version = COALESCE(
                        (SELECT scanner_version FROM version_check),
                        (SELECT scanner_version FROM fallback_version),
                        %s
                    )
                    ORDER BY CASE WHEN code = 'NORESULT' THEN 0 ELSE score END DESC
                """, (target_date, target_scanner_version, target_date, target_date, target_scanner_version))
                rows = cur.fetchall()
                
                # detected_version 추출 (첫 번째 행에서)
                detected_version = target_scanner_version
                if rows:
                    # 실제 사용된 버전 확인을 위해 별도 쿼리 (필요시)
                    cur.execute("""
                        SELECT DISTINCT scanner_version
                        FROM scan_rank
                        WHERE date = %s AND scanner_version IN ('v1', 'v2')
                        ORDER BY scanner_version DESC
                        LIMIT 1
                    """, (target_date,))
                    version_row = cur.fetchone()
                    if version_row:
                        if isinstance(version_row, dict):
                            detected_version = version_row.get("scanner_version", target_scanner_version)
                        else:
                            detected_version = version_row[0] if version_row[0] else target_scanner_version
        
        # us_v2 데이터가 없으면 NORESULT 반환
        if not rows and target_scanner_version == 'us_v2':
            return {
                "ok": True,
                "data": {
                    "as_of": formatted_date,
                    "scan_date": formatted_date,
                    "is_latest": False,
                    "universe_count": 0,
                    "matched_count": 0,
                    "items": [{"ticker": "NORESULT", "name": "추천종목 없음", "score": 0.0, "score_label": "추천종목 없음"}],
                    "scanner_version": "us_v2"
                }
            }
        
        if not rows:
            return {"ok": False, "error": f"{date} 날짜의 스캔 결과가 없습니다."}

        # recurrence 보강: DB에 저장된 recurrence가 비어있는 경우에도 v2 화면에서 재등장 정보를 노출할 수 있도록
        # scan_rank 이력 기반으로 계산한 recurrence를 주입한다. (저장값 우선, 없으면 계산값)
        try:
            codes_for_recurrence = []
            for r in rows:
                d = _row_to_dict(r)
                c = d.get("code")
                if c and c != "NORESULT":
                    codes_for_recurrence.append(c)
            recurrence_data_map = get_recurrence_data(list(set(codes_for_recurrence)), formatted_date)
        except Exception:
            recurrence_data_map = {}
        
        # DB에 저장된 returns 데이터 우선 사용 (성능 최적화)
        # 필요한 경우에만 실시간 계산
        returns_data = {}
        codes_needing_calculation = []
        
        for row in rows:
            data = _row_to_dict(row)
            code = data.get("code")
            if code == 'NORESULT':
                continue
            
            # DB에 저장된 returns 데이터 확인
            returns_raw = data.get("returns")
            should_recalculate = False
            
            if returns_raw:
                try:
                    if isinstance(returns_raw, str):
                        returns_dict = json.loads(returns_raw)
                    else:
                        returns_dict = returns_raw
                    
                    # 저장된 데이터가 유효한지 확인 (빈 딕셔너리나 None 값 제외)
                    if isinstance(returns_dict, dict) and returns_dict and returns_dict.get('current_return') is not None:
                        # 스캔일이 오늘이 아니면 항상 재계산 (매일 최신 수익률 표시를 위해)
                        from date_helper import get_kst_now
                        today_str = get_kst_now().strftime('%Y%m%d')
                        if formatted_date < today_str:
                            # 전일 이전 스캔이면 항상 재계산하여 최신 수익률 표시
                            should_recalculate = True
                        else:
                            # 당일 스캔이면 저장된 데이터 사용
                            returns_data[code] = returns_dict
                            continue
                except:
                    pass
            
            # DB에 없거나 유효하지 않거나 재계산이 필요한 경우
            if should_recalculate or not returns_raw:
                codes_needing_calculation.append(code)
        
        # 필요한 종목만 배치 계산
        if codes_needing_calculation:
            from services.returns_service import calculate_returns_batch
            try:
                # 재등장 종목인 경우 최초 추천일 기준으로 수익률 계산
                # 먼저 recurrence 데이터를 파싱하여 최초 추천일 확인
                recurrence_map = {}
                for row in rows:
                    row_data = _row_to_dict(row)
                    code = row_data.get("code")
                    if code in codes_needing_calculation:
                        recurrence_raw = row_data.get("recurrence")
                        if recurrence_raw:
                            try:
                                recurrence_dict = json.loads(recurrence_raw) if isinstance(recurrence_raw, str) else recurrence_raw
                                if recurrence_dict and recurrence_dict.get("appeared_before") and recurrence_dict.get("first_as_of"):
                                    recurrence_map[code] = recurrence_dict.get("first_as_of")
                            except:
                                pass
                
                # DB의 close_price를 scan_price로 사용 (스캔일 종가)
                scan_prices = {}
                scan_dates = {}
                for row in rows:
                    row_data = _row_to_dict(row)
                    code = row_data.get("code")
                    if code in codes_needing_calculation:
                        # 재등장 종목인 경우 최초 추천일 기준으로 계산
                        if code in recurrence_map:
                            first_as_of = recurrence_map[code]
                            scan_dates[code] = first_as_of
                            # 최초 추천일의 종가 조회
                            try:
                                from kiwoom_api import api
                                df_first = api.get_ohlcv(code, 1, first_as_of)
                                if not df_first.empty:
                                    scan_prices[code] = float(df_first.iloc[-1]['close'])
                                else:
                                    # 최초 추천일 데이터가 없으면 현재 스캔일 종가 사용
                                    close_price = row_data.get("current_price")
                                    if close_price and close_price > 0:
                                        scan_prices[code] = float(close_price)
                                    scan_dates[code] = formatted_date
                            except:
                                # 실패 시 현재 스캔일 종가 사용
                                close_price = row_data.get("current_price")
                                if close_price and close_price > 0:
                                    scan_prices[code] = float(close_price)
                                scan_dates[code] = formatted_date
                        else:
                            # 일반 종목은 현재 스캔일 기준
                            close_price = row_data.get("current_price")
                            if close_price and close_price > 0:
                                scan_prices[code] = float(close_price)
                            scan_dates[code] = formatted_date
                
                # 재등장 종목과 일반 종목을 분리하여 계산
                recurring_codes = [code for code in codes_needing_calculation if code in recurrence_map]
                normal_codes = [code for code in codes_needing_calculation if code not in recurrence_map]
                
                # 재등장 종목은 각각 최초 추천일 기준으로 계산
                for code in recurring_codes:
                    if code in scan_dates and code in scan_prices:
                        try:
                            from services.returns_service import calculate_returns
                            calculated_returns = calculate_returns(code, scan_dates[code], None, scan_prices[code])
                            if calculated_returns:
                                returns_data[code] = calculated_returns
                        except Exception as e:
                            print(f"재등장 종목 수익률 계산 오류 ({code}): {e}")
                
                # 일반 종목은 배치 처리
                if normal_codes:
                    normal_scan_prices = {code: scan_prices[code] for code in normal_codes if code in scan_prices}
                    calculated_returns = calculate_returns_batch(normal_codes, formatted_date, None, normal_scan_prices)
                    returns_data.update(calculated_returns)
            except Exception as e:
                print(f"배치 수익률 계산 오류: {e}")
        
        # 재등장 정보: DB에 저장된 정보를 사용하되, days_since_last만 현재 날짜 기준으로 실시간 계산
        # 성능 최적화: 전체 재등장 이력을 다시 조회하지 않고, 저장된 정보 + days_since_last만 업데이트
        from date_helper import yyyymmdd_to_date
        from datetime import datetime
        today_date_str = datetime.now().strftime('%Y%m%d')
        today_date_obj = yyyymmdd_to_date(today_date_str)
        
        items = []
        for row in rows:
            data = _row_to_dict(row)
            indicators = data.get("indicators")
            trend = data.get("trend")
            flags = data.get("flags")
            details = data.get("details")
            returns_raw = data.get("returns")
            recurrence_raw = data.get("recurrence")
            
            code = data.get("code")
            name = data.get("name")
            score = data.get("score")
            score_label = data.get("score_label")
            current_price = data.get("current_price")
            volume = data.get("volume")
            # change_rate 정규화: scanner_version이 'v2' 또는 'v3'인 경우 이미 퍼센트 형태로 저장됨
            # v1의 경우 소수 형태일 수 있으므로 변환 필요
            change_rate_raw = data.get("change_rate") or 0.0
            change_rate = float(change_rate_raw)
            # DB에서 직접 scanner_version 확인 (v2, v3는 이미 퍼센트 형태)
            row_scanner_version = data.get("scanner_version") or (detected_version if 'detected_version' in locals() else target_scanner_version)
            if row_scanner_version not in ['v2', 'v3'] and abs(change_rate) < 1.0 and change_rate != 0.0:
                # 소수로 저장된 경우 퍼센트로 변환 (v1만 해당)
                change_rate = change_rate * 100
            change_rate = round(change_rate, 2)  # 퍼센트로 정규화, 소수점 2자리
            market = data.get("market")
            # flags 파싱 (strategy 추출을 위해 먼저 파싱)
            flags_dict = flags
            if isinstance(flags, str) and flags:
                try:
                    flags_dict = json.loads(flags)
                except:
                    flags_dict = {}
            elif not flags:
                flags_dict = {}
            
            # strategy 추출: DB 컬럼 > flags.trading_strategy (우선순위)
            strategy = data.get("strategy")  # DB 컬럼에서 먼저 시도 (v1 호환성)
            
            # flags에서 trading_strategy가 있으면 사용 (v2, DB 컬럼이 없거나 None인 경우)
            if not strategy and flags_dict and isinstance(flags_dict, dict):
                strategy = flags_dict.get('trading_strategy')
            
            # 최종 fallback: strategy가 여전히 없으면 None (프론트엔드에서 "관찰"로 처리)
            
            # 가격 변수 정리:
            # - scan_date_close_price: 스캔일 종가 (DB의 current_price 컬럼)
            # - today_close_price: 오늘 종가 (returns에서 계산)
            # - display_price: 프론트엔드에 표시할 가격 (오늘 종가 우선, 없으면 스캔일 종가)
            
            scan_date_close_price = current_price  # DB의 current_price = 스캔일 종가
            
            # anchor_close 우선 사용 (추천 생성 시점에 저장된 값)
            anchor_close = data.get("anchor_close")
            anchor_date = data.get("anchor_date")
            anchor_price_type = data.get("anchor_price_type", "CLOSE")
            anchor_source = data.get("anchor_source", "KRX_EOD")
            
            # 추천일 종가 (recommended_price) - anchor_close 우선, 없으면 스캔일 종가
            if anchor_close and anchor_close > 0:
                recommended_price = float(anchor_close)
            else:
                recommended_price = scan_date_close_price if scan_date_close_price and scan_date_close_price > 0 else None
            
            # 수익률 계산 (배치 처리 결과 사용)
            returns_info = returns_data.get(code) if code != 'NORESULT' else None
            today_close_price = None  # 오늘 종가 (returns에서 가져옴)
            if returns_info and isinstance(returns_info, dict) and returns_info.get('current_return') is not None:
                current_return = returns_info.get('current_return')
                max_return = returns_info.get('max_return', current_return)
                min_return = returns_info.get('min_return', current_return)
                days_elapsed = returns_info.get('days_elapsed', 0)
                # returns_info에 scan_price가 있지만, anchor_close가 우선 (재계산 방지)
                # anchor_close가 없을 때만 returns_info.scan_price 사용
                if not anchor_close or anchor_close <= 0:
                    if returns_info.get('scan_price'):
                        recommended_price = returns_info.get('scan_price')
                # returns_info에 current_price가 있으면 오늘 종가로 사용
                if returns_info.get('current_price'):
                    today_close_price = returns_info.get('current_price')
                # returns_info에 scan_price가 없으면 DB의 close_price 사용 (스캔일 종가)
                # 이미 위에서 설정했으므로 그대로 유지
            else:
                # returns_info가 없으면 수익률 데이터 없음으로 설정
                # DB에 저장된 returns 데이터 확인
                if returns_raw:
                    try:
                        if isinstance(returns_raw, str):
                            returns_dict = json.loads(returns_raw)
                        else:
                            returns_dict = returns_raw
                        
                        if isinstance(returns_dict, dict) and returns_dict.get('current_return') is not None:
                            current_return = returns_dict.get('current_return')
                            max_return = returns_dict.get('max_return', current_return)
                            min_return = returns_dict.get('min_return', current_return)
                            days_elapsed = returns_dict.get('days_elapsed', 0)
                            # anchor_close가 우선 (재계산 방지)
                            if not anchor_close or anchor_close <= 0:
                                if returns_dict.get('scan_price'):
                                    recommended_price = returns_dict.get('scan_price')
                            if returns_dict.get('current_price'):
                                today_close_price = returns_dict.get('current_price')
                        else:
                            # DB에 returns가 있지만 current_return이 None인 경우
                            current_return = 0
                            max_return = 0
                            min_return = 0
                            days_elapsed = 0
                    except:
                        current_return = 0
                        max_return = 0
                        min_return = 0
                        days_elapsed = 0
                else:
                    # returns_info도 없고 DB returns도 없는 경우
                    # v3의 경우에도 수익률 카드를 표시하기 위해 기본값 설정
                    current_return = 0
                    max_return = 0
                    min_return = 0
                    days_elapsed = 0
                # recommended_price는 이미 DB의 close_price로 설정되어 있음
                # recommended_price가 None이면 스캔일 종가 사용
                if not recommended_price or recommended_price <= 0:
                    recommended_price = scan_date_close_price if scan_date_close_price and scan_date_close_price > 0 else None
            
            # JSON 파싱 최적화: 한 번만 파싱
            indicators_dict = indicators
            if isinstance(indicators, str) and indicators:
                try:
                    indicators_dict = json.loads(indicators)
                except:
                    indicators_dict = {}
            elif not indicators:
                indicators_dict = {}
            
            trend_dict = trend
            if isinstance(trend, str) and trend:
                try:
                    trend_dict = json.loads(trend)
                except:
                    trend_dict = {}
            elif not trend:
                trend_dict = {}
            
            # flags는 이미 위에서 파싱됨 (strategy 추출을 위해)
            # 중복 파싱 방지
            if 'flags_dict' not in locals():
                if isinstance(flags, str) and flags:
                    try:
                        flags_dict = json.loads(flags)
                    except:
                        flags_dict = {}
                elif not flags:
                    flags_dict = {}
                else:
                    flags_dict = flags
            
            # v3의 경우 target_profit이 없으면 strategy에 따라 기본값 설정
            if not flags_dict.get("target_profit"):
                if strategy == "v2_lite":
                    flags_dict["target_profit"] = 0.05  # 5%
                    flags_dict["stop_loss"] = 0.02  # 2%
                    flags_dict["holding_period"] = 14  # 2주
                elif strategy == "midterm":
                    flags_dict["target_profit"] = 0.10  # 10%
                    flags_dict["stop_loss"] = 0.07  # 7%
                    flags_dict["holding_period"] = 15  # 15일
            
            # stop_loss가 없으면 기본값 설정 (v2_lite 기본값 사용)
            if flags_dict.get("stop_loss") is None:
                flags_dict["stop_loss"] = 0.02  # 2% 기본값
            
            # flags_dict는 나중에 item 생성 시 사용됨 (item은 아직 정의되지 않음)
            
            details_dict = details
            if isinstance(details, str) and details:
                try:
                    details_dict = json.loads(details)
                except:
                    details_dict = {}
            elif not details:
                details_dict = {}
            
            # 재등장 정보: DB에 저장된 정보를 사용하되, days_since_last만 현재 날짜 기준으로 실시간 계산
            recurrence_dict = recurrence_raw
            if isinstance(recurrence_raw, str) and recurrence_raw:
                try:
                    recurrence_dict = json.loads(recurrence_raw)
                except:
                    recurrence_dict = {}
            elif not recurrence_raw:
                recurrence_dict = {}
            
            # DB 저장값이 비어있으면 이력 기반 계산값으로 보강 (v2 스캔 화면 재등장 정보 노출)
            if (not recurrence_dict) and code and code != "NORESULT":
                recurrence_dict = recurrence_data_map.get(code, {}) or {}
            
            # days_since_last 실시간 계산 (last_as_of가 있으면 현재 날짜 기준으로 업데이트)
            if recurrence_dict and recurrence_dict.get("appeared_before") and recurrence_dict.get("last_as_of"):
                try:
                    last_as_of_str = recurrence_dict.get("last_as_of")
                    if last_as_of_str:
                        last_as_of_date = yyyymmdd_to_date(last_as_of_str)
                        days_since_last = (today_date_obj - last_as_of_date).days
                        recurrence_dict["days_since_last"] = days_since_last
                except Exception as e:
                    # 계산 실패 시 기존 값 유지
                    pass
            
            # 재등장 종목인 경우 최초 추천일 기준으로 recommended_date와 recommended_price 설정
            is_recurring = recurrence_dict and recurrence_dict.get("appeared_before", False)
            first_as_of = recurrence_dict.get("first_as_of") if is_recurring else None
            recommended_date = formatted_date  # 기본값: 현재 스캔일
            
            if is_recurring and first_as_of:
                recommended_date = first_as_of
                # 최초 추천일의 종가를 조회하여 recommended_price 설정
                try:
                    from kiwoom_api import api
                    df_first = api.get_ohlcv(code, 1, first_as_of)
                    if not df_first.empty:
                        recommended_price = float(df_first.iloc[-1]['close'])
                except:
                    pass  # 실패 시 기존 값 유지
            
            # v3 화면에서 수익률 카드 표시를 위해 recommended_date와 recommended_price 보장
            # recommended_date가 없으면 스캔일 사용
            if not recommended_date:
                recommended_date = formatted_date
            # recommended_price가 없으면 스캔일 종가 사용
            # display_price는 나중에 설정되므로 먼저 scan_date_close_price 사용
            if not recommended_price or recommended_price <= 0:
                recommended_price = scan_date_close_price if scan_date_close_price and scan_date_close_price > 0 else None
            
            # 프론트엔드에 표시할 가격: 오늘 종가 우선, 없으면 스캔일 종가
            display_price = today_close_price if today_close_price and today_close_price > 0 else scan_date_close_price
            
            # recommended_price가 여전히 None이면 display_price 사용 (수익률 카드 표시를 위해)
            if not recommended_price or recommended_price <= 0:
                recommended_price = display_price if display_price and display_price > 0 else None
            
            # 등락률 재계산: 오늘 종가가 있으면 오늘 기준 등락률 계산
            display_change_rate = change_rate  # 기본값: 스캔일 등락률
            if today_close_price and today_close_price > 0:
                try:
                    # OHLCV 데이터로 직접 계산 (더 안정적)
                    from date_helper import get_kst_now
                    today_str = get_kst_now().strftime('%Y%m%d')
                    df_today = api.get_ohlcv(code, 2, today_str)
                    if not df_today.empty and len(df_today) >= 2:
                        today_close = float(df_today.iloc[-1]['close'])
                        prev_close = float(df_today.iloc[-2]['close'])
                        if prev_close > 0:
                            calculated_rate = ((today_close - prev_close) / prev_close) * 100
                            display_change_rate = round(calculated_rate, 2)
                    else:
                        # OHLCV 실패 시 키움 API 시도
                        quote = api.get_stock_quote(code)
                        if quote and quote.get("change_rate") is not None and quote.get("change_rate") != 0.0:
                            display_change_rate = quote.get("change_rate")
                except Exception as e:
                    print(f"등락률 재계산 오류 ({code}): {e}")
                    # 오류 시 기존 change_rate 유지
            
            item = {
                "ticker": code,
                "name": name,
                "score": score,
                "score_label": score_label,
                "current_price": display_price,  # 오늘 종가 우선, 없으면 스캔일 종가
                "volume": volume,
                "change_rate": display_change_rate,  # 오늘 기준 등락률
                "market": market,
                "strategy": strategy,
                "recommended_date": recommended_date if recommended_date else formatted_date,  # 재등장 종목인 경우 최초 추천일, 없으면 스캔일
                "recommended_price": recommended_price if (recommended_price and recommended_price > 0) else (scan_date_close_price if (scan_date_close_price and scan_date_close_price > 0) else display_price),  # 재등장 종목인 경우 최초 추천가, 없으면 스캔일 종가, 그것도 없으면 표시 가격
                "current_return": current_return if current_return is not None else 0,
                "indicators": indicators_dict,
                "trend": trend_dict,
                "flags": flags_dict,
                "details": details_dict,
                "returns": {
                    "current_return": current_return,
                    "max_return": max_return,
                    "min_return": min_return,
                    "days_elapsed": days_elapsed,
                    "current_price": today_close_price if today_close_price else None,  # 오늘 종가
                    "scan_price": float(anchor_close) if anchor_close and anchor_close > 0 else None  # anchor_close를 scan_price로 설정
                },
                # V2 UI를 위한 추가 필드 (중복이지만 호환성을 위해 유지)
                "recommended_price": recommended_price if (recommended_price and recommended_price > 0) else (scan_date_close_price if (scan_date_close_price and scan_date_close_price > 0) else display_price),
                "recommended_date": recommended_date if recommended_date else formatted_date,  # 재등장 종목인 경우 최초 추천일, 없으면 스캔일
                "current_return": current_return if current_return is not None else 0,  # None인 경우 0으로 처리
                "recurrence": recurrence_dict
            }
            items.append(item)
        
        # 시장 상황 데이터 조회
        market_condition = None
        try:
            with db_manager.get_cursor(commit=False) as cur_mc:
                # market_conditions.date는 TEXT 타입이므로 문자열 형식으로 변환
                # target_date는 DATE 타입, formatted_date는 YYYYMMDD 문자열
                if isinstance(target_date, str):
                    # 이미 문자열이면 YYYY-MM-DD 형식으로 정규화
                    if len(target_date) == 8 and '-' not in target_date:
                        # YYYYMMDD 형식
                        query_date = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:8]}"
                    elif '-' in target_date:
                        # 이미 YYYY-MM-DD 형식
                        query_date = target_date
                    else:
                        query_date = target_date
                else:
                    # DATE 타입이면 문자열로 변환 (YYYY-MM-DD)
                    if hasattr(target_date, 'strftime'):
                        query_date = target_date.strftime('%Y-%m-%d')
                    else:
                        query_date = str(target_date)
                
                # institution_flow 컬럼 존재 여부 확인
                cur_mc.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'market_conditions' AND column_name = 'institution_flow'
                """)
                has_institution_flow = cur_mc.fetchone() is not None
                
                # 동적으로 컬럼 선택
                if has_institution_flow:
                    cur_mc.execute("""
                        SELECT market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                               sector_rotation, foreign_flow, institution_flow, volume_trend,
                               min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                               trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                               foreign_flow_label, institution_flow_label, volume_trend_label, adjusted_params, analysis_notes,
                               midterm_regime, short_term_risk_score, final_regime, longterm_regime
                        FROM market_conditions WHERE date = %s
                    """, (query_date,))
                else:
                    cur_mc.execute("""
                        SELECT market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                               sector_rotation, foreign_flow, NULL as institution_flow, volume_trend,
                               min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                               trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                               foreign_flow_label, NULL as institution_flow_label, volume_trend_label, adjusted_params, analysis_notes,
                               midterm_regime, short_term_risk_score, final_regime, longterm_regime
                        FROM market_conditions WHERE date = %s
                    """, (query_date,))
                row_mc = cur_mc.fetchone()
            
            if row_mc:
                if isinstance(row_mc, dict):
                    values = row_mc
                else:
                    keys = [
                        "market_sentiment", "sentiment_score", "kospi_return", "volatility", "rsi_threshold",
                        "sector_rotation", "foreign_flow", "institution_flow", "volume_trend",
                        "min_signals", "macd_osc_min", "vol_ma5_mult", "gap_max", "ext_from_tema20_max",
                        "trend_metrics", "breadth_metrics", "flow_metrics", "sector_metrics", "volatility_metrics",
                        "foreign_flow_label", "institution_flow_label", "volume_trend_label", "adjusted_params", "analysis_notes",
                        "midterm_regime", "short_term_risk_score", "final_regime", "longterm_regime"
                    ]
                    values = dict(zip(keys, row_mc))
                
                def _ensure_json(value):
                    if isinstance(value, str) and value:
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            return {}
                    return value or {}

                trend_metrics = _ensure_json(values.get("trend_metrics"))
                breadth_metrics = _ensure_json(values.get("breadth_metrics"))
                flow_metrics = _ensure_json(values.get("flow_metrics"))
                sector_metrics = _ensure_json(values.get("sector_metrics"))
                volatility_metrics = _ensure_json(values.get("volatility_metrics"))
                adjusted_params = _ensure_json(values.get("adjusted_params"))
                sentiment_score = values.get("sentiment_score") or 0.0
                foreign_flow_label = values.get("foreign_flow_label") or values.get("foreign_flow") or "neutral"
                institution_flow_label = values.get("institution_flow_label") or values.get("institution_flow") or "neutral"
                volume_trend_label = values.get("volume_trend_label") or values.get("volume_trend") or "normal"
                analysis_notes = values.get("analysis_notes")

                from market_analyzer import MarketCondition
                market_condition = MarketCondition(
                    date=formatted_date,
                    market_sentiment=values.get("market_sentiment"),
                    kospi_return=values.get("kospi_return"),
                    volatility=values.get("volatility"),
                    rsi_threshold=values.get("rsi_threshold"),
                    sector_rotation=values.get("sector_rotation"),
                    foreign_flow=values.get("foreign_flow"),
                    institution_flow=values.get("institution_flow"),
                    volume_trend=values.get("volume_trend"),
                    min_signals=values.get("min_signals"),
                    macd_osc_min=values.get("macd_osc_min"),
                    vol_ma5_mult=values.get("vol_ma5_mult"),
                    gap_max=values.get("gap_max"),
                    ext_from_tema20_max=values.get("ext_from_tema20_max"),
                    sentiment_score=sentiment_score,
                    trend_metrics=trend_metrics,
                    breadth_metrics=breadth_metrics,
                    flow_metrics=flow_metrics,
                    sector_metrics=sector_metrics,
                    volatility_metrics=volatility_metrics,
                    foreign_flow_label=foreign_flow_label,
                    institution_flow_label=institution_flow_label,
                    volume_trend_label=volume_trend_label,
                    adjusted_params=adjusted_params,
                    analysis_notes=analysis_notes,
                    midterm_regime=values.get("midterm_regime"),
                    short_term_risk_score=int(values.get("short_term_risk_score")) if values.get("short_term_risk_score") is not None else None,
                    final_regime=values.get("final_regime"),
                    longterm_regime=values.get("longterm_regime"),
                )
                print(f"📊 시장 상황 조회 (DB): {market_condition.market_sentiment} (유효 수익률: {market_condition.kospi_return*100:.2f}%, RSI 임계값: {market_condition.rsi_threshold})")
            else:
                print(f"ℹ️ 시장 상황 데이터 없음 (날짜: {formatted_date})")
        except Exception as e:
            print(f"⚠️ 시장 상황 DB 조회 실패: {e}")
            market_condition = None
        
        # market_condition을 dict로 변환
        market_condition_dict = None
        if market_condition:
            from dataclasses import asdict
            market_condition_dict = asdict(market_condition)
        
        # v3 케이스 판별 필드 추가 (v3일 때만, v2_lite는 UI에서 숨김)
        v3_case_info = None
        if detected_version == 'v3':
            # strategy별로 분류 (v2_lite 제외)
            midterm_items = [item for item in items if item.get("strategy") == "midterm" and item.get("ticker") != "NORESULT"]
            
            has_midterm = len(midterm_items) > 0
            has_recommendations = has_midterm
            
            active_engines = []
            if has_midterm:
                active_engines.append("midterm")
            
            # scan_date를 YYYY-MM-DD 형식으로 변환
            scan_date_formatted = f"{formatted_date[:4]}-{formatted_date[4:6]}-{formatted_date[6:8]}"
            
            v3_case_info = {
                "has_recommendations": has_recommendations,
                "active_engines": active_engines,
                "scan_date": scan_date_formatted,
                "engine_labels": {
                    "midterm": "중기 추세형"
                }
            }
        
        data = {
            "as_of": formatted_date,
            "scan_date": formatted_date,
            "is_latest": False,
            "universe_count": 100,
            "matched_count": len(items),
            "rsi_mode": "current_status",
            "rsi_period": 14,
            "rsi_threshold": market_condition.rsi_threshold if market_condition else 57.0,
            "items": items,
            "market_condition": market_condition_dict,
            "scanner_version": detected_version
        }
        data["enhanced_items"] = items
        
        # v3 케이스 정보 추가 (optional 필드)
        if v3_case_info:
            data["v3_case_info"] = v3_case_info
        
        return {"ok": True, "data": data}
        
    except Exception as e:
        return {"ok": False, "error": f"스캔 결과를 가져오는 중 오류가 발생했습니다: {str(e)}"}


# 기존 스냅샷 파일 관련 함수들은 제거됨 - DB만 사용

def get_latest_scan_from_db(scanner_version: Optional[str] = None, disable_recalculate_returns: bool = False, user_id: Optional[int] = None):
    """DB에서 직접 최신 스캔 결과를 조회하는 함수 (SSR용)
    
    Args:
        scanner_version: 스캐너 버전 ('v1', 'v2', 또는 'v2-lite'). None이면 DB 설정 사용
        disable_recalculate_returns: True이면 수익률 재계산을 절대 수행하지 않음 (v3 홈용)
        user_id: 사용자 ID (ack 필터링용, None이면 필터링 안 함)
    """
    import time
    import logging
    logger = logging.getLogger(__name__)
    start_time = time.time()
    
    logger.info(f"[get_latest_scan_from_db] 시작: scanner_version={scanner_version}, disable_recalculate={disable_recalculate_returns}, user_id={user_id}")
    
    try:
        from datetime import datetime
        
        def _row_to_dict(row):
            if isinstance(row, dict):
                return row
            # anchor 필드 포함 여부 확인 (컬럼 수로 판단)
            if len(row) >= 19:  # anchor 필드 포함
                return {desc: value for desc, value in zip(
                    ["date", "code", "name", "score", "score_label", "current_price",
                     "volume", "change_rate", "market", "strategy", "indicators",
                     "trend", "flags", "details", "returns", "recurrence",
                     "anchor_date", "anchor_close", "anchor_price_type", "anchor_source"],
                    row
                )}
            else:  # anchor 필드 없음 (하위 호환성)
                return {desc: value for desc, value in zip(
                    ["date", "code", "name", "score", "score_label", "current_price",
                     "volume", "change_rate", "market", "strategy", "indicators",
                     "trend", "flags", "details", "returns", "recurrence"],
                    row
                )}
        
        # 스캐너 버전 결정: 파라미터 > DB 설정 > 기본값
        # 'us_v2', 'v2-lite', 'v3'도 허용
        if scanner_version and scanner_version in ['v1', 'v2', 'v2-lite', 'us_v2', 'v3']:
            target_scanner_version = scanner_version
        else:
            # DB 설정에서 읽기
            try:
                from scanner_settings_manager import get_scanner_version
                target_scanner_version = get_scanner_version()
            except Exception:
                from config import config
                target_scanner_version = getattr(config, 'scanner_version', 'v1')
        
        logger.info(f"[get_latest_scan_from_db] 스캐너 버전 결정: {target_scanner_version}")
        
        # 요청한 스캐너 버전으로 최신 스캔 찾기 (우선) - 인덱스 활용
        latest_row = None
        if target_scanner_version:
            logger.info(f"[get_latest_scan_from_db] 최신 스캔 조회 시작: {target_scanner_version}")
            with db_manager.get_cursor(commit=False) as cur:
                # 인덱스 활용: idx_scan_rank_version_date_desc 사용
                cur.execute("""
                    SELECT date, scanner_version
                    FROM scan_rank
                    WHERE scanner_version = %s AND ((score >= 1 AND score <= 10) OR code = 'NORESULT')
                    ORDER BY date DESC
                    LIMIT 1
                """, (target_scanner_version,))
                version_specific_row = cur.fetchone()
                # 요청한 버전의 데이터가 있으면 사용
                if version_specific_row:
                    latest_row = version_specific_row
        
        # 요청한 버전의 데이터가 없으면, 같은 카테고리(v1/v2는 한국, us_v2는 미국, v2-lite는 한국)에서만 fallback
        # 성능 최적화: fallback 로직을 단일 쿼리로 통합
        if not latest_row:
            # us_v2, v2-lite, v3는 fallback하지 않음
            if target_scanner_version in ['us_v2', 'v2-lite', 'v3']:
                # us_v2 데이터가 없으면 빈 결과 반환
                return {
                    "ok": True,
                    "data": {
                        "as_of": None,
                        "scan_date": None,
                        "is_latest": False,
                        "universe_count": 0,
                        "matched_count": 0,
                        "items": [{"ticker": "NORESULT", "name": "추천종목 없음", "score": 0.0, "score_label": "추천종목 없음"}],
                        "scanner_version": target_scanner_version
                    }
                }
            # v1/v2는 한국 주식이므로 서로 fallback 가능 - 단일 쿼리로 통합
            with db_manager.get_cursor(commit=False) as cur:
                fallback_version = 'v2' if target_scanner_version == 'v1' else 'v1'
                # 먼저 fallback 버전 확인
                cur.execute("""
                    SELECT date, scanner_version
                    FROM scan_rank
                    WHERE scanner_version = %s AND code != 'NORESULT'
                    ORDER BY date DESC
                    LIMIT 1
                """, (fallback_version,))
                fallback_row = cur.fetchone()
                if fallback_row:
                    latest_row = fallback_row
                else:
                    # 여전히 없으면 v1/v2 중 최신 날짜 찾기 (단일 쿼리)
                    cur.execute("""
                        SELECT date, scanner_version
                        FROM scan_rank
                        WHERE scanner_version IN ('v1', 'v2') AND code != 'NORESULT'
                        ORDER BY date DESC, scanner_version DESC
                        LIMIT 1
                    """)
                    latest_row = cur.fetchone()
        
        if not latest_row:
            return {"ok": False, "error": "올바른 스캔 결과가 없습니다."}
        
        if isinstance(latest_row, dict):
            raw_date = latest_row.get("date")
            detected_version = latest_row.get("scanner_version", target_scanner_version)
        else:
            raw_date = latest_row[0]
            detected_version = latest_row[1] if len(latest_row) > 1 else target_scanner_version
        
        # 최종적으로 요청한 버전 사용 (우선순위)
        # 단, us_v2, v2-lite는 절대 다른 버전으로 fallback하지 않음
        if target_scanner_version in ['us_v2', 'v2-lite'] and detected_version != target_scanner_version:
            return {
                "ok": True,
                "data": {
                    "as_of": None,
                    "scan_date": None,
                    "is_latest": False,
                    "universe_count": 0,
                    "matched_count": 0,
                    "items": [{"ticker": "NORESULT", "name": "추천종목 없음", "score": 0.0, "score_label": "추천종목 없음"}],
                    "scanner_version": "us_v2"
                }
            }
        
        final_version = target_scanner_version if detected_version == target_scanner_version else detected_version
        
        if not raw_date:
            return {"ok": False, "error": "스캔 결과가 없습니다."}
        
        if hasattr(raw_date, "strftime"):
            formatted_date = raw_date.strftime('%Y%m%d')
        else:
            formatted_date = str(raw_date).replace('-', '')
        
        with db_manager.get_cursor(commit=False) as cur:
            # v3는 strategy로 구분 (v2_lite는 UI에서 숨김, 백데이터로만 저장)
            if final_version == 'v3':
                cur.execute("""
                    SELECT date,
                           code,
                           name,
                           score,
                           score_label,
                           close_price AS current_price,
                           volume,
                           change_rate,
                           market,
                           strategy,
                           indicators,
                           trend,
                           flags,
                           details,
                           returns,
                           recurrence,
                           anchor_date,
                           anchor_close,
                           anchor_price_type,
                           anchor_source
                    FROM scan_rank
                    WHERE date = %s AND scanner_version = %s 
                      AND strategy != 'v2_lite'
                      AND ((score >= 1 AND score <= 10) OR code = 'NORESULT')
                    ORDER BY 
                        CASE WHEN code = 'NORESULT' THEN 0 ELSE 1 END,
                        CASE strategy
                            WHEN 'midterm' THEN 1
                            ELSE 2
                        END,
                        CASE WHEN code = 'NORESULT' THEN 0 ELSE score END DESC
                """, (raw_date, final_version))
            else:
                cur.execute("""
                    SELECT date,
                           code,
                           name,
                           score,
                           score_label,
                           close_price AS current_price,
                           volume,
                           change_rate,
                           market,
                           strategy,
                           indicators,
                           trend,
                           flags,
                           details,
                           returns,
                           recurrence,
                           anchor_date,
                           anchor_close,
                           anchor_price_type,
                           anchor_source
                    FROM scan_rank
                    WHERE date = %s AND scanner_version = %s AND ((score >= 1 AND score <= 10) OR code = 'NORESULT')
                    ORDER BY CASE WHEN code = 'NORESULT' THEN 0 ELSE score END DESC
                """, (raw_date, final_version))
            rows = cur.fetchall()
        
        logger.info(f"[get_latest_scan_from_db] DB 쿼리 완료: {len(rows)}개 행 조회, date={raw_date}, version={final_version}")
        
        if not rows:
            logger.warning(f"[get_latest_scan_from_db] 스캔 결과 없음")
            return {"ok": False, "error": "스캔 결과가 없습니다."}
        
        # 재등장 정보: DB에 저장된 정보를 사용하되, days_since_last만 현재 날짜 기준으로 실시간 계산
        # 성능 최적화: 전체 재등장 이력을 다시 조회하지 않고, 저장된 정보 + days_since_last만 업데이트
        from date_helper import yyyymmdd_to_date
        from datetime import datetime
        today_date_str = datetime.now().strftime('%Y%m%d')
        today_date_obj = yyyymmdd_to_date(today_date_str)
        
        logger.info(f"[get_latest_scan_from_db] 아이템 처리 시작: {len(rows)}개")
        
        # recurrence 보강: DB에 저장된 recurrence가 비어있는 경우에도 v2 화면에서 재등장 정보를 노출할 수 있도록
        # scan_rank 이력 기반으로 계산한 recurrence를 주입한다. (저장값 우선, 없으면 계산값)
        try:
            codes_for_recurrence = []
            for r in rows:
                d = _row_to_dict(r)
                c = d.get("code")
                if c and c != "NORESULT":
                    codes_for_recurrence.append(c)
            recurrence_data_map = get_recurrence_data(list(set(codes_for_recurrence)), formatted_date)
        except Exception:
            recurrence_data_map = {}
        
        # JSON 파싱 최적화: 한 번만 파싱하는 헬퍼 함수 (루프 밖에서 정의)
        def _parse_json_field(field_value):
            if isinstance(field_value, str) and field_value:
                try:
                    return json.loads(field_value)
                except:
                    return {}
            return field_value or {}
        
        items = []
        item_process_start = time.time()
        for idx, row in enumerate(rows):
            if idx % 10 == 0 and idx > 0:
                elapsed = time.time() - item_process_start
                logger.info(f"[get_latest_scan_from_db] 아이템 처리 중: {idx}/{len(rows)}, elapsed={elapsed:.2f}s")
            data = _row_to_dict(row)  # 중복 제거
            code = data.get("code")
            flags = data.get("flags")
            indicators = data.get("indicators")
            trend = data.get("trend")
            details = data.get("details")
            returns = data.get("returns")
            recurrence = data.get("recurrence")
            
            # change_rate 정규화: scanner_version이 'v2' 또는 'v3'인 경우 이미 퍼센트 형태로 저장됨
            # v1의 경우 소수 형태일 수 있으므로 변환 필요
            change_rate_raw = data.get("change_rate") or 0.0
            change_rate = float(change_rate_raw)
            # scanner_version 파라미터 확인 (없으면 기본값 'v1'로 간주)
            scanner_ver = scanner_version or 'v1'
            if scanner_ver not in ['v2', 'v3'] and abs(change_rate) < 1.0 and change_rate != 0.0:
                # 소수로 저장된 경우 퍼센트로 변환 (v1만 해당)
                change_rate = change_rate * 100
            
            # 재등장 정보 파싱 및 days_since_last 실시간 계산
            recurrence_dict = recurrence
            if isinstance(recurrence, str) and recurrence:
                try:
                    recurrence_dict = json.loads(recurrence)
                except:
                    recurrence_dict = {}
            elif not recurrence:
                recurrence_dict = {}
            
            # DB 저장값이 비어있으면 이력 기반 계산값으로 보강 (v2 스캔 화면 재등장 정보 노출)
            if (not recurrence_dict) and code and code != "NORESULT":
                recurrence_dict = recurrence_data_map.get(code, {}) or {}
            
            # days_since_last 실시간 계산 (last_as_of가 있으면 현재 날짜 기준으로 업데이트)
            if recurrence_dict and recurrence_dict.get("appeared_before") and recurrence_dict.get("last_as_of"):
                try:
                    last_as_of_str = recurrence_dict.get("last_as_of")
                    if last_as_of_str:
                        last_as_of_date = yyyymmdd_to_date(last_as_of_str)
                        days_since_last = (today_date_obj - last_as_of_date).days
                        recurrence_dict["days_since_last"] = days_since_last
                except Exception as e:
                    # 계산 실패 시 기존 값 유지
                    pass
            
            # 디버깅: anchor_close 확인 (047810만)
            if code == "047810":
                print(f"🔍 [DEBUG 047810-1] data.get('anchor_close'): {data.get('anchor_close')}")
                print(f"🔍 [DEBUG 047810-1] data.get('anchor_date'): {data.get('anchor_date')}")
                print(f"🔍 [DEBUG 047810-1] 'anchor_close' in data: {'anchor_close' in data}")
            
            # JSON 파싱 (헬퍼 함수 사용)
            # flags 파싱 및 stop_loss 설정
            flags_dict = _parse_json_field(flags)
            # stop_loss가 없으면 기본값 설정 (v2_lite 기본값 사용)
            if flags_dict.get("stop_loss") is None:
                strategy = data.get("strategy")
                if strategy == "v2_lite":
                    flags_dict["stop_loss"] = 0.02  # 2%
                elif strategy == "midterm":
                    flags_dict["stop_loss"] = 0.07  # 7%
                else:
                    flags_dict["stop_loss"] = 0.02  # 기본값 2%
            
            item = {
                "ticker": code,
                "name": data.get("name"),
                "score": data.get("score"),
                "score_label": data.get("score_label"),
                "current_price": data.get("current_price"),
                "volume": data.get("volume"),
                "change_rate": round(change_rate, 2),  # 퍼센트로 정규화, 소수점 2자리
                "market": data.get("market"),
                "strategy": data.get("strategy"),
                "indicators": _parse_json_field(indicators),
                "trend": _parse_json_field(trend),
                "flags": flags_dict,  # stop_loss가 설정된 flags_dict 사용
                "details": _parse_json_field(details),
                "returns": _parse_json_field(returns),
                "recurrence": recurrence_dict,
            }
            # returns 필드 호환성 보정
            # returns가 None이거나 빈 딕셔너리면 빈 딕셔너리로 설정 (재계산 필요)
            if not item["returns"]:
                item["returns"] = {}
            else:
                # returns가 있으면 기본값 설정 (None은 유지하여 재계산 트리거)
                if "current_return" not in item["returns"]:
                    item["returns"]["current_return"] = None
                item["returns"].setdefault("max_return", 0)
                item["returns"].setdefault("min_return", 0)
                item["returns"].setdefault("days_elapsed", 0)
            
            # 가격 변수 정리:
            # - scan_date_close_price: 스캔일 종가 (DB의 current_price 컬럼 = close_price)
            # - today_close_price: 오늘 종가 (returns에서 계산)
            # - display_price: 프론트엔드에 표시할 가격 (오늘 종가 우선, 없으면 스캔일 종가)
            
            scan_date_close_price = item.get("current_price")  # DB의 current_price = 스캔일 종가
            
            # anchor_close 우선 사용 (추천 생성 시점에 저장된 값)
            anchor_close = data.get("anchor_close")
            anchor_date = data.get("anchor_date")
            anchor_price_type = data.get("anchor_price_type", "CLOSE")
            anchor_source = data.get("anchor_source", "KRX_EOD")
            
            # 디버깅: anchor_close 확인 (047810만)
            if code == "047810":
                print(f"🔍 [DEBUG 047810] anchor_close from data: {anchor_close}, type: {type(anchor_close)}")
                print(f"🔍 [DEBUG 047810] data keys: {list(data.keys())[:10]}...")
                print(f"🔍 [DEBUG 047810] 'anchor_close' in data: {'anchor_close' in data}")
            
            # 추천일 종가 (recommended_price) - anchor_close 우선, 없으면 기존 로직
            if anchor_close and anchor_close > 0:
                recommended_price = float(anchor_close)
            else:
                # anchor_close가 없으면 기존 로직 사용 (하위 호환성)
                recommended_price = None
                if item["returns"] and isinstance(item["returns"], dict) and item["returns"].get("scan_price"):
                    recommended_price = item["returns"].get("scan_price")
                elif scan_date_close_price and scan_date_close_price > 0:
                    recommended_price = scan_date_close_price
            
            # 오늘 종가 추출 (returns에서)
            today_close_price = None
            if item["returns"] and isinstance(item["returns"], dict) and item["returns"].get("current_price"):
                today_close_price = item["returns"].get("current_price")
            
            # current_return 추출 및 재계산 필요 여부 확인
            current_return = None
            should_recalculate_returns = False
            
            # 재등장 정보 파싱 (v3 홈에서도 recommended_date 설정에 필요)
            recurrence = item.get("recurrence", {})
            is_recurring = recurrence and recurrence.get("appeared_before", False)
            first_as_of = recurrence.get("first_as_of") if is_recurring else None
            
            # v3 홈에서는 재계산을 절대 수행하지 않음 (disable_recalculate_returns=True)
            if disable_recalculate_returns:
                # DB에 저장된 returns 데이터만 사용
                returns_data = item.get("returns")
                if returns_data and isinstance(returns_data, dict):
                    current_return = returns_data.get("current_return")
                else:
                    current_return = None
                # should_recalculate_returns는 False로 유지 (절대 True가 되지 않음)
                should_recalculate_returns = False  # 강제로 False 설정
            else:
                # 재등장 종목인 경우 항상 재계산 (최초 추천일 기준으로 계산하기 위해)
                
                # returns가 없거나 None이거나 current_return이 None이거나 0이면 재계산 필요
                returns_data = item.get("returns")
                if not returns_data or not isinstance(returns_data, dict):
                    should_recalculate_returns = True
                    current_return = None
                else:
                    current_return = returns_data.get("current_return")
                    
                    # current_return이 None이거나 0이면 재계산 필요 (0은 빈 값으로 간주)
                    if current_return is None or current_return == 0:
                        should_recalculate_returns = True
                    else:
                        # 재등장 종목이거나, 스캔일이 오늘이 아니면 항상 재계산
                        from date_helper import get_kst_now
                        today_str = get_kst_now().strftime('%Y%m%d')
                        if is_recurring or formatted_date < today_str:
                            # 재등장 종목이거나 전일 이전 스캔이면 항상 재계산하여 최신 수익률 표시
                            should_recalculate_returns = True
            
            # 재등장 종목인 경우 최초 추천일 기준으로 수익률 계산 (위에서 이미 정의됨)
            
            # recommended_date 설정 (anchor_date 우선)
            recommended_date = formatted_date
            if anchor_date:
                if isinstance(anchor_date, str):
                    recommended_date = anchor_date.replace('-', '')[:8]
                elif hasattr(anchor_date, 'strftime'):
                    recommended_date = anchor_date.strftime('%Y%m%d')
            
            # 재계산이 필요한 경우 실시간 계산
            # anchor_close가 있으면 그것을 scan_price_from_db로 전달하여 정확한 수익률 계산
            # v3 홈에서는 재계산을 절대 수행하지 않음 (회귀 방지)
            if disable_recalculate_returns:
                # v3 홈에서는 calculate_returns를 절대 호출하지 않음
                import logging
                logger = logging.getLogger(__name__)
                # v3 홈에서 재계산이 시도되려고 하면 경고 로그 + 메트릭 (회귀 방지)
                if should_recalculate_returns:
                    logger.warning(
                        f"⚠️ [V3_HOME_GUARD] calculate_returns 호출 시도 차단: "
                        f"code={data.get('code')}, scanner_version={scanner_version}, "
                        f"formatted_date={formatted_date}, user_id={user_id}"
                    )
                    # 메트릭 증가 (가능하면)
                    try:
                        # 메트릭 시스템이 있다면 여기서 증가
                        # 예: metrics.increment('v3_home_recalc_attempt')
                        pass
                    except:
                        pass
                    # 개발/테스트 환경에서는 예외 throw (즉시 발견)
                    if os.getenv('ENV') in ['development', 'test']:
                        raise RuntimeError(
                            f"[V3_HOME_GUARD] v3 홈에서 재계산 시도 감지: "
                            f"code={data.get('code')}, scanner_version={scanner_version}"
                        )
                    # should_recalculate_returns를 강제로 False로 설정
                    should_recalculate_returns = False
            
            if should_recalculate_returns and data.get("code") and data.get("code") != 'NORESULT':
                try:
                    from services.returns_service import calculate_returns
                    code = data.get("code")
                    
                    # scan_price 결정: anchor_close 우선, 없으면 scan_date_close_price
                    scan_price_for_calc = None
                    if anchor_close and anchor_close > 0:
                        scan_price_for_calc = float(anchor_close)
                        print(f"🔄 수익률 재계산 시작: {code}, scan_date={formatted_date}, scan_price={scan_price_for_calc} (anchor_close 사용)")
                    elif scan_date_close_price and scan_date_close_price > 0:
                        scan_price_for_calc = scan_date_close_price
                        print(f"🔄 수익률 재계산 시작: {code}, scan_date={formatted_date}, scan_price={scan_price_for_calc} (close_price 사용)")
                    
                    # 재등장 종목인 경우 최초 추천일 기준으로 계산
                    from kiwoom_api import api  # api import를 조건문 밖으로 이동
                    if is_recurring and first_as_of:
                        # 최초 추천일의 종가 조회
                        df_first = api.get_ohlcv(code, 1, first_as_of)
                        if not df_first.empty:
                            first_price = float(df_first.iloc[-1]['close'])
                            calculated_returns = calculate_returns(code, first_as_of, None, first_price)
                            # recommended_date와 recommended_price를 최초 추천일 기준으로 설정
                            if calculated_returns:
                                recommended_date = first_as_of
                                # anchor_close가 없을 때만 recommended_price 업데이트
                                if not anchor_close or anchor_close <= 0:
                                    recommended_price = first_price
                        else:
                            # 최초 추천일 데이터가 없으면 현재 스캔일 기준으로 계산
                            if scan_price_for_calc:
                                calculated_returns = calculate_returns(code, formatted_date, None, scan_price_for_calc)
                            else:
                                calculated_returns = None
                    else:
                        # 일반 종목은 현재 스캔일 기준으로 계산
                        if scan_price_for_calc:
                            calculated_returns = calculate_returns(code, formatted_date, None, scan_price_for_calc)
                        else:
                            # scan_price_for_calc가 없으면 OHLCV에서 가져오기 (디스크 캐시 우선)
                            try:
                                # 디스크 캐시에서 먼저 시도 (키움 API 인증 실패 시에도 사용 가능)
                                df_scan = api.get_ohlcv(code, 1, formatted_date)
                                if not df_scan.empty:
                                    scan_price = float(df_scan.iloc[-1]['close'])
                                    calculated_returns = calculate_returns(code, formatted_date, None, scan_price)
                                else:
                                    print(f"⚠️ OHLCV 데이터 없음 ({code}, {formatted_date})")
                                    calculated_returns = None
                            except Exception as e:
                                print(f"⚠️ OHLCV 조회 실패 ({code}, {formatted_date}): {e}")
                                # 예외 발생 시에도 calculate_returns에 None을 전달하여 시도
                                # (calculate_returns 내부에서 OHLCV 재시도)
                                calculated_returns = calculate_returns(code, formatted_date, None, None)
                    
                    if calculated_returns and calculated_returns.get('current_return') is not None:
                        current_return = calculated_returns.get('current_return')
                        # item["returns"]도 업데이트
                        if item["returns"]:
                            item["returns"].update(calculated_returns)
                        else:
                            item["returns"] = calculated_returns
                        # recommended_price 업데이트 (anchor_close가 없을 때만, 재등장 종목이 아니거나 최초 추천일 데이터가 없는 경우만)
                        if not anchor_close or anchor_close <= 0:
                            if not (is_recurring and first_as_of) and calculated_returns.get('scan_price'):
                                recommended_price = calculated_returns.get('scan_price')
                        # anchor_close가 있으면 returns.scan_price도 anchor_close로 설정 (일관성 유지)
                        # calculate_returns의 scan_price를 anchor_close로 덮어쓰기
                        if anchor_close and anchor_close > 0:
                            if not item["returns"]:
                                item["returns"] = {}
                            # anchor_close를 scan_price로 명시적으로 설정
                            item["returns"]["scan_price"] = float(anchor_close)
                        # 오늘 종가 업데이트
                        if calculated_returns.get('current_price') and calculated_returns.get('current_price') > 0:
                            today_close_price = calculated_returns.get('current_price')
                    else:
                        # 수익률 계산 실패 시 current_return을 0으로 설정하고 recommended_price는 스캔일 종가 사용
                        if current_return is None:
                            current_return = 0
                            # item["returns"]에도 0으로 설정
                            if item["returns"]:
                                item["returns"]["current_return"] = 0
                            else:
                                item["returns"] = {"current_return": 0, "max_return": 0, "min_return": 0, "days_elapsed": 0}
                        # recommended_price가 없으면 스캔일 종가 사용
                        if not recommended_price or recommended_price <= 0:
                            recommended_price = scan_date_close_price if scan_date_close_price and scan_date_close_price > 0 else None
                        # 수익률 계산 실패 시 로그 출력
                        print(f"⚠️ 수익률 계산 실패 ({code}): calculated_returns={calculated_returns}, scan_date_close_price={scan_date_close_price}")
                except Exception as e:
                    print(f"수익률 재계산 오류 ({data.get('code')}): {e}")
                    import traceback
                    traceback.print_exc()
                    # 오류 발생 시에도 기본값 설정
                    if current_return is None:
                        current_return = 0
                    if not recommended_price or recommended_price <= 0:
                        recommended_price = scan_date_close_price if scan_date_close_price and scan_date_close_price > 0 else None
            
            # 프론트엔드에 표시할 가격: 오늘 종가 우선, 없으면 스캔일 종가
            display_price = today_close_price if today_close_price and today_close_price > 0 else scan_date_close_price
            
            # v3에서도 current_return 계산을 위해 오늘 가격 조회 (표시용, status 판정과 무관)
            # ⚠️ 주의: 이 가격은 current_return 계산(표시용)에만 사용되며, status 판정에는 사용되지 않음
            # GET 요청에서는 status를 계산하지 않고 DB 저장값만 사용
            if scanner_version == 'v3' and (not today_close_price or today_close_price <= 0):
                try:
                    code = data.get("code")
                    if code and code != 'NORESULT':
                        from date_helper import get_kst_now
                        from kiwoom_api import api
                        today_str = get_kst_now().strftime('%Y%m%d')
                        df_today = api.get_ohlcv(code, 1, today_str)
                        if not df_today.empty:
                            today_close_price = float(df_today.iloc[-1]['close'])
                except Exception as e:
                    # 오류 시 today_close_price는 그대로 유지
                    pass
            
            # 등락률 재계산: 오늘 종가가 있으면 오늘 기준 등락률 계산
            display_change_rate = item.get("change_rate", 0.0)  # 기본값: 스캔일 등락률
            if today_close_price and today_close_price > 0:
                try:
                    # OHLCV 데이터로 직접 계산 (더 안정적)
                    code = data.get("code")
                    if code and code != 'NORESULT':
                        from date_helper import get_kst_now
                        from kiwoom_api import api  # api import 추가
                        today_str = get_kst_now().strftime('%Y%m%d')
                        df_today = api.get_ohlcv(code, 2, today_str)
                        if not df_today.empty and len(df_today) >= 2:
                            today_close = float(df_today.iloc[-1]['close'])
                            prev_close = float(df_today.iloc[-2]['close'])
                            if prev_close > 0:
                                calculated_rate = ((today_close - prev_close) / prev_close) * 100
                                display_change_rate = round(calculated_rate, 2)
                        else:
                            # OHLCV 실패 시 키움 API 시도
                            quote = api.get_stock_quote(code)
                            if quote and quote.get("change_rate") is not None and quote.get("change_rate") != 0.0:
                                display_change_rate = quote.get("change_rate")
                except Exception as e:
                    print(f"등락률 재계산 오류 ({data.get('code')}): {e}")
                    # 오류 시 기존 change_rate 유지
            
            # V2 UI 필드 추가
            # recommended_date 설정 (anchor_date 우선, 없으면 재등장 종목 처리)
            if anchor_date:
                # anchor_date가 있으면 그것을 사용
                if isinstance(anchor_date, str):
                    item["recommended_date"] = anchor_date.replace('-', '')[:8]
                elif hasattr(anchor_date, 'strftime'):
                    item["recommended_date"] = anchor_date.strftime('%Y%m%d')
                else:
                    item["recommended_date"] = recommended_date
            elif is_recurring and first_as_of:
                # anchor_date가 없고 재등장 종목인 경우 최초 추천일 기준으로 설정
                item["recommended_date"] = first_as_of
                # anchor_close가 없을 때만 최초 추천일의 종가를 조회하여 recommended_price 설정
                if (not recommended_price or recommended_price <= 0) and (not anchor_close or anchor_close <= 0):
                    try:
                        from kiwoom_api import api
                        code = data.get("code")  # code 변수 정의
                        if code and code != 'NORESULT':
                            df_first = api.get_ohlcv(code, 1, first_as_of)
                            if not df_first.empty:
                                recommended_price = float(df_first.iloc[-1]['close'])
                    except:
                        pass  # 실패 시 기존 값 유지
            else:
                item["recommended_date"] = recommended_date
            
            # recommended_price가 없으면 스캔일 종가 사용
            if not recommended_price or recommended_price <= 0:
                recommended_price = scan_date_close_price if scan_date_close_price and scan_date_close_price > 0 else None
            
            # current_return 계산 (표시용으로만 사용, status 판정과 완전히 분리)
            # ⚠️ 주의: current_return은 status 판정에 사용하지 않음
            # GET 요청에서는 status를 계산하지 않고 DB 저장값(flags의 assumption_broken/flow_broken)만 사용
            if current_return is None:
                # recommended_price와 현재 가격으로 수익률 계산 (표시용)
                if recommended_price and recommended_price > 0:
                    # 오늘 종가 사용 (이미 위에서 today_close_price 계산됨)
                    if today_close_price and today_close_price > 0:
                        current_return = ((today_close_price - recommended_price) / recommended_price) * 100
                    elif display_price and display_price > 0:
                        # display_price가 있으면 사용
                        current_return = ((display_price - recommended_price) / recommended_price) * 100
                    else:
                        current_return = 0
                else:
                    current_return = 0
            
            item["recommended_price"] = recommended_price
            item["current_return"] = current_return  # 이미 None 체크 완료
            
            # 도메인 상태 계산 (v3 UI용) - GET 요청에서는 DB 저장값만 사용
            # ⚠️ 회귀 방지: current_return 기반 status 판정 로직은 완전히 제거됨
            # ACTIVE: 유효한 추천, BROKEN: 관리 필요, ARCHIVED: 아카이브됨
            domain_status = None
            # flags_dict는 이미 위에서 파싱하고 stop_loss를 설정했으므로 재사용
            # item["flags"]에 이미 반영되어 있으므로 그대로 사용
            if "flags" in item and isinstance(item["flags"], dict):
                flags_dict = item["flags"]
            else:
                # fallback: item["flags"]가 없거나 dict가 아니면 다시 파싱
                flags_raw = item.get("flags", {})
                if isinstance(flags_raw, str):
                    try:
                        flags_dict = json.loads(flags_raw)
                    except:
                        flags_dict = {}
                elif isinstance(flags_raw, dict):
                    flags_dict = flags_raw
                else:
                    flags_dict = {}
                # stop_loss가 없으면 기본값 설정 (표시용, status 판정과 무관)
                if flags_dict.get("stop_loss") is None:
                    flags_dict["stop_loss"] = 0.02  # 2% 기본값
                item["flags"] = flags_dict
            
            # 추천 여부 확인
            is_recommended = recommended_date and recommended_price and recommended_price > 0
            
            if is_recommended:
                # 추천된 종목: DB에 저장된 플래그만 사용 (GET 요청에서는 계산하지 않음)
                # ⚠️ 회귀 방지: current_return <= stop_loss_pct 로직은 완전히 제거됨
                # GET 요청에서는 flags의 assumption_broken/flow_broken만 확인
                assumption_broken = flags_dict.get("assumption_broken") == True or flags_dict.get("flow_broken") == True
                
                if assumption_broken:
                    domain_status = "BROKEN"
                    # 디버깅: BROKEN 상태 로그 (플래그 기반만)
                    if code and code != 'NORESULT':
                        logger.debug(f"[get_latest_scan_from_db] BROKEN 상태 (플래그 기반): {code}, assumption_broken={flags_dict.get('assumption_broken')}, flow_broken={flags_dict.get('flow_broken')}")
                else:
                    domain_status = "ACTIVE"
            else:
                # 추천되지 않은 종목: ARCHIVED로 처리 (홈에서 노출하지 않음)
                domain_status = "ARCHIVED"
            
            # ⚠️ 회귀 방지 가드: current_return이 status 판정에 사용되었는지 확인
            # (현재는 제거되었지만, 혹시 모를 재도입 방지)
            # Python에서는 os.environ 사용
            import os
            if code and code != 'NORESULT' and os.getenv('NODE_ENV') != 'production':
                # 개발 환경에서만 경고 (프로덕션에서는 성능 영향 없음)
                # current_return이 status 판정에 사용되면 안 됨 (이미 제거됨)
                pass
            
            item["status"] = domain_status  # v3 UI에서 사용할 도메인 상태
            # current_return은 표시용으로만 사용 (status 판정과 완전히 분리)
            item["recommended_date"] = recommended_date  # ack 필터링을 위해 필수
            
            # anchor_close가 있으면 returns.scan_price도 명시적으로 설정 (일관성 유지)
            # should_recalculate_returns와 관계없이 항상 설정
            # 이 코드는 모든 경우에 실행되어야 함 (calculate_returns 호출 전후 모두)
            if anchor_close and anchor_close > 0:
                if not item.get("returns"):
                    item["returns"] = {}
                # anchor_close를 scan_price로 설정 (추천 기준 종가)
                item["returns"]["scan_price"] = float(anchor_close)
                # 디버깅 로그 (047810만)
                if code == "047810":
                    print(f"✅ [DEBUG 047810] anchor_close를 returns.scan_price로 설정: {anchor_close}")
            
            # current_price 업데이트 (오늘 종가 우선, 없으면 스캔일 종가)
            if display_price and display_price > 0:
                item["current_price"] = display_price
            # change_rate를 오늘 기준 등락률로 업데이트
            item["change_rate"] = display_change_rate
            
            items.append(item)
        
        # 상태별 통계 로깅 (디버깅용)
        status_counts = {}
        for item in items:
            status = item.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        logger.info(f"[get_latest_scan_from_db] 상태별 통계: {status_counts}, 총 {len(items)}개")
        
        # v3에서 ack 필터링 (user_id가 있는 경우만)
        if scanner_version == 'v3' and user_id is not None:
            logger.info(f"[get_latest_scan_from_db] ack 필터링 시작: user_id={user_id}, items={len(items)}개")
            ack_start = time.time()
            try:
                acked_rec_instances = set()
                with db_manager.get_cursor(commit=False) as cur:
                    cur.execute("""
                        SELECT rec_date, rec_code, rec_scanner_version
                        FROM user_rec_ack
                        WHERE user_id = %s AND ack_type = 'BROKEN_VIEWED'
                    """, (user_id,))
                    for row in cur.fetchall():
                        rec_date = row.get('rec_date') if isinstance(row, dict) else row[0]
                        rec_code = row.get('rec_code') if isinstance(row, dict) else row[1]
                        rec_scanner_version = row.get('rec_scanner_version') if isinstance(row, dict) else (row[2] if len(row) > 2 else 'v3')
                        # 날짜 형식 정규화 (YYYYMMDD)
                        if isinstance(rec_date, str):
                            rec_date_normalized = rec_date.replace('-', '')[:8]
                        elif hasattr(rec_date, 'strftime'):
                            rec_date_normalized = rec_date.strftime('%Y%m%d')
                        else:
                            rec_date_normalized = str(rec_date).replace('-', '')[:8]
                        acked_rec_instances.add((rec_date_normalized, rec_code, rec_scanner_version))
                
                ack_elapsed = time.time() - ack_start
                logger.info(f"[get_latest_scan_from_db] ack 조회 완료: {len(acked_rec_instances)}개, elapsed={ack_elapsed:.2f}s")
                
                # BROKEN 항목만 필터링
                original_count = len(items)
                filtered_items = []
                for item in items:
                    if item.get("status") == "BROKEN":
                        rec_date = item.get("recommended_date") or item.get("date") or formatted_date
                        rec_code = item.get("ticker")
                        rec_scanner_version = item.get("scanner_version", "v3")
                        
                        # 날짜 형식 정규화
                        if isinstance(rec_date, str):
                            rec_date_normalized = rec_date.replace('-', '')[:8]
                        elif hasattr(rec_date, 'strftime'):
                            rec_date_normalized = rec_date.strftime('%Y%m%d')
                        else:
                            rec_date_normalized = str(rec_date).replace('-', '')[:8]
                        
                        if (rec_date_normalized, rec_code, rec_scanner_version) in acked_rec_instances:
                            # ack된 BROKEN 항목은 제외
                            logger.info(f"[get_latest_scan_from_db] ack된 BROKEN 항목 제외: {rec_code}, {rec_date_normalized}")
                            continue
                    filtered_items.append(item)
                
                items = filtered_items
                logger.info(f"[get_latest_scan_from_db] ack 필터링 완료: {len(items)}개 남음 (원본 {original_count}개, 제외 {original_count - len(items)}개)")
            except Exception as e:
                logger.error(f"[get_latest_scan_from_db] ack 필터링 오류: {e}")
                # 오류 발생 시 필터링 없이 진행
        
        market_condition = None
        try:
            with db_manager.get_cursor(commit=False) as cur_mc:
                # market_conditions.date는 TEXT 타입이므로 문자열 형식으로 변환
                if isinstance(raw_date, str):
                    # 이미 문자열이면 YYYY-MM-DD 형식으로 정규화
                    if len(raw_date) == 8 and '-' not in raw_date:
                        # YYYYMMDD 형식
                        query_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                    elif '-' in raw_date:
                        # 이미 YYYY-MM-DD 형식
                        query_date = raw_date
                    else:
                        query_date = raw_date
                else:
                    # DATE 타입이면 문자열로 변환 (YYYY-MM-DD)
                    if hasattr(raw_date, 'strftime'):
                        query_date = raw_date.strftime('%Y-%m-%d')
                    else:
                        query_date = str(raw_date)
                
                # institution_flow 컬럼 존재 여부 확인
                cur_mc.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'market_conditions' AND column_name = 'institution_flow'
                """)
                has_institution_flow = cur_mc.fetchone() is not None
                
                # 동적으로 컬럼 선택
                if has_institution_flow:
                    cur_mc.execute("""
                        SELECT market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                               sector_rotation, foreign_flow, institution_flow, volume_trend,
                               min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                               trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                               foreign_flow_label, institution_flow_label, volume_trend_label, adjusted_params, analysis_notes,
                               midterm_regime, short_term_risk_score, final_regime, longterm_regime
                        FROM market_conditions WHERE date = %s
                    """, (query_date,))
                else:
                    cur_mc.execute("""
                        SELECT market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                               sector_rotation, foreign_flow, NULL as institution_flow, volume_trend,
                               min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                               trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                               foreign_flow_label, NULL as institution_flow_label, volume_trend_label, adjusted_params, analysis_notes,
                               midterm_regime, short_term_risk_score, final_regime, longterm_regime
                        FROM market_conditions WHERE date = %s
                    """, (query_date,))
                row_mc = cur_mc.fetchone()
            
            if row_mc:
                if isinstance(row_mc, dict):
                    values = row_mc
                else:
                    keys = [
                        "market_sentiment", "sentiment_score", "kospi_return", "volatility", "rsi_threshold",
                        "sector_rotation", "foreign_flow", "institution_flow", "volume_trend",
                        "min_signals", "macd_osc_min", "vol_ma5_mult", "gap_max", "ext_from_tema20_max",
                        "trend_metrics", "breadth_metrics", "flow_metrics", "sector_metrics", "volatility_metrics",
                        "foreign_flow_label", "institution_flow_label", "volume_trend_label", "adjusted_params", "analysis_notes",
                        "midterm_regime", "short_term_risk_score", "final_regime", "longterm_regime"
                    ]
                    values = dict(zip(keys, row_mc))
                
                def _ensure_json(value):
                    if isinstance(value, str) and value:
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            return {}
                    return value or {}

                trend_metrics = _ensure_json(values.get("trend_metrics"))
                breadth_metrics = _ensure_json(values.get("breadth_metrics"))
                flow_metrics = _ensure_json(values.get("flow_metrics"))
                sector_metrics = _ensure_json(values.get("sector_metrics"))
                volatility_metrics = _ensure_json(values.get("volatility_metrics"))
                adjusted_params = _ensure_json(values.get("adjusted_params"))
                sentiment_score = values.get("sentiment_score") or 0.0
                foreign_flow_label = values.get("foreign_flow_label") or values.get("foreign_flow") or "neutral"
                institution_flow_label = values.get("institution_flow_label") or values.get("institution_flow") or "neutral"
                volume_trend_label = values.get("volume_trend_label") or values.get("volume_trend") or "normal"
                analysis_notes = values.get("analysis_notes")

                from market_analyzer import MarketCondition
                market_condition = MarketCondition(
                    date=formatted_date,
                    market_sentiment=values.get("market_sentiment"),
                    kospi_return=values.get("kospi_return"),
                    volatility=values.get("volatility"),
                    rsi_threshold=values.get("rsi_threshold"),
                    sector_rotation=values.get("sector_rotation"),
                    foreign_flow=values.get("foreign_flow"),
                    institution_flow=values.get("institution_flow"),
                    volume_trend=values.get("volume_trend"),
                    min_signals=values.get("min_signals"),
                    macd_osc_min=values.get("macd_osc_min"),
                    vol_ma5_mult=values.get("vol_ma5_mult"),
                    gap_max=values.get("gap_max"),
                    ext_from_tema20_max=values.get("ext_from_tema20_max"),
                    sentiment_score=sentiment_score,
                    trend_metrics=trend_metrics,
                    breadth_metrics=breadth_metrics,
                    flow_metrics=flow_metrics,
                    sector_metrics=sector_metrics,
                    volatility_metrics=volatility_metrics,
                    foreign_flow_label=foreign_flow_label,
                    institution_flow_label=institution_flow_label,
                    volume_trend_label=volume_trend_label,
                    adjusted_params=adjusted_params,
                    analysis_notes=analysis_notes,
                    midterm_regime=values.get("midterm_regime"),
                    short_term_risk_score=int(values.get("short_term_risk_score")) if values.get("short_term_risk_score") is not None else None,
                    final_regime=values.get("final_regime"),
                    longterm_regime=values.get("longterm_regime"),
                )
                print(f"📊 시장 상황 조회 (DB): {market_condition.market_sentiment} (유효 수익률: {market_condition.kospi_return*100:.2f}%, RSI 임계값: {market_condition.rsi_threshold})")
            else:
                print(f"ℹ️ 시장 상황 데이터 없음 (날짜: {formatted_date})")
        except Exception as e:
            print(f"⚠️ 시장 상황 DB 조회 실패: {e}")
        
        actual_matched_count = len([item for item in items if item.get('ticker') != 'NORESULT'])
        scan_result_dict = {
            'matched_count': actual_matched_count,
            'rsi_threshold': market_condition.rsi_threshold if market_condition else 57.0,
            'items': [{
                'ticker': item.get('ticker', ''),
                'indicators': {'change_rate': item.get('change_rate', 0)},
                'flags': {'vol_expand': False}
            } for item in items],
            'market_sentiment': market_condition.market_sentiment if market_condition else None
        }
        market_guide = get_market_guide(scan_result_dict)
        
        today = datetime.now().strftime('%Y%m%d')
        is_today = formatted_date == today
        # market_condition을 dict로 변환
        market_condition_dict = None
        if market_condition:
            from dataclasses import asdict
            market_condition_dict = asdict(market_condition)
        
        # v3 케이스 판별 필드 추가 (v3일 때만, v2_lite는 UI에서 숨김)
        v3_case_info = None
        if final_version == 'v3':
            # strategy별로 분류 (v2_lite 제외)
            midterm_items = [item for item in items if item.get("strategy") == "midterm" and item.get("ticker") != "NORESULT"]
            
            has_midterm = len(midterm_items) > 0
            has_recommendations = has_midterm
            
            active_engines = []
            if has_midterm:
                active_engines.append("midterm")
            
            # scan_date를 YYYY-MM-DD 형식으로 변환
            scan_date_formatted = f"{formatted_date[:4]}-{formatted_date[4:6]}-{formatted_date[6:8]}"
            
            v3_case_info = {
                "has_recommendations": has_recommendations,
                "active_engines": active_engines,
                "scan_date": scan_date_formatted,
                "engine_labels": {
                    "midterm": "중기 추세형"
                }
            }
        
        data = {
            "as_of": formatted_date,
            "scan_date": formatted_date,
            "is_latest": True,
            "is_today": is_today,
            "is_holiday": not is_today,
            "universe_count": 100,
            "matched_count": len(items),
            "rsi_mode": "current_status",
            "rsi_period": 14,
            "rsi_threshold": market_condition.rsi_threshold if market_condition else 57.0,
            "items": items,
            "market_guide": market_guide,
            "market_condition": market_condition_dict,
            "scanner_version": final_version  # 현재 DB 설정 버전 사용
        }
        data["enhanced_items"] = items
        
        # v3 케이스 정보 추가 (optional 필드)
        if v3_case_info:
            data["v3_case_info"] = v3_case_info
        
        elapsed_time = time.time() - start_time
        logger.info(f"[get_latest_scan_from_db] 완료: scanner_version={scanner_version}, items={len(items)}, elapsed={elapsed_time:.2f}s")
        
        return {"ok": True, "data": data}
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[get_latest_scan_from_db] 오류: scanner_version={scanner_version}, elapsed={elapsed_time:.2f}s, error={str(e)}")
        return {"ok": False, "error": f"스캔 결과를 가져오는 중 오류가 발생했습니다: {str(e)}"}

# Optional 인증을 위한 헬퍼 함수
async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """선택적 인증: 토큰이 있으면 사용자 반환, 없으면 None"""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get('auth_token')
    if not token:
        return None
    try:
        token_data = auth_service.verify_token(token)
        if token_data:
            user = auth_service.get_user_by_id(token_data.user_id)
            # 사용자 활성 상태 확인
            if user and not user.is_active:
                return None  # 비활성화된 계정은 None 반환
            return user
    except HTTPException:
        # HTTP 예외는 그대로 전파하지 않고 None 반환
        return None
    except Exception as e:
        # 기타 예외는 로깅하고 None 반환
        import logging
        logging.getLogger(__name__).warning(f"get_optional_user에서 예외 발생: {e}")
        return None
    return None

# 필수 인증을 위한 헬퍼 함수 (ack API에서 사용)
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """현재 로그인한 사용자 정보 가져오기"""
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    user = auth_service.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # 사용자 활성 상태 확인
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    return user

@app.get("/latest-scan")
async def get_latest_scan(
    scanner_version: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """최신 스캔 결과를 가져옵니다. DB에서 직접 조회하여 빠른 응답을 제공합니다.
    
    Args:
        scanner_version: 스캐너 버전 ('v1', 'v2', 또는 'v2-lite'). None이면 DB 설정 사용
        current_user: 현재 로그인한 사용자 (선택, v3에서 ack 필터링용)
    """
    # v3 홈에서는 재계산을 절대 수행하지 않음 (GET 요청마다 current_return이 바뀌는 문제 방지)
    disable_recalculate = (scanner_version == 'v3')
    
    # 인증된 사용자 ID 추출 (v3에서 ack 필터링용)
    user_id = current_user.id if current_user else None
    
    # DB 직접 조회 함수 사용 (성능 최적화)
    return get_latest_scan_from_db(
        scanner_version=scanner_version, 
        disable_recalculate_returns=disable_recalculate,
        user_id=user_id
    )


@app.get("/api/v3/recommendations/active")
async def get_active_recommendations(user_id: Optional[int] = None):
    """
    ACTIVE 상태인 추천 목록 조회 (daily_digest, weekly_digest 포함)
    
    Returns:
        {
            "ok": true,
            "data": {
                "items": [...],
                "count": 0
            },
            "daily_digest": {
                "date_kst": "2026-01-01",
                "as_of": "2026-01-01T15:36:00+09:00",
                "window": "POST_1535",
                "new_recommendations": 2,
                "new_broken": 1,
                "new_archived": 3,
                "has_changes": true
            },
            "weekly_digest": {
                "week_start": "2026-01-13",
                "week_end": "2026-01-17",
                "as_of": "2026-01-17T18:00:00+09:00",
                "new_recommendations": 12,
                "archived": 4,
                "repeat_signals": 3
            }
        }
    """
    try:
        from services.recommendation_service import get_active_recommendations_list
        from services.daily_digest_service import calculate_daily_digest
        from services.weekly_digest_service import calculate_weekly_digest
        
        items = get_active_recommendations_list(user_id=user_id)
        daily_digest = calculate_daily_digest()
        weekly_digest = calculate_weekly_digest()
        
        return {
            "ok": True,
            "data": {
                "items": items,
                "count": len(items)
            },
            "daily_digest": daily_digest,
            "weekly_digest": weekly_digest
        }
    except Exception as e:
        logger.error(f"[get_active_recommendations] 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/recommendations/needs-attention")
async def get_needs_attention_recommendations(user_id: Optional[int] = None):
    """
    주의가 필요한 추천 목록 조회 (WEAK_WARNING, BROKEN)
    
    Returns:
        {
            "ok": true,
            "data": {
                "items": [...],
                "count": 0
            }
        }
    """
    try:
        from services.recommendation_service import get_needs_attention_recommendations_list
        
        items = get_needs_attention_recommendations_list(user_id=user_id)
        
        return {
            "ok": True,
            "data": {
                "items": items,
                "count": len(items)
            }
        }
    except Exception as e:
        logger.error(f"[get_needs_attention_recommendations] 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/recommendations/weekly-detail")
async def get_weekly_recommendation_detail(reference_date: Optional[str] = None):
    """
    주간 추천 상세 리스트 (월~금, KST)
    
    Returns:
        {
            "ok": true,
            "data": {
                "week_start": "2026-01-12",
                "week_end": "2026-01-16",
                "as_of": "2026-01-15T18:00:00+09:00",
                "new_items": [...],
                "archived_items": [...],
                "repeat_items": [...]
            }
        }
    """
    try:
        from services.weekly_digest_service import calculate_weekly_detail
        from datetime import datetime
        
        ref_date_obj = None
        if reference_date:
            ref_date_obj = datetime.strptime(reference_date, "%Y-%m-%d").date()
        
        detail = calculate_weekly_detail(reference_date=ref_date_obj)
        return {
            "ok": True,
            "data": detail
        }
    except Exception as e:
        logger.error(f"[get_weekly_recommendation_detail] 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/recommendations/archived")
async def get_archived_recommendations(user_id: Optional[int] = None, limit: Optional[int] = None):
    """
    ARCHIVED 상태인 추천 목록 조회
    
    Returns:
        {
            "ok": true,
            "data": {
                "items": [...],
                "count": 0
            }
        }
    """
    try:
        from services.recommendation_service import get_archived_recommendations_list
        
        items = get_archived_recommendations_list(user_id=user_id, limit=limit)
        
        return {
            "ok": True,
            "data": {
                "items": items,
                "count": len(items)
            }
        }
    except Exception as e:
        logger.error(f"[get_archived_recommendations] 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/recommendations/archived/count")
async def get_archived_recommendations_count(user_id: Optional[int] = None):
    """
    ARCHIVED 상태인 추천 개수만 조회 (성능 최적화)
    
    Returns:
        {
            "ok": true,
            "data": {
                "count": 0
            }
        }
    """
    try:
        from db_manager import db_manager
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM recommendations
                WHERE status = 'ARCHIVED'
                AND scanner_version = 'v3'
            """)
            count = cur.fetchone()[0] if cur.rowcount > 0 else 0
        
        return {
            "ok": True,
            "data": {
                "count": count
            }
        }
    except Exception as e:
        logger.error(f"[get_archived_recommendations_count] 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v3/cache/fill-today-ohlcv")
async def fill_today_ohlcv_cache():
    """
    추천 목록의 모든 종목에 대해 오늘 날짜 OHLCV 캐시 채우기
    """
    try:
        from date_helper import get_kst_now
        from kiwoom_api import api
        from db_manager import db_manager
        
        today_str = get_kst_now().strftime('%Y%m%d')
        
        # 모든 추천 종목 수집
        tickers = set()
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT DISTINCT ticker
                FROM recommendations
                WHERE status IN ('ACTIVE', 'WEAK_WARNING', 'BROKEN')
                AND ticker IS NOT NULL
                AND ticker != ''
            """)
            rows = cur.fetchall()
            for row in rows:
                if row[0]:
                    tickers.add(row[0])
        
        if not tickers:
            return {
                "ok": True,
                "data": {
                    "message": "추천 종목이 없습니다.",
                    "success_count": 0,
                    "fail_count": 0,
                    "failed_tickers": []
                }
            }
        
        # 순차 처리로 캐시 채우기
        success_count = 0
        fail_count = 0
        failed_tickers = []
        
        for ticker in sorted(tickers):
            try:
                # base_dt=today_str로 명시적으로 호출하여 오늘 날짜 캐시 생성/확인
                df_today = api.get_ohlcv(ticker, 1, today_str)
                if not df_today.empty:
                    success_count += 1
                else:
                    fail_count += 1
                    failed_tickers.append(ticker)
            except Exception as e:
                fail_count += 1
                failed_tickers.append(ticker)
                logger.error(f"{ticker}: 캐시 채우기 실패: {e}")
        
        return {
            "ok": True,
            "data": {
                "message": "오늘 날짜 OHLCV 캐시 채우기 완료",
                "success_count": success_count,
                "fail_count": fail_count,
                "failed_tickers": failed_tickers
            }
        }
    except Exception as e:
        logger.error(f"[fill_today_ohlcv_cache] 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/recommendations/{recommendation_id}")
async def get_recommendation_by_id(recommendation_id: int, user_id: Optional[int] = None):
    """
    특정 추천 상세 조회
    
    Args:
        recommendation_id: 추천 ID
        
    Returns:
        {
            "ok": true,
            "data": {...}
        }
    """
    try:
        from services.recommendation_service import get_recommendation_by_id as get_rec
        
        rec = get_rec(recommendation_id, user_id=user_id)
        
        if not rec:
            raise HTTPException(status_code=404, detail="추천을 찾을 수 없습니다")
        
        return {
            "ok": True,
            "data": rec
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_recommendation_by_id] 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v3/recommendations/{rec_date}/{rec_code}/{rec_scanner_version}/ack")
async def ack_recommendation(
    rec_date: str,
    rec_code: str,
    rec_scanner_version: str = "v3",
    ack_type: str = "BROKEN_VIEWED",
    current_user: User = Depends(get_current_user)
):
    """추천 인스턴스 확인(ack) 처리
    
    Args:
        rec_date: 추천 날짜 (YYYYMMDD 또는 YYYY-MM-DD)
        rec_code: 종목 코드
        rec_scanner_version: 스캐너 버전 (기본값: v3)
        ack_type: 확인 타입 (기본값: BROKEN_VIEWED)
        current_user: 현재 로그인한 사용자
    
    Returns:
        200 OK (idempotent)
    """
    try:
        from date_helper import yyyymmdd_to_date
        
        # 날짜 정규화
        normalized_date = yyyymmdd_to_date(rec_date)
        if not normalized_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="잘못된 날짜 형식입니다"
            )
        
        # user_rec_ack 테이블 생성 확인
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_rec_ack (
                    id                  BIGSERIAL PRIMARY KEY,
                    user_id             BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
                    rec_date            DATE NOT NULL,
                    rec_code            TEXT NOT NULL,
                    rec_scanner_version TEXT NOT NULL DEFAULT 'v1',
                    ack_type            TEXT NOT NULL DEFAULT 'BROKEN_VIEWED',
                    acked_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, rec_date, rec_code, rec_scanner_version, ack_type)
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_rec_ack_user_id 
                ON user_rec_ack(user_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_rec_ack_rec 
                ON user_rec_ack(rec_date, rec_code, rec_scanner_version)
            """)
        
        # Upsert (idempotent)
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO user_rec_ack (user_id, rec_date, rec_code, rec_scanner_version, ack_type, acked_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id, rec_date, rec_code, rec_scanner_version, ack_type)
                DO UPDATE SET acked_at = NOW()
                RETURNING id
            """, (
                current_user.id,
                normalized_date,
                rec_code,
                rec_scanner_version,
                ack_type
            ))
            result = cur.fetchone()
        
        return {"ok": True, "message": "확인 처리되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[ack_recommendation] 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"확인 처리 중 오류가 발생했습니다: {str(e)}"
        )


@app.get("/v3/scan")
async def get_v3_scan(date: Optional[str] = None):
    """V3 엔진 스캔 결과를 가져옵니다. v2-lite와 midterm 결과를 분리하여 반환합니다.
    
    Args:
        date: 날짜 (YYYYMMDD 형식). None이면 오늘 날짜 사용
    
    Returns:
        {
            "ok": true,
            "data": {
                "engine": "v3",
                "date": "YYYYMMDD",
                "regime": {
                    "final": "...",
                    "risk": "..."
                },
                "v2lite_candidates": [...],
                "midterm_candidates": [...]
            }
        }
    """
    try:
        from date_helper import yyyymmdd_to_date
        from datetime import datetime
        
        # 날짜 처리
        if date:
            try:
                target_date_str = normalize_date(date)
            except ValueError:
                return {"ok": False, "error": "날짜 형식이 올바르지 않습니다. YYYYMMDD 형식을 사용해주세요."}
        else:
            target_date_str = datetime.now().strftime('%Y%m%d')
        
        target_date = yyyymmdd_to_date(target_date_str)
        
        # DB에서 v3 결과 조회 (strategy로 구분)
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT code, name, score, score_label, close_price AS current_price, volume,
                       change_rate, market, strategy, indicators, trend, flags, details, returns, recurrence,
                       anchor_date, anchor_close, anchor_price_type, anchor_source
                FROM scan_rank
                WHERE date = %s AND scanner_version = 'v3'
                ORDER BY 
                    CASE strategy
                        WHEN 'v2_lite' THEN 1
                        WHEN 'midterm' THEN 2
                        ELSE 3
                    END,
                    CASE WHEN code = 'NORESULT' THEN 0 ELSE score END DESC
            """, (target_date,))
            rows = cur.fetchall()
        
        # 결과 분리 및 수익률 정보 추가 (v2와 동일한 로직)
        v2lite_candidates = []
        midterm_candidates = []
        
        # 수익률 계산을 위한 서비스 import
        from services.returns_service import calculate_returns_batch
        from date_helper import get_kst_now
        from kiwoom_api import api
        
        # 오늘 날짜
        today_str = get_kst_now().strftime('%Y%m%d')
        
        for row in rows:
            if isinstance(row, dict):
                item = row
            else:
                keys = [
                    "code", "name", "score", "score_label", "current_price", "volume",
                    "change_rate", "market", "strategy", "indicators", "trend",
                    "flags", "details", "returns", "recurrence",
                    "anchor_date", "anchor_close", "anchor_price_type", "anchor_source"
                ]
                item = dict(zip(keys, row))
            
            code = item.get("code", "")
            if code == 'NORESULT':
                continue
            
            # JSON 필드 파싱
            import json
            for field in ['indicators', 'trend', 'flags', 'details', 'returns', 'recurrence']:
                if item.get(field) and isinstance(item[field], str):
                    try:
                        item[field] = json.loads(item[field])
                    except:
                        item[field] = {}
            
            # returns 데이터에서 수익률 정보 추출
            returns_data = item.get("returns", {})
            current_return = returns_data.get("current_return") if returns_data else None
            max_return = returns_data.get("max_return") if returns_data else None
            min_return = returns_data.get("min_return") if returns_data else None
            days_elapsed = returns_data.get("days_elapsed", 0) if returns_data else 0
            
            # anchor_close 우선 사용 (재계산 방지)
            anchor_close = item.get("anchor_close")
            anchor_date = item.get("anchor_date")
            anchor_price_type = item.get("anchor_price_type", "CLOSE")
            anchor_source = item.get("anchor_source", "KRX_EOD")
            
            # recommended_price와 recommended_date 설정
            scan_date_close_price = item.get("current_price", 0)  # 스캔일 종가
            
            # anchor_close가 있으면 우선 사용 (추천 생성 시점에 저장된 값)
            if anchor_close and anchor_close > 0:
                recommended_price = float(anchor_close)
                # anchor_date가 있으면 그것을 recommended_date로 사용
                if anchor_date:
                    if isinstance(anchor_date, str):
                        recommended_date = anchor_date.replace('-', '')[:8]
                    elif hasattr(anchor_date, 'strftime'):
                        recommended_date = anchor_date.strftime('%Y%m%d')
                    else:
                        recommended_date = target_date_str
                else:
                    recommended_date = target_date_str
            else:
                # anchor_close가 없으면 기존 로직 사용 (하위 호환성)
                recommended_price = scan_date_close_price
                recommended_date = target_date_str
                
                # returns에서 scan_price가 있으면 사용
                if returns_data and returns_data.get("scan_price"):
                    recommended_price = returns_data.get("scan_price")
                
                # 재등장 종목인 경우 최초 추천일 기준으로 설정
                recurrence_data = item.get("recurrence", {})
                is_recurring = recurrence_data and recurrence_data.get("appeared_before", False)
                first_as_of = recurrence_data.get("first_as_of") if is_recurring else None
                
                if is_recurring and first_as_of:
                    recommended_date = first_as_of
                    # 최초 추천일의 종가를 조회하여 recommended_price 설정
                    try:
                        df_first = api.get_ohlcv(code, 1, first_as_of)
                        if not df_first.empty:
                            recommended_price = float(df_first.iloc[-1]['close'])
                    except:
                        pass  # 실패 시 기존 값 유지
            
            # 오늘 종가 조회 (수익률 계산용)
            today_close_price = None
            try:
                df_today = api.get_ohlcv(code, 1, today_str)
                if not df_today.empty:
                    today_close_price = float(df_today.iloc[-1]['close'])
            except:
                pass
            
            # current_return이 없으면 계산
            if current_return is None:
                if recommended_price and recommended_price > 0 and today_close_price:
                    current_return = ((today_close_price - recommended_price) / recommended_price) * 100
                else:
                    current_return = 0
            
            # v2와 동일한 필드 구조로 변환
            item["ticker"] = code
            item["recommended_price"] = recommended_price
            item["recommended_date"] = recommended_date
            item["current_return"] = current_return if current_return is not None else 0
            
            # returns 객체 업데이트
            if not item.get("returns"):
                item["returns"] = {}
            item["returns"]["current_return"] = current_return if current_return is not None else 0
            item["returns"]["max_return"] = max_return if max_return is not None else (current_return if current_return and current_return > 0 else 0)
            item["returns"]["min_return"] = min_return if min_return is not None else (current_return if current_return and current_return < 0 else 0)
            item["returns"]["days_elapsed"] = days_elapsed
            item["returns"]["current_price"] = today_close_price
            
            strategy = item.get("strategy", "")
            if strategy == "v2_lite":
                v2lite_candidates.append(item)
            elif strategy == "midterm":
                midterm_candidates.append(item)
        
        # 레짐 정보 조회
        regime_info = {"final": "unknown", "risk": "unknown"}
        try:
            query_date = target_date_str[:4] + "-" + target_date_str[4:6] + "-" + target_date_str[6:8]
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT final_regime, short_term_risk_score
                    FROM market_conditions
                    WHERE date = %s
                    LIMIT 1
                """, (query_date,))
                row = cur.fetchone()
                if row:
                    if isinstance(row, dict):
                        regime_info["final"] = row.get("final_regime", "unknown")
                        risk_score = row.get("short_term_risk_score")
                    else:
                        regime_info["final"] = row[0] if row[0] else "unknown"
                        risk_score = row[1]
                    
                    # risk_score를 risk_label로 변환 (normal/elevated/stressed)
                    if risk_score is not None:
                        if risk_score >= 3:
                            regime_info["risk"] = "stressed"
                        elif risk_score >= 2:
                            regime_info["risk"] = "elevated"
                        else:
                            regime_info["risk"] = "normal"
        except Exception as e:
            print(f"⚠️ 레짐 정보 조회 실패: {e}")
        
        return {
            "ok": True,
            "data": {
                "engine": "v3",
                "date": target_date_str,
                "regime": regime_info,
                "v2lite_candidates": v2lite_candidates,
                "midterm_candidates": midterm_candidates
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": f"V3 스캔 결과를 가져오는 중 오류가 발생했습니다: {str(e)}"}


# 인증 관련 라우터들

# ==================== 인증 관련 엔드포인트 ====================

# JWT 토큰 검증을 위한 의존성
# security와 get_current_user는 위에서 이미 정의됨 (중복 제거)
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
        
        # JWT 토큰 생성 (기본값 7일 사용)
        access_token = auth_service.create_access_token(
            data={"sub": user.email}
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

@app.post("/auth/dev-login", response_model=Token)
async def dev_login(request: dict):
    """개발 모드 로그인 (로컬 환경에서만 사용)"""
    import os
    # 프로덕션 환경에서는 비활성화
    if os.getenv("ENVIRONMENT") == "production" or os.getenv("NODE_ENV") == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="개발 모드 로그인은 프로덕션 환경에서 사용할 수 없습니다"
        )
    
    try:
        email = request.get("email", "kuksos80215@daum.net")
        
        # 사용자 조회
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, email, name, provider, provider_id, membership_tier, is_admin, is_active, created_at, last_login
                FROM users
                WHERE email = %s
            """, (email,))
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"사용자를 찾을 수 없습니다: {email}"
                )
            
            # 사용자 정보 구성
            user = User(
                id=row[0],
                email=row[1],
                name=row[2] or "",
                provider=row[3] or "kakao",
                provider_id=row[4] or str(row[0]),  # provider_id가 없으면 id를 사용
                membership_tier=row[5] or "free",
                is_admin=bool(row[6]),
                is_active=bool(row[7]) if row[7] is not None else True,
                created_at=row[8].isoformat() if row[8] else None,
                last_login=row[9].isoformat() if row[9] else None
            )
        
        # 마지막 로그인 시간 업데이트
        auth_service.update_last_login(user.id)
        
        # JWT 토큰 생성
        access_token_expires = timedelta(days=7)  # 개발 모드에서는 7일간 유효
        access_token = auth_service.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"개발 모드 로그인 오류: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"개발 모드 로그인 중 오류가 발생했습니다: {str(e)}"
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
        
        # JWT 토큰 생성 (기본값 7일 사용)
        access_token = auth_service.create_access_token(
            data={"sub": user.email}
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
                    "client_id": os.getenv("KAKAO_CLIENT_ID", "4eb579e52709ea64e8b941b9c95d20da"),
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
            
            # 사용자 ID 검증
            kakao_user_id = user_data.get("id")
            if not kakao_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="카카오 사용자 ID를 받을 수 없습니다"
                )
            
            # 사용자 정보 구성
            social_user_info = {
                "provider": "kakao",
                "provider_id": str(kakao_user_id),
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
            except ValueError as e:
                print(f"사용자 정보 검증 오류: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"카카오 사용자 정보가 유효하지 않습니다: {str(e)}"
                )
            except Exception as e:
                print(f"사용자 생성 오류: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"사용자 생성 중 오류가 발생했습니다: {str(e)}"
                )
            
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
        print(f"카카오 로그인 처리 중 예상치 못한 오류: {e}")
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


# ===== 매매 내역 API =====

@app.post("/trading-history", response_model=TradingHistory)
async def add_trading_history(
    request: AddTradingRequest,
    current_user: User = Depends(get_current_user)
):
    """매매 내역 추가"""
    try:
        trading_history = portfolio_service.add_trading_history(current_user.id, request)
        return trading_history
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"매매 내역 추가 중 오류가 발생했습니다: {str(e)}"
        )


@app.get("/trading-history", response_model=TradingHistoryResponse)
async def get_trading_history(
    ticker: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """매매 내역 조회"""
    try:
        trading_history = portfolio_service.get_trading_history(current_user.id, ticker)
        return trading_history
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"매매 내역 조회 중 오류가 발생했습니다: {str(e)}"
        )


@app.delete("/trading-history/{trading_id}")
async def delete_trading_history(
    trading_id: int,
    current_user: User = Depends(get_current_user)
):
    """매매 내역 삭제"""
    try:
        success = portfolio_service.delete_trading_history(current_user.id, trading_id)
        if success:
            return {"message": "매매 내역이 삭제되었습니다."}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 매매 내역을 찾을 수 없습니다."
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"매매 내역 삭제 중 오류가 발생했습니다: {str(e)}"
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

# 개인용 키움 API 키 관리
@app.get("/user/kiwoom-keys")
async def get_user_kiwoom_keys(current_user: User = Depends(get_current_user)):
    """개인 키움 API 키 상태 조회"""
    try:
        credentials = parameter_store.get_user_kiwoom_credentials(current_user.id)
        return {
            "ok": True,
            "data": {
                "api_key_exists": bool(credentials['api_key']),
                "api_secret_exists": bool(credentials['api_secret']),
                "account_no_exists": bool(credentials['account_no']),
                "api_key_preview": credentials['api_key'][:8] + "..." if credentials['api_key'] else None
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/user/kiwoom-keys")
async def set_user_kiwoom_keys(request: dict, current_user: User = Depends(get_current_user)):
    """개인 키움 API 키 등록/수정"""
    try:
        api_key = request.get('api_key')
        api_secret = request.get('api_secret')
        account_no = request.get('account_no')
        
        if not api_key or not api_secret:
            return {"ok": False, "error": "API Key와 API Secret은 필수입니다"}
        
        success = parameter_store.set_user_kiwoom_credentials(current_user.id, api_key, api_secret, account_no)
        
        if success:
            return {"ok": True, "message": "키움 API 키가 성공적으로 저장되었습니다"}
        else:
            return {"ok": False, "error": "키 저장에 실패했습니다"}
            
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.delete("/user/kiwoom-keys")
async def delete_user_kiwoom_keys(current_user: User = Depends(get_current_user)):
    """개인 키움 API 키 삭제"""
    try:
        success = parameter_store.delete_user_kiwoom_credentials(current_user.id)
        
        if success:
            return {"ok": True, "message": "키움 API 키가 성공적으로 삭제되었습니다"}
        else:
            return {"ok": False, "error": "키 삭제에 실패했습니다"}
            
    except Exception as e:
        return {"ok": False, "error": str(e)}

# 사용자별 추천 방식 설정
@app.get("/user/preferences")
async def get_user_preferences(current_user: User = Depends(get_current_user)):
    """사용자별 추천 방식 설정 조회"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT recommendation_type, updated_at
                FROM user_preferences
                WHERE user_id = %s
            """, (current_user.id,))
            
            row = cur.fetchone()
            
            if row:
                return {
                    "ok": True,
                    "data": {
                        "recommendation_type": row[0],  # 'daily' 또는 'conditional'
                        "updated_at": row[1].isoformat() if row[1] else None
                    }
                }
            else:
                # 기본값: 일일 추천 (v2)
                return {
                    "ok": True,
                    "data": {
                        "recommendation_type": "daily",
                        "updated_at": None
                    }
                }
    except Exception as e:
        logger.error(f"[get_user_preferences] 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"ok": False, "error": str(e)}

@app.post("/user/preferences")
async def set_user_preferences(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """사용자별 추천 방식 설정 저장"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        recommendation_type = request.get('recommendation_type')
        
        if recommendation_type not in ['daily', 'conditional']:
            return {
                "ok": False,
                "error": "recommendation_type은 'daily' 또는 'conditional'이어야 합니다"
            }
        
        with db_manager.get_cursor(commit=True) as cur:
            # UPSERT: 있으면 업데이트, 없으면 삽입
            cur.execute("""
                INSERT INTO user_preferences (user_id, recommendation_type, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET
                    recommendation_type = EXCLUDED.recommendation_type,
                    updated_at = NOW()
            """, (current_user.id, recommendation_type))
        
        return {
            "ok": True,
            "message": "추천 방식이 성공적으로 저장되었습니다",
            "data": {
                "recommendation_type": recommendation_type
            }
        }
    except Exception as e:
        logger.error(f"[set_user_preferences] 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"ok": False, "error": str(e)}

# 관리자용 키움 API 키 관리
@app.get("/admin/kiwoom-keys")
async def get_all_kiwoom_keys(admin_user: User = Depends(get_admin_user)):
    """모든 사용자의 키움 API 키 상태 조회 (관리자 전용)"""
    try:
        all_keys = parameter_store.list_all_user_keys()
        return {"ok": True, "data": all_keys}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/admin/kiwoom-keys/{user_id}")
async def get_user_kiwoom_keys_admin(user_id: int, admin_user: User = Depends(get_admin_user)):
    """특정 사용자의 키움 API 키 상태 조회 (관리자 전용)"""
    try:
        credentials = parameter_store.get_user_kiwoom_credentials(user_id)
        return {
            "ok": True,
            "data": {
                "user_id": user_id,
                "api_key_exists": bool(credentials['api_key']),
                "api_secret_exists": bool(credentials['api_secret']),
                "account_no_exists": bool(credentials['account_no']),
                "api_key_preview": credentials['api_key'][:8] + "..." if credentials['api_key'] else None
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.delete("/admin/kiwoom-keys/{user_id}")
async def delete_user_kiwoom_keys_admin(user_id: int, admin_user: User = Depends(get_admin_user)):
    """특정 사용자의 키움 API 키 삭제 (관리자 전용)"""
    try:
        success = parameter_store.delete_all_user_keys(user_id)
        
        if success:
            return {"ok": True, "message": f"사용자 {user_id}의 키움 API 키가 성공적으로 삭제되었습니다"}
        else:
            return {"ok": False, "error": "키 삭제에 실패했습니다"}
            
    except Exception as e:
        return {"ok": False, "error": str(e)}


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


@app.get("/admin/cache-status")
async def get_cache_status(admin_user: User = Depends(get_admin_user)):
    """캐시 현황 조회 (관리자 전용)"""
    try:
        import os
        import re
        from datetime import datetime
        
        base_dir = os.path.dirname(__file__)
        cache_targets = {
            "ohlcv_cache": os.path.join(base_dir, "cache", "ohlcv"),
            "us_futures_cache": os.path.join(base_dir, "cache", "us_futures"),
            "us_stocks_ohlcv_cache": os.path.join(base_dir, "cache", "us_stocks_ohlcv"),
            "us_universe_cache": os.path.join(base_dir, "cache", "us_stocks"),
            "regime_cache": os.path.join(base_dir, "cache", "regime"),
            "data_cache_ohlcv": os.path.join(base_dir, "data_cache", "ohlcv"),
            "data_cache": os.path.join(base_dir, "data_cache")
        }
        
        def _format_ts(ts: float) -> str:
            return datetime.fromtimestamp(ts).isoformat() if ts else None
        
        def _read_last_line(path: str) -> str:
            with open(path, 'rb') as fh:
                fh.seek(0, os.SEEK_END)
                position = fh.tell()
                if position == 0:
                    return ''
                while position > 0:
                    position -= 1
                    fh.seek(position)
                    if fh.read(1) == b'\n':
                        line = fh.readline().strip()
                        if line:
                            return line.decode(errors='ignore')
                fh.seek(0)
                return fh.readline().decode(errors='ignore').strip()

        def _parse_date(value: str):
            if not value:
                return None
            value = value.strip()
            if not value:
                return None
            if re.match(r"^\d{8}$", value):
                return datetime.strptime(value, "%Y%m%d").date()
            if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                return datetime.strptime(value, "%Y-%m-%d").date()
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None

        def _update_range(current_range, candidate):
            if candidate is None:
                return current_range
            if current_range[0] is None or candidate < current_range[0]:
                current_range[0] = candidate
            if current_range[1] is None or candidate > current_range[1]:
                current_range[1] = candidate
            return current_range

        def _csv_date_range(path: str):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    header = fh.readline()
                    first_line = ''
                    while True:
                        line = fh.readline()
                        if not line:
                            break
                        if line.strip():
                            first_line = line.strip()
                            break
                last_line = _read_last_line(path)
                first_date = _parse_date(first_line.split(',')[0]) if first_line else None
                last_date = _parse_date(last_line.split(',')[0]) if last_line else None
                return first_date, last_date
            except Exception:
                return None, None

        def _pkl_date_range(path: str):
            try:
                import pandas as pd
            except Exception:
                return None, None
            try:
                data = pd.read_pickle(path)
            except Exception:
                return None, None
            try:
                if hasattr(data, 'index'):
                    index = data.index
                    if hasattr(index, 'min') and hasattr(index, 'max'):
                        start = index.min()
                        end = index.max()
                        start_date = start.date() if hasattr(start, 'date') else _parse_date(str(start))
                        end_date = end.date() if hasattr(end, 'date') else _parse_date(str(end))
                        return start_date, end_date
                if isinstance(data, dict):
                    date_value = data.get('date')
                    parsed = _parse_date(date_value) if date_value else None
                    return parsed, parsed
            except Exception:
                return None, None
            return None, None

        def _scan_path(path: str, cache_name: str) -> dict:
            if not os.path.exists(path):
                return {
                    "path": path,
                    "exists": False,
                    "type": None,
                    "file_count": 0,
                    "total_size_bytes": 0,
                    "newest_mtime": None,
                    "oldest_mtime": None,
                    "data_start": None,
                    "data_end": None
                }
            
            if cache_name == "ohlcv_cache" and os.path.isdir(path):
                file_count = 0
                total_size = 0
                newest = None
                oldest = None
                date_range = [None, None]
                for entry in os.scandir(path):
                    if not entry.is_file():
                        continue
                    try:
                        stat = entry.stat()
                    except OSError:
                        continue
                    file_count += 1
                    total_size += stat.st_size
                    mtime = stat.st_mtime
                    newest = mtime if newest is None else max(newest, mtime)
                    oldest = mtime if oldest is None else min(oldest, mtime)
                    name_parts = entry.name.rsplit('_', 1)
                    if len(name_parts) == 2 and name_parts[1].endswith('.pkl'):
                        date_part = name_parts[1][:-4]
                        if len(date_part) == 8 and date_part.isdigit():
                            date_value = _parse_date(date_part)
                            _update_range(date_range, date_value)
                return {
                    "path": path,
                    "exists": True,
                    "type": "dir",
                    "file_count": file_count,
                    "total_size_bytes": total_size,
                    "newest_mtime": _format_ts(newest),
                    "oldest_mtime": _format_ts(oldest),
                    "data_start": date_range[0].isoformat() if date_range[0] else None,
                    "data_end": date_range[1].isoformat() if date_range[1] else None
                }

            if os.path.isfile(path):
                size = os.path.getsize(path)
                mtime = os.path.getmtime(path)
                data_start, data_end = (None, None)
                if path.endswith('.csv'):
                    data_start, data_end = _csv_date_range(path)
                elif path.endswith('.pkl'):
                    data_start, data_end = _pkl_date_range(path)
                return {
                    "path": path,
                    "exists": True,
                    "type": "file",
                    "file_count": 1,
                    "total_size_bytes": size,
                    "newest_mtime": _format_ts(mtime),
                    "oldest_mtime": _format_ts(mtime),
                    "data_start": data_start.isoformat() if data_start else None,
                    "data_end": data_end.isoformat() if data_end else None
                }
            
            file_count = 0
            total_size = 0
            newest = None
            oldest = None
            date_range = [None, None]
            for root, _, files in os.walk(path):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    try:
                        stat = os.stat(filepath)
                    except OSError:
                        continue
                    file_count += 1
                    total_size += stat.st_size
                    mtime = stat.st_mtime
                    newest = mtime if newest is None else max(newest, mtime)
                    oldest = mtime if oldest is None else min(oldest, mtime)
                    if filename.endswith('.csv'):
                        start_date, end_date = _csv_date_range(filepath)
                        _update_range(date_range, start_date)
                        _update_range(date_range, end_date)
                    elif filename.endswith('.pkl'):
                        start_date, end_date = _pkl_date_range(filepath)
                        _update_range(date_range, start_date)
                        _update_range(date_range, end_date)
            return {
                "path": path,
                "exists": True,
                "type": "dir",
                "file_count": file_count,
                "total_size_bytes": total_size,
                "newest_mtime": _format_ts(newest),
                "oldest_mtime": _format_ts(oldest),
                "data_start": date_range[0].isoformat() if date_range[0] else None,
                "data_end": date_range[1].isoformat() if date_range[1] else None
            }
        
        results = []
        for name, path in cache_targets.items():
            stats = _scan_path(path, name)
            stats["name"] = name
            results.append(stats)
        
        return {
            "ok": True,
            "data": results
        }
    except Exception as e:
        logger.error(f"[get_cache_status] 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/access-logs")
async def get_access_logs(
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    admin_user: User = Depends(get_admin_user)
):
    """접속 기록 조회 (관리자 전용)"""
    try:
        from services.access_log_service import get_access_logs
        from datetime import datetime
        
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        logs = get_access_logs(
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit
        )
        
        return {
            "ok": True,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"접속 기록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/admin/access-logs/daily-stats")
async def get_daily_visitor_stats_endpoint(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin_user: User = Depends(get_admin_user)
):
    """일별 방문자 수 조회 (관리자 전용)"""
    try:
        from services.access_log_service import get_daily_visitor_stats
        from datetime import datetime
        
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        stats = get_daily_visitor_stats(start_dt, end_dt)
        
        return {
            "ok": True,
            "count": len(stats),
            "stats": stats
        }
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        error_detail = f"일별 방문자 수 조회 중 오류가 발생했습니다: {str(e)}"
        error_traceback = traceback.format_exc()
        print(f"[ERROR] {error_detail}\n{error_traceback}")
        logger.error(f"{error_detail}\n{error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@app.get("/admin/access-logs/daily-stats-by-path")
async def get_daily_visitor_stats_by_path_endpoint(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin_user: User = Depends(get_admin_user)
):
    """화면별 일 방문자 수 조회 (관리자 전용)"""
    try:
        from services.access_log_service import get_daily_visitor_stats_by_path
        from datetime import datetime
        
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        stats = get_daily_visitor_stats_by_path(start_dt, end_dt)
        
        return {
            "ok": True,
            "count": len(stats),
            "stats": stats
        }
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        error_detail = f"화면별 일 방문자 수 조회 중 오류가 발생했습니다: {str(e)}"
        error_traceback = traceback.format_exc()
        print(f"[ERROR] {error_detail}\n{error_traceback}")
        logger.error(f"{error_detail}\n{error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@app.get("/admin/access-logs/cumulative-stats")
async def get_cumulative_visitor_stats_endpoint(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin_user: User = Depends(get_admin_user)
):
    """누적 방문자 수 조회 (관리자 전용)"""
    try:
        from services.access_log_service import get_cumulative_visitor_stats
        from datetime import datetime
        
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        stats = get_cumulative_visitor_stats(start_dt, end_dt)
        
        return {
            "ok": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"누적 방문자 수 조회 중 오류가 발생했습니다: {str(e)}"
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

@app.get("/admin/maintenance")
async def get_maintenance_settings(admin_user: User = Depends(get_admin_user)):
    """메인트넌스 설정 조회"""
    try:
        with db_manager.get_cursor(commit=True) as cur:
            create_maintenance_settings_table(cur)
            cur.execute("SELECT * FROM maintenance_settings ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
        if row:
            end_date_value = row[2]
            if end_date_value and hasattr(end_date_value, "strftime"):
                end_date_value = end_date_value.strftime("%Y%m%d")
            settings = {
                "id": row[0],
                "is_enabled": bool(row[1]),
                "end_date": end_date_value,
                "message": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "updated_at": row[5].isoformat() if row[5] else None,
            }
        else:
            settings = {
                "id": None,
                "is_enabled": False,
                "end_date": None,
                "message": "서비스 점검 중입니다.",
                "created_at": None,
                "updated_at": None
            }
        return settings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메인트넌스 설정 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/admin/popup-notice")
async def get_popup_notice(admin_user: User = Depends(get_admin_user)):
    """팝업 공지 설정 조회"""
    try:
        with db_manager.get_cursor() as cur:
            create_popup_notice_table(cur)
            cur.execute("SELECT * FROM popup_notice ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
        if row:
            notice = {
                "id": row[0],
                "is_enabled": bool(row[1]),
                "title": row[2],
                "message": row[3],
                "start_date": row[4],
                "end_date": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None,
            }
        else:
            notice = {
                "id": None,
                "is_enabled": False,
                "title": "",
                "message": "",
                "start_date": "",
                "end_date": "",
                "created_at": None,
                "updated_at": None
            }
        return notice
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"팝업 공지 설정 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/admin/popup-notice")
async def update_popup_notice(
    notice: PopupNoticeRequest,
    admin_user: User = Depends(get_admin_user)
):
    """팝업 공지 설정 업데이트"""
    try:
        from date_helper import yyyymmdd_to_timestamp
        
        # YYYYMMDD 문자열을 TIMESTAMP WITH TIME ZONE으로 변환
        start_dt = yyyymmdd_to_timestamp(notice.start_date, hour=0, minute=0, second=0)
        end_dt = yyyymmdd_to_timestamp(notice.end_date, hour=23, minute=59, second=59)
        
        with db_manager.get_connection() as conn:
            cur = conn.cursor()
            create_popup_notice_table(cur)
            cur.execute("DELETE FROM popup_notice")
            cur.execute("""
                INSERT INTO popup_notice (is_enabled, title, message, start_date, end_date, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (
                notice.is_enabled,
                notice.title,
                notice.message,
                start_dt,
                end_dt
            ))
            conn.commit()
        return {"message": "팝업 공지 설정이 업데이트되었습니다."}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"날짜 형식 오류: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"팝업 공지 설정 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/popup-notice/status")
async def get_popup_notice_status():
    """팝업 공지 상태 조회 (공개 API)"""
    try:
        from date_helper import timestamp_to_yyyymmdd
        
        with db_manager.get_cursor() as cur:
            create_popup_notice_table(cur)
            cur.execute("""
                SELECT is_enabled, title, message, start_date, end_date
                FROM popup_notice
                ORDER BY id DESC LIMIT 1
            """)
            row = cur.fetchone()
        if row:
            is_enabled = bool(row[0])
            title = row[1]
            message = row[2]
            start_date_raw = row[3]  # TIMESTAMP WITH TIME ZONE 객체
            end_date_raw = row[4]    # TIMESTAMP WITH TIME ZONE 객체
            
            # TIMESTAMP 객체를 YYYYMMDD 문자열로 변환
            start_date = timestamp_to_yyyymmdd(start_date_raw) if start_date_raw else None
            end_date = timestamp_to_yyyymmdd(end_date_raw) if end_date_raw else None
            
            # 날짜 범위 확인 (KST 기준 날짜만 비교)
            if is_enabled and start_date and end_date:
                try:
                    from date_helper import yyyymmdd_to_date
                    start_date_obj = yyyymmdd_to_date(start_date)
                    end_date_obj = yyyymmdd_to_date(end_date)
                    now_date = get_kst_now().date()
                    
                    # 날짜 범위 확인
                    if now_date < start_date_obj or now_date > end_date_obj:
                        is_enabled = False
                except (ValueError, AttributeError, TypeError) as e:
                    # 날짜 파싱 실패 시 로그 출력 (디버깅용)
                    print(f"⚠️ 팝업 공지 날짜 파싱 실패: start_date={start_date}, end_date={end_date}, error={e}")
                    is_enabled = False
            
            return {
                "is_enabled": is_enabled,
                "title": title,
                "message": message,
                "start_date": start_date or "",
                "end_date": end_date or ""
            }
        else:
            return {
                "is_enabled": False,
                "title": "",
                "message": "",
                "start_date": "",
                "end_date": ""
            }
    except Exception as e:
        print(f"⚠️ 팝업 공지 조회 오류: {e}")
        return {
            "is_enabled": False,
            "title": "",
            "message": "",
            "start_date": "",
            "end_date": ""
        }

@app.post("/admin/maintenance")
async def update_maintenance_settings(
    settings: MaintenanceSettingsRequest,
    admin_user: User = Depends(get_admin_user)
):
    """메인트넌스 설정 업데이트"""
    try:
        end_date_value = None
        if settings.end_date:
            try:
                if len(settings.end_date) == 8:
                    end_date_value = datetime.strptime(settings.end_date, "%Y%m%d")
                elif len(settings.end_date) == 10 and "-" in settings.end_date:
                    end_date_value = datetime.strptime(settings.end_date, "%Y-%m-%d")
            except Exception:
                end_date_value = None
        with db_manager.get_connection() as conn:
            cur = conn.cursor()
            create_maintenance_settings_table(cur)
            cur.execute("DELETE FROM maintenance_settings")
            cur.execute("""
                INSERT INTO maintenance_settings (is_enabled, end_date, message, updated_at)
                VALUES (%s, %s, %s, NOW())
            """, (
                settings.is_enabled,
                end_date_value,
                settings.message or "서비스 점검 중입니다."
            ))
            conn.commit()
        return {"message": "메인트넌스 설정이 업데이트되었습니다."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메인트넌스 설정 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/maintenance/status")
async def get_maintenance_status():
    """메인트넌스 상태 조회 (공개 API)"""
    try:
        with db_manager.get_cursor() as cur:
            create_maintenance_settings_table(cur)
            cur.execute("""
                SELECT is_enabled, end_date, message, id
                FROM maintenance_settings
                ORDER BY id DESC LIMIT 1
            """)
            row = cur.fetchone()
        if row:
            is_enabled = bool(row[0])
            end_date = row[1]
            message = row[2]
            record_id = row[3]
            
            # 종료 날짜가 설정되어 있고 현재 날짜가 종료 날짜를 지났으면 자동으로 비활성화
            if is_enabled and end_date:
                try:
                    if isinstance(end_date, str):
                        end_datetime = datetime.strptime(end_date, "%Y%m%d")
                    else:
                        end_datetime = end_date
                    if datetime.now() > end_datetime:
                        is_enabled = False
                        # 자동으로 비활성화
                        with db_manager.get_cursor() as cur_update:
                            cur_update.execute("""
                                UPDATE maintenance_settings 
                                SET is_enabled = FALSE, updated_at = NOW()
                                WHERE id = %s
                            """, (record_id,))
                except ValueError:
                    pass  # 날짜 형식이 잘못된 경우 무시
            
            return {
                "is_enabled": is_enabled,
                "end_date": end_date,
                "message": message
            }
        else:
            return {
                "is_enabled": False,
                "end_date": None,
                "message": "서비스 점검 중입니다."
            }
    except Exception as e:
        return {
            "is_enabled": False,
            "end_date": None,
            "message": "서비스 점검 중입니다."
        }

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


@app.get("/admin/trend-analysis")
async def get_trend_analysis(admin_user: User = Depends(get_admin_user)):
    """추세 변동 대응 분석 (관리자 전용)"""
    try:
        import sys
        import os
        # 경로 추가 (trend_adaptive_scanner.py가 backend 디렉토리에 있음)
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        
        from trend_adaptive_scanner import TrendAdaptiveScanner
        from config import config
        
        scanner = TrendAdaptiveScanner()
        result = scanner.analyze_and_recommend()
        
        # analyze_and_recommend()는 recommended_params, evaluation을 반환
        if isinstance(result, tuple) and len(result) == 2:
            recommended_params, evaluation = result
        else:
            # 반환값이 다른 형식일 경우 처리
            recommended_params = result if isinstance(result, dict) else {}
            evaluation = "good"  # 기본값
        
        # 현재 설정 가져오기
        current_params = {
            "min_signals": config.min_signals,
            "rsi_upper_limit": config.rsi_upper_limit,
            "vol_ma5_mult": config.vol_ma5_mult,
            "gap_max": config.gap_max,
            "ext_from_tema20_max": config.ext_from_tema20_max,
        }
        
        # 최근 4주간 성과
        recent_4weeks = scanner.get_recent_performance(weeks=4)
        recent_metrics = {
            "avg_return": recent_4weeks.avg_return if recent_4weeks else None,
            "win_rate": recent_4weeks.win_rate if recent_4weeks else None,
            "total_stocks": recent_4weeks.total_stocks if recent_4weeks else None,
            "best_return": recent_4weeks.best_return if recent_4weeks else None,
            "worst_return": recent_4weeks.worst_return if recent_4weeks else None,
        }
        
        # 현재 월 성과
        now = datetime.now()
        monthly_perf = scanner.get_monthly_performance(now.year, now.month)
        monthly_metrics = {
            "avg_return": monthly_perf.avg_return if monthly_perf else None,
            "win_rate": monthly_perf.win_rate if monthly_perf else None,
            "total_stocks": monthly_perf.total_stocks if monthly_perf else None,
        }
        
        return {
            "ok": True,
            "data": {
                "evaluation": evaluation,
                "current_params": current_params,
                "recommended_params": recommended_params,
                "recent_4weeks": recent_metrics,
                "current_month": monthly_metrics,
                "fallback_enabled": config.fallback_enable,
                "fallback_target_min": config.fallback_target_min,
                "fallback_target_max": config.fallback_target_max,
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


@app.post("/admin/trend-apply")
async def apply_trend_params(
    params: dict,
    admin_user: User = Depends(get_admin_user)
):
    """추세 변동 대응 파라미터 적용 (관리자 전용)"""
    try:
        import subprocess
        import os
        import shutil
        
        # .env 파일 경로
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(backend_dir, ".env")
        
        # 백업
        backup_path = f"{env_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if os.path.exists(env_path):
            shutil.copy2(env_path, backup_path)
        
        # .env 파일 읽기
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()
        
        # 파라미터 업데이트
        env_dict = {}
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        # 새로운 파라미터 적용
        param_mapping = {
            "min_signals": "MIN_SIGNALS",
            "rsi_upper_limit": "RSI_UPPER_LIMIT",
            "vol_ma5_mult": "VOL_MA5_MULT",
            "gap_max": "GAP_MAX",
            "ext_from_tema20_max": "EXT_FROM_TEMA20_MAX",
        }
        
        changes = []
        for key, env_key in param_mapping.items():
            if key in params:
                old_value = env_dict.get(env_key, "")
                new_value = str(params[key])
                env_dict[env_key] = new_value
                if old_value != new_value:
                    changes.append(f"{key}: {old_value} → {new_value}")
        
        # .env 파일 쓰기 (더 간단한 방법)
        output_lines = []
        existing_keys = set()
        
        # 기존 라인 처리
        # 역매핑 생성 (성능 향상 및 안전성)
        reverse_mapping = {v: k for k, v in param_mapping.items()}
        
        for line in env_lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                key = line_stripped.split('=')[0].strip()
                if key in reverse_mapping:
                    # 업데이트할 키 찾기 (안전하게)
                    param_key = reverse_mapping.get(key)
                    if param_key and param_key in params:
                        output_lines.append(f"{key}={params[param_key]}\n")
                        existing_keys.add(key)
                    else:
                        output_lines.append(line)  # 기존 값 유지
                        existing_keys.add(key)
                else:
                    output_lines.append(line)
            else:
                output_lines.append(line)
        
        # 새로 추가해야 할 항목
        for param_key, env_key in param_mapping.items():
            if env_key not in existing_keys and param_key in params:
                output_lines.append(f"{env_key}={params[param_key]}\n")
        
        # 파일 쓰기
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
        
        return {
            "ok": True,
            "message": "파라미터가 성공적으로 적용되었습니다. 서버 재시작이 필요할 수 있습니다.",
            "changes": changes,
            "backup_path": os.path.basename(backup_path) if os.path.exists(backup_path) else None
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


@app.get("/admin/bottom-nav-link")
async def get_bottom_nav_link(admin_user: User = Depends(get_admin_user)):
    """바텀메뉴 추천종목 링크 설정 조회 (active_engine 우선)"""
    try:
        from scanner_settings_manager import get_active_engine, get_scanner_setting
        
        # active_engine 우선 확인
        active_engine = get_active_engine()
        
        # active_engine에 따라 링크 결정
        if active_engine == 'v3':
            # v3 전용 화면 사용
            return {
                "link_type": "v3",
                "link_url": "/v3/scanner-v3"
            }
        elif active_engine == 'v2':
            return {
                "link_type": "v2",
                "link_url": "/v2/scanner-v2"
            }
        else:
            # v1 또는 기존 설정 사용
            link_type = get_scanner_setting('bottom_nav_scanner_link', 'v1')
            return {
                "link_type": link_type,  # 'v1' 또는 'v2'
                "link_url": "/customer-scanner" if link_type == "v1" else "/v2/scanner-v2"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"바텀메뉴 링크 설정 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/admin/bottom-nav-link")
async def update_bottom_nav_link(
    request: dict,
    admin_user: User = Depends(get_admin_user)
):
    """바텀메뉴 추천종목 링크 설정 업데이트 (v3 지원)"""
    try:
        link_type = request.get('link_type') if isinstance(request, dict) else request
        if not link_type or link_type not in ['v1', 'v2', 'v3']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="link_type은 'v1', 'v2', 또는 'v3'여야 합니다."
            )
        
        from scanner_settings_manager import set_scanner_setting
        
        # v3는 active_engine으로 관리되므로 active_engine을 v3로 설정
        if link_type == 'v3':
            from scanner_settings_manager import set_active_engine
            if not set_active_engine(
                'v3',
                updated_by=admin_user.email if admin_user else None
            ):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="active_engine을 v3로 저장하는 데 실패했습니다."
                )
            return {
                "message": "V3 엔진으로 전환되었습니다.",
                "link_type": "v3",
                "link_url": "/v3/scanner-v3"
            }
        
        success = set_scanner_setting(
            'bottom_nav_scanner_link',
            link_type,
            description='바텀메뉴 추천종목 링크 타입 (v1: /customer-scanner, v2: /v2/scanner-v2)',
            updated_by=admin_user.email if admin_user else None
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="바텀메뉴 링크 설정 저장에 실패했습니다."
            )
        
        link_url_map = {
            'v1': '/customer-scanner',
            'v2': '/v2/scanner-v2',
            'v3': '/v3/scanner-v3'
        }
        
        return {
            "message": "바텀메뉴 링크 설정이 업데이트되었습니다.",
            "link_type": link_type,
            "link_url": link_url_map.get(link_type, '/customer-scanner')
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"바텀메뉴 링크 설정 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/admin/bottom-nav-visible")
async def get_bottom_nav_visible(admin_user: User = Depends(get_admin_user)):
    """바텀메뉴 노출 설정 조회 (관리자 전용)"""
    try:
        from scanner_settings_manager import get_scanner_setting
        visible = get_scanner_setting('bottom_nav_visible', 'true')
        return {
            "is_visible": visible.lower() == 'true' if visible else True
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"바텀메뉴 노출 설정 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/admin/bottom-nav-visible")
async def update_bottom_nav_visible(
    request: dict,
    admin_user: User = Depends(get_admin_user)
):
    """바텀메뉴 노출 설정 업데이트 (관리자 전용)"""
    try:
        is_visible = request.get('is_visible') if isinstance(request, dict) else request
        if not isinstance(is_visible, bool):
            # 문자열로 전달된 경우 변환
            if isinstance(is_visible, str):
                is_visible = is_visible.lower() in ['true', '1', 'yes']
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="is_visible은 boolean 값이어야 합니다."
                )
        
        from scanner_settings_manager import set_scanner_setting
        success = set_scanner_setting(
            'bottom_nav_visible',
            'true' if is_visible else 'false',
            description='바텀메뉴 노출 여부 (true: 표시, false: 숨김)',
            updated_by=admin_user.email if admin_user else None
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="바텀메뉴 노출 설정 저장에 실패했습니다."
            )
        
        return {
            "ok": True,
            "message": "바텀메뉴 노출 설정이 업데이트되었습니다.",
            "is_visible": is_visible
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"바텀메뉴 노출 설정 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/admin/bottom-nav-menu-items")
async def get_bottom_nav_menu_items(admin_user: User = Depends(get_admin_user)):
    """바텀메뉴 개별 메뉴 아이템 설정 조회 (관리자 전용)"""
    try:
        from scanner_settings_manager import get_scanner_setting
        import json
        
        # 기본 메뉴 아이템 설정
        default_items = {
            "korean_stocks": True,
            "us_stocks": True,
            "stock_analysis": True,
            "portfolio": True,
            "more": True
        }
        
        menu_items_json = get_scanner_setting('bottom_nav_menu_items', None)
        if menu_items_json:
            try:
                menu_items = json.loads(menu_items_json)
                # 기본값과 병합
                return {**default_items, **menu_items}
            except:
                return default_items
        
        return default_items
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"바텀메뉴 메뉴 아이템 설정 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/admin/bottom-nav-menu-items")
async def update_bottom_nav_menu_items(
    request: dict,
    admin_user: User = Depends(get_admin_user)
):
    """바텀메뉴 개별 메뉴 아이템 설정 업데이트 (관리자 전용)"""
    try:
        import json
        from scanner_settings_manager import set_scanner_setting
        
        # request가 dict인 경우 'menu_items' 키에서 가져오기
        if isinstance(request, dict):
            menu_items = request.get('menu_items')
        else:
            menu_items = request
        
        # menu_items가 없거나 dict가 아니면 에러
        if not menu_items or not isinstance(menu_items, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="menu_items는 객체여야 합니다."
            )
        
        # JSON 문자열로 변환하여 저장
        menu_items_json = json.dumps(menu_items)
        
        success = set_scanner_setting(
            'bottom_nav_menu_items',
            menu_items_json,
            description='바텀메뉴 개별 메뉴 아이템 표시 여부 (JSON 형식)',
            updated_by=admin_user.email if admin_user else None
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="바텀메뉴 메뉴 아이템 설정 저장에 실패했습니다."
            )
        
        return {
            "ok": True,
            "message": "바텀메뉴 메뉴 아이템 설정이 업데이트되었습니다.",
            "menu_items": menu_items
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"바텀메뉴 메뉴 아이템 설정 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/bottom-nav-visible")
async def get_bottom_nav_visible_public():
    """바텀메뉴 노출 설정 조회 (공개 API)"""
    try:
        from scanner_settings_manager import get_scanner_setting
        visible = get_scanner_setting('bottom_nav_visible', 'true')
        return {
            "is_visible": visible.lower() == 'true' if visible else True
        }
    except Exception as e:
        # 에러 발생 시 기본값으로 true 반환
        return {
            "is_visible": True
        }

@app.get("/bottom-nav-menu-items")
async def get_bottom_nav_menu_items_public():
    """바텀메뉴 개별 메뉴 아이템 설정 조회 (공개 API)"""
    try:
        from scanner_settings_manager import get_scanner_setting
        import json
        
        # 기본 메뉴 아이템 설정
        default_items = {
            "korean_stocks": True,
            "us_stocks": True,
            "stock_analysis": True,
            "portfolio": True,
            "more": True
        }
        
        menu_items_json = get_scanner_setting('bottom_nav_menu_items', None)
        if menu_items_json:
            try:
                menu_items = json.loads(menu_items_json)
                # 기본값과 병합
                return {**default_items, **menu_items}
            except:
                return default_items
        
        return default_items
    except Exception as e:
        # 에러 발생 시 기본값 반환
        return {
            "korean_stocks": True,
            "us_stocks": True,
            "stock_analysis": True,
            "portfolio": True,
            "more": True
        }

@app.get("/bottom-nav-link")
async def get_bottom_nav_link_public(current_user: Optional[User] = Depends(get_optional_user)):
    """바텀메뉴 추천종목 링크 조회 (공개 API, 사용자별 설정 우선, active_engine 차순)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from scanner_settings_manager import get_active_engine, get_scanner_setting
        # 1) 로그인하지 않은 사용자는 항상 v2
        if not current_user:
            return {
                "link_type": "v2",
                "link_url": "/v2/scanner-v2"
            }

        # 2) 로그인한 사용자는 개인 설정 우선
        try:
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT recommendation_type
                    FROM user_preferences
                    WHERE user_id = %s
                """, (current_user.id,))
                row = cur.fetchone()
                if row:
                    recommendation_type = row[0]
                    # 'daily' -> v2, 'conditional' -> v3
                    if recommendation_type == 'conditional':
                        return {
                            "link_type": "v3",
                            "link_url": "/v3/scanner-v3"
                        }
                    if recommendation_type == 'daily':
                        return {
                            "link_type": "v2",
                            "link_url": "/v2/scanner-v2"
                        }
        except Exception as e:
            logger.warning(f"[get_bottom_nav_link_public] 사용자별 설정 조회 실패: {e}")
        
        # 3) 개인 설정이 없으면 전역 설정 확인 (active_engine 우선)
        active_engine = get_active_engine()
        
        # active_engine에 따라 링크 결정
        if active_engine == 'v3':
            # v3 전용 화면 사용
            return {
                "link_type": "v3",
                "link_url": "/v3/scanner-v3"
            }
        elif active_engine == 'v2':
            return {
                "link_type": "v2",
                "link_url": "/v2/scanner-v2"
            }
        else:
            # v1 또는 기존 설정 사용
            link_type = get_scanner_setting('bottom_nav_scanner_link', 'v1')
            link_url_map = {
                "v1": "/customer-scanner",
                "v2": "/v2/scanner-v2",
                "v3": "/v3/scanner-v3",
            }
            return {
                "link_type": link_type,
                "link_url": link_url_map.get(link_type, "/customer-scanner")
            }
    except Exception as e:
        logger.error(f"[get_bottom_nav_link_public] 오류: {e}")
        # 에러 발생 시 기본값 반환 (v2 일일 추천)
        return {
            "link_type": "v2",
            "link_url": "/v2/scanner-v2"
        }

@app.get("/admin/scanner-settings")
async def get_scanner_settings(admin_user: User = Depends(get_admin_user)):
    """스캐너 설정 조회 (관리자 전용)"""
    try:
        from scanner_settings_manager import get_all_scanner_settings
        settings = get_all_scanner_settings()
        return {
            "ok": True,
            "settings": settings
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/admin/scanner-settings")
async def update_scanner_settings(
    settings: dict,
    admin_user: User = Depends(get_admin_user)
):
    """스캐너 설정 업데이트 (관리자 전용)"""
    try:
        from scanner_settings_manager import set_scanner_setting
        
        changes = []
        allowed_keys = ['scanner_version', 'scanner_v2_enabled', 'regime_version', 'active_engine']
        
        for key, value in settings.items():
            if key not in allowed_keys:
                continue
            
            # 값 검증
            if key == 'scanner_version':
                if value not in ['v1', 'v2', 'v2-lite', 'v3']:
                    return {"ok": False, "error": f"scanner_version은 'v1', 'v2', 'v2-lite', 또는 'v3'만 가능합니다."}
            elif key == 'regime_version':
                if value not in ['v1', 'v3', 'v4']:
                    return {"ok": False, "error": f"regime_version은 'v1', 'v3', 또는 'v4'만 가능합니다."}
            elif key == 'active_engine':
                if value not in ['v1', 'v2', 'v3']:
                    return {"ok": False, "error": f"active_engine은 'v1', 'v2', 또는 'v3'만 가능합니다."}
            elif key == 'scanner_v2_enabled':
                if not isinstance(value, bool):
                    value = str(value).lower() == 'true'
                value = 'true' if value else 'false'
            
            # DB에 저장
            from scanner_settings_manager import get_scanner_setting, set_active_engine
            
            old_value = get_scanner_setting(key)
            
            # active_engine은 별도 함수 사용
            if key == 'active_engine':
                success = set_active_engine(
                    str(value),
                    updated_by=admin_user.email if hasattr(admin_user, 'email') else None
                )
            else:
                success = set_scanner_setting(
                    key, 
                    str(value), 
                    description=f"스캐너 {key} 설정",
                    updated_by=admin_user.email if hasattr(admin_user, 'email') else None
                )
            
            if success:
                changes.append(f"{key}: {old_value} → {value}")
        
        return {
            "ok": True,
            "message": "스캐너 설정이 업데이트되었습니다. 다음 스캔부터 적용됩니다.",
            "changes": changes
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


@app.post("/admin/backtest")
async def run_backtest_admin(
    payload: dict,
    admin_user: User = Depends(get_admin_user)
):
    """백테스트 실행 (관리자 전용)"""
    try:
        scanner = payload.get("scanner")
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        
        if scanner not in ["v2", "v3", "v3_midterm", "v3_v2_lite"]:
            return {"ok": False, "error": "scanner는 v2, v3, v3_midterm, v3_v2_lite만 가능합니다."}
        if not start_date or not end_date:
            return {"ok": False, "error": "start_date, end_date는 필수입니다."}
        if not (len(start_date) == 8 and start_date.isdigit() and len(end_date) == 8 and end_date.isdigit()):
            return {"ok": False, "error": "날짜 형식은 YYYYMMDD 입니다."}
        
        from pathlib import Path
        from services.backtest_service import run_backtest, write_backtest_report
        
        Path("backend/reports/backtest").mkdir(parents=True, exist_ok=True)
        output_path = f"backend/reports/backtest/backtest_{scanner}_{start_date}_{end_date}.json"
        report = run_backtest(scanner, start_date, end_date)
        write_backtest_report(scanner, start_date, end_date, output_path)
        
        return {
            "ok": True,
            "report": report,
            "output_path": output_path
        }
    except Exception as e:
        logger.error(f"[run_backtest_admin] 오류: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@app.post("/admin/scan-range")
async def run_scan_range_admin(
    payload: dict,
    admin_user: User = Depends(get_admin_user)
):
    """기간 스캔 실행 (관리자 전용)"""
    try:
        scanner = payload.get("scanner")
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        if scanner not in ["v1", "v2", "v3"]:
            return {"ok": False, "error": "scanner는 v1, v2, v3만 가능합니다."}
        if not start_date or not end_date:
            return {"ok": False, "error": "start_date, end_date는 필수입니다."}
        if not (len(start_date) == 8 and start_date.isdigit() and len(end_date) == 8 and end_date.isdigit()):
            return {"ok": False, "error": "날짜 형식은 YYYYMMDD 입니다."}
        
        start_obj = yyyymmdd_to_date(start_date)
        end_obj = yyyymmdd_to_date(end_date)
        if start_obj > end_obj:
            return {"ok": False, "error": "start_date는 end_date보다 이전이어야 합니다."}
        
        today_str = get_kst_now().strftime('%Y%m%d')
        if end_date > today_str:
            return {"ok": False, "error": "end_date는 오늘 이후일 수 없습니다."}
        
        current = start_obj
        scanned_days = 0
        skipped_days = 0
        total_matched = 0
        errors = []
        
        while current <= end_obj:
            day_str = current.strftime('%Y%m%d')
            if not is_trading_day(day_str):
                skipped_days += 1
                current += timedelta(days=1)
                continue
            try:
                resp = scan(
                    kospi_limit=None,
                    kosdaq_limit=None,
                    save_snapshot=True,
                    sort_by='score',
                    date=day_str,
                    scanner_version=scanner
                )
                scanned_days += 1
                total_matched += getattr(resp, "matched_count", 0)
            except Exception as e:
                errors.append({"date": day_str, "error": str(e)})
            current += timedelta(days=1)
        
        return {
            "ok": True,
            "scanner": scanner,
            "start_date": start_date,
            "end_date": end_date,
            "scanned_days": scanned_days,
            "skipped_days": skipped_days,
            "total_matched": total_matched,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"[run_scan_range_admin] 오류: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@app.post("/clear-cache")
async def clear_returns_cache():
    """수익률 계산 캐시를 클리어합니다"""
    try:
        clear_cache()
        return {"ok": True, "message": "캐시가 클리어되었습니다"}
    except Exception as e:
        return {"ok": False, "error": f"캐시 클리어 중 오류: {str(e)}"}


@app.get("/quarterly-analysis")
async def get_quarterly_analysis(year: int = 2025, quarter: int = 1):
    """분기별 추천 종목 성과 분석"""
    try:
        # 분기별 날짜 범위 계산 (YYYYMMDD 형식)
        if quarter == 1:
            start_date = f"{year}0101"
            end_date = f"{year}0331"
        elif quarter == 2:
            start_date = f"{year}0401"
            end_date = f"{year}0630"
        elif quarter == 3:
            start_date = f"{year}0701"
            end_date = f"{year}0930"
        elif quarter == 4:
            start_date = f"{year}1001"
            end_date = f"{year}1231"
        else:
            raise HTTPException(status_code=400, detail="잘못된 분기입니다")
        
        start_dt = datetime.strptime(start_date, '%Y%m%d').date()
        end_dt = datetime.strptime(end_date, '%Y%m%d').date()
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT date, code, name, current_price, volume, change_rate, market, strategy,
                       indicators, trend, flags, details, returns, recurrence
                FROM scan_rank
                WHERE date BETWEEN %s AND %s
                ORDER BY date
            """, (start_dt, end_dt))
            rows = cur.fetchall()
        
        if not rows:
            return {
                "ok": True,
                "data": {
                    "total_stocks": 0,
                    "avg_return": 0,
                    "positive_rate": 0,
                    "dates": [],
                    "stocks": [],
                    "best_stock": None,
                    "worst_stock": None
                }
            }
        
        # 데이터 처리
        stocks = []
        dates = set()
        total_return = 0
        positive_count = 0
        
        for row in rows:
            if isinstance(row, dict):
                data = row
            else:
                columns = [
                    "date", "code", "name", "current_price", "volume", "change_rate",
                    "market", "strategy", "indicators", "trend", "flags", "details",
                    "returns", "recurrence"
                ]
                data = dict(zip(columns, row))
            
            date_value = data.get("date")
            code = data.get("code")
            name = data.get("name")
            current_price = data.get("current_price")
            volume = data.get("volume")
            change_rate = data.get("change_rate")
            market = data.get("market")
            strategy = data.get("strategy")
            
            if not name or not current_price:
                continue
                
            if hasattr(date_value, "strftime"):
                date_str = date_value.strftime('%Y%m%d')
                dates.add(date_value.strftime('%Y-%m-%d'))
            else:
                date_str = str(date_value)
                dates.add(date_str)
            
            # 수익률 계산 (실시간)
            try:
                returns_info = calculate_returns(code, date_str)
                current_return = returns_info.get('current_return', 0)
                max_return = returns_info.get('max_return', 0)
                min_return = returns_info.get('min_return', 0)
                days_elapsed = returns_info.get('days_elapsed', 0)
            except:
                current_return = 0
                max_return = 0
                min_return = 0
                days_elapsed = 0
            
            stock_data = {
                "ticker": code,
                "name": name,
                "scan_price": current_price,
                "scan_date": date_str,
                "current_return": current_return,
                "max_return": max_return,
                "min_return": min_return,
                "days_elapsed": days_elapsed
            }
            
            stocks.append(stock_data)
            total_return += current_return
            
            if max_return > 0:
                positive_count += 1
        
        # 통계 계산
        total_stocks = len(stocks)
        avg_return = total_return / total_stocks if total_stocks > 0 else 0
        positive_rate = (positive_count / total_stocks * 100) if total_stocks > 0 else 0
        
        # 최고/최저 성과 종목 찾기
        best_stock = max(stocks, key=lambda x: x['current_return']) if stocks else None
        worst_stock = min(stocks, key=lambda x: x['current_return']) if stocks else None
        
        return {
            "ok": True,
            "data": {
                "total_stocks": total_stocks,
                "avg_return": round(avg_return, 2),
                "positive_rate": round(positive_rate, 2),
                "dates": sorted(list(dates)),
                "stocks": stocks,
                "best_stock": best_stock,
                "worst_stock": worst_stock
            }
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"분기별 분석 중 오류가 발생했습니다: {str(e)}"
        }


# ==================== 보고서 조회 API ====================

@app.get("/reports/weekly/{year}/{month}/{week}")
async def get_weekly_report(year: int, month: int, week: int):
    """주간 보고서 조회 (향상된 버전)"""
    try:
        enhanced_report = report_generator.generate_enhanced_report("weekly", year, month, week)
        
        if "error" in enhanced_report:
            return {
                "ok": False,
                "error": f"{year}년 {month}월 {week}주차 보고서가 없습니다."
            }
        
        return {
            "ok": True,
            "data": enhanced_report
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"주간 보고서 조회 중 오류가 발생했습니다: {str(e)}"
        }


@app.get("/reports/monthly/{year}/{month}")
async def get_monthly_report(year: int, month: int):
    """월간 보고서 조회 (향상된 버전)"""
    try:
        enhanced_report = report_generator.generate_enhanced_report("monthly", year, month)
        
        if "error" in enhanced_report:
            return {
                "ok": False,
                "error": f"{year}년 {month}월 보고서가 없습니다."
            }
        
        return {
            "ok": True,
            "data": enhanced_report
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"월간 보고서 조회 중 오류가 발생했습니다: {str(e)}"
        }


@app.get("/reports/quarterly/{year}/{quarter}")
async def get_quarterly_report(year: int, quarter: int):
    """분기 보고서 조회"""
    try:
        filename = f"quarterly_{year}_Q{quarter}.json"
        report_data = report_generator._load_report("quarterly", filename)
        
        if not report_data:
            return {
                "ok": False,
                "error": f"{year}년 {quarter}분기 보고서가 없습니다."
            }
        
        return {
            "ok": True,
            "data": report_data
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"분기 보고서 조회 중 오류가 발생했습니다: {str(e)}"
        }


@app.get("/reports/yearly/{year}")
async def get_yearly_report(year: int):
    """연간 보고서 조회"""
    try:
        filename = f"yearly_{year}.json"
        report_data = report_generator._load_report("yearly", filename)
        
        if not report_data:
            return {
                "ok": False,
                "error": f"{year}년 보고서가 없습니다."
            }
        
        return {
            "ok": True,
            "data": report_data
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"연간 보고서 조회 중 오류가 발생했습니다: {str(e)}"
        }


@app.get("/reports/available/{report_type}")
async def get_available_reports(report_type: str):
    """사용 가능한 보고서 목록 조회"""
    try:
        import os
        import glob
        
        if report_type not in ["weekly", "monthly", "quarterly", "yearly"]:
            return {
                "ok": False,
                "error": "잘못된 보고서 유형입니다."
            }
        
        # 절대 경로 사용 (main.py는 backend/main.py이므로)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        report_dir = os.path.join(base_dir, "backend", "reports", report_type)
        if not os.path.exists(report_dir):
            return {
                "ok": True,
                "data": []
            }
        
        # 파일 목록 조회
        pattern = f"{report_dir}/*.json"
        files = glob.glob(pattern)
        
        reports = []
        for file_path in files:
            filename = os.path.basename(file_path)
            # 파일명에서 정보 추출
            if report_type == "weekly":
                # weekly_2025_08_week1.json
                parts = filename.replace(".json", "").split("_")
                if len(parts) == 4:
                    year = int(parts[1])
                    month = int(parts[2])
                    week = int(parts[3].replace("week", ""))
                    reports.append({
                        "year": year,
                        "month": month,
                        "week": week,
                        "filename": filename
                    })
            elif report_type == "monthly":
                # monthly_2025_08.json
                parts = filename.replace(".json", "").split("_")
                if len(parts) == 3:
                    year = int(parts[1])
                    month = int(parts[2])
                    reports.append({
                        "year": year,
                        "month": month,
                        "filename": filename
                    })
            elif report_type == "quarterly":
                # quarterly_2025_Q1.json
                parts = filename.replace(".json", "").split("_")
                if len(parts) == 3:
                    year = int(parts[1])
                    quarter = int(parts[2].replace("Q", ""))
                    reports.append({
                        "year": year,
                        "quarter": quarter,
                        "filename": filename
                    })
            elif report_type == "yearly":
                # yearly_2025.json
                parts = filename.replace(".json", "").split("_")
                if len(parts) == 2:
                    year = int(parts[1])
                    reports.append({
                        "year": year,
                        "filename": filename
                    })
        
        # 정렬
        reports.sort(key=lambda x: (x["year"], x.get("month", 0), x.get("quarter", 0), x.get("week", 0)))
        
        return {
            "ok": True,
            "data": reports
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"보고서 목록 조회 중 오류가 발생했습니다: {str(e)}"
        }


@app.get("/weekly-analysis")
async def get_weekly_analysis(year: int = 2025, month: int = 1, week: int = 1):
    """주별 추천 종목 성과 분석"""
    try:
        # 월별 날짜 범위 계산
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="잘못된 월입니다 (1-12)")
        
        if week < 1 or week > 5:
            raise HTTPException(status_code=400, detail="잘못된 주차입니다 (1-5)")
        
        # 해당 월의 첫날과 마지막날 계산
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        
        # 주차별 날짜 범위 계산 (YYYYMMDD 형식)
        week_start = (week - 1) * 7 + 1
        week_end = min(week_start + 6, last_day)
        
        start_date = f"{year}{month:02d}{week_start:02d}"
        end_date = f"{year}{month:02d}{week_end:02d}"
        
        start_dt = datetime.strptime(start_date, '%Y%m%d').date()
        end_dt = datetime.strptime(end_date, '%Y%m%d').date()
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT date, code, name, current_price, volume, change_rate, market, strategy,
                       indicators, trend, flags, details, returns, recurrence
                FROM scan_rank
                WHERE date BETWEEN %s AND %s
                ORDER BY date
            """, (start_dt, end_dt))
            rows = cur.fetchall()
        
        if not rows:
            return {
            "ok": True,
            "data": {
                    "total_stocks": 0,
                    "avg_return": 0,
                    "positive_rate": 0,
                    "dates": [],
                    "stocks": [],
                    "best_stock": None,
                    "worst_stock": None
                }
            }
        
        # 데이터 처리
        stocks = []
        dates = set()
        total_return = 0
        positive_count = 0
        
        # 유효한 데이터만 필터링
        valid_rows = []
        for row in rows:
            if isinstance(row, dict):
                data = row
            else:
                columns = [
                    "date", "code", "name", "current_price", "volume", "change_rate",
                    "market", "strategy", "indicators", "trend", "flags", "details",
                    "returns", "recurrence"
                ]
                data = dict(zip(columns, row))
            
            date_value = data.get("date")
            code = data.get("code")
            name = data.get("name")
            current_price = data.get("current_price")
            
            if not name or not current_price:
                continue
                
            if hasattr(date_value, "strftime"):
                date_label = date_value.strftime('%Y-%m-%d')
            else:
                date_label = str(date_value)
            dates.add(date_label)
            valid_rows.append(data)
        
        # 데이터 구성 및 수익률 계산
        for data in valid_rows:
            date_value = data.get("date")
            code = data.get("code")
            name = data.get("name")
            current_price = data.get("current_price")
            
            # 수익률 계산 (임시로 비활성화 - 성능 문제)
            current_return = 0
            max_return = 0
            min_return = 0
            days_elapsed = 0
            
            stock_data = {
                "ticker": code,
                "name": name,
                "scan_price": current_price,
                "scan_date": date_value.strftime('%Y%m%d') if hasattr(date_value, "strftime") else str(date_value),
                "current_return": current_return,
                "max_return": max_return,
                "min_return": min_return,
                "days_elapsed": days_elapsed
            }
            
            stocks.append(stock_data)
            total_return += current_return
            
            if max_return > 0:
                positive_count += 1
        
        # 통계 계산
        total_stocks = len(stocks)
        avg_return = total_return / total_stocks if total_stocks > 0 else 0
        positive_rate = (positive_count / total_stocks * 100) if total_stocks > 0 else 0
        
        # 최고/최저 성과 종목 찾기
        best_stock = max(stocks, key=lambda x: x['current_return']) if stocks else None
        worst_stock = min(stocks, key=lambda x: x['current_return']) if stocks else None
        
        return {
            "ok": True,
            "data": {
                "total_stocks": total_stocks,
                "avg_return": round(avg_return, 2),
                "positive_rate": round(positive_rate, 2),
                "dates": sorted(list(dates)),
                "stocks": stocks,
                "best_stock": best_stock,
                "worst_stock": worst_stock
            }
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"월별 분석 중 오류가 발생했습니다: {str(e)}"
        }


@app.get("/quarterly-summary")
async def get_quarterly_summary(year: int = 2025):
    """연도별 분기 요약"""
    try:
        quarters = []
        yearly_total_stocks = 0
        yearly_total_return = 0
        yearly_positive_count = 0
        
        for quarter in range(1, 5):
            # 분기별 데이터 조회
            quarterly_response = await get_quarterly_analysis(year, quarter)
            
            if quarterly_response["ok"]:
                quarterly_data = quarterly_response["data"]
                quarters.append({
                    "quarter": quarter,
                    "total_stocks": quarterly_data["total_stocks"],
                    "avg_return": quarterly_data["avg_return"],
                    "positive_rate": quarterly_data["positive_rate"]
                })
                
                yearly_total_stocks += quarterly_data["total_stocks"]
                yearly_total_return += quarterly_data["avg_return"] * quarterly_data["total_stocks"]
                yearly_positive_count += quarterly_data["positive_rate"] * quarterly_data["total_stocks"] / 100
        
        # 연도 전체 요약
        yearly_avg_return = yearly_total_return / yearly_total_stocks if yearly_total_stocks > 0 else 0
        yearly_positive_rate = yearly_positive_count / yearly_total_stocks * 100 if yearly_total_stocks > 0 else 0
        
        return {
            "ok": True,
            "data": {
                "year": year,
                "quarters": quarters,
                "yearly_summary": {
                    "total_stocks": yearly_total_stocks,
                    "avg_return": round(yearly_avg_return, 2),
                    "positive_rate": round(yearly_positive_rate, 2)
                }
            }
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"연도별 요약 중 오류가 발생했습니다: {str(e)}"
        }


@app.get("/recurring-stocks")
async def get_recurring_stocks(days: int = 14, min_appearances: int = 2):
    """재등장 종목 정보를 가져옵니다."""
    try:
        from datetime import datetime, timedelta
        
        end_dt = datetime.now().date()
        start_dt = (datetime.now() - timedelta(days=days)).date()
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT date, code, name, current_price, volume, change_rate, market, strategy,
                       indicators, trend, flags, details, returns, recurrence
                FROM scan_rank
                WHERE date BETWEEN %s AND %s
                ORDER BY date DESC
            """, (start_dt, end_dt))
            rows = cur.fetchall()
        
        if not rows:
            return {"ok": True, "data": {"recurring_stocks": {}}}
        
        # 종목별 등장 횟수와 날짜 수집
        stock_data = {}
        for row in rows:
            if isinstance(row, dict):
                data = row
            else:
                columns = [
                    "date", "code", "name", "current_price", "volume", "change_rate",
                    "market", "strategy", "indicators", "trend", "flags", "details",
                    "returns", "recurrence"
                ]
                data = dict(zip(columns, row))
            
            date_val = data.get("date")
            code = data.get("code")
            name = data.get("name")
            current_price = data.get("current_price")
            change_rate = data.get("change_rate")
            
            if not name or not code:
                continue
                
            if code not in stock_data:
                stock_data[code] = {
                    "name": name,
                    "appearances": 0,
                    "dates": [],
                    "latest_price": current_price,
                    "latest_change_rate": change_rate
                }
            
            stock_data[code]["appearances"] += 1
            if hasattr(date_val, "strftime"):
                stock_data[code]["dates"].append(date_val.strftime('%Y%m%d'))
            else:
                stock_data[code]["dates"].append(str(date_val))
            stock_data[code]["latest_price"] = current_price
            stock_data[code]["latest_change_rate"] = change_rate
        
        # 최소 등장 횟수 이상인 종목만 필터링
        recurring_stocks = {}
        for code, data in stock_data.items():
            if data["appearances"] >= min_appearances:
                recurring_stocks[code] = {
                    "name": data["name"],
                    "appearances": data["appearances"],
                    "dates": sorted(data["dates"], reverse=True),  # 최신 날짜부터
                    "latest_price": data["latest_price"],
                    "latest_change_rate": data["latest_change_rate"]
                }
        
        return {"ok": True, "data": {"recurring_stocks": recurring_stocks}}
        
    except Exception as e:
        return {"ok": False, "error": f"재등장 종목 조회 중 오류가 발생했습니다: {str(e)}"}


@app.get('/test-market-scenarios')
def get_test_market_scenarios():
    """테스트용 시장 상황별 스캔 결과 시나리오"""
    scenarios = {
        "bull": {
            "name": "강세장",
            "as_of": "20250101",
            "matched_count": 15,
            "rsi_threshold": 65,
            "items": [
                {"ticker": "005930", "name": "삼성전자", "score": 9.2, "indicators": {"change_rate": 3.5}},
                {"ticker": "000660", "name": "SK하이닉스", "score": 8.8, "indicators": {"change_rate": 2.8}},
                {"ticker": "035420", "name": "NAVER", "score": 8.5, "indicators": {"change_rate": 4.1}}
            ]
        },
        "bear": {
            "name": "약세장",
            "as_of": "20250102", 
            "matched_count": 2,
            "rsi_threshold": 45,
            "items": [
                {"ticker": "084110", "name": "휴온스글로벌", "score": 6.5, "indicators": {"change_rate": -2.1}},
                {"ticker": "096530", "name": "씨젠", "score": 6.0, "indicators": {"change_rate": -1.8}}
            ]
        },
        "neutral": {
            "name": "중립장",
            "as_of": "20250103",
            "matched_count": 5,
            "rsi_threshold": 55,
            "items": [
                {"ticker": "005930", "name": "삼성전자", "score": 7.2, "indicators": {"change_rate": 0.8}},
                {"ticker": "051910", "name": "LG화학", "score": 6.8, "indicators": {"change_rate": -0.5}},
                {"ticker": "035720", "name": "카카오", "score": 6.5, "indicators": {"change_rate": 1.2}}
            ]
        },
        "noresult": {
            "name": "추천종목 없음",
            "as_of": "20250104",
            "matched_count": 0,
            "rsi_threshold": 40,
            "items": [{"ticker": "NORESULT", "name": "추천 종목 없음", "score": 0, "indicators": {"change_rate": 0}}]
        }
    }
    return {"scenarios": scenarios}

@app.get('/test-scan/{scenario}')
def get_test_scan_result(scenario: str):
    """테스트용 스캔 결과 반환"""
    scenarios = get_test_market_scenarios()["scenarios"]
    
    if scenario not in scenarios:
        raise HTTPException(status_code=404, detail="시나리오를 찾을 수 없습니다")
    
    scenario_data = scenarios[scenario]
    
    # 시장 가이드 생성
    market_guide = get_market_guide(scenario_data)
    
    # items에 market_guide 추가
    items_with_guide = scenario_data["items"].copy()
    if items_with_guide:
        items_with_guide[0]["market_guide"] = market_guide
    
    # ScanResponse 형태로 반환
    return {
        "as_of": scenario_data["as_of"],
        "universe_count": 200,
        "matched_count": scenario_data["matched_count"],
        "rsi_mode": "test_mode",
        "rsi_period": 14,
        "rsi_threshold": scenario_data["rsi_threshold"],
        "items": items_with_guide,
        "market_guide": market_guide,
        "test_scenario": scenario_data["name"]
    }

@app.get("/admin/market-validation")
async def get_market_validation(date: str = None):
    """장세 데이터 검증 결과 조회 (관리자용)"""
    try:
        from datetime import datetime, timedelta
        
        # 날짜 파라미터 처리
        if date:
            target_date = datetime.strptime(date, '%Y%m%d').date()
        else:
            target_date = datetime.now().date()
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT 
                    analysis_date,
                    analysis_time,
                    kospi_return,
                    kospi_close,
                    kospi_prev_close,
                    samsung_return,
                    samsung_close,
                    samsung_prev_close,
                    data_available,
                    data_complete,
                    error_message,
                    created_at
                FROM market_analysis_validation
                WHERE analysis_date = %s
                ORDER BY analysis_time
            """, (target_date,))
            
            rows = cur.fetchall()
        
        if not rows:
            return {
                "ok": False,
                "error": f"해당 날짜({target_date})의 검증 데이터가 없습니다."
            }
        
        # 결과 변환
        validations = []
        for row in rows:
            # row가 dict인지 tuple인지 확인
            if isinstance(row, dict):
                data = row
            else:
                # tuple인 경우 컬럼명으로 매핑
                data = {
                    "analysis_date": row[0],
                    "analysis_time": row[1],
                    "kospi_return": row[2],
                    "kospi_close": row[3],
                    "kospi_prev_close": row[4],
                    "samsung_return": row[5],
                    "samsung_close": row[6],
                    "samsung_prev_close": row[7],
                    "data_available": row[8],
                    "data_complete": row[9],
                    "error_message": row[10],
                    "created_at": row[11]
                }
            
            validations.append({
                "time": str(data["analysis_time"])[:5],  # HH:MM
                "kospi_return": round(data["kospi_return"] * 100, 2) if data["kospi_return"] else None,
                "kospi_close": data["kospi_close"],
                "samsung_return": round(data["samsung_return"] * 100, 2) if data["samsung_return"] else None,
                "samsung_close": data["samsung_close"],
                "data_available": data["data_available"],
                "data_complete": data["data_complete"],
                "error_message": data["error_message"]
            })
        
        # 데이터 확정 시점 분석
        first_complete = None
        for v in validations:
            if v["data_complete"]:
                first_complete = v["time"]
                break
        
        return {
            "ok": True,
            "data": {
                "date": str(target_date),
                "validations": validations,
                "first_complete_time": first_complete,
                "total_checks": len(validations)
            }
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"검증 데이터 조회 중 오류: {str(e)}"
        }

# 라우터 포함
app.include_router(recurrence_router)


# ==================== 미국 레짐 분석 API ====================

@app.get("/api/us-regime/analyze")
async def analyze_us_regime(date: str = None):
    """미국 시장 레짐 분석
    
    Args:
        date: 분석 날짜 (YYYYMMDD 형식, None이면 오늘)
    
    Returns:
        {
            "date": "20251205",
            "regime": "bull",
            "regime_kr": "강세장",
            "score": 75.5,
            "components": {...},
            "market_data": {...},
            "filter_values": {...},
            "advice": "..."
        }
    """
    try:
        from services.us_regime_analyzer import us_regime_analyzer
        
        # 날짜 처리
        analysis_date = normalize_date(date) if date else get_kst_now().strftime('%Y%m%d')
        
        # 레짐 분석 실행
        result = us_regime_analyzer.analyze_us_market(analysis_date)
        
        # 레짐 한글 변환
        regime_kr_map = {
            "bull": "강세장",
            "neutral_bull": "약한 강세장",
            "neutral": "중립",
            "neutral_bear": "약한 약세장",
            "bear": "약세장"
        }
        
        return {
            "ok": True,
            "data": {
                "date": analysis_date,
                "regime": result.get("final_regime"),
                "regime_kr": regime_kr_map.get(result.get("final_regime"), "중립"),
                "score": round(result.get("final_score", 0), 2),
                "components": {
                    "stocks": {
                        "score": round(result.get("us_equity_score", 0), 2),
                        "weight": 0.5,
                        "regime": result.get("us_equity_regime")
                    },
                    "futures": {
                        "score": round(result.get("us_futures_score", 0), 2),
                        "weight": 0.3,
                        "regime": result.get("us_futures_regime")
                    },
                    "volatility": {
                        "score": round(result.get("us_volatility_score", 0), 2),
                        "weight": 0.2
                    }
                },
                "market_data": {
                    "SPY": {
                        "change_pct": round(result.get("spy_change", 0), 2)
                    },
                    "QQQ": {
                        "change_pct": round(result.get("qqq_change", 0), 2)
                    },
                    "VIX": {
                        "level": round(result.get("vix_level", 0), 2)
                    }
                },
                "filter_values": {
                    "rsi_threshold": result.get("rsi_threshold", 58),
                    "min_signals": result.get("min_signals", 3),
                    "vol_ma5_mult": result.get("vol_ma5_mult", 2.5),
                    "gap_max": result.get("gap_max", 0.015),
                    "ext_from_tema20_max": result.get("ext_from_tema20_max", 0.015)
                },
                "advice": result.get("advice", "시장 상황을 주의 깊게 관찰하세요.")
            }
        }
        
    except Exception as e:
        import traceback
        print(f"미국 레짐 분석 오류: {e}")
        traceback.print_exc()
        return {
            "ok": False,
            "error": f"미국 레짐 분석 중 오류가 발생했습니다: {str(e)}"
        }
