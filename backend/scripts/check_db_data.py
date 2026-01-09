#!/usr/bin/env python3
"""
DB 데이터 존재 유무 확인 스크립트

scan_rank 테이블의 데이터를 확인합니다.
"""

import sys
import os
from datetime import datetime, date

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import db_manager


def check_db_data():
    """DB 데이터 존재 유무 확인"""
    print("🔍 DB 데이터 확인 중...")
    print()
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 1. 전체 레코드 수
            cur.execute("SELECT COUNT(*) FROM scan_rank")
            total_count = cur.fetchone()[0]
            print(f"📊 전체 레코드 수: {total_count:,}건")
            
            # 2. NORESULT 제외한 실제 추천 종목 수
            cur.execute("SELECT COUNT(*) FROM scan_rank WHERE code != 'NORESULT'")
            actual_count = cur.fetchone()[0]
            print(f"📊 실제 추천 종목 수: {actual_count:,}건 (NORESULT 제외)")
            
            # 3. scanner_version별 통계
            print()
            print("📊 scanner_version별 통계:")
            print("-" * 60)
            cur.execute("""
                SELECT 
                    scanner_version,
                    COUNT(*) as total,
                    COUNT(CASE WHEN code != 'NORESULT' THEN 1 END) as candidates,
                    MIN(date) as min_date,
                    MAX(date) as max_date
                FROM scan_rank
                GROUP BY scanner_version
                ORDER BY scanner_version
            """)
            
            for row in cur.fetchall():
                version, total, candidates, min_date, max_date = row
                print(f"  {version or 'NULL'}:")
                print(f"    총 레코드: {total:,}건")
                print(f"    추천 종목: {candidates:,}건")
                print(f"    날짜 범위: {min_date} ~ {max_date}")
                print()
            
            # 4. 최근 10일 데이터 확인
            print("📅 최근 10일 데이터:")
            print("-" * 60)
            cur.execute("""
                SELECT 
                    date,
                    scanner_version,
                    COUNT(*) as total,
                    COUNT(CASE WHEN code != 'NORESULT' THEN 1 END) as candidates
                FROM scan_rank
                GROUP BY date, scanner_version
                ORDER BY date DESC, scanner_version
                LIMIT 20
            """)
            
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    date_val, version, total, candidates = row
                    date_str = str(date_val).replace('-', '')
                    print(f"  {date_str} ({version or 'NULL'}): 총 {total}건, 추천 {candidates}건")
            else:
                print("  ❌ 데이터 없음")
            
            print()
            
            # 5. anchor_close 필드 통계
            print("📊 anchor_close 필드 통계:")
            print("-" * 60)
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(anchor_close) as has_anchor_close,
                    COUNT(CASE WHEN anchor_close IS NULL OR anchor_close <= 0 THEN 1 END) as missing_anchor_close
                FROM scan_rank
                WHERE code != 'NORESULT'
            """)
            
            row = cur.fetchone()
            if row:
                total, has_anchor, missing = row
                print(f"  전체 추천 종목: {total:,}건")
                print(f"  anchor_close 있음: {has_anchor:,}건")
                print(f"  anchor_close 없음: {missing:,}건")
                if total > 0:
                    coverage = (has_anchor / total) * 100
                    print(f"  커버리지: {coverage:.1f}%")
            
            print()
            
            # 6. 특정 날짜 확인 (2025-12-10)
            print("📅 2025-12-10 데이터 확인:")
            print("-" * 60)
            cur.execute("""
                SELECT 
                    code, name, scanner_version, 
                    close_price, anchor_close, anchor_date, anchor_source
                FROM scan_rank
                WHERE date = '2025-12-10' AND code != 'NORESULT'
                ORDER BY scanner_version, code
                LIMIT 20
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"  총 {len(rows)}건 발견 (최대 20건 표시)")
                for row in rows:
                    code, name, version, close_price, anchor_close, anchor_date, anchor_source = row
                    print(f"  {code} ({name}):")
                    print(f"    버전: {version}")
                    print(f"    close_price: {close_price:.0f if close_price else 'NULL'}")
                    print(f"    anchor_close: {anchor_close:.0f if anchor_close else 'NULL'}")
                    print(f"    anchor_date: {anchor_date}")
                    print(f"    anchor_source: {anchor_source}")
                    print()
            else:
                print("  ❌ 2025-12-10 데이터 없음")
            
            # 7. 한국항공우주(047810) 확인
            print("📊 한국항공우주(047810) 데이터 확인:")
            print("-" * 60)
            cur.execute("""
                SELECT 
                    date, scanner_version, 
                    close_price, anchor_close, anchor_date, anchor_source
                FROM scan_rank
                WHERE code = '047810'
                ORDER BY date DESC
                LIMIT 10
            """)
            
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    date_val, version, close_price, anchor_close, anchor_date, anchor_source = row
                    date_str = str(date_val).replace('-', '')
                    print(f"  {date_str} ({version}):")
                    print(f"    close_price: {close_price:.0f if close_price else 'NULL'}")
                    print(f"    anchor_close: {anchor_close:.0f if anchor_close else 'NULL'}")
                    print(f"    anchor_date: {anchor_date}")
                    print(f"    anchor_source: {anchor_source}")
                    print()
            else:
                print("  ❌ 한국항공우주 데이터 없음")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = check_db_data()
    sys.exit(0 if success else 1)



