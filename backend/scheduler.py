import schedule
import time
import requests
import logging
from datetime import datetime, timedelta
import holidays

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_trading_day():
    """거래일인지 확인 (주말과 공휴일 제외)"""
    today = datetime.now().date()
    
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
        
        # 백엔드 API 호출
        response = requests.post("http://localhost:8010/scan", timeout=300)
        
        if response.status_code == 200:
            data = response.json()
            matched_count = data.get('matched_count', 0)
            logger.info(f"자동 스캔 완료: {matched_count}개 종목 매칭")
            
            # 스캔 결과를 파일로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backend/snapshots/auto-scan-{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                import json
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"스캔 결과가 {filename}에 저장되었습니다.")
            
        else:
            logger.error(f"스캔 실패: HTTP {response.status_code}")
            
    except Exception as e:
        logger.error(f"자동 스캔 중 오류 발생: {str(e)}")

def setup_scheduler():
    """스케줄러 설정"""
    # 매일 오전 9시에 스캔 실행 (장 시작 전)
    schedule.every().day.at("09:00").do(run_scan)
    
    # 매일 오후 3시에 스캔 실행 (장 마감 후)
    schedule.every().day.at("15:30").do(run_scan)
    
    logger.info("자동 스캔 스케줄러가 설정되었습니다.")
    logger.info("- 매일 오전 9:00 (장 시작 전)")
    logger.info("- 매일 오후 3:30 (장 마감 후)")
    logger.info("- 주말과 공휴일은 자동으로 제외됩니다.")

def run_scheduler():
    """스케줄러 실행"""
    setup_scheduler()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == "__main__":
    run_scheduler()
