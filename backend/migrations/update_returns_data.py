#!/usr/bin/env python3
"""
기존 scan_rank 데이터의 returns 필드를 업데이트하는 마이그레이션 스크립트
- returns 필드가 비어있거나 유효하지 않은 경우 재계산
- recommended_price, recommended_date, current_return 정보를 returns 필드에 포함
"""

import sys
import os
import json
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import db_manager
from services.returns_service import calculate_returns_batch
from date_helper import yyyymmdd_to_date


def get_rows_needing_update():
    """업데이트가 필요한 레코드 조회"""
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute("""
            SELECT date, code, close_price, scanner_version
            FROM scan_rank
            WHERE (returns IS NULL 
               OR returns = '{}'::jsonb
               OR returns::text LIKE '%"current_return":null%'
               OR returns::text NOT LIKE '%"current_return"%')
              AND code != 'NORESULT'
            ORDER BY date DESC, code
        """)
        return cur.fetchall()


def update_returns_for_row(date, code, close_price, scanner_version):
    """단일 레코드의 returns 필드 업데이트"""
    try:
        # 날짜 형식 변환
        if hasattr(date, 'strftime'):
            formatted_date = date.strftime('%Y%m%d')
        else:
            formatted_date = str(date).replace('-', '')
        
        # 수익률 계산
        scan_prices = {code: float(close_price)} if close_price and close_price > 0 else {}
        returns_data = calculate_returns_batch([code], formatted_date, None, scan_prices)
        
        if code in returns_data and returns_data[code]:
            returns_info = returns_data[code]
            
            # returns JSON 구성
            returns_json = {
                "current_return": returns_info.get("current_return"),
                "max_return": returns_info.get("max_return"),
                "min_return": returns_info.get("min_return"),
                "days_elapsed": returns_info.get("days_elapsed", 0),
                "scan_price": returns_info.get("scan_price", close_price),
                "current_price": returns_info.get("current_price"),
                "max_price": returns_info.get("max_price"),
                "min_price": returns_info.get("min_price")
            }
            
            # DB 업데이트
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("""
                    UPDATE scan_rank
                    SET returns = %s::jsonb
                    WHERE date = %s AND code = %s AND scanner_version = %s
                """, (json.dumps(returns_json, ensure_ascii=False), date, code, scanner_version))
            
            return True, returns_info.get("current_return")
        else:
            # 수익률 계산 실패 시 기본값 설정
            returns_json = {
                "current_return": None,
                "max_return": None,
                "min_return": None,
                "days_elapsed": 0,
                "scan_price": close_price if close_price and close_price > 0 else None
            }
            
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("""
                    UPDATE scan_rank
                    SET returns = %s::jsonb
                    WHERE date = %s AND code = %s AND scanner_version = %s
                """, (json.dumps(returns_json, ensure_ascii=False), date, code, scanner_version))
            
            return True, None
            
    except Exception as e:
        print(f"  ❌ {code} ({date}) 업데이트 실패: {e}")
        return False, None


def main():
    print("=" * 60)
    print("scan_rank 테이블 returns 필드 업데이트 마이그레이션")
    print("=" * 60)
    
    # 업데이트가 필요한 레코드 조회
    print("\n📊 업데이트가 필요한 레코드 조회 중...")
    rows = get_rows_needing_update()
    
    if not rows:
        print("✅ 업데이트가 필요한 레코드가 없습니다.")
        return
    
    print(f"📋 총 {len(rows)}개 레코드가 업데이트가 필요합니다.")
    
    # 사용자 확인
    response = input(f"\n{len(rows)}개 레코드를 업데이트하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("❌ 취소되었습니다.")
        return
    
    # 배치 처리
    batch_size = 50
    success_count = 0
    error_count = 0
    total_updated = 0
    
    print(f"\n🔄 업데이트 시작 (배치 크기: {batch_size})...")
    
    for i, row in enumerate(rows, 1):
        date, code, close_price, scanner_version = row
        
        if i % batch_size == 0:
            print(f"  진행 중: {i}/{len(rows)} ({i*100//len(rows)}%)")
        
        success, current_return = update_returns_for_row(date, code, close_price, scanner_version)
        
        if success:
            success_count += 1
            if current_return is not None:
                total_updated += 1
        else:
            error_count += 1
    
    print("\n" + "=" * 60)
    print("✅ 마이그레이션 완료")
    print("=" * 60)
    print(f"  성공: {success_count}개")
    print(f"  수익률 계산 완료: {total_updated}개")
    print(f"  실패: {error_count}개")
    print(f"  총 처리: {len(rows)}개")


if __name__ == "__main__":
    main()

