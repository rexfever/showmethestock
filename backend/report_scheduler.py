"""
보고서 생성 스케줄러
"""
import schedule
import time
from datetime import datetime, timedelta
import calendar
from services.report_generator import report_generator


def is_trading_day(date):
    """거래일 여부 확인 (주말 제외)"""
    return date.weekday() < 5  # 월요일(0) ~ 금요일(4)


def get_last_trading_day_of_month(year, month):
    """해당 월의 마지막 거래일 반환"""
    last_day = calendar.monthrange(year, month)[1]
    
    for day in range(last_day, 0, -1):
        date = datetime(year, month, day)
        if is_trading_day(date):
            return date
    
    return None


def get_last_trading_day_of_quarter(year, quarter):
    """해당 분기의 마지막 거래일 반환"""
    if quarter == 1:
        return get_last_trading_day_of_month(year, 3)
    elif quarter == 2:
        return get_last_trading_day_of_month(year, 6)
    elif quarter == 3:
        return get_last_trading_day_of_month(year, 9)
    elif quarter == 4:
        return get_last_trading_day_of_month(year, 12)
    
    return None


def get_last_trading_day_of_year(year):
    """해당 연도의 마지막 거래일 반환"""
    return get_last_trading_day_of_month(year, 12)


def generate_weekly_reports():
    """주간 보고서 생성 (매주 금요일 오후 6시)"""
    try:
        today = datetime.now()
        year = today.year
        month = today.month
        
        # 이번 주가 몇 주차인지 계산
        first_day = datetime(year, month, 1)
        week_of_month = ((today - first_day).days // 7) + 1
        
        print(f"주간 보고서 생성 시작: {year}년 {month}월 {week_of_month}주차")
        
        success = report_generator.generate_weekly_report(year, month, week_of_month)
        
        if success:
            print(f"주간 보고서 생성 완료: {year}년 {month}월 {week_of_month}주차")
        else:
            print(f"주간 보고서 생성 실패: {year}년 {month}월 {week_of_month}주차")
            
    except Exception as e:
        print(f"주간 보고서 생성 중 오류: {e}")


def generate_monthly_reports():
    """월간 보고서 생성 (매월 마지막 거래일 오후 6시)"""
    try:
        today = datetime.now()
        year = today.year
        month = today.month
        
        print(f"월간 보고서 생성 시작: {year}년 {month}월")
        
        success = report_generator.generate_monthly_report(year, month)
        
        if success:
            print(f"월간 보고서 생성 완료: {year}년 {month}월")
        else:
            print(f"월간 보고서 생성 실패: {year}년 {month}월")
            
    except Exception as e:
        print(f"월간 보고서 생성 중 오류: {e}")


def generate_quarterly_reports():
    """분기 보고서 생성 (분기 마지막 거래일 오후 6시)"""
    try:
        today = datetime.now()
        year = today.year
        month = today.month
        
        # 분기 계산
        quarter = (month - 1) // 3 + 1
        
        print(f"분기 보고서 생성 시작: {year}년 {quarter}분기")
        
        success = report_generator.generate_quarterly_report(year, quarter)
        
        if success:
            print(f"분기 보고서 생성 완료: {year}년 {quarter}분기")
        else:
            print(f"분기 보고서 생성 실패: {year}년 {quarter}분기")
            
    except Exception as e:
        print(f"분기 보고서 생성 중 오류: {e}")


def generate_yearly_reports():
    """연간 보고서 생성 (12월 마지막 거래일 오후 6시)"""
    try:
        today = datetime.now()
        year = today.year
        
        print(f"연간 보고서 생성 시작: {year}년")
        
        success = report_generator.generate_yearly_report(year)
        
        if success:
            print(f"연간 보고서 생성 완료: {year}년")
        else:
            print(f"연간 보고서 생성 실패: {year}년")
            
    except Exception as e:
        print(f"연간 보고서 생성 중 오류: {e}")


def setup_scheduler():
    """스케줄러 설정"""
    print("보고서 생성 스케줄러 설정 중...")
    
    # 주간 보고서: 매주 금요일 오후 6시
    schedule.every().friday.at("18:00").do(generate_weekly_reports)
    
    # 월간 보고서: 매월 마지막 거래일 오후 6시
    # 실제로는 매일 확인해서 마지막 거래일인지 체크
    schedule.every().day.at("18:00").do(check_and_generate_monthly_report)
    
    # 분기 보고서: 분기 마지막 거래일 오후 6시
    schedule.every().day.at("18:00").do(check_and_generate_quarterly_report)
    
    # 연간 보고서: 12월 마지막 거래일 오후 6시
    schedule.every().day.at("18:00").do(check_and_generate_yearly_report)
    
    print("보고서 생성 스케줄러 설정 완료")


def check_and_generate_monthly_report():
    """월간 보고서 생성 필요 여부 확인"""
    try:
        today = datetime.now()
        year = today.year
        month = today.month
        
        # 오늘이 해당 월의 마지막 거래일인지 확인
        last_trading_day = get_last_trading_day_of_month(year, month)
        
        if last_trading_day and today.date() == last_trading_day.date():
            generate_monthly_reports()
            
    except Exception as e:
        print(f"월간 보고서 생성 확인 중 오류: {e}")


def check_and_generate_quarterly_report():
    """분기 보고서 생성 필요 여부 확인"""
    try:
        today = datetime.now()
        year = today.year
        month = today.month
        
        # 분기 계산
        quarter = (month - 1) // 3 + 1
        
        # 오늘이 해당 분기의 마지막 거래일인지 확인
        last_trading_day = get_last_trading_day_of_quarter(year, quarter)
        
        if last_trading_day and today.date() == last_trading_day.date():
            generate_quarterly_reports()
            
    except Exception as e:
        print(f"분기 보고서 생성 확인 중 오류: {e}")


def check_and_generate_yearly_report():
    """연간 보고서 생성 필요 여부 확인"""
    try:
        today = datetime.now()
        year = today.year
        
        # 오늘이 해당 연도의 마지막 거래일인지 확인
        last_trading_day = get_last_trading_day_of_year(year)
        
        if last_trading_day and today.date() == last_trading_day.date():
            generate_yearly_reports()
            
    except Exception as e:
        print(f"연간 보고서 생성 확인 중 오류: {e}")


def run_scheduler():
    """스케줄러 실행"""
    setup_scheduler()
    
    print("보고서 생성 스케줄러 시작...")
    print("주간 보고서: 매주 금요일 오후 6시")
    print("월간 보고서: 매월 마지막 거래일 오후 6시")
    print("분기 보고서: 분기 마지막 거래일 오후 6시")
    print("연간 보고서: 12월 마지막 거래일 오후 6시")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 확인


if __name__ == "__main__":
    run_scheduler()
