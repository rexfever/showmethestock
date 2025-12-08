import schedule
import time
import requests
import logging
from datetime import datetime, timedelta
import holidays
import os
import pytz
from environment import get_environment_info
from db_manager import db_manager

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_notification_recipients():
    """알림 수신자 목록을 데이터베이스에서 조회"""
    try:
        # 데이터베이스에서 알림 수신 동의한 사용자 조회
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute("""
                SELECT phone
                FROM users
                WHERE notification_enabled = TRUE
                  AND phone IS NOT NULL
                  AND phone != ''
            """)
            rows = cursor.fetchall()
        
        recipients = [row["phone"] for row in rows if row.get("phone")]
        
        if recipients:
            logger.info(f"데이터베이스에서 {len(recipients)}명의 수신자 조회")
            return recipients
        
        # 데이터베이스에 수신자가 없으면 환경변수에서 읽기 (fallback)
        env_recipients = os.getenv('NOTIFICATION_RECIPIENTS', '').split(',')
        fallback_recipients = [r.strip() for r in env_recipients if r.strip()]
        
        if fallback_recipients:
            logger.info(f"환경변수에서 {len(fallback_recipients)}명의 수신자 조회")
        
        return fallback_recipients
        
    except Exception as e:
        logger.error(f"수신자 목록 조회 실패: {str(e)}")
        # 에러 시 환경변수 fallback
        env_recipients = os.getenv('NOTIFICATION_RECIPIENTS', '').split(',')
        return [r.strip() for r in env_recipients if r.strip()]

def is_trading_day():
    """거래일인지 확인 (주말과 공휴일 제외) - KST 기준"""
    # KST 시간대 사용
    kst = pytz.timezone('Asia/Seoul')
    today = datetime.now(kst).date()
    
    # 주말 체크
    if today.weekday() >= 5:  # 토요일(5), 일요일(6)
        return False
    
    # 한국 공휴일 체크
    kr_holidays = holidays.SouthKorea()
    if today in kr_holidays:
        return False
    
    return True

def is_us_trading_day():
    """미국 거래일인지 확인 (주말과 미국 공휴일 제외) - KST 기준"""
    # KST 시간대 사용
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    
    # 미국 시간대로 변환 (EST/EDT)
    # 서머타임 자동 처리
    us_eastern = pytz.timezone('US/Eastern')
    now_us = now_kst.astimezone(us_eastern)
    today_us = now_us.date()
    
    # 주말 체크 (토요일, 일요일)
    if today_us.weekday() >= 5:
        return False
    
    # 미국 공휴일 체크
    try:
        us_holidays = holidays.UnitedStates()
        if today_us in us_holidays:
            return False
    except Exception:
        # holidays 모듈에서 미국 공휴일을 지원하지 않으면 주말만 체크
        pass
    
    return True

def run_market_analysis():
    """장세 분석 실행 (15:35)"""
    if not is_trading_day():
        logger.info(f"오늘은 거래일이 아닙니다. 장세 분석을 건너뜁니다.")
        return
    
    try:
        logger.info("📊 자동 장세 분석을 시작합니다...")
        
        from market_analyzer import market_analyzer
        from datetime import datetime
        from db_manager import db_manager
        import json
        
        # 오늘 날짜 (YYYYMMDD 형식)
        today = datetime.now().strftime('%Y%m%d')
        
        # 레짐 버전 가져오기
        try:
            from config import config
            regime_version = getattr(config, 'regime_version', 'v1')
        except Exception:
            regime_version = 'v1'
        
        # 장세 분석 실행 (레짐 버전 자동 선택)
        market_condition = market_analyzer.analyze_market_condition(today, regime_version=regime_version)
        
        # 레짐 버전에 따른 로그 출력
        if hasattr(market_condition, 'version'):
            if market_condition.version == 'regime_v4':
                logger.info(f"📊 Global Regime v4 분석 완료: {market_condition.final_regime} (trend: {market_condition.global_trend_score:.2f}, risk: {market_condition.global_risk_score:.2f})")
            elif market_condition.version == 'regime_v3':
                logger.info(f"📊 Global Regime v3 분석 완료: {market_condition.final_regime} (점수: {market_condition.final_score:.2f})")
            else:
                logger.info(f"📊 장세 분석 v1 완료: {market_condition.market_sentiment} (유효 수익률: {market_condition.kospi_return*100:.2f}%, RSI 임계값: {market_condition.rsi_threshold})")
        else:
            logger.info(f"📊 장세 분석 완료: {market_condition.market_sentiment} (유효 수익률: {market_condition.kospi_return*100:.2f}%, RSI 임계값: {market_condition.rsi_threshold})")
        
        # DB에 저장
        with db_manager.get_cursor(commit=True) as cur:
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
                today,
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
        
        logger.info(f"✅ 장세 분석 결과가 DB에 저장되었습니다: {today}")
        
    except Exception as e:
        logger.error(f"자동 장세 분석 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def run_scan():
    """한국 주식 스캔 실행 (15:42)"""
    if not is_trading_day():
        logger.info(f"오늘은 거래일이 아닙니다. 스캔을 건너뜁니다.")
        return
    
    try:
        logger.info("📈 한국 주식 자동 스캔을 시작합니다...")
        
        # 백엔드 API 호출 (환경별 URL 사용)
        env_info = get_environment_info()
        if env_info['is_local']:
            backend_url = "http://localhost:8010"
        else:
            backend_url = "http://localhost:8010"  # 서버에서는 내부 통신
        
        response = requests.get(f"{backend_url}/scan?save_snapshot=true", timeout=300)
        
        if response.status_code == 200:
            data = response.json()
            matched_count = data.get('matched_count', 0)
            logger.info(f"✅ 한국 주식 자동 스캔 완료: {matched_count}개 종목 매칭")
            
            # 스캔 결과는 DB에 저장됨 (JSON 파일 저장 제거)
            logger.info("스캔 결과가 DB에 저장되었습니다.")
            
            # 자동 알림 발송
            send_auto_notification(matched_count)
            
        else:
            logger.error(f"한국 주식 스캔 실패: HTTP {response.status_code}")
            
    except Exception as e:
        logger.error(f"한국 주식 자동 스캔 중 오류 발생: {str(e)}")

def run_us_scan():
    """미국 주식 스캔 실행 (오전 7:00 KST)"""
    # 미국 시장이 마감된 후 데이터 확정 시점에 실행
    # 서머타임: 미국 정규장 마감 5:00 KST → 스캔 7:00 KST
    # 비서머타임: 미국 정규장 마감 6:00 KST → 스캔 7:00 KST
    if not is_us_trading_day():
        logger.info(f"오늘은 미국 거래일이 아닙니다. 미국 주식 스캔을 건너뜁니다.")
        return
    
    try:
        logger.info("🇺🇸 미국 주식 자동 스캔을 시작합니다...")
        
        # 백엔드 API 호출 (환경별 URL 사용)
        env_info = get_environment_info()
        if env_info['is_local']:
            backend_url = "http://localhost:8010"
        else:
            backend_url = "http://localhost:8010"  # 서버에서는 내부 통신
        
        # S&P 500 + NASDAQ 100 통합 스캔
        response = requests.get(
            f"{backend_url}/scan/us-stocks?universe_type=combined&limit=500&save_snapshot=true",
            timeout=600  # 미국 주식은 종목 수가 많아 타임아웃을 더 길게
        )
        
        if response.status_code == 200:
            data = response.json()
            matched_count = data.get('matched_count', 0)
            logger.info(f"✅ 미국 주식 자동 스캔 완료: {matched_count}개 종목 매칭")
            
            # 스캔 결과는 DB에 저장됨
            logger.info("미국 주식 스캔 결과가 DB에 저장되었습니다.")
            
        else:
            logger.error(f"미국 주식 스캔 실패: HTTP {response.status_code}")
            
    except Exception as e:
        logger.error(f"미국 주식 자동 스캔 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def send_auto_notification(matched_count):
    """자동 알림 발송 (솔라피 알림톡)"""
    try:
        # 알림 수신자 목록 (파일에서 실시간 읽기)
        notification_recipients = get_notification_recipients()
        
        if not notification_recipients:
            logger.info("알림 수신자가 설정되지 않았습니다.")
            return
        
        # 솔라피 알림톡 템플릿 변수 생성
        from kakao import format_scan_alert_message, send_alert
        
        scan_date = datetime.now().strftime("%Y년 %m월 %d일")
        template_data = format_scan_alert_message(
            matched_count=matched_count,
            scan_date=scan_date,
            user_name="고객님"
        )
        
        # 각 수신자에게 알림 발송
        for recipient in notification_recipients:
            try:
                # 솔라피 알림톡 발송
                result = send_alert(to=recipient, template_data=template_data)
                
                if result.get('ok'):
                    logger.info(f"솔라피 알림톡 발송 성공: {recipient}")
                else:
                    logger.error(f"솔라피 알림톡 발송 실패: {recipient}, {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"알림 발송 중 오류 ({recipient}): {str(e)}")
                
    except Exception as e:
        logger.error(f"자동 알림 발송 중 오류 발생: {str(e)}")

def preload_regime_cache_kr():
    """한국 주식 레짐 분석용 캐시 사전 생성 (15:35)"""
    if not is_trading_day():
        logger.info("오늘은 거래일이 아닙니다. 레짐 분석용 캐시 생성을 건너뜁니다.")
        return
    
    try:
        logger.info("📊 레짐 분석용 캐시 사전 생성 시작 (한국)")
        
        # 1. KOSPI 데이터 (FinanceDataReader 자동 생성)
        try:
            import FinanceDataReader as fdr
            today = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            kospi_df = fdr.DataReader('KS11', start_date, today)
            if not kospi_df.empty:
                logger.info(f"✅ KOSPI 데이터 생성 완료: {len(kospi_df)}개 행")
            else:
                logger.warning("KOSPI 데이터가 비어있습니다.")
        except ImportError:
            logger.warning("FinanceDataReader가 설치되지 않음")
        except Exception as e:
            logger.warning(f"KOSPI 데이터 생성 실패: {e}")
        
        # 2. KOSDAQ 데이터 (CSV 캐시 확인/생성)
        kosdaq_csv = os.path.join(os.path.dirname(__file__), '..', 'data_cache', 'ohlcv', '229200.csv')
        if os.path.exists(kosdaq_csv):
            logger.info("✅ KOSDAQ 캐시 확인됨")
        else:
            logger.warning("KOSDAQ 캐시 없음 - 수동 생성 필요")
        
        # 3. 미국 선물 데이터 (레짐 분석에 필요)
        try:
            from services.us_futures_data_v8 import us_futures_data_v8
            symbols = ['SPY', 'QQQ', '^VIX']
            for symbol in symbols:
                try:
                    df = us_futures_data_v8.fetch_data(symbol, period='1y')
                    if not df.empty:
                        logger.info(f"✅ {symbol} 캐시 생성 완료: {len(df)}개 행")
                    else:
                        logger.warning(f"{symbol} 캐시 생성 실패 (빈 데이터)")
                except Exception as e:
                    logger.error(f"{symbol} 캐시 생성 오류: {e}")
        except Exception as e:
            logger.error(f"미국 선물 데이터 캐시 생성 실패: {e}")
        
        logger.info("✅ 레짐 분석용 캐시 사전 생성 완료 (한국)")
        
    except Exception as e:
        logger.error(f"레짐 분석용 캐시 사전 생성 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def preload_regime_cache_us():
    """미국 주식 레짐 분석용 캐시 사전 생성 (06:50)"""
    if not is_us_trading_day():
        logger.info("오늘은 미국 거래일이 아닙니다. 레짐 분석용 캐시 생성을 건너뜁니다.")
        return
    
    try:
        logger.info("📊 레짐 분석용 캐시 사전 생성 시작 (미국)")
        
        from services.us_futures_data_v8 import us_futures_data_v8
        symbols = ['SPY', 'QQQ', '^VIX', 'ES=F', 'NQ=F', 'DX-Y.NYB']
        
        for symbol in symbols:
            try:
                df = us_futures_data_v8.fetch_data(symbol, period='1y')
                if not df.empty:
                    logger.info(f"✅ {symbol} 캐시 생성 완료: {len(df)}개 행")
                else:
                    logger.warning(f"{symbol} 캐시 생성 실패 (빈 데이터)")
            except Exception as e:
                logger.error(f"{symbol} 캐시 생성 오류: {e}")
        
        logger.info("✅ 레짐 분석용 캐시 사전 생성 완료 (미국)")
        
    except Exception as e:
        logger.error(f"레짐 분석용 캐시 사전 생성 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def preload_scan_cache_kr(limit: int = 200):
    """한국 주식 스캔용 캐시 사전 생성 (과거 데이터만, 선택적)"""
    if not is_trading_day():
        logger.info("오늘은 거래일이 아닙니다. 스캔용 캐시 생성을 건너뜁니다.")
        return
    
    try:
        logger.info(f"📈 스캔용 캐시 사전 생성 시작 (한국, 상위 {limit}개 종목)")
        
        from kiwoom_api import api
        
        # 유니버스 로드
        kospi_codes = api.get_top_codes("KOSPI", limit // 2)
        kosdaq_codes = api.get_top_codes("KOSDAQ", limit // 2)
        universe = kospi_codes + kosdaq_codes
        
        logger.info(f"유니버스 로드 완료: {len(universe)}개 종목")
        
        # 과거 30일 데이터만 사전 생성
        today = datetime.now()
        success_count = 0
        for code in universe:
            try:
                for days_ago in range(1, 31):  # 최근 30일
                    past_date = (today - timedelta(days=days_ago)).strftime('%Y%m%d')
                    # base_dt를 지정하여 과거 날짜 데이터만 생성
                    api.get_ohlcv(code, 220, past_date)
                success_count += 1
            except Exception as e:
                logger.warning(f"{code} 캐시 생성 실패: {e}")
        
        logger.info(f"✅ 스캔용 캐시 사전 생성 완료: {success_count}/{len(universe)}개 종목")
        
    except Exception as e:
        logger.error(f"스캔용 캐시 사전 생성 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def preload_scan_cache_us(limit: int = 200):
    """미국 주식 스캔용 캐시 사전 생성 (과거 데이터만, 선택적)"""
    if not is_us_trading_day():
        logger.info("오늘은 미국 거래일이 아닙니다. 스캔용 캐시 생성을 건너뜁니다.")
        return
    
    try:
        logger.info(f"📈 스캔용 캐시 사전 생성 시작 (미국, 상위 {limit}개 종목)")
        
        from services.us_stocks_universe import USStocksUniverse
        from services.us_stocks_data import us_stocks_data
        
        us_universe = USStocksUniverse()
        
        # 유니버스 로드
        symbols = us_universe.get_combined_universe(limit=limit)
        symbol_list = [item['symbol'] for item in symbols]
        
        logger.info(f"유니버스 로드 완료: {len(symbol_list)}개 종목")
        
        # 과거 30일 데이터만 사전 생성
        today = datetime.now()
        success_count = 0
        for symbol in symbol_list:
            try:
                for days_ago in range(1, 31):  # 최근 30일
                    past_date = (today - timedelta(days=days_ago)).strftime('%Y%m%d')
                    # base_dt를 지정하여 과거 날짜 데이터만 생성
                    us_stocks_data.get_ohlcv(symbol, 220, past_date)
                success_count += 1
            except Exception as e:
                logger.warning(f"{symbol} 캐시 생성 실패: {e}")
        
        logger.info(f"✅ 스캔용 캐시 사전 생성 완료: {success_count}/{len(symbol_list)}개 종목")
        
    except Exception as e:
        logger.error(f"스캔용 캐시 사전 생성 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def run_validation():
    """데이터 확정 시점 검증 (15:31~15:40)"""
    if not is_trading_day():
        return
    
    try:
        logger.info("🔍 장세 데이터 검증을 시작합니다...")
        import subprocess
        result = subprocess.run(
            ["python", "validate_market_data_timing.py"],
            cwd="/home/ubuntu/showmethestock/backend",
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("✅ 검증 완료")
        else:
            logger.error(f"❌ 검증 실패: {result.stderr}")
    except Exception as e:
        logger.error(f"검증 중 오류 발생: {str(e)}")

def setup_scheduler():
    """스케줄러 설정 - KST 기준"""
    # === 레짐 분석용 캐시 사전 생성 (필수) ===
    
    # 한국 주식: 장 마감 직후 (15:35)
    schedule.every().day.at("15:35").do(preload_regime_cache_kr)
    # - KOSPI: FinanceDataReader (자동)
    # - KOSDAQ: CSV 캐시 확인/생성
    # - SPY/QQQ/VIX: us_futures_data_v8.fetch_data()
    
    # 미국 주식: 미국 장 마감 후 (06:50)
    schedule.every().day.at("06:50").do(preload_regime_cache_us)
    # - SPY/QQQ/VIX/ES=F/NQ=F/DX-Y.NYB: us_futures_data_v8.fetch_data()
    
    # === 스캔용 캐시 사전 생성 (선택적) ===
    
    # 한국 주식: 스캔 30분 전 (15:12)
    # schedule.every().day.at("15:12").do(preload_scan_cache_kr)
    # - 상위 200개 종목의 과거 30일 데이터만 생성
    # - 당일 데이터는 생성하지 않음
    # 주석 처리: 선택적 기능이므로 필요 시 활성화
    
    # 미국 주식: 스캔 30분 전 (06:30)
    # schedule.every().day.at("06:30").do(preload_scan_cache_us)
    # - 상위 200개 종목의 과거 30일 데이터만 생성
    # - 당일 데이터는 생성하지 않음
    # 주석 처리: 선택적 기능이므로 필요 시 활성화
    
    # === 한국 주식 스캔 ===
    # 데이터 확정 시점 검증 (15:31~15:40, 매분)
    schedule.every().day.at("15:31").do(run_validation)
    schedule.every().day.at("15:32").do(run_validation)
    schedule.every().day.at("15:33").do(run_validation)
    schedule.every().day.at("15:34").do(run_validation)
    schedule.every().day.at("15:35").do(run_validation)
    schedule.every().day.at("15:36").do(run_validation)
    schedule.every().day.at("15:37").do(run_validation)
    schedule.every().day.at("15:38").do(run_validation)
    schedule.every().day.at("15:39").do(run_validation)
    schedule.every().day.at("15:40").do(run_validation)
    
    # 매일 오후 3시 40분에 장세 분석 실행 (데이터 확정 후) - KST 기준
    schedule.every().day.at("15:40").do(run_market_analysis)
    # - 레짐 분석용 캐시 사용 ✅
    
    # 매일 오후 3시 42분에 한국 주식 스캔 실행 (장세 분석 후) - KST 기준
    schedule.every().day.at("15:42").do(run_scan)
    # - 과거 데이터: 사전 생성된 캐시 사용 ✅ (선택적)
    # - 당일 데이터: 스캔 시점에 생성 (최신 데이터 보장)
    
    # === 미국 주식 스캔 ===
    # 매일 오전 7시에 미국 주식 스캔 실행 (미국 시장 마감 후 데이터 확정 시점) - KST 기준
    # 서머타임: 미국 정규장 마감 5:00 KST → 스캔 7:00 KST
    # 비서머타임: 미국 정규장 마감 6:00 KST → 스캔 7:00 KST
    schedule.every().day.at("07:00").do(run_us_scan)
    # - 과거 데이터: 사전 생성된 캐시 사용 ✅ (선택적)
    # - 당일 데이터: 스캔 시점에 생성 (최신 데이터 보장)
    
    logger.info("자동 스케줄러가 설정되었습니다.")
    logger.info("=== 레짐 분석용 캐시 사전 생성 (필수) ===")
    logger.info("- 매일 오후 3:35 KST: 한국 주식 레짐 분석용 캐시 생성")
    logger.info("- 매일 오전 6:50 KST: 미국 주식 레짐 분석용 캐시 생성")
    logger.info("=== 스캔용 캐시 사전 생성 (선택적) ===")
    logger.info("- 주석 처리됨: 필요 시 15:12 (한국), 06:30 (미국) 활성화")
    logger.info("=== 한국 주식 ===")
    logger.info("- 매일 오후 3:31~3:40 KST: 데이터 검증 (매분)")
    logger.info("- 매일 오후 3:40 KST: 장세 분석 실행 (레짐 분석용 캐시 사용)")
    logger.info("- 매일 오후 3:42 KST: 한국 주식 스캔 실행")
    logger.info("=== 미국 주식 ===")
    logger.info("- 매일 오전 7:00 KST: 미국 주식 스캔 실행")
    logger.info("- 주말과 공휴일은 자동으로 제외됩니다.")

def run_scheduler():
    """스케줄러 실행"""
    setup_scheduler()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == "__main__":
    run_scheduler()
