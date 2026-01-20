#!/usr/bin/env python3
"""
AWS 서버 DB의 V2 스캔 데이터 확인
"""

import os
import pymysql

# AWS RDS 연결 정보
AWS_DB_CONFIG = {
    'host': 'stock-finder-db.c123456789.ap-northeast-2.rds.amazonaws.com',  # 실제 엔드포인트로 변경 필요
    'user': 'admin',
    'password': os.getenv('AWS_DB_PASSWORD', 'your_password'),  # 환경변수 또는 직접 입력
    'database': 'stock_finder',
    'charset': 'utf8mb4'
}

def check_aws_v2_data():
    try:
        # AWS RDS 연결
        conn = pymysql.connect(**AWS_DB_CONFIG)
        
        queries = [
            ("전체 스캔 데이터", "SELECT COUNT(*) FROM scan_rank"),
            ("V2 스캔 데이터", "SELECT COUNT(*) FROM scan_rank WHERE scanner_version = 'v2'"),
            ("V1 스캔 데이터", "SELECT COUNT(*) FROM scan_rank WHERE scanner_version = 'v1' OR scanner_version IS NULL"),
            ("V2 스캔 날짜 범위", "SELECT MIN(date), MAX(date) FROM scan_rank WHERE scanner_version = 'v2'"),
            ("V2 스캔 최근 10일", """
                SELECT date, COUNT(*) as count 
                FROM scan_rank 
                WHERE scanner_version = 'v2' 
                GROUP BY date 
                ORDER BY date DESC 
                LIMIT 10
            """)
        ]
        
        with conn.cursor() as cur:
            for title, query in queries:
                print(f"\n📊 {title}:")
                cur.execute(query)
                
                if "최근" in title:
                    rows = cur.fetchall()
                    if rows:
                        for row in rows:
                            print(f"  {row[0]}: {row[1]}건")
                    else:
                        print("  데이터 없음")
                else:
                    result = cur.fetchone()
                    if len(result) == 1:
                        print(f"  {result[0]:,}건")
                    else:
                        print(f"  시작: {result[0]}, 종료: {result[1]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ AWS DB 연결 실패: {e}")
        print("💡 DB 연결 정보를 확인하세요:")
        print("   - 엔드포인트 주소")
        print("   - 사용자명/비밀번호")
        print("   - 보안그룹 설정")

if __name__ == "__main__":
    check_aws_v2_data()