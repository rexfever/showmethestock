import schedule
import time
import requests
import logging
from datetime import datetime, timedelta
import holidays
import os
import sqlite3
import pytz
from environment import get_environment_info

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_notification_recipients():
    """알림 수신자 목록을 데이터베이스에서 조회"""
    try:
        # 데이터베이스에서 알림 수신 동의한 사용자 조회
        # 현재 스크립트 위치 기준으로 절대경로 계산
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, 'snapshots.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT phone FROM users 
            WHERE notification_enabled = 1 AND phone IS NOT NULL AND phone != ''
        """)
        
        recipients = [row[0] for row in cursor.fetchall()]
        conn.close()
        
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

def run_scan():
    """스캔 실행"""
    if not is_trading_day():
        logger.info(f"오늘은 거래일이 아닙니다. 스캔을 건너뜁니다.")
        return
    
    try:
        logger.info("자동 스캔을 시작합니다...")
        
        # 백엔드 API 호출 (환경별 URL 사용)
        env_info = get_environment_info()
        if env_info['is_local']:
            backend_url = "http://localhost:8010"
        else:
            backend_url = "http://localhost:8010"  # 서버에서는 내부 통신
        
        response = requests.get(f"{backend_url}/scan", timeout=300)
        
        if response.status_code == 200:
            data = response.json()
            matched_count = data.get('matched_count', 0)
            logger.info(f"자동 스캔 완료: {matched_count}개 종목 매칭")
            
            # 스캔 결과를 파일로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 현재 스크립트 위치 기준으로 절대경로 계산
            current_dir = os.path.dirname(os.path.abspath(__file__))
            snapshots_dir = os.path.join(current_dir, 'snapshots')
            filename = os.path.join(snapshots_dir, f"auto-scan-{timestamp}.json")
            
            with open(filename, 'w', encoding='utf-8') as f:
                import json
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"스캔 결과가 {filename}에 저장되었습니다.")
            
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

def setup_scheduler():
    """스케줄러 설정 - KST 기준"""
    # 매일 오후 3시 30분에 스캔 실행 (장 마감 후) - KST 기준
    schedule.every().day.at("15:30").do(run_scan)
    
    logger.info("자동 스캔 스케줄러가 설정되었습니다.")
    logger.info("- 매일 오후 3:30 KST (장 마감 후)")
    logger.info("- 주말과 공휴일은 자동으로 제외됩니다.")

def run_scheduler():
    """스케줄러 실행"""
    setup_scheduler()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == "__main__":
    run_scheduler()
