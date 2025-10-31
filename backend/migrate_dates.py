#!/usr/bin/env python3
"""
날짜 형식 마이그레이션 스크립트
YYYY-MM-DD -> YYYYMMDD 형식으로 변환
"""
import sqlite3
import os
from datetime import datetime

def migrate_dates():
    """로컬 DB의 날짜를 YYYYMMDD 형식으로 마이그레이션"""
    db_path = os.path.join(os.path.dirname(__file__), 'snapshots.db')
    
    if not os.path.exists(db_path):
        print("❌ snapshots.db 파일이 없습니다.")
        return
    
    print("🔄 날짜 마이그레이션 시작...")
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 현재 날짜 형식 확인
        cur.execute("SELECT DISTINCT date FROM scan_rank LIMIT 10")
        sample_dates = cur.fetchall()
        
        print(f"📊 샘플 날짜들: {[row[0] for row in sample_dates]}")
        
        # YYYY-MM-DD 형식인 날짜들을 YYYYMMDD로 변환
        cur.execute("SELECT date, COUNT(*) FROM scan_rank WHERE date LIKE '____-__-__' GROUP BY date")
        dates_to_migrate = cur.fetchall()
        
        if not dates_to_migrate:
            print("✅ 마이그레이션할 날짜가 없습니다.")
            return
        
        print(f"🔄 {len(dates_to_migrate)}개 날짜를 마이그레이션합니다...")
        
        for old_date, count in dates_to_migrate:
            # YYYY-MM-DD -> YYYYMMDD 변환
            new_date = old_date.replace('-', '')
            
            # 중복 방지: 새 날짜로 이미 데이터가 있으면 기존 데이터 삭제
            cur.execute("DELETE FROM scan_rank WHERE date = ?", (new_date,))
            
            # 데이터 업데이트
            cur.execute("UPDATE scan_rank SET date = ? WHERE date = ?", (new_date, old_date))
            print(f"  {old_date} -> {new_date} ({count}개 레코드)")
        
        conn.commit()
        print(f"✅ 총 {len(dates_to_migrate)}개 날짜 마이그레이션 완료")
        
        # 결과 확인
        cur.execute("SELECT DISTINCT date FROM scan_rank ORDER BY date DESC LIMIT 5")
        updated_dates = cur.fetchall()
        print(f"✅ 마이그레이션 완료. 최신 날짜들: {[row[0] for row in updated_dates]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 마이그레이션 오류: {e}")

if __name__ == "__main__":
    migrate_dates()