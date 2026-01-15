"""
daily_digest 서버 집계 서비스

메인 UX 상단에 노출될 "오늘의 변화(NEW 요약 카드)"를
클라이언트 계산 없이, 서버에서 일관되게 생성한다.
시간 기준은 KST, 추천 확정 규칙(15:35)을 따른다.
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import concurrent.futures
from date_helper import get_kst_now, is_trading_day_kr

from db_manager import db_manager

logger = logging.getLogger(__name__)


def calculate_daily_digest() -> Dict:
    """
    일일 변화 집계 (KST 기준)
    
    집계 규칙:
    - 기준 날짜: todayKST
    - 기준 시각: nowKST
    - 윈도우 구분:
      - PRE_1535: nowKST < 오늘 15:35
      - POST_1535: nowKST >= 오늘 15:35
      - HOLIDAY: 시장 휴장일
    
    집계 항목:
    - 신규 추천 수: anchor_date = todayKST, status IN ('ACTIVE','WEAK_WARNING')
    - 신규 BROKEN 수: status = 'BROKEN', status_changed_at >= todayKST 00:00
    - 신규 ARCHIVED 수: status = 'ARCHIVED', status_changed_at >= todayKST 00:00
    
    Returns:
        {
            "date_kst": "2026-01-01",
            "as_of": "2026-01-01T15:36:00+09:00",
            "window": "POST_1535",
            "new_recommendations": 2,
            "new_broken": 1,
            "new_archived": 3,
            "has_changes": true
        }
    """
    try:
        now_kst = get_kst_now()
        today_kst = now_kst.date()
        today_str = today_kst.strftime('%Y-%m-%d')
        tomorrow_kst = today_kst + timedelta(days=1)
        tomorrow_str = tomorrow_kst.strftime('%Y-%m-%d')
        
        # 윈도우 구분
        is_holiday = not is_trading_day_kr(today_str.replace('-', ''))
        if is_holiday:
            window = "HOLIDAY"
        else:
            # 15:35 기준 확인
            recommendation_time = now_kst.replace(hour=15, minute=35, second=0, microsecond=0)
            if now_kst < recommendation_time:
                window = "PRE_1535"
            else:
                window = "POST_1535"
        
        # 집계 쿼리 실행
        with db_manager.get_cursor(commit=False) as cur:
            # A) 신규 추천 수 및 종목 리스트: anchor_date = todayKST, status IN ('ACTIVE','WEAK_WARNING')
            cur.execute("""
                SELECT COUNT(*)
                FROM recommendations
                WHERE anchor_date = %s
                  AND status IN ('ACTIVE', 'WEAK_WARNING')
                  AND scanner_version = 'v3'
            """, (today_kst,))
            new_recommendations = cur.fetchone()[0] if cur.rowcount > 0 else 0
            
            # A-2) 신규 추천 종목 리스트 (종목명 포함)
            cur.execute("""
                SELECT ticker, name
                FROM recommendations
                WHERE anchor_date = %s
                  AND status IN ('ACTIVE', 'WEAK_WARNING')
                  AND scanner_version = 'v3'
                ORDER BY created_at DESC
            """, (today_kst,))
            new_rows = cur.fetchall()
            new_items = []
            new_tickers_for_name = set()
            for row in new_rows:
                if isinstance(row, dict):
                    ticker = row.get('ticker')
                    name = row.get('name')
                else:
                    ticker = row[0] if len(row) > 0 else None
                    name = row[1] if len(row) > 1 else None
                
                if ticker:
                    new_items.append({
                        'ticker': ticker,
                        'name': name
                    })
                    if not name:
                        new_tickers_for_name.add(ticker)
            
            # 종목명이 없는 경우 조회
            if new_tickers_for_name:
                def fetch_stock_name_new(ticker):
                    """종목명 조회 헬퍼 함수 (신규 추천용)"""
                    try:
                        from pykrx import stock
                        result = stock.get_market_ticker_name(ticker)
                        if isinstance(result, str) and result:
                            return ticker, result
                        elif hasattr(result, 'empty') and not result.empty:
                            if hasattr(result, 'iloc'):
                                name = str(result.iloc[0]) if len(result) > 0 else None
                            elif hasattr(result, 'values'):
                                name = str(result.values[0]) if len(result.values) > 0 else None
                            else:
                                name = None
                            if name:
                                return ticker, name
                    except Exception as e:
                        logger.debug(f"[calculate_daily_digest] pykrx 종목명 조회 실패 (ticker={ticker}): {e}")
                    
                    # pykrx 실패 시 kiwoom_api로 fallback
                    try:
                        from kiwoom_api import api
                        stock_name = api.get_stock_name(ticker)
                        if stock_name:
                            return ticker, stock_name
                    except Exception as e:
                        logger.debug(f"[calculate_daily_digest] kiwoom_api 종목명 조회 실패 (ticker={ticker}): {e}")
                    
                    return ticker, None
                
                # 병렬 처리로 종목명 조회
                max_workers = min(10, len(new_tickers_for_name))
                ticker_to_name_new = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_ticker = {
                        executor.submit(fetch_stock_name_new, ticker): ticker 
                        for ticker in new_tickers_for_name
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_ticker):
                        try:
                            ticker, name = future.result()
                            if name:
                                ticker_to_name_new[ticker] = name
                        except Exception as e:
                            ticker = future_to_ticker[future]
                            logger.debug(f"[calculate_daily_digest] 종목명 조회 오류 (ticker={ticker}): {e}")
                
                # 종목명 업데이트
                for item in new_items:
                    if not item['name'] and item['ticker'] in ticker_to_name_new:
                        item['name'] = ticker_to_name_new[item['ticker']]
            
            # B) 신규 BROKEN 수 및 종목 리스트: status = 'BROKEN', status_changed_at >= todayKST 00:00
            cur.execute("""
                SELECT COUNT(*)
                FROM recommendations
                WHERE status = 'BROKEN'
                  AND status_changed_at >= %s
                  AND status_changed_at < %s
                  AND scanner_version = 'v3'
            """, (today_kst, tomorrow_kst))
            new_broken = cur.fetchone()[0] if cur.rowcount > 0 else 0
            
            # B-2) 신규 BROKEN 종목 리스트 (종목명, reason 포함)
            cur.execute("""
                SELECT ticker, name, reason
                FROM recommendations
                WHERE status = 'BROKEN'
                  AND status_changed_at >= %s
                  AND status_changed_at < %s
                  AND scanner_version = 'v3'
                ORDER BY status_changed_at DESC
            """, (today_kst, tomorrow_kst))
            broken_rows = cur.fetchall()
            broken_items = []
            broken_tickers_for_name = set()
            for row in broken_rows:
                if isinstance(row, dict):
                    ticker = row.get('ticker')
                    name = row.get('name')
                    reason = row.get('reason')
                else:
                    ticker = row[0] if len(row) > 0 else None
                    name = row[1] if len(row) > 1 else None
                    reason = row[2] if len(row) > 2 else None
                
                if ticker:
                    broken_items.append({
                        'ticker': ticker,
                        'name': name,
                        'reason': reason
                    })
                    if not name:
                        broken_tickers_for_name.add(ticker)
            
            # 종목명이 없는 경우 조회
            if broken_tickers_for_name:
                def fetch_stock_name(ticker):
                    """종목명 조회 헬퍼 함수"""
                    try:
                        from pykrx import stock
                        result = stock.get_market_ticker_name(ticker)
                        if isinstance(result, str) and result:
                            return ticker, result
                        elif hasattr(result, 'empty') and not result.empty:
                            if hasattr(result, 'iloc'):
                                name = str(result.iloc[0]) if len(result) > 0 else None
                            elif hasattr(result, 'values'):
                                name = str(result.values[0]) if len(result.values) > 0 else None
                            else:
                                name = None
                            if name:
                                return ticker, name
                    except Exception as e:
                        logger.debug(f"[calculate_daily_digest] pykrx 종목명 조회 실패 (ticker={ticker}): {e}")
                    
                    # pykrx 실패 시 kiwoom_api로 fallback
                    try:
                        from kiwoom_api import api
                        stock_name = api.get_stock_name(ticker)
                        if stock_name:
                            return ticker, stock_name
                    except Exception as e:
                        logger.debug(f"[calculate_daily_digest] kiwoom_api 종목명 조회 실패 (ticker={ticker}): {e}")
                    
                    return ticker, None
                
                # 병렬 처리로 종목명 조회
                max_workers = min(10, len(broken_tickers_for_name))
                ticker_to_name = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_ticker = {
                        executor.submit(fetch_stock_name, ticker): ticker 
                        for ticker in broken_tickers_for_name
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_ticker):
                        try:
                            ticker, name = future.result()
                            if name:
                                ticker_to_name[ticker] = name
                        except Exception as e:
                            ticker = future_to_ticker[future]
                            logger.debug(f"[calculate_daily_digest] 종목명 조회 오류 (ticker={ticker}): {e}")
                
                # 종목명 업데이트
                for item in broken_items:
                    if not item['name'] and item['ticker'] in ticker_to_name:
                        item['name'] = ticker_to_name[item['ticker']]
            
            # C) 신규 ARCHIVED 수: status = 'ARCHIVED', status_changed_at >= todayKST 00:00
            cur.execute("""
                SELECT COUNT(*)
                FROM recommendations
                WHERE status = 'ARCHIVED'
                  AND status_changed_at >= %s
                  AND status_changed_at < %s
                  AND scanner_version = 'v3'
            """, (today_kst, tomorrow_kst))
            new_archived = cur.fetchone()[0] if cur.rowcount > 0 else 0
            
            # D) 신규 WEAK_WARNING 종목 리스트 (오늘 status_changed_at이 변경된 것)
            cur.execute("""
                SELECT ticker, name
                FROM recommendations
                WHERE status = 'WEAK_WARNING'
                  AND status_changed_at >= %s
                  AND status_changed_at < %s
                  AND scanner_version = 'v3'
                ORDER BY status_changed_at DESC
            """, (today_kst, tomorrow_kst))
            weak_warning_rows = cur.fetchall()
            weak_warning_items = []
            weak_warning_tickers_for_name = set()
            for row in weak_warning_rows:
                if isinstance(row, dict):
                    ticker = row.get('ticker')
                    name = row.get('name')
                else:
                    ticker = row[0] if len(row) > 0 else None
                    name = row[1] if len(row) > 1 else None
                
                if ticker:
                    weak_warning_items.append({
                        'ticker': ticker,
                        'name': name
                    })
                    if not name:
                        weak_warning_tickers_for_name.add(ticker)
            
            # 종목명이 없는 경우 조회
            if weak_warning_tickers_for_name:
                def fetch_stock_name_ww(ticker):
                    """종목명 조회 헬퍼 함수 (WEAK_WARNING용)"""
                    try:
                        from pykrx import stock
                        result = stock.get_market_ticker_name(ticker)
                        if isinstance(result, str) and result:
                            return ticker, result
                        elif hasattr(result, 'empty') and not result.empty:
                            if hasattr(result, 'iloc'):
                                name = str(result.iloc[0]) if len(result) > 0 else None
                            elif hasattr(result, 'values'):
                                name = str(result.values[0]) if len(result.values) > 0 else None
                            else:
                                name = None
                            if name:
                                return ticker, name
                    except Exception as e:
                        logger.debug(f"[calculate_daily_digest] pykrx 종목명 조회 실패 (ticker={ticker}): {e}")
                    
                    # pykrx 실패 시 kiwoom_api로 fallback
                    try:
                        from kiwoom_api import api
                        stock_name = api.get_stock_name(ticker)
                        if stock_name:
                            return ticker, stock_name
                    except Exception as e:
                        logger.debug(f"[calculate_daily_digest] kiwoom_api 종목명 조회 실패 (ticker={ticker}): {e}")
                    
                    return ticker, None
                
                # 병렬 처리로 종목명 조회
                max_workers = min(10, len(weak_warning_tickers_for_name))
                ticker_to_name_ww = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_ticker = {
                        executor.submit(fetch_stock_name_ww, ticker): ticker 
                        for ticker in weak_warning_tickers_for_name
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_ticker):
                        try:
                            ticker, name = future.result()
                            if name:
                                ticker_to_name_ww[ticker] = name
                        except Exception as e:
                            ticker = future_to_ticker[future]
                            logger.debug(f"[calculate_daily_digest] 종목명 조회 오류 (ticker={ticker}): {e}")
                
                # 종목명 업데이트
                for item in weak_warning_items:
                    if not item['name'] and item['ticker'] in ticker_to_name_ww:
                        item['name'] = ticker_to_name_ww[item['ticker']]
        
        # has_changes 계산
        has_changes = (new_recommendations > 0) or (new_broken > 0) or (new_archived > 0)
        
        # ISO 8601 형식으로 as_of 생성 (KST)
        as_of = now_kst.strftime('%Y-%m-%dT%H:%M:%S%z')
        # +09:00 형식으로 변환
        if as_of.endswith('+0900'):
            as_of = as_of[:-5] + '+09:00'
        elif as_of.endswith('+09:00'):
            pass
        else:
            # 기본 형식이 아니면 수동으로 생성
            as_of = now_kst.strftime('%Y-%m-%dT%H:%M:%S+09:00')
        
        result = {
            "date_kst": today_str,
            "as_of": as_of,
            "window": window,
            "new_recommendations": new_recommendations,
            "new_items": new_items,  # 신규 추천 종목 리스트 추가
            "new_broken": new_broken,
            "new_archived": new_archived,
            "has_changes": has_changes,
            "broken_items": broken_items,
            "weak_warning_items": weak_warning_items
        }
        
        logger.debug(f"[calculate_daily_digest] 집계 완료: {result}")
        return result
        
    except Exception as e:
        logger.error(f"[calculate_daily_digest] 집계 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 에러 시 기본값 반환
        now_kst = get_kst_now()
        today_str = now_kst.date().strftime('%Y-%m-%d')
        as_of = now_kst.strftime('%Y-%m-%dT%H:%M:%S+09:00')
        return {
            "date_kst": today_str,
            "as_of": as_of,
            "window": "ERROR",
            "new_recommendations": 0,
            "new_items": [],  # 에러 시 빈 배열
            "new_broken": 0,
            "new_archived": 0,
            "has_changes": False,
            "broken_items": [],
            "weak_warning_items": []
        }


