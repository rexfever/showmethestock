"""
SQLite → PostgreSQL 데이터 마이그레이션 스크립트 (초안)

Step 2: 스키마 이식 준비용으로 기본 구조만 마련한다.

실행 전 준비사항
----------------
1. psycopg 설치
   pip install psycopg[binary]

2. .env 혹은 환경 변수 설정
   POSTGRES_DSN=postgresql://user:password@localhost:5432/stockfinder

3. PostgreSQL에 schema 파일 적용
   psql -d stockfinder -f backend/sql/postgres_schema.sql
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Callable, Iterable, List, Optional, Sequence, Tuple, Any

import json

import psycopg
from psycopg import sql
from psycopg.types.json import Json

# SQLite 파일 경로
SQLITE_DATABASES = {
    "snapshots": "backend/snapshots.db",
    "portfolio": "backend/portfolio.db",
    "email_verifications": "backend/email_verifications.db",
    "news_data": "backend/news_data.db",
}


@dataclass
class TableCopyPlan:
    sqlite_db: str
    sqlite_table: str
    postgres_table: str
    column_mapping: Optional[List[str]] = None  # 타겟 컬럼 순서
    transform_row: Optional[Callable[[sqlite3.Row], Sequence[Any]]] = None
    conflict_target: Optional[List[str]] = None


COPY_PLANS: List[TableCopyPlan] = [
    TableCopyPlan(
        "snapshots",
        "users",
        "users",
        column_mapping=[
            "id",
            "email",
            "phone",
            "notification_enabled",
            "name",
            "provider",
            "provider_id",
            "membership_tier",
            "subscription_status",
            "subscription_expires_at",
            "payment_method",
            "is_admin",
            "last_login",
            "is_active",
            "password_hash",
            "is_email_verified",
            "created_at",
            "updated_at",
        ],
        transform_row=lambda row: (
            row["id"],
            row["email"],
            row["phone"],
            parse_bool(row["notification_enabled"]),
            row["name"],
            row["provider"] or "local",
            row["provider_id"],
            row["membership_tier"] or "free",
            row["subscription_status"] or "active",
            parse_timestamp(row["subscription_expires_at"]),
            row["payment_method"],
            parse_bool(row["is_admin"]),
            parse_timestamp(row["last_login"]),
            parse_bool(row["is_active"], default=True),
            row["password_hash"],
            parse_bool(row["is_email_verified"]),
            parse_timestamp(row["created_at"]),
            parse_timestamp(row["updated_at"]),
        ),
    ),
    TableCopyPlan(
        "snapshots",
        "subscriptions",
        "subscriptions",
        column_mapping=[
            "id",
            "user_id",
            "plan_id",
            "payment_id",
            "amount",
            "status",
            "started_at",
            "expires_at",
            "cancelled_at",
            "created_at",
        ],
        transform_row=lambda row: (
            row["id"],
            row["user_id"],
            row["plan_id"],
            row["payment_id"],
            parse_decimal(row["amount"]),
            row["status"] or "active",
            parse_timestamp(row["started_at"]),
            parse_timestamp(row["expires_at"]),
            parse_timestamp(row["cancelled_at"]),
            parse_timestamp(row["created_at"]),
        ),
    ),
    TableCopyPlan(
        "snapshots",
        "payments",
        "payments",
        column_mapping=[
            "id",
            "user_id",
            "subscription_id",
            "payment_id",
            "amount",
            "method",
            "status",
            "created_at",
        ],
        transform_row=lambda row: (
            row["id"],
            row["user_id"],
            row["subscription_id"],
            row["payment_id"],
            parse_decimal(row["amount"]),
            row["method"],
            row["status"],
            parse_timestamp(row["created_at"]),
        ),
    ),
    TableCopyPlan(
        "snapshots",
        "maintenance_settings",
        "maintenance_settings",
        column_mapping=[
            "id",
            "is_enabled",
            "end_date",
            "message",
            "created_at",
            "updated_at",
        ],
        transform_row=lambda row: (
            row["id"],
            parse_bool(row["is_enabled"]),
            parse_timestamp(row["end_date"]),
            row["message"] or "서비스 점검 중입니다.",
            parse_timestamp(row["created_at"]),
            parse_timestamp(row["updated_at"]),
        ),
    ),
    TableCopyPlan(
        "snapshots",
        "popup_notice",
        "popup_notice",
        column_mapping=[
            "id",
            "is_enabled",
            "title",
            "message",
            "start_date",
            "end_date",
            "created_at",
            "updated_at",
        ],
        transform_row=lambda row: (
            row["id"],
            parse_bool(row["is_enabled"]),
            row["title"],
            row["message"],
            parse_timestamp(row["start_date"]),
            parse_timestamp(row["end_date"]),
            parse_timestamp(row["created_at"]),
            parse_timestamp(row["updated_at"]),
        ),
    ),
    TableCopyPlan(
        "snapshots",
        "market_conditions",
        "market_conditions",
        column_mapping=[
            "date",
            "market_sentiment",
            "kospi_return",
            "volatility",
            "rsi_threshold",
            "sector_rotation",
            "foreign_flow",
            "volume_trend",
            "min_signals",
            "macd_osc_min",
            "vol_ma5_mult",
            "gap_max",
            "ext_from_tema20_max",
            "created_at",
        ],
        transform_row=lambda row: (
            parse_date(row["date"]),
            row["market_sentiment"],
            parse_float(row["kospi_return"]),
            parse_float(row["volatility"]),
            parse_float(row["rsi_threshold"]),
            row["sector_rotation"],
            row["foreign_flow"],
            row["volume_trend"],
            row["min_signals"],
            parse_float(row["macd_osc_min"]),
            parse_float(row["vol_ma5_mult"]),
            parse_float(row["gap_max"]),
            parse_float(row["ext_from_tema20_max"]),
            parse_timestamp(row["created_at"]),
        ),
    ),
    TableCopyPlan(
        "snapshots",
        "send_logs",
        "send_logs",
        column_mapping=[
            "ts",
            "to_no",
            "matched_count",
        ],
        transform_row=lambda row: (
            parse_timestamp(row["ts"]),
            row["to_no"],
            row["matched_count"],
        ),
    ),
    TableCopyPlan(
        "snapshots",
        "positions",
        "positions",
        column_mapping=[
            "id",
            "ticker",
            "name",
            "entry_date",
            "quantity",
            "score",
            "strategy",
            "current_return_pct",
            "max_return_pct",
            "exit_date",
            "status",
            "created_at",
            "updated_at",
        ],
        transform_row=lambda row: (
            row["id"],
            row["ticker"],
            row["name"],
            parse_date(row["entry_date"]),
            row["quantity"],
            row["score"],
            row["strategy"],
            parse_float(row["current_return_pct"]),
            parse_float(row["max_return_pct"]),
            parse_date(row["exit_date"]),
            row["status"] or "open",
            parse_timestamp(row["created_at"]),
            parse_timestamp(row["updated_at"]),
        ),
    ),
    TableCopyPlan(
        "snapshots",
        "scan_rank",
        "scan_rank",
        column_mapping=[
            "date",
            "code",
            "name",
            "score",
            "score_label",
            "current_price",
            "close_price",
            "volume",
            "change_rate",
            "market",
            "strategy",
            "indicators",
            "trend",
            "flags",
            "details",
            "returns",
            "recurrence",
            "created_at",
        ],
        conflict_target=["date", "code"],
        transform_row=lambda row: (
            parse_date(row["date"]),
            row["code"],
            row["name"],
            parse_float(row["score"]),
            row["score_label"],
            parse_float(row["current_price"]),
            parse_float(row["close_price"]),
            parse_bigint(row["volume"]),
            parse_float(row["change_rate"]),
            row["market"],
            row["strategy"],
            parse_json(row["indicators"]),
            row["trend"],
            row["flags"],
            parse_json(row["details"]),
            parse_json(row["returns"]),
            parse_json(row["recurrence"]),
            parse_timestamp(row["created_at"]) or datetime.utcnow(),
        ),
    ),
    TableCopyPlan(
        "portfolio",
        "portfolio",
        "portfolio",
        column_mapping=[
            "id",
            "user_id",
            "ticker",
            "name",
            "entry_price",
            "quantity",
            "entry_date",
            "current_price",
            "total_investment",
            "current_value",
            "profit_loss",
            "profit_loss_pct",
            "status",
            "source",
            "recommendation_score",
            "recommendation_date",
            "daily_return_pct",
            "max_return_pct",
            "min_return_pct",
            "holding_days",
            "created_at",
            "updated_at",
        ],
        transform_row=lambda row: (
            row["id"],
            row["user_id"],
            row["ticker"],
            row["name"],
            parse_float(row["entry_price"]),
            row["quantity"],
            parse_date(row["entry_date"]),
            parse_float(row["current_price"]),
            parse_float(row["total_investment"]),
            parse_float(row["current_value"]),
            parse_float(row["profit_loss"]),
            parse_float(row["profit_loss_pct"]),
            row["status"] or "watching",
            row["source"] or "recommended",
            row["recommendation_score"],
            parse_date(row["recommendation_date"]),
            parse_float(row["daily_return_pct"]),
            parse_float(row["max_return_pct"]),
            parse_float(row["min_return_pct"]),
            row["holding_days"],
            parse_timestamp(row["created_at"]),
            parse_timestamp(row["updated_at"]),
        ),
    ),
    TableCopyPlan(
        "portfolio",
        "trading_history",
        "trading_history",
        column_mapping=[
            "id",
            "user_id",
            "ticker",
            "name",
            "trade_type",
            "quantity",
            "price",
            "trade_date",
            "notes",
            "created_at",
            "updated_at",
        ],
        transform_row=lambda row: (
            row["id"],
            row["user_id"],
            row["ticker"],
            row["name"],
            row["trade_type"],
            row["quantity"],
            parse_float(row["price"]),
            parse_date(row["trade_date"]),
            row["notes"],
            parse_timestamp(row["created_at"]),
            parse_timestamp(row["updated_at"]),
        ),
    ),
    TableCopyPlan(
        "email_verifications",
        "email_verifications",
        "email_verifications",
        column_mapping=[
            "id",
            "email",
            "verification_code",
            "verification_type",
            "is_verified",
            "created_at",
            "expires_at",
        ],
        transform_row=lambda row: (
            row["id"],
            row["email"],
            row["verification_code"],
            row["verification_type"] or "signup",
            parse_bool(row["is_verified"]),
            parse_timestamp(row["created_at"]),
            parse_timestamp(row["expires_at"]),
        ),
    ),
    TableCopyPlan(
        "news_data",
        "news_data",
        "news_data",
        column_mapping=[
            "id",
            "ticker",
            "title",
            "content",
            "source",
            "published_at",
            "sentiment_score",
            "relevance_score",
            "created_at",
        ],
        transform_row=lambda row: (
            row["id"],
            row["ticker"],
            row["title"],
            row["content"],
            row["source"],
            parse_timestamp(row["published_at"]),
            parse_float(row["sentiment_score"]),
            parse_float(row["relevance_score"]),
            parse_timestamp(row["created_at"]),
        ),
    ),
    TableCopyPlan(
        "news_data",
        "search_trends",
        "search_trends",
        column_mapping=[
            "id",
            "ticker",
            "search_volume",
            "trend_score",
            "date",
            "source",
            "created_at",
        ],
        transform_row=lambda row: (
            row["id"],
            row["ticker"],
            row["search_volume"],
            parse_float(row["trend_score"]),
            parse_date(row["date"]),
            row["source"],
            parse_timestamp(row["created_at"]),
        ),
    ),
]

SERIAL_TABLES = {
    "users": "id",
    "subscriptions": "id",
    "payments": "id",
    "maintenance_settings": "id",
    "popup_notice": "id",
    "positions": "id",
    "portfolio": "id",
    "trading_history": "id",
    "email_verifications": "id",
    "news_data": "id",
    "search_trends": "id",
}


def parse_bool(value, *, default: bool = False) -> Optional[bool]:
    if value is None:
        return default if default is not None else None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y"}:
        return True
    if text in {"0", "false", "f", "no", "n"}:
        return False
    return default


def parse_timestamp(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("T", " ").replace("Z", "+00:00")
    try:
        if "+" in text[10:]:
            return datetime.fromisoformat(text)
        if "." in text:
            return datetime.strptime(text, "%Y-%m-%d %H:%M:%S.%f")
        if len(text) == 19:
            return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(text, "%Y%m%d%H%M%S")
        except ValueError:
            return None


def parse_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        if len(text) == 8 and text.isdigit():
            return datetime.strptime(text, "%Y%m%d").date()
        if len(text) == 10 and text[4] in {"-", "/"}:
            fmt = "%Y-%m-%d" if "-" in text else "%Y/%m/%d"
            return datetime.strptime(text, fmt).date()
        if len(text) == 19:
            return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").date()
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def parse_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).strip()
    if not text:
        return None
    return Decimal(text)


def parse_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_bigint(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_json(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return Json(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return Json(json.loads(text))
    except json.JSONDecodeError:
        return None


def get_postgres_connection() -> psycopg.Connection:
    dsn = os.environ.get("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("POSTGRES_DSN 환경 변수를 설정하세요.")
    return psycopg.connect(dsn)


def copy_table(plan: TableCopyPlan, conn_pg: psycopg.Connection) -> None:
    sqlite_path = SQLITE_DATABASES.get(plan.sqlite_db)
    if not sqlite_path:
        raise ValueError(f"정의되지 않은 SQLite DB 별칭: {plan.sqlite_db}")

    with sqlite3.connect(sqlite_path) as conn_sqlite:
        conn_sqlite.row_factory = sqlite3.Row
        cur_sqlite = conn_sqlite.cursor()
        rows = cur_sqlite.execute(f"SELECT * FROM {plan.sqlite_table}").fetchall()

    if not rows:
        print(f"[SKIP] {plan.sqlite_table}: 데이터 없음")
        return

    column_list = plan.column_mapping or rows[0].keys()
    if plan.conflict_target:
        conflict_clause = sql.SQL(" ON CONFLICT ({cols}) DO NOTHING").format(
            cols=sql.SQL(", ").join(sql.Identifier(c) for c in plan.conflict_target)
        )
    else:
        conflict_clause = sql.SQL("")

    total = 0
    with conn_pg.cursor() as cur_pg:
        for row in rows:
            if plan.transform_row is not None:
                values = plan.transform_row(row)
            else:
                values = tuple(row[col] for col in column_list)
            query = sql.SQL("INSERT INTO {table} ({cols}) VALUES ({placeholders}){conflict}").format(
                table=sql.Identifier(plan.postgres_table),
                cols=sql.SQL(", ").join(sql.Identifier(col) for col in column_list),
                placeholders=sql.SQL(", ").join(sql.Placeholder() for _ in column_list),
                conflict=conflict_clause,
            )
            cur_pg.execute(query, values)
            if cur_pg.rowcount:
                total += 1
    conn_pg.commit()

    if plan.postgres_table in SERIAL_TABLES:
        reset_sequence(conn_pg, plan.postgres_table, SERIAL_TABLES[plan.postgres_table])

    print(f"[DONE] {plan.sqlite_table} → {plan.postgres_table} ({total} rows)")


def reset_sequence(conn_pg: psycopg.Connection, table: str, pk_column: str) -> None:
    with conn_pg.cursor() as cur:
        query = sql.SQL(
            "SELECT setval(pg_get_serial_sequence({table_literal}, {pk_literal}), "
            "COALESCE(MAX({pk_ident}), 1)) FROM {table_ident}"
        ).format(
            table_literal=sql.Literal(table),
            pk_literal=sql.Literal(pk_column),
            pk_ident=sql.Identifier(pk_column),
            table_ident=sql.Identifier(table),
        )
        cur.execute(query)
    conn_pg.commit()


def main():
    with get_postgres_connection() as conn_pg:
        for plan in COPY_PLANS:
            copy_table(plan, conn_pg)


if __name__ == "__main__":
    main()

