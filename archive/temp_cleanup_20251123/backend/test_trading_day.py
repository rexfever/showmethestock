#!/usr/bin/env python3
"""거래일 체크 함수 테스트"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from main import is_trading_day
from datetime import datetime, timedelta

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
    
    # 주말 테스트 (토요일, 일요일)
    print("\n--- 주말 테스트 ---")
    test_dates = [
        "20250111",  # 토요일
        "20250112",  # 일요일
        "20250113",  # 월요일
        "2025-01-11",  # 토요일
        "2025-01-12",  # 일요일
        "2025-01-13",  # 월요일
    ]
    
    for date in test_dates:
        result = is_trading_day(date)
        weekday = datetime.strptime(date.replace('-', ''), '%Y%m%d').strftime('%A')
        print(f"{date} ({weekday}): {result}")
    
    # 공휴일 테스트
    print("\n--- 공휴일 테스트 ---")
    holidays = [
        "20250101",  # 신정
        "20250128",  # 설날 연휴 시작
        "20250129",  # 설날
        "20250130",  # 설날 연휴 끝
    ]
    
    for date in holidays:
        result = is_trading_day(date)
        print(f"{date}: {result}")

if __name__ == "__main__":
    test_trading_day()