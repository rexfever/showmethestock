#!/usr/bin/env python3
"""간단한 거래일 체크 테스트"""

import pytz
import holidays
from datetime import datetime

def is_trading_day(check_date: str = None):
    """거래일인지 확인 (주말과 공휴일 제외)"""
    
    if check_date:
        # 지정된 날짜 확인
        try:
            if len(check_date) == 8 and check_date.isdigit():  # YYYYMMDD 형식
                date_str = f"{check_date[:4]}-{check_date[4:6]}-{check_date[6:8]}"
            elif len(check_date) == 10 and check_date.count('-') == 2:  # YYYY-MM-DD 형식
                date_str = check_date
            else:
                return False
            
            check_dt = datetime.strptime(date_str, '%Y%m%d').date()
        except:
            return False
    else:
        # 오늘 날짜 확인
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

def test_trading_day():
    """거래일 체크 함수 테스트"""
    print("=== 거래일 체크 테스트 ===")
    
    # 오늘 날짜 테스트
    today = datetime.now().strftime('%Y%m%d')
    today_dash = datetime.now().strftime('%Y%m%d')
    
    print(f"오늘 날짜: {today} ({today_dash})")
    print(f"오늘 거래일 여부 (YYYYMMDD): {is_trading_day(today)}")
    print(f"오늘 거래일 여부 (YYYY-MM-DD): {is_trading_day(today_dash)}")
    print(f"오늘 거래일 여부 (None): {is_trading_day(None)}")
    
    # 주말 테스트
    print("\n--- 주말 테스트 ---")
    test_dates = [
        "20250111",  # 토요일
        "20250112",  # 일요일
        "20250113",  # 월요일
        "20250111",  # 토요일
        "20250112",  # 일요일
        "2025-01-13",  # 월요일
    ]
    
    for date in test_dates:
        result = is_trading_day(date)
        try:
            weekday = datetime.strptime(date.replace('-', ''), '%Y%m%d').strftime('%A')
            print(f"{date} ({weekday}): {result}")
        except:
            print(f"{date} (파싱 오류): {result}")

if __name__ == "__main__":
    test_trading_day()