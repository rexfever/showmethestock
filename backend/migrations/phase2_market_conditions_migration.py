#!/usr/bin/env python3
"""
Phase 2: Market Conditions Table Scanner Version Migration
- Add scanner_version column to market_conditions table
- Update primary key to include scanner_version
- Preserve existing data
"""

import sqlite3
import os
from datetime import datetime

def backup_market_conditions_table(conn, backup_timestamp):
    """기존 market_conditions 테이블 백업"""
    cursor = conn.cursor()
    
    # 백업 테이블 생성
    backup_table = f"market_conditions_backup_{backup_timestamp}"
    cursor.execute(f"""
        CREATE TABLE {backup_table} AS 
        SELECT * FROM market_conditions
    """)
    
    # 백업된 레코드 수 확인
    cursor.execute(f"SELECT COUNT(*) FROM {backup_table}")
    backup_count = cursor.fetchone()[0]
    
    print(f"✅ Market conditions 백업 완료: {backup_count}개 레코드 → {backup_table}")
    return backup_count

def migrate_market_conditions_table(conn):
    """market_conditions 테이블에 scanner_version 컬럼 추가 및 PK 업데이트"""
    cursor = conn.cursor()
    
    # 1. 임시 테이블 생성 (새 스키마)
    cursor.execute("""
        CREATE TABLE market_conditions_new (
            date TEXT NOT NULL,
            market_trend TEXT,
            trend_strength REAL,
            volatility REAL,
            volume_trend TEXT,
            sector_rotation TEXT,
            risk_level TEXT,
            scanner_version TEXT NOT NULL DEFAULT 'v1',
            PRIMARY KEY (date, scanner_version)
        )
    """)
    
    # 2. 기존 데이터를 새 테이블로 복사 (scanner_version = 'v1')
    cursor.execute("""
        INSERT INTO market_conditions_new 
        (date, market_trend, trend_strength, volatility, volume_trend, 
         sector_rotation, risk_level, scanner_version)
        SELECT date, market_trend, trend_strength, volatility, volume_trend,
               sector_rotation, risk_level, 'v1'
        FROM market_conditions
    """)
    
    # 3. 기존 테이블 삭제
    cursor.execute("DROP TABLE market_conditions")
    
    # 4. 새 테이블을 원래 이름으로 변경
    cursor.execute("ALTER TABLE market_conditions_new RENAME TO market_conditions")
    
    print("✅ Market conditions 테이블 스키마 업데이트 완료")

def verify_migration(conn):
    """마이그레이션 결과 검증"""
    cursor = conn.cursor()
    
    # 스키마 확인
    cursor.execute("PRAGMA table_info(market_conditions)")
    columns = cursor.fetchall()
    
    expected_columns = ['date', 'market_trend', 'trend_strength', 'volatility', 
                       'volume_trend', 'sector_rotation', 'risk_level', 'scanner_version']
    actual_columns = [col[1] for col in columns]
    
    print(f"📋 Market conditions 테이블 컬럼: {actual_columns}")
    
    # PK 확인
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='market_conditions'")
    schema = cursor.fetchone()[0]
    
    if 'PRIMARY KEY (date, scanner_version)' in schema:
        print("✅ 복합 Primary Key 설정 확인")
    else:
        print("❌ Primary Key 설정 오류")
        return False
    
    # 데이터 개수 확인
    cursor.execute("SELECT COUNT(*) FROM market_conditions")
    total_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM market_conditions WHERE scanner_version = 'v1'")
    v1_count = cursor.fetchone()[0]
    
    print(f"📊 마이그레이션 후 데이터: 총 {total_count}개, V1: {v1_count}개")
    
    return total_count == v1_count and total_count > 0

def main():
    """Phase 2 마이그레이션 실행"""
    # 여러 가능한 데이터베이스 경로 확인
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'snapshots.db'),
        os.path.join(os.path.dirname(__file__), '..', 'stock_data.db'),
        '/Users/rexsmac/workspace/stock-finder/snapshots.db',
        '/Users/rexsmac/workspace/stock-finder/backend/snapshots.db'
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다. 확인한 경로: {possible_paths}")
        return False
    
    print(f"💾 데이터베이스 파일 발견: {db_path}")
    
    backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"🚀 Phase 2 Market Conditions 마이그레이션 시작 - {backup_timestamp}")
    print(f"📁 사용할 데이터베이스: {db_path}")
    
    try:
        with sqlite3.connect(db_path) as conn:
            # 백업
            backup_count = backup_market_conditions_table(conn, backup_timestamp)
            
            # 마이그레이션
            migrate_market_conditions_table(conn)
            
            # 검증
            if verify_migration(conn):
                print(f"✅ Phase 2 마이그레이션 성공 완료!")
                print(f"📁 백업 테이블: market_conditions_backup_{backup_timestamp}")
                return True
            else:
                print("❌ 마이그레이션 검증 실패")
                return False
                
    except Exception as e:
        print(f"❌ 마이그레이션 실행 중 오류: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)