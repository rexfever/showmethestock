"""Create market_regime_daily table for Global Regime Model v3.

Usage:
    DB_ENGINE=postgres DATABASE_URL=postgresql://user:pass@host/db \
        POSTGRES_DSN=postgresql://user:pass@host/db \
        python backend/migrations/create_market_regime_daily.py
"""

import logging
import os
from pathlib import Path

import psycopg

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def get_dsn() -> str:
    dsn = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("DATABASE_URL or POSTGRES_DSN must be set")
    return dsn

def apply_migration() -> None:
    dsn = get_dsn()
    logger.info("Connecting to PostgreSQL...")
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS market_regime_daily (
        date DATE PRIMARY KEY,
        us_prev_sentiment VARCHAR(20) NOT NULL DEFAULT 'neutral',
        kr_sentiment VARCHAR(20) NOT NULL DEFAULT 'neutral', 
        us_preopen_sentiment VARCHAR(20) NOT NULL DEFAULT 'none',
        final_regime VARCHAR(20) NOT NULL DEFAULT 'neutral',
        us_metrics JSONB,
        kr_metrics JSONB,
        us_preopen_metrics JSONB,
        run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        version VARCHAR(20) NOT NULL DEFAULT 'regime_v3'
    );
    
    CREATE INDEX IF NOT EXISTS idx_market_regime_daily_date ON market_regime_daily(date);
    CREATE INDEX IF NOT EXISTS idx_market_regime_daily_final_regime ON market_regime_daily(final_regime);
    CREATE INDEX IF NOT EXISTS idx_market_regime_daily_version ON market_regime_daily(version);
    """
    
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            logger.info("Creating market_regime_daily table...")
            cur.execute(create_table_sql)
    
    logger.info("market_regime_daily table migration complete.")

if __name__ == "__main__":
    try:
        apply_migration()
    except Exception as exc:
        logger.exception("Migration failed: %s", exc)
        raise