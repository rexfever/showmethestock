#!/usr/bin/env python3
"""
DB에서 가격 정보가 없는 종목들을 조회하여 스캔 당시 가격을 채워넣는 스크립트
"""
import os
import sys
import sqlite3
import json
import logging
from typing import List, Tuple, Optional
from kiwoom_api import api

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_db_path():
    """데이터베이스 경로 반환"""
    # 현재 스크립트 위치 기준으로 DB 경로 찾기
    current_file = os.path.abspath(__file__)
    # fill_missing_prices.py가 있는 디렉토리 (backend)에서 찾기
    backend_dir = os.path.dirname(current_file)
    db_path = os.path.join(backend_dir, "snapshots.db")
    
    # 존재하지 않으면 프로젝트 루트에서 찾기
    if not os.path.exists(db_path):
        project_root = os.path.dirname(backend_dir)
        db_path = os.path.join(project_root, "backend", "snapshots.db")
    
    return db_path


def get_missing_price_stocks() -> List[Tuple]:
    """가격 정보가 없는 종목 조회"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # current_price가 0이거나 NULL인 종목 조회
        cursor.execute("""
            SELECT date, code, name, indicators
            FROM scan_rank
            WHERE (current_price IS NULL OR current_price = 0 OR current_price < 1000)
            AND code != 'NORESULT'
            ORDER BY date DESC, code
        """)
        
        rows = cursor.fetchall()
        logger.info(f"가격 정보가 없는 종목: {len(rows)}개")
        return rows
    finally:
        conn.close()


def get_price_from_indicators(indicators_json: str) -> Optional[float]:
    """indicators JSON에서 close 가격 추출"""
    try:
        if not indicators_json:
            return None
        
        indicators = json.loads(indicators_json)
        close_price = indicators.get("close", 0)
        
        if close_price and close_price > 1000:
            return float(close_price)
        
        return None
    except Exception as e:
        logger.debug(f"indicators에서 가격 추출 실패: {e}")
        return None


def get_price_from_api(ticker: str, scan_date: str) -> Optional[float]:
    """KIWOOM API를 사용하여 스캔 날짜 기준 가격 조회"""
    try:
        # 날짜 형식: YYYYMMDD
        date_formatted = scan_date.replace('-', '') if '-' in scan_date else scan_date
        
        # 스캔 날짜 기준으로 OHLCV 데이터 가져오기
        df = api.get_ohlcv(ticker, 1, date_formatted)
        
        if df.empty:
            # 스캔 날짜에서 실패하면 이전 영업일 시도
            import pandas as pd
            try:
                scan_date_dt = pd.to_datetime(date_formatted, format='%Y%m%d')
                for i in range(1, 5):
                    prev_date = (scan_date_dt - pd.tseries.offsets.BDay(i)).strftime('%Y%m%d')
                    df = api.get_ohlcv(ticker, 1, prev_date)
                    if not df.empty:
                        logger.info(f"  이전 영업일({prev_date}) 데이터 사용: {ticker}")
                        break
            except Exception:
                pass
        
        if df.empty:
            return None
        
        # 종가 가져오기
        close_price = float(df.iloc[-1]['close'])
        
        if close_price and close_price > 1000:
            return close_price
        
        return None
    except Exception as e:
        logger.warning(f"API 가격 조회 실패 ({ticker}, {scan_date}): {e}")
        return None


def update_price(date: str, code: str, price: float, volume: Optional[int] = None) -> bool:
    """DB에 가격 정보 업데이트"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        if volume is not None:
            cursor.execute("""
                UPDATE scan_rank
                SET current_price = ?, volume = ?
                WHERE date = ? AND code = ?
            """, (price, volume, date, code))
        else:
            cursor.execute("""
                UPDATE scan_rank
                SET current_price = ?
                WHERE date = ? AND code = ?
            """, (price, date, code))
        
        conn.commit()
        updated = cursor.rowcount > 0
        return updated
    except Exception as e:
        logger.error(f"가격 업데이트 실패 ({code}, {date}): {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def fill_missing_prices(dry_run: bool = False, limit: Optional[int] = None):
    """가격 정보가 없는 종목들의 가격을 채워넣기"""
    logger.info("가격 정보 채우기 시작...")
    
    # 가격이 없는 종목 조회
    missing_stocks = get_missing_price_stocks()
    
    if limit:
        missing_stocks = missing_stocks[:limit]
    
    logger.info(f"처리할 종목 수: {len(missing_stocks)}개")
    
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    for date, code, name, indicators_json in missing_stocks:
        logger.info(f"처리 중: {code} {name} ({date})")
        
        # 1. indicators JSON에서 가격 확인
        price = get_price_from_indicators(indicators_json)
        
        if price:
            logger.info(f"  ✅ indicators에서 가격 발견: {price}원")
            if not dry_run:
                if update_price(date, code, price):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                logger.info(f"  [DRY RUN] 가격 업데이트: {date} {code} {price}원")
                success_count += 1
            continue
        
        # 2. KIWOOM API로 가격 조회
        price = get_price_from_api(code, date)
        
        if price:
            logger.info(f"  ✅ API에서 가격 조회: {price}원")
            if not dry_run:
                if update_price(date, code, price):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                logger.info(f"  [DRY RUN] 가격 업데이트: {date} {code} {price}원")
                success_count += 1
        else:
            logger.warning(f"  ❌ 가격 조회 실패: {code} {name} ({date})")
            fail_count += 1
    
    logger.info(f"\n=== 처리 완료 ===")
    logger.info(f"성공: {success_count}개")
    logger.info(f"실패: {fail_count}개")
    logger.info(f"총 처리: {len(missing_stocks)}개")
    
    if dry_run:
        logger.info("\n⚠️ DRY RUN 모드였습니다. 실제 업데이트를 하려면 --apply 옵션을 사용하세요.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='DB에서 가격 정보가 없는 종목들의 가격을 채워넣기')
    parser.add_argument('--apply', action='store_true', help='실제로 DB를 업데이트 (기본값: dry-run)')
    parser.add_argument('--limit', type=int, help='처리할 최대 종목 수')
    
    args = parser.parse_args()
    
    fill_missing_prices(dry_run=not args.apply, limit=args.limit)

