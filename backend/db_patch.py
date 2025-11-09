"""
sqlite3.connect 패치를 통해 PostgreSQL을 사용할 수 있도록 래퍼 제공.

환경 변수
---------
- DB_ENGINE=postgres : PostgreSQL 사용 여부
- POSTGRES_DSN=postgresql://user:pass@host:port/dbname : psycopg 접속 정보
"""

import os
import sqlite3
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Iterable, Optional, Sequence
import json as json_module
import re

USE_POSTGRES = os.getenv("DB_ENGINE", "sqlite").lower() == "postgres"

if USE_POSTGRES:
    import psycopg
    from psycopg import sql
    from psycopg import errors as pg_errors
    from psycopg.types.json import Json

    # sqlite 호환 예외 정의
    class SQLiteError(Exception):
        pass

    class IntegrityError(SQLiteError):
        pass

    sqlite3.Error = SQLiteError  # type: ignore
    sqlite3.IntegrityError = IntegrityError  # type: ignore

    AUTOINCREMENT_PATTERN = re.compile(r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", re.IGNORECASE)
    BOOL_DEFAULT_ZERO_PATTERN = re.compile(r"BOOLEAN\s+DEFAULT\s+0", re.IGNORECASE)
    BOOL_DEFAULT_ONE_PATTERN = re.compile(r"BOOLEAN\s+DEFAULT\s+1", re.IGNORECASE)
    CURRENT_TIMESTAMP_PATTERN = re.compile(r"DEFAULT\s+CURRENT_TIMESTAMP", re.IGNORECASE)

    def _translate_query(query: str) -> str:
        q = AUTOINCREMENT_PATTERN.sub("SERIAL PRIMARY KEY", query)
        q = BOOL_DEFAULT_ZERO_PATTERN.sub("BOOLEAN DEFAULT FALSE", q)
        q = BOOL_DEFAULT_ONE_PATTERN.sub("BOOLEAN DEFAULT TRUE", q)
        q = CURRENT_TIMESTAMP_PATTERN.sub("DEFAULT NOW()", q)
        return q

    def _convert_qmark(query: str) -> str:
        """SQLite 스타일 '?' 플레이스홀더를 PostgreSQL '%s'로 변환."""
        query = _translate_query(query)
        result = []
        in_single = False
        in_double = False
        escape = False

        for ch in query:
            if escape:
                result.append(ch)
                escape = False
                continue
            if ch == "\\":
                result.append(ch)
                escape = True
                continue
            if ch == "'" and not in_double:
                in_single = not in_single
                result.append(ch)
                continue
            if ch == '"' and not in_single:
                in_double = not in_double
                result.append(ch)
                continue
            if ch == "?" and not in_single and not in_double:
                result.append("%s")
            else:
                result.append(ch)
        return "".join(result)

    def _adapt_params(params: Optional[Sequence[Any]]) -> Sequence[Any]:
        if params is None:
            return ()
        if isinstance(params, (list, tuple)):
            return tuple(
                Json(p) if isinstance(p, (dict, list)) else p
                for p in params
            )
        return (params,)

    class PostgresCursor:
        def __init__(self, connection: "PostgresConnection"):
            self._connection = connection
            self._cursor = connection._conn.cursor()
            self._lastrowid: Optional[int] = None

        @staticmethod
        def _convert_value(value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, bool):
                return value
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(value, date):
                return value.strftime("%Y%m%d")
            if isinstance(value, Decimal):
                return float(value)
            if isinstance(value, (dict, list)):
                return json_module.dumps(value, ensure_ascii=False)
            return value

        def _convert_row(self, row):
            if row is None:
                return None
            return tuple(self._convert_value(v) for v in row)

        def execute(self, query: str, params: Optional[Sequence[Any]] = None):
            try:
                converted = _convert_qmark(query)
                adapted = _adapt_params(params)
                self._cursor.execute(converted, adapted)
                if not converted.lstrip().lower().startswith("insert"):
                    self._lastrowid = None
                else:
                    try:
                        with self._connection._conn.cursor(row_factory=None) as aux:
                            aux.execute(sql.SQL("SELECT LASTVAL()"))
                            res = aux.fetchone()
                            if res:
                                if hasattr(res, "values"):
                                    self._lastrowid = next(iter(res.values()))
                                elif isinstance(res, (list, tuple)):
                                    self._lastrowid = res[0]
                                else:
                                    self._lastrowid = res  # type: ignore[assignment]
                            else:
                                self._lastrowid = None
                    except pg_errors.ObjectNotInPrerequisiteState:
                        self._lastrowid = None
            except pg_errors.UniqueViolation as exc:
                raise IntegrityError(str(exc)) from exc
            except pg_errors.Error as exc:
                raise SQLiteError(str(exc)) from exc
            return self

        def executemany(self, query: str, seq_of_params: Iterable[Sequence[Any]]):
            try:
                converted = _convert_qmark(query)
                seq = [tuple(_adapt_params(params)) for params in seq_of_params]
                self._cursor.executemany(converted, seq)
            except pg_errors.UniqueViolation as exc:
                raise IntegrityError(str(exc)) from exc
            except pg_errors.Error as exc:
                raise SQLiteError(str(exc)) from exc
            self._lastrowid = None
            return self

        def fetchone(self):
            return self._convert_row(self._cursor.fetchone())

        def fetchall(self):
            return [self._convert_row(row) for row in self._cursor.fetchall()]

        def fetchmany(self, size: int = None):
            rows = self._cursor.fetchmany(size)
            return [self._convert_row(row) for row in rows]

        def close(self):
            self._cursor.close()

        @property
        def lastrowid(self) -> Optional[int]:
            return self._lastrowid

        @property
        def rowcount(self) -> int:
            return self._cursor.rowcount

        def __iter__(self):
            return iter(self._cursor)

    class PostgresConnection:
        def __init__(self, dsn: str, *, db_path: str):
            self._conn = psycopg.connect(dsn, autocommit=False)
            self._db_path = db_path
            self.row_factory = None

        def cursor(self):
            return PostgresCursor(self)

        def execute(self, query: str, params: Optional[Sequence[Any]] = None):
            cur = self.cursor()
            cur.execute(query, params)
            return cur

        def executemany(self, query: str, seq_of_params: Iterable[Sequence[Any]]):
            cur = self.cursor()
            cur.executemany(query, seq_of_params)
            return cur

        def commit(self):
            self._conn.commit()

        def rollback(self):
            self._conn.rollback()

        def close(self):
            self._conn.close()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc is None:
                self.commit()
            else:
                self.rollback()
            self.close()

    def _postgres_connect(db_path: str, *args, **kwargs):
        dsn = os.getenv("POSTGRES_DSN")
        if not dsn:
            raise RuntimeError("POSTGRES_DSN 환경 변수를 설정해야 합니다.")
        return PostgresConnection(dsn, db_path=db_path)

    # sqlite3.connect 패치
    _original_connect = sqlite3.connect

    def patched_connect(db_path: str, *args, **kwargs):
        return _postgres_connect(db_path, *args, **kwargs)

    sqlite3.connect = patched_connect  # type: ignore


