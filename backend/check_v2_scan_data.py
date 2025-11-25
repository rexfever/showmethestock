#!/usr/bin/env python3
"""
V2 스캔 데이터 확인
"""

from db_manager import db_manager

def check_v2_data():
    queries = [
        ("전체 스캔 데이터", "SELECT COUNT(*) FROM scan_rank"),
        ("V2 스캔 데이터", "SELECT COUNT(*) FROM scan_rank WHERE scanner_version = 'v2'"),
        ("V1 스캔 데이터", "SELECT COUNT(*) FROM scan_rank WHERE scanner_version = 'v1' OR scanner_version IS NULL"),
        ("V2 스캔 날짜 범위", "SELECT MIN(date), MAX(date) FROM scan_rank WHERE scanner_version = 'v2'"),
        ("V2 스캔 날짜별 개수", """
            SELECT date, COUNT(*) as count 
            FROM scan_rank 
            WHERE scanner_version = 'v2' 
            GROUP BY date 
            ORDER BY date DESC 
            LIMIT 10
        """)
    ]
    
    with db_manager.get_cursor(commit=False) as cur:
        for title, query in queries:
            print(f"\n📊 {title}:")
            cur.execute(query)
            
            if "날짜별" in title:
                rows = cur.fetchall()
                for row in rows:
                    print(f"  {row[0]}: {row[1]}건")
            else:
                result = cur.fetchone()
                if len(result) == 1:
                    print(f"  {result[0]:,}건")
                else:
                    print(f"  시작: {result[0]}, 종료: {result[1]}")

if __name__ == "__main__":
    check_v2_data()