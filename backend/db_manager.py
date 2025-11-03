"""데이터베이스 연결 관리자 - 리소스 누수 방지"""
import sqlite3
from contextlib import contextmanager
from typing import Generator

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager로 안전한 DB 연결 관리"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager로 안전한 커서 관리"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

# 전역 인스턴스
db_manager = DatabaseManager('snapshots.db')