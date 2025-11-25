#!/usr/bin/env python3
"""
SQLite용 market_regime_daily 테이블 생성 스크립트
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_market_regime_daily_table():
    """market_regime_daily 테이블 생성"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS market_regime_daily (
        date TEXT PRIMARY KEY,
        us_prev_sentiment TEXT NOT NULL DEFAULT 'neutral',
        kr_sentiment TEXT NOT NULL DEFAULT 'neutral', 
        us_preopen_sentiment TEXT NOT NULL DEFAULT 'none',
        final_regime TEXT NOT NULL DEFAULT 'neutral',
        us_metrics TEXT,
        kr_metrics TEXT,
        us_preopen_metrics TEXT,
        run_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        version TEXT NOT NULL DEFAULT 'regime_v3'
    );
    """
    
    create_indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_market_regime_daily_date ON market_regime_daily(date);
    CREATE INDEX IF NOT EXISTS idx_market_regime_daily_final_regime ON market_regime_daily(final_regime);
    CREATE INDEX IF NOT EXISTS idx_market_regime_daily_version ON market_regime_daily(version);
    """
    
    try:
        conn = sqlite3.connect('snapshots.db')
        cur = conn.cursor()
        
        logger.info("Creating market_regime_daily table...")
        cur.execute(create_table_sql)
        
        logger.info("Creating indexes...")
        cur.executescript(create_indexes_sql)
        
        conn.commit()
        conn.close()
        
        logger.info("market_regime_daily table created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create table: {e}")
        raise

if __name__ == "__main__":
    create_market_regime_daily_table()