#!/usr/bin/env python3
"""
anchor_close 디버그 스크립트

한국항공우주(또는 특정 종목)의 추천 레코드에서 anchor_close 관련 정보를 출력

사용법:
    python debug_anchor_close.py [--ticker CODE] [--date YYYYMMDD]
"""

import sys
import os
import argparse
from datetime import date

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import db_manager
from date_helper import yyyymmdd_to_date, get_anchor_close, get_trading_date
from kiwoom_api import api


def debug_anchor_close(ticker: str = "047810", target_date: str = "20251210"):
    """한국항공우주(또는 특정 종목)의 anchor_close 정보 출력
    
    Args:
        ticker: 종목 코드 (기본값: 047810 = 한국항공우주)
        target_date: 확인할 날짜 (YYYYMMDD, 기본값: 2025-12-10)
    """
    print(f"🔍 anchor_close 디버그: {ticker} ({target_date})")
    print()
    
    date_obj = yyyymmdd_to_date(target_date)
    
    with db_manager.get_cursor(commit=False) as cur:
        # 추천 레코드 조회
        cur.execute("""
            SELECT date, code, name, close_price, anchor_date, anchor_close, 
                   anchor_price_type, anchor_source, scanner_version, created_at
            FROM scan_rank
            WHERE code = %s AND date = %s AND code != 'NORESULT'
            ORDER BY scanner_version
        """, (ticker, date_obj))
        
        rows = cur.fetchall()
        
        if not rows:
            print(f"❌ 추천 레코드를 찾을 수 없습니다: {ticker} ({target_date})")
            return
        
        for row in rows:
            if isinstance(row, dict):
                date_val = row.get('date')
                code = row.get('code')
                name = row.get('name')
                close_price = row.get('close_price')
                anchor_date = row.get('anchor_date')
                anchor_close = row.get('anchor_close')
                anchor_price_type = row.get('anchor_price_type')
                anchor_source = row.get('anchor_source')
                scanner_version = row.get('scanner_version')
                created_at = row.get('created_at')
            else:
                date_val = row[0]
                code = row[1]
                name = row[2]
                close_price = row[3]
                anchor_date = row[4]
                anchor_close = row[5]
                anchor_price_type = row[6]
                anchor_source = row[7]
                scanner_version = row[8] if len(row) > 8 else 'v1'
                created_at = row[9] if len(row) > 9 else None
            
            print(f"📊 추천 레코드 (scanner_version: {scanner_version})")
            print(f"   종목: {code} ({name})")
            print(f"   추천일: {date_val}")
            print(f"   close_price (DB): {close_price:.0f if close_price else 'NULL'}")
            print(f"   anchor_date: {anchor_date}")
            print(f"   anchor_close: {anchor_close:.0f if anchor_close else 'NULL'}")
            print(f"   anchor_price_type: {anchor_price_type}")
            print(f"   anchor_source: {anchor_source}")
            print(f"   created_at: {created_at}")
            print()
            
            # anchor_close가 없으면 조회 시도
            if not anchor_close or anchor_close <= 0:
                print("   ⚠️  anchor_close가 없습니다. 조회 시도...")
                
                # date_val을 YYYYMMDD 문자열로 변환
                if isinstance(date_val, date):
                    date_str = date_val.strftime('%Y%m%d')
                elif isinstance(date_val, str):
                    if len(date_val) == 10 and '-' in date_val:
                        date_str = date_val.replace('-', '')
                    else:
                        date_str = date_val
                else:
                    date_str = str(date_val)
                
                # 거래일 결정
                anchor_date_str = get_trading_date(date_str)
                print(f"   거래일 결정: {date_str} -> {anchor_date_str}")
                
                # anchor_close 조회
                try:
                    retrieved_close = get_anchor_close(code, anchor_date_str, price_type="CLOSE")
                    if retrieved_close:
                        print(f"   조회된 종가: {retrieved_close:.0f}")
                        
                        # close_price와 비교
                        if close_price:
                            diff = abs(retrieved_close - close_price)
                            diff_pct = (diff / close_price) * 100
                            print(f"   차이: {diff:.0f}원 ({diff_pct:.2f}%)")
                            if diff > 0.01:  # 1원 이상 차이
                                print(f"   ⚠️  불일치 감지!")
                    else:
                        print(f"   ❌ 종가 조회 실패")
                except Exception as e:
                    print(f"   ❌ 오류: {e}")
            else:
                # anchor_close가 있으면 실제 종가와 비교
                print("   ✅ anchor_close가 저장되어 있습니다.")
                
                # date_val을 YYYYMMDD 문자열로 변환
                if isinstance(date_val, date):
                    date_str = date_val.strftime('%Y%m%d')
                elif isinstance(date_val, str):
                    if len(date_val) == 10 and '-' in date_val:
                        date_str = date_val.replace('-', '')
                    else:
                        date_str = date_val
                else:
                    date_str = str(date_val)
                
                # 거래일 결정
                anchor_date_str = get_trading_date(date_str)
                
                # 실제 종가 조회
                try:
                    actual_close = get_anchor_close(code, anchor_date_str, price_type="CLOSE")
                    if actual_close:
                        diff = abs(anchor_close - actual_close)
                        diff_pct = (diff / actual_close) * 100 if actual_close > 0 else 0
                        print(f"   실제 종가: {actual_close:.0f}")
                        print(f"   차이: {diff:.0f}원 ({diff_pct:.2f}%)")
                        if diff > 0.01:  # 1원 이상 차이
                            print(f"   ⚠️  불일치 감지!")
                        else:
                            print(f"   ✅ 일치 확인")
                except Exception as e:
                    print(f"   ⚠️  실제 종가 조회 실패: {e}")
            
            print()


def main():
    parser = argparse.ArgumentParser(description='anchor_close 디버그 스크립트')
    parser.add_argument('--ticker', type=str, default='047810', help='종목 코드 (기본값: 047810 = 한국항공우주)')
    parser.add_argument('--date', type=str, default='20251210', help='확인할 날짜 (YYYYMMDD, 기본값: 2025-12-10)')
    
    args = parser.parse_args()
    
    debug_anchor_close(args.ticker, args.date)


if __name__ == '__main__':
    main()



