"""데이터베이스 연결 관리자 - 리소스 누수 방지"""
from contextlib import contextmanager
from typing import Generator

from psycopg import Connection, Cursor

from db import get_connection


class DatabaseManager:
    """Backward-compatible wrapper around the new PostgreSQL helper."""

    @contextmanager
    def get_connection(self) -> Generator[Connection, None, None]:
        with get_connection() as conn:
            yield conn
    
    @contextmanager
    def get_cursor(self, *, commit: bool = True) -> Generator[Cursor, None, None]:
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as exc:
                conn.rollback()
                raise exc
            finally:
                cursor.close()


# 전역 인스턴스 (경로 인자 불필요, 호환성 유지)
db_manager = DatabaseManager()