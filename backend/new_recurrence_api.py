from fastapi import APIRouter, Query
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime, timedelta

from db_manager import db_manager

router = APIRouter()


def _calculate_start_date(days: int) -> str:
    """최근 N일 기준 시작 날짜(YYYYMMDD) 계산"""
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y%m%d")
    return start_date


def _fetch_scan_rows(start_date: str) -> List[Dict[str, Any]]:
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT code, name, date, score, score_label, close_price
            FROM scan_rank
            WHERE date >= %s
            ORDER BY date DESC, score DESC
            """,
            (start_date,),
        )
        rows = cur.fetchall()
    return rows


@router.get("/recurring-stocks")
async def get_recurring_stocks(
    days: int = Query(7, description="최근 몇 일간의 데이터를 확인할지"),
    min_appearances: int = Query(2, description="최소 등장 횟수")
) -> Dict[str, Any]:
    """
    최근 N일간 재등장한 종목들을 조회하는 API
    """
    start_date = _calculate_start_date(days)
    rows = _fetch_scan_rows(start_date)

    stock_appearances = defaultdict(list)
    for row in rows:
        stock_appearances[row["code"]].append({
            'name': row["name"],
            'date': row["date"],
            'score': row["score"],
            'score_label': row["score_label"],
            'close_price': row["close_price"]
        })

    recurring_stocks = {}
    for code, appearances in stock_appearances.items():
        if len(appearances) >= min_appearances:
            recurring_stocks[code] = {
                'name': appearances[0]['name'],
                'appear_count': len(appearances),
                'appearances': appearances,
                'latest_score': appearances[0]['score'],
                'latest_date': appearances[0]['date']
            }

    return {
        "ok": True,
        "data": {
            "recurring_stocks": recurring_stocks,
            "total_count": len(recurring_stocks),
            "days": days,
            "min_appearances": min_appearances
        }
    }


@router.get("/scan-with-recurring")
async def get_scan_with_recurring(
    days: int = Query(7, description="재등장 확인 기간"),
    min_appearances: int = Query(2, description="최소 등장 횟수")
) -> Dict[str, Any]:
    """
    최신 스캔 결과와 재등장 종목을 함께 조회하는 API
    """
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute("SELECT MAX(date) AS latest_date FROM scan_rank")
        latest_row = cur.fetchone()
        latest_date = latest_row["latest_date"] if latest_row else None

    latest_scan: List[Dict[str, Any]] = []
    if latest_date:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute(
                """
                SELECT code, name, score, score_label, close_price
                FROM scan_rank
                WHERE date = %s
                ORDER BY score DESC
                """,
                (latest_date,),
            )
            latest_rows = cur.fetchall()
            latest_scan = [
                {
                    "code": row["code"],
                    "name": row["name"],
                    "score": row["score"],
                    "score_label": row["score_label"],
                    "close_price": row["close_price"]
                }
                for row in latest_rows
            ]

    start_date = _calculate_start_date(days)
    rows = _fetch_scan_rows(start_date)

    stock_appearances = defaultdict(list)
    for row in rows:
        stock_appearances[row["code"]].append({
            'name': row["name"],
            'date': row["date"],
            'score': row["score"],
            'score_label': row["score_label"],
            'close_price': row["close_price"]
        })

    recurring_stocks = {}
    for code, appearances in stock_appearances.items():
        if len(appearances) >= min_appearances:
            recurring_stocks[code] = {
                'name': appearances[0]['name'],
                'appear_count': len(appearances),
                'appearances': appearances,
                'latest_score': appearances[0]['score'],
                'latest_date': appearances[0]['date']
            }

    return {
        "ok": True,
        "data": {
            "latest_scan": {
                "date": latest_date,
                "stocks": latest_scan
            },
            "recurring_stocks": recurring_stocks,
            "total_recurring": len(recurring_stocks)
        }
    }
