from fastapi import APIRouter, Query
from typing import Dict, Any, Optional
import sqlite3
from collections import defaultdict

router = APIRouter()

@router.get("/recurring-stocks")
async def get_recurring_stocks(
    days: int = Query(7, description="최근 몇 일간의 데이터를 확인할지"),
    min_appearances: int = Query(2, description="최소 등장 횟수")
) -> Dict[str, Any]:
    """
    최근 N일간 재등장한 종목들을 조회하는 API
    
    Args:
        days: 최근 몇 일간의 데이터를 확인할지 (기본값: 7)
        min_appearances: 최소 등장 횟수 (기본값: 2)
    
    Returns:
        재등장 종목 정보
    """
    conn = sqlite3.connect('snapshots.db')
    cur = conn.cursor()
    
    # 최근 N일간의 스캔 결과 조회 (파라미터화된 쿼리)
    query = """
    SELECT code, name, date, score, score_label, close_price
    FROM scan_rank 
    WHERE date >= date('now', '-' || ? || ' days')
    ORDER BY date DESC, score DESC
    """
    
    cur.execute(query, (days,))
    results = cur.fetchall()
    conn.close()
    
    # 종목별 등장 횟수 계산
    stock_appearances = defaultdict(list)
    for row in results:
        code, name, date, score, score_label, close_price = row
        stock_appearances[code].append({
            'name': name,
            'date': date,
            'score': score,
            'score_label': score_label,
            'close_price': close_price
        })
    
    # 재등장 종목 필터링
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
    # 최신 스캔 결과 조회
    conn = sqlite3.connect('snapshots.db')
    cur = conn.cursor()
    
    # 최신 스캔 날짜 조회
    cur.execute("SELECT MAX(date) FROM scan_rank")
    latest_date = cur.fetchone()[0]
    
    # 최신 스캔 결과 조회
    cur.execute("""
        SELECT code, name, score, score_label, close_price
        FROM scan_rank 
        WHERE date = ?
        ORDER BY score DESC
    """, (latest_date,))
    
    latest_scan = cur.fetchall()
    
    # 재등장 종목 조회 (파라미터화된 쿼리)
    recurring_query = """
    SELECT code, name, date, score, score_label, close_price
    FROM scan_rank 
    WHERE date >= date('now', '-' || ? || ' days')
    ORDER BY date DESC, score DESC
    """
    
    cur.execute(recurring_query, (days,))
    results = cur.fetchall()
    conn.close()
    
    # 종목별 등장 횟수 계산
    stock_appearances = defaultdict(list)
    for row in results:
        code, name, date, score, score_label, close_price = row
        stock_appearances[code].append({
            'name': name,
            'date': date,
            'score': score,
            'score_label': score_label,
            'close_price': close_price
        })
    
    # 재등장 종목 필터링
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
