"""Extend market_conditions schema with additional metrics fields.

Usage:
    DB_ENGINE=postgres DATABASE_URL=postgresql://user:pass@host/db \
        POSTGRES_DSN=postgresql://user:pass@host/db \
        backend/venv/bin/python backend/migrations/extend_market_conditions.py
"""

import logging
import os
from pathlib import Path

import psycopg


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def load_sql() -> str:
    sql_path = Path(__file__).resolve().parent.parent / "sql" / "market_conditions_extension.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    return sql_path.read_text(encoding="utf-8")


def get_dsn() -> str:
    dsn = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("DATABASE_URL or POSTGRES_DSN must be set")
    return dsn


def apply_migration() -> None:
    sql = load_sql()
    dsn = get_dsn()
    logger.info("Connecting to PostgreSQL...")
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            logger.info("Applying market_conditions extension SQL...")
            cur.execute(sql)
    logger.info("Migration complete.")


if __name__ == "__main__":
    try:
        apply_migration()
    except Exception as exc:
        logger.exception("Migration failed: %s", exc)
        raise
