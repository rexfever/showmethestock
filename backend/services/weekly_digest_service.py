"""
weekly_digest 서버 집계 서비스

주간 기준(월~금, KST)으로 신규 추천/종료/재추천을 집계한다.
"""
import logging
from datetime import datetime, timedelta, time, date
from typing import Dict, Optional, List, Any, Set
import concurrent.futures

from date_helper import get_kst_now, KST
from db_manager import db_manager

logger = logging.getLogger(__name__)


def _get_week_range_kst(reference_date: date) -> Dict[str, datetime]:
    """KST 기준 주간 범위(월~금) 계산."""
    week_start = reference_date - timedelta(days=reference_date.weekday())
    week_end = week_start + timedelta(days=4)
    start_dt = KST.localize(datetime.combine(week_start, time.min))
    end_dt = KST.localize(datetime.combine(week_end + timedelta(days=1), time.min))
    return {"start": start_dt, "end": end_dt, "week_start": week_start, "week_end": week_end}


def calculate_weekly_digest(reference_date: Optional[date] = None) -> Dict:
    """
    주간 변화 집계 (KST 기준, 월~금)
    
    집계 항목:
    - 신규 추천: recommendation_state_events reason_code = 'RECOMMEND_CREATED' 또는 'CREATED'
    - 종료: recommendation_state_events to_status = 'ARCHIVED'
    - 재추천: recommendation_state_events reason_code = 'REPEAT_SIGNAL'
    """
    now_kst = get_kst_now()
    ref_date = reference_date or now_kst.date()
    week_range = _get_week_range_kst(ref_date)
    start_dt = week_range["start"]
    end_dt = week_range["end"]
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 신규 추천
            cur.execute("""
                SELECT COUNT(*)
                FROM recommendation_state_events e
                JOIN recommendations r ON r.recommendation_id = e.recommendation_id
                WHERE e.reason_code IN ('RECOMMEND_CREATED', 'CREATED')
                  AND e.to_status = 'ACTIVE'
                  AND e.occurred_at >= %s
                  AND e.occurred_at < %s
                  AND r.scanner_version = 'v3'
            """, (start_dt, end_dt))
            new_recommendations = cur.fetchone()[0] if cur.rowcount > 0 else 0
            
            # 종료
            cur.execute("""
                SELECT COUNT(*)
                FROM recommendation_state_events e
                JOIN recommendations r ON r.recommendation_id = e.recommendation_id
                WHERE e.to_status = 'ARCHIVED'
                  AND e.occurred_at >= %s
                  AND e.occurred_at < %s
                  AND r.scanner_version = 'v3'
            """, (start_dt, end_dt))
            archived = cur.fetchone()[0] if cur.rowcount > 0 else 0
            
            # 재추천
            cur.execute("""
                SELECT COUNT(*)
                FROM recommendation_state_events e
                JOIN recommendations r ON r.recommendation_id = e.recommendation_id
                WHERE e.reason_code = 'REPEAT_SIGNAL'
                  AND e.to_status = 'ACTIVE'
                  AND e.occurred_at >= %s
                  AND e.occurred_at < %s
                  AND r.scanner_version = 'v3'
            """, (start_dt, end_dt))
            repeat_signals = cur.fetchone()[0] if cur.rowcount > 0 else 0
        
        return {
            "week_start": week_range["week_start"].isoformat(),
            "week_end": week_range["week_end"].isoformat(),
            "as_of": now_kst.isoformat(),
            "new_recommendations": new_recommendations,
            "archived": archived,
            "repeat_signals": repeat_signals
        }
    except Exception as e:
        logger.error(f"[calculate_weekly_digest] 주간 집계 오류: {e}", exc_info=True)
        return {
            "week_start": week_range["week_start"].isoformat(),
            "week_end": week_range["week_end"].isoformat(),
            "as_of": now_kst.isoformat(),
            "new_recommendations": 0,
            "archived": 0,
            "repeat_signals": 0,
            "error": str(e)
        }


def _map_rows(rows: List[Any], columns: List[str]) -> List[Dict]:
    mapped = []
    for row in rows:
        if isinstance(row, dict):
            mapped.append({col: row.get(col) for col in columns})
        else:
            mapped.append(dict(zip(columns, row)))
    return mapped


def _collect_missing_name_tickers(items: List[Dict]) -> Set[str]:
    tickers = set()
    for item in items:
        ticker = item.get("ticker")
        name = item.get("name")
        if ticker and (not name or (isinstance(name, str) and not name.strip())):
            tickers.add(ticker)
    return tickers


def _fill_missing_names(cur, items: List[Dict]) -> None:
    tickers = _collect_missing_name_tickers(items)
    if not tickers:
        return
    
    ticker_list = list(tickers)
    ticker_to_name = {}
    
    # 1) recommendations 테이블의 최근 name 우선 사용
    cur.execute("""
        SELECT DISTINCT ON (ticker) ticker, name
        FROM recommendations
        WHERE ticker = ANY(%s)
          AND name IS NOT NULL
          AND name <> ''
        ORDER BY ticker, created_at DESC
    """, (ticker_list,))
    for row in cur.fetchall():
        if isinstance(row, dict):
            ticker_to_name[row.get("ticker")] = row.get("name")
        else:
            ticker_to_name[row[0]] = row[1]
    
    # 2) scan_rank의 최근 name으로 보완
    missing_after_rec = [ticker for ticker in tickers if not ticker_to_name.get(ticker)]
    if missing_after_rec:
        cur.execute("""
            SELECT DISTINCT ON (code) code, name
            FROM scan_rank
            WHERE code = ANY(%s)
              AND name IS NOT NULL
              AND name <> ''
            ORDER BY code, date DESC
        """, (missing_after_rec,))
        for row in cur.fetchall():
            if isinstance(row, dict):
                ticker_to_name[row.get("code")] = row.get("name")
            else:
                ticker_to_name[row[0]] = row[1]

    missing_after_scan = [ticker for ticker in tickers if not ticker_to_name.get(ticker)]
    if missing_after_scan:
        def fetch_stock_name(ticker):
            try:
                from pykrx import stock
                result = stock.get_market_ticker_name(ticker)
                if isinstance(result, str) and result:
                    return ticker, result
                if hasattr(result, 'empty') and not result.empty:
                    if hasattr(result, 'iloc'):
                        name = str(result.iloc[0]) if len(result) > 0 else None
                    elif hasattr(result, 'values'):
                        name = str(result.values[0]) if len(result.values) > 0 else None
                    else:
                        name = None
                    if name:
                        return ticker, name
            except Exception as exc:
                logger.debug(f"[weekly_detail] pykrx 종목명 조회 실패 (ticker={ticker}): {exc}")
            
            try:
                from kiwoom_api import api
                stock_name = api.get_stock_name(ticker)
                if stock_name:
                    return ticker, stock_name
            except Exception as exc:
                logger.debug(f"[weekly_detail] kiwoom_api 종목명 조회 실패 (ticker={ticker}): {exc}")
            
            return ticker, None
        
        max_workers = min(10, len(missing_after_scan))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(fetch_stock_name, ticker): ticker
                for ticker in missing_after_scan
            }
            for future in concurrent.futures.as_completed(future_to_ticker):
                try:
                    ticker, name = future.result()
                    if name:
                        ticker_to_name[ticker] = name
                except Exception as exc:
                    ticker = future_to_ticker[future]
                    logger.debug(f"[weekly_detail] 종목명 조회 오류 (ticker={ticker}): {exc}")
    
    for item in items:
        if item.get("ticker") and (not item.get("name") or (isinstance(item.get("name"), str) and not item.get("name").strip())):
            item["name"] = ticker_to_name.get(item["ticker"]) or item.get("name")


def calculate_weekly_detail(reference_date: Optional[date] = None) -> Dict:
    """
    주간 상세 리스트 (KST 기준, 월~금)
    
    항목:
    - 신규 추천: reason_code IN ('RECOMMEND_CREATED', 'CREATED')
    - 종료: to_status = 'ARCHIVED'
    - 재추천: reason_code = 'REPEAT_SIGNAL'
    """
    now_kst = get_kst_now()
    ref_date = reference_date or now_kst.date()
    week_range = _get_week_range_kst(ref_date)
    start_dt = week_range["start"]
    end_dt = week_range["end"]
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 신규 추천 리스트
            cur.execute("""
                SELECT DISTINCT ON (e.recommendation_id)
                    e.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    e.occurred_at
                FROM recommendation_state_events e
                JOIN recommendations r ON r.recommendation_id = e.recommendation_id
                WHERE e.reason_code IN ('RECOMMEND_CREATED', 'CREATED')
                  AND e.to_status = 'ACTIVE'
                  AND e.occurred_at >= %s
                  AND e.occurred_at < %s
                  AND r.scanner_version = 'v3'
                ORDER BY e.recommendation_id, e.occurred_at DESC
            """, (start_dt, end_dt))
            new_rows = _map_rows(cur.fetchall(), ["recommendation_id", "ticker", "name", "anchor_date", "occurred_at"])
            
            # 종료 리스트
            cur.execute("""
                SELECT DISTINCT ON (e.recommendation_id)
                    e.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    e.occurred_at,
                    e.reason_code
                FROM recommendation_state_events e
                JOIN recommendations r ON r.recommendation_id = e.recommendation_id
                WHERE e.to_status = 'ARCHIVED'
                  AND e.occurred_at >= %s
                  AND e.occurred_at < %s
                  AND r.scanner_version = 'v3'
                ORDER BY e.recommendation_id, e.occurred_at DESC
            """, (start_dt, end_dt))
            archived_rows = _map_rows(cur.fetchall(), ["recommendation_id", "ticker", "name", "anchor_date", "occurred_at", "reason_code"])
            
            # 재추천 리스트
            cur.execute("""
                SELECT DISTINCT ON (e.recommendation_id)
                    e.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    e.occurred_at
                FROM recommendation_state_events e
                JOIN recommendations r ON r.recommendation_id = e.recommendation_id
                WHERE e.reason_code = 'REPEAT_SIGNAL'
                  AND e.to_status = 'ACTIVE'
                  AND e.occurred_at >= %s
                  AND e.occurred_at < %s
                  AND r.scanner_version = 'v3'
                ORDER BY e.recommendation_id, e.occurred_at DESC
            """, (start_dt, end_dt))
            repeat_rows = _map_rows(cur.fetchall(), ["recommendation_id", "ticker", "name", "anchor_date", "occurred_at"])
            
            # 누락된 name 보완
            _fill_missing_names(cur, new_rows)
            _fill_missing_names(cur, archived_rows)
            _fill_missing_names(cur, repeat_rows)
        
        return {
            "week_start": week_range["week_start"].isoformat(),
            "week_end": week_range["week_end"].isoformat(),
            "as_of": now_kst.isoformat(),
            "new_items": new_rows,
            "archived_items": archived_rows,
            "repeat_items": repeat_rows
        }
    except Exception as e:
        logger.error(f"[calculate_weekly_detail] 주간 상세 오류: {e}", exc_info=True)
        return {
            "week_start": week_range["week_start"].isoformat(),
            "week_end": week_range["week_end"].isoformat(),
            "as_of": now_kst.isoformat(),
            "new_items": [],
            "archived_items": [],
            "repeat_items": [],
            "error": str(e)
        }
