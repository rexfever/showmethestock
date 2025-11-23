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
    """기존 market_conditions 테이블 백업 (테이블이 존재하는 경우만)"""
    cursor = conn.cursor()
    
    # 테이블 존재 여부 확인
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='market_conditions'
    """)
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print("ℹ️ market_conditions 테이블이 존재하지 않음 - 백업 생략")
        return 0
    
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
    
    # 테이블 존재 여부 확인
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='market_conditions'
    """)
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        # 테이블이 없으면 새로 생성
        print("📋 market_conditions 테이블이 없음 - 새로 생성")
        cursor.execute("""
            CREATE TABLE market_conditions (
                date TEXT NOT NULL,
                market_sentiment TEXT NOT NULL,
                sentiment_score NUMERIC(5,2) DEFAULT 0,
                kospi_return REAL,
                volatility REAL,
                rsi_threshold REAL,
                sector_rotation TEXT,
                foreign_flow TEXT,
                volume_trend TEXT,
                min_signals INTEGER,
                macd_osc_min REAL,
                vol_ma5_mult REAL,
                gap_max REAL,
                ext_from_tema20_max REAL,
                trend_metrics TEXT DEFAULT '{}',
                breadth_metrics TEXT DEFAULT '{}',
                flow_metrics TEXT DEFAULT '{}',
                sector_metrics TEXT DEFAULT '{}',
                volatility_metrics TEXT DEFAULT '{}',
                foreign_flow_label TEXT,
                volume_trend_label TEXT,
                adjusted_params TEXT DEFAULT '{}',
                analysis_notes TEXT,
                scanner_version TEXT NOT NULL DEFAULT 'v1',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, scanner_version)
            )
        """)
        print("✅ Market conditions 테이블 생성 완료")
        return
    
    # 기존 테이블이 있는 경우 - scanner_version 컬럼 확인
    cursor.execute("PRAGMA table_info(market_conditions)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'scanner_version' in columns:
        print("ℹ️ scanner_version 컬럼이 이미 존재함 - 마이그레이션 생략")
        return
    
    # 1. 임시 테이블 생성 (새 스키마)
    cursor.execute("""
        CREATE TABLE market_conditions_new (
            date TEXT NOT NULL,
            market_sentiment TEXT NOT NULL,
            sentiment_score NUMERIC(5,2) DEFAULT 0,
            kospi_return REAL,
            volatility REAL,
            rsi_threshold REAL,
            sector_rotation TEXT,
            foreign_flow TEXT,
            volume_trend TEXT,
            min_signals INTEGER,
            macd_osc_min REAL,
            vol_ma5_mult REAL,
            gap_max REAL,
            ext_from_tema20_max REAL,
            trend_metrics TEXT DEFAULT '{}',
            breadth_metrics TEXT DEFAULT '{}',
            flow_metrics TEXT DEFAULT '{}',
            sector_metrics TEXT DEFAULT '{}',
            volatility_metrics TEXT DEFAULT '{}',
            foreign_flow_label TEXT,
            volume_trend_label TEXT,
            adjusted_params TEXT DEFAULT '{}',
            analysis_notes TEXT,
            scanner_version TEXT NOT NULL DEFAULT 'v1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date, scanner_version)
        )
    """)
    
    # 2. 기존 데이터를 새 테이블로 복사 (scanner_version = 'v1')
    # 기존 테이블의 실제 컬럼 구조에 맞춰 복사
    cursor.execute("""
        INSERT INTO market_conditions_new 
        (date, market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
         sector_rotation, foreign_flow, volume_trend, min_signals, macd_osc_min, 
         vol_ma5_mult, gap_max, ext_from_tema20_max, trend_metrics, breadth_metrics,
         flow_metrics, sector_metrics, volatility_metrics, foreign_flow_label,
         volume_trend_label, adjusted_params, analysis_notes, scanner_version)
        SELECT 
            date,
            COALESCE(market_sentiment, 'neutral') as market_sentiment,
            COALESCE(sentiment_score, 0) as sentiment_score,
            kospi_return,
            volatility,
            rsi_threshold,
            sector_rotation,
            foreign_flow,
            volume_trend,
            min_signals,
            macd_osc_min,
            vol_ma5_mult,
            gap_max,
            ext_from_tema20_max,
            COALESCE(trend_metrics, '{}') as trend_metrics,
            COALESCE(breadth_metrics, '{}') as breadth_metrics,
            COALESCE(flow_metrics, '{}') as flow_metrics,
            COALESCE(sector_metrics, '{}') as sector_metrics,
            COALESCE(volatility_metrics, '{}') as volatility_metrics,
            foreign_flow_label,
            volume_trend_label,
            COALESCE(adjusted_params, '{}') as adjusted_params,
            analysis_notes,
            'v1' as scanner_version
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
    
    actual_columns = [col[1] for col in columns]
    
    print(f"📋 Market conditions 테이블 컬럼: {actual_columns}")
    
    # scanner_version 컬럼 존재 확인
    if 'scanner_version' not in actual_columns:
        print("❌ scanner_version 컬럼이 없음")
        return False
    
    # PK 확인
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='market_conditions'")
    schema_result = cursor.fetchone()
    if not schema_result:
        print("❌ 테이블 스키마 조회 실패")
        return False
        
    schema = schema_result[0]
    
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
    
    return total_count == v1_count and total_count >= 0

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
            # 백업 (테이블이 존재하는 경우만)
            backup_count = backup_market_conditions_table(conn, backup_timestamp)
            
            # 마이그레이션
            migrate_market_conditions_table(conn)
            
            # 검증
            if verify_migration(conn):
                print(f"✅ Phase 2 마이그레이션 성공 완료!")
                if backup_count > 0:
                    print(f"📁 백업 테이블: market_conditions_backup_{backup_timestamp}")
                return True
            else:
                print("❌ 마이그레이션 검증 실패")
                return False
                
    except Exception as e:
        print(f"❌ 마이그레이션 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)