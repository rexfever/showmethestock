"""
Regime v4 필드 추가 마이그레이션
"""
import logging
import os
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
    
    migration_sql = """
    -- Regime v4 필드 추가
    ALTER TABLE market_regime_daily 
    ADD COLUMN IF NOT EXISTS us_futures_score FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS us_futures_regime VARCHAR(20) DEFAULT 'neutral',
    ADD COLUMN IF NOT EXISTS dxy FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    
    -- 인덱스 추가
    CREATE INDEX IF NOT EXISTS idx_market_regime_daily_us_futures_regime 
    ON market_regime_daily(us_futures_regime);
    
    CREATE INDEX IF NOT EXISTS idx_market_regime_daily_updated_at 
    ON market_regime_daily(updated_at);
    """
    
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            logger.info("Adding Regime v4 fields...")
            cur.execute(migration_sql)
    
    logger.info("Regime v4 migration complete.")

if __name__ == "__main__":
    try:
        apply_migration()
    except Exception as exc:
        logger.exception("Migration failed: %s", exc)
        raise