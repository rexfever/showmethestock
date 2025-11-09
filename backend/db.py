"""
PostgreSQL database helper utilities.

This module centralises connection management so that backend services can use
Postgres directly instead of relying on sqlite3 compatibility patches.
"""

from __future__ import annotations

import atexit
from contextlib import contextmanager
from typing import Iterable, Optional, Sequence, Any

from psycopg_pool import ConnectionPool, PoolClosed

from config import config


if not config.database_url:
    raise RuntimeError(
        "DATABASE_URL (or POSTGRES_DSN) is not configured. "
        "Set it in your environment before starting the backend."
    )


_pool = ConnectionPool(
    conninfo=config.database_url,
    min_size=1,
    max_size=10,
)


def close_pool():
    global _pool
    if _pool is not None:
        try:
            _pool.close()
            try:
                _pool.wait()
            except PoolClosed:
                pass
        finally:
            _pool = None


atexit.register(close_pool)


@contextmanager
def get_connection():
    """Yield a pooled psycopg connection."""
    with _pool.connection() as conn:
        yield conn


@contextmanager
def get_cursor(*, commit: bool = False):
    """
    Yield a cursor with automatic commit/rollback.

    Args:
        commit: whether to commit automatically after the with block.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            yield cur
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def fetch_one(query: str, params: Optional[Sequence[Any]] = None):
    with get_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchone()


def fetch_all(query: str, params: Optional[Sequence[Any]] = None):
    with get_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def execute(query: str, params: Optional[Sequence[Any]] = None) -> int:
    with get_cursor(commit=True) as cur:
        cur.execute(query, params)
        return cur.rowcount


def executemany(query: str, param_list: Iterable[Sequence[Any]]) -> int:
    with get_cursor(commit=True) as cur:
        cur.executemany(query, param_list)
        return cur.rowcount


