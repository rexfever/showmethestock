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
        
        # 장세 분석 실행
        market_condition = market_analyzer.analyze_market_condition(today)
        
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
    """스캔 실행 (15:40)"""
    if not is_trading_day():
        logger.info(f"오늘은 거래일이 아닙니다. 스캔을 건너뜁니다.")
        return
    
    try:
        logger.info("📈 자동 스캔을 시작합니다...")
        
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
            logger.info(f"✅ 자동 스캔 완료: {matched_count}개 종목 매칭")
            
            # 스캔 결과는 DB에 저장됨 (JSON 파일 저장 제거)
            logger.info("스캔 결과가 DB에 저장되었습니다.")
            
            # 자동 알림 발송
            send_auto_notification(matched_count)
            
        else:
            logger.error(f"스캔 실패: HTTP {response.status_code}")
            
    except Exception as e:
        logger.error(f"자동 스캔 중 오류 발생: {str(e)}")

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
    
    # 매일 오후 3시 42분에 스캔 실행 (장세 분석 후) - KST 기준
    schedule.every().day.at("15:42").do(run_scan)
    
    logger.info("자동 스케줄러가 설정되었습니다.")
    logger.info("- 매일 오후 3:31~3:40 KST: 데이터 검증 (매분)")
    logger.info("- 매일 오후 3:40 KST: 장세 분석 실행")
    logger.info("- 매일 오후 3:42 KST: 스캔 실행")
    logger.info("- 주말과 공휴일은 자동으로 제외됩니다.")

def run_scheduler():
    """스케줄러 실행"""
    setup_scheduler()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == "__main__":
    run_scheduler()
