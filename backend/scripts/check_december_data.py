#!/usr/bin/env python3
"""
12월 데이터 확인 스크립트
"""

import sys
import os
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from db_manager import db_manager
    
    print("🔍 12월 데이터 확인 중...")
    print()
    
    with db_manager.get_cursor(commit=False) as cur:
        # 12월 전체 데이터 통계
        print("📊 2024년 12월 데이터 통계:")
        print("-" * 60)
        cur.execute("""
            SELECT 
                scanner_version,
                COUNT(*) as total,
                COUNT(CASE WHEN code != 'NORESULT' THEN 1 END) as candidates,
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM scan_rank
            WHERE date >= '2024-12-01' AND date < '2025-01-01'
            GROUP BY scanner_version
            ORDER BY scanner_version
        """)
        
        rows = cur.fetchall()
        if rows:
            for row in rows:
                version, total, candidates, min_date, max_date = row
                print(f"  {version or 'NULL'}:")
                print(f"    총 레코드: {total:,}건")
                print(f"    추천 종목: {candidates:,}건")
                print(f"    날짜 범위: {min_date} ~ {max_date}")
                print()
        else:
            print("  ❌ 2024년 12월 데이터 없음")
        
        print()
        
        # 2025년 12월 데이터 통계
        print("📊 2025년 12월 데이터 통계:")
        print("-" * 60)
        cur.execute("""
            SELECT 
                scanner_version,
                COUNT(*) as total,
                COUNT(CASE WHEN code != 'NORESULT' THEN 1 END) as candidates,
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM scan_rank
            WHERE date >= '2025-12-01' AND date < '2026-01-01'
            GROUP BY scanner_version
            ORDER BY scanner_version
        """)
        
        rows = cur.fetchall()
        if rows:
            for row in rows:
                version, total, candidates, min_date, max_date = row
                print(f"  {version or 'NULL'}:")
                print(f"    총 레코드: {total:,}건")
                print(f"    추천 종목: {candidates:,}건")
                print(f"    날짜 범위: {min_date} ~ {max_date}")
                print()
        else:
            print("  ❌ 2025년 12월 데이터 없음")
        
        print()
        
        # 12월 날짜별 상세 데이터 (최근 20일)
        print("📅 12월 날짜별 상세 데이터 (최근 20일):")
        print("-" * 60)
        cur.execute("""
            SELECT 
                date,
                scanner_version,
                COUNT(*) as total,
                COUNT(CASE WHEN code != 'NORESULT' THEN 1 END) as candidates
            FROM scan_rank
            WHERE (date >= '2024-12-01' AND date < '2025-01-01')
               OR (date >= '2025-12-01' AND date < '2026-01-01')
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
            print("  ❌ 12월 데이터 없음")
        
        print()
        
        # anchor_close 컬럼 존재 여부 확인
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'scan_rank' AND column_name = 'anchor_close'
            )
        """)
        has_anchor_close = cur.fetchone()[0]
        
        # 2025-12-10 특정 확인
        print("📅 2025-12-10 상세 데이터:")
        print("-" * 60)
        if has_anchor_close:
            cur.execute("""
                SELECT 
                    code, name, scanner_version, 
                    close_price, anchor_close, anchor_date
                FROM scan_rank
                WHERE date = '2025-12-10' AND code != 'NORESULT'
                ORDER BY scanner_version, code
                LIMIT 10
            """)
        else:
            cur.execute("""
                SELECT 
                    code, name, scanner_version, 
                    close_price
                FROM scan_rank
                WHERE date = '2025-12-10' AND code != 'NORESULT'
                ORDER BY scanner_version, code
                LIMIT 10
            """)
        
        rows = cur.fetchall()
        if rows:
            print(f"  총 {len(rows)}건 발견 (최대 10건 표시)")
            for row in rows:
                if has_anchor_close:
                    code, name, version, close_price, anchor_close, anchor_date = row
                    close_str = f"{close_price:.0f}" if close_price is not None else "NULL"
                    anchor_str = f"{anchor_close:.0f}" if anchor_close is not None else "NULL"
                    print(f"  {code} ({name}):")
                    print(f"    버전: {version}")
                    print(f"    close_price: {close_str}")
                    print(f"    anchor_close: {anchor_str}")
                    print(f"    anchor_date: {anchor_date}")
                else:
                    code, name, version, close_price = row
                    close_str = f"{close_price:.0f}" if close_price is not None else "NULL"
                    print(f"  {code} ({name}):")
                    print(f"    버전: {version}")
                    print(f"    close_price: {close_str}")
                    print(f"    ⚠️  anchor_close 컬럼 없음 (마이그레이션 필요)")
                print()
        else:
            print("  ❌ 2025-12-10 데이터 없음")
        
        # 전체 날짜 범위 확인
        print()
        print("📅 전체 데이터 날짜 범위:")
        print("-" * 60)
        cur.execute("""
            SELECT 
                MIN(date) as min_date,
                MAX(date) as max_date,
                COUNT(DISTINCT date) as total_days
            FROM scan_rank
        """)
        
        row = cur.fetchone()
        if row:
            min_date, max_date, total_days = row
            print(f"  최소 날짜: {min_date}")
            print(f"  최대 날짜: {max_date}")
            print(f"  총 날짜 수: {total_days}일")
        
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

