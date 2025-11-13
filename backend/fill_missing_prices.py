#!/usr/bin/env python3
"""
스캔 결과에서 가격 정보가 없는 데이터를 키움 REST API로 채우는 스크립트
"""
import sys
import os
from datetime import datetime, timedelta, date
import time

# 프로젝트 루트 디렉토리를 PYTHONPATH에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kiwoom_api import api
from db_manager import db_manager
from main import is_trading_day


def fill_missing_prices(dry_run=False, date_limit=None):
    """
    가격 정보가 없는 스캔 결과를 키움 API로 채우기
    
    Args:
        dry_run: True면 실제 업데이트 없이 보기만 함
        date_limit: 처리할 최대 날짜 수 (None이면 전체)
    """
    print("=" * 80)
    print("🔍 가격 정보가 없는 스캔 결과 조회")
    print("=" * 80)
    
    # 가격이 없는 데이터 조회 (NORESULT 제외)
    with db_manager.get_cursor(commit=False) as cur:
        query = """
            SELECT date, code, name, current_price, close_price
            FROM scan_rank
            WHERE (current_price IS NULL OR current_price = 0)
              AND code != 'NORESULT'
            ORDER BY date DESC, code
        """
        if date_limit:
            query += f" LIMIT {date_limit}"
        
        cur.execute(query)
        rows = cur.fetchall()
    
    if not rows:
        print("✅ 가격 정보가 없는 데이터가 없습니다.")
        return
    
    print(f"📊 가격 정보가 없는 레코드: {len(rows)}개")
    print()
    
    # 날짜별로 그룹화
    by_date = {}
    for row in rows:
        if isinstance(row, dict):
            date = row['date']
            code = row['code']
            name = row['name']
        else:
            date = row[0]
            code = row[1]
            name = row[2]
        
        if date not in by_date:
            by_date[date] = []
        by_date[date].append((code, name))
    
    print(f"📅 날짜별 분류: {len(by_date)}개 날짜")
    print()
    
    updated_count = 0
    error_count = 0
    skipped_count = 0
    
    # 날짜순으로 처리 (오래된 것부터)
    for date_str in sorted(by_date.keys()):
        codes = by_date[date_str]
        print(f"📅 {date_str}: {len(codes)}개 종목")
        
        # 날짜 형식 변환 (YYYY-MM-DD -> YYYYMMDD)
        try:
            # date_str이 datetime.date 객체일 수도 있음
            if hasattr(date_str, 'strftime'):
                date_formatted = date_str.strftime('%Y%m%d')
            elif isinstance(date_str, str):
                if '-' in date_str:
                    date_formatted = date_str.replace('-', '')
                else:
                    date_formatted = date_str
            else:
                date_formatted = str(date_str).replace('-', '')
        except Exception as e:
            print(f"  ⚠️ 날짜 형식 오류: {date_str} ({type(date_str)}), 오류: {e}, 건너뜀")
            skipped_count += len(codes)
            continue
        
        # 거래일 체크
        if not is_trading_day(date_formatted):
            print(f"  ⚠️ 거래일이 아닙니다: {date_str}, 건너뜀")
            skipped_count += len(codes)
            continue
        
        for code, name in codes:
            try:
                print(f"  🔍 {code} ({name}): 가격 조회 중...", end=" ")
                
                # 키움 API로 해당 날짜의 OHLCV 조회
                df = api.get_ohlcv(code, count=2, base_dt=date_formatted)
                
                if df.empty:
                    print("❌ 데이터 없음")
                    error_count += 1
                    continue
                
                # 해당 날짜의 종가 찾기
                target_price = None
                for idx, row in df.iterrows():
                    row_date = str(row['date']).replace('-', '')
                    if row_date == date_formatted or row_date[:8] == date_formatted[:8]:
                        target_price = float(row['close'])
                        break
                
                # 정확히 일치하는 날짜가 없으면 마지막 행 사용
                if target_price is None and not df.empty:
                    target_price = float(df.iloc[-1]['close'])
                
                if target_price is None or target_price <= 0:
                    print("❌ 가격 정보 없음")
                    error_count += 1
                    continue
                
                print(f"✅ {target_price:,.0f}원")
                
                if not dry_run:
                    # DB 업데이트
                    with db_manager.get_cursor(commit=True) as cur_update:
                        cur_update.execute("""
                            UPDATE scan_rank
                            SET current_price = %s,
                                close_price = %s
                            WHERE date = %s AND code = %s
                        """, (target_price, target_price, date_str, code))
                    
                    updated_count += 1
                else:
                    print(f"    [DRY RUN] 업데이트 예정: {target_price:,.0f}원")
                    updated_count += 1
                
                # API 호출 제한 고려 (약간의 지연)
                time.sleep(0.2)
                
            except Exception as e:
                print(f"❌ 오류: {str(e)}")
                error_count += 1
                time.sleep(1)  # 오류 시 더 긴 지연
        
        print()
    
    print("=" * 80)
    print("📊 처리 결과")
    print("=" * 80)
    print(f"✅ 업데이트: {updated_count}개")
    print(f"❌ 오류: {error_count}개")
    print(f"⚠️ 건너뜀: {skipped_count}개")
    if dry_run:
        print()
        print("⚠️ DRY RUN 모드였습니다. 실제 업데이트를 하려면 --execute 플래그를 사용하세요.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="스캔 결과의 누락된 가격 정보 채우기")
    parser.add_argument("--execute", action="store_true", help="실제 업데이트 실행 (기본은 dry-run)")
    parser.add_argument("--limit", type=int, help="처리할 최대 레코드 수")
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    fill_missing_prices(dry_run=dry_run, date_limit=args.limit)
