#!/usr/bin/env python3
"""
한국항공우주(047810) 가격 확인 스크립트
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import db_manager
from kiwoom_api import api
from date_helper import yyyymmdd_to_date

ticker = "047810"
target_date = "20251210"

print(f"🔍 한국항공우주({ticker}) 가격 확인: {target_date}")
print()

# 1. DB에 저장된 값 확인
print("📊 DB에 저장된 값:")
print("-" * 60)
with db_manager.get_cursor(commit=False) as cur:
    date_obj = yyyymmdd_to_date(target_date)
    cur.execute("""
        SELECT date, scanner_version, close_price, anchor_close, anchor_date, anchor_source
        FROM scan_rank
        WHERE code = %s AND date = %s
        ORDER BY scanner_version
    """, (ticker, date_obj))
    
    rows = cur.fetchall()
    if rows:
        for row in rows:
            if isinstance(row, dict):
                date_val = row.get('date')
                version = row.get('scanner_version')
                close_price = row.get('close_price')
                anchor_close = row.get('anchor_close')
                anchor_date = row.get('anchor_date')
                anchor_source = row.get('anchor_source')
            else:
                date_val = row[0]
                version = row[1]
                close_price = row[2]
                anchor_close = row[3]
                anchor_date = row[4]
                anchor_source = row[5] if len(row) > 5 else None
            
            print(f"  버전: {version}")
            close_str = f"{close_price:.0f}" if close_price is not None else "NULL"
            anchor_str = f"{anchor_close:.0f}" if anchor_close is not None else "NULL"
            print(f"  close_price (DB): {close_str}")
            print(f"  anchor_close: {anchor_str}")
            print(f"  anchor_date: {anchor_date}")
            print(f"  anchor_source: {anchor_source}")
            print()
    else:
        print("  ❌ DB에 데이터 없음")
        print()

# 2. 실제 일봉 종가 확인
print("📊 실제 일봉 종가 (API 조회):")
print("-" * 60)
try:
    df = api.get_ohlcv(ticker, 1, target_date)
    if not df.empty:
        latest = df.iloc[-1]
        actual_close = float(latest['close'])
        actual_date = latest.get('date', target_date)
        
        print(f"  날짜: {actual_date}")
        print(f"  종가: {actual_close:.0f}원")
        print()
        
        # DB 값과 비교
        if rows:
            for row in rows:
                if isinstance(row, dict):
                    close_price = row.get('close_price')
                    anchor_close = row.get('anchor_close')
                    version = row.get('scanner_version')
                else:
                    close_price = row[2]
                    anchor_close = row[3]
                    version = row[1]
                
                print(f"  [{version}] 비교:")
                if close_price:
                    diff_close = abs(actual_close - close_price)
                    print(f"    close_price 차이: {diff_close:.0f}원 ({actual_close:.0f} vs {close_price:.0f})")
                    if diff_close > 0.01:
                        print(f"    ⚠️  불일치!")
                
                if anchor_close:
                    diff_anchor = abs(actual_close - anchor_close)
                    print(f"    anchor_close 차이: {diff_anchor:.0f}원 ({actual_close:.0f} vs {anchor_close:.0f})")
                    if diff_anchor > 0.01:
                        print(f"    ⚠️  불일치!")
                else:
                    print(f"    anchor_close: NULL (마이그레이션 필요)")
                print()
    else:
        print("  ❌ 일봉 데이터 없음")
except Exception as e:
    print(f"  ❌ 오류: {e}")
    import traceback
    traceback.print_exc()

# 3. 최근 일봉 데이터 확인 (참고)
print("📊 최근 일봉 데이터 (참고):")
print("-" * 60)
try:
    df_recent = api.get_ohlcv(ticker, 10)
    if not df_recent.empty:
        print("  날짜별 종가:")
        for idx, row in df_recent.tail(10).iterrows():
            date_str = str(row.get('date', ''))[:10] if hasattr(row.get('date', ''), '__str__') else str(row.get('date', ''))
            close = float(row['close'])
            print(f"    {date_str}: {close:.0f}원")
except Exception as e:
    print(f"  ❌ 오류: {e}")

