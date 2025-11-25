"""
Global Regime Model v3 데이터 저장/로드 서비스 (SQLite용)
"""
import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def yyyymmdd_to_date(s: str) -> str:
    """YYYYMMDD -> YYYY-MM-DD 변환"""
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"

def date_to_yyyymmdd(s: str) -> str:
    """YYYY-MM-DD -> YYYYMMDD 변환"""
    return s.replace("-", "")

def get_connection():
    """SQLite 연결 반환"""
    conn = sqlite3.connect('snapshots.db')
    conn.row_factory = sqlite3.Row
    return conn

def save_regime(date: str, data: dict) -> None:
    """
    date (= 'YYYYMMDD') 를 기준으로 market_regime_daily 에 한 건 insert.
    이미 있으면 에러 발생.
    """
    try:
        # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
        formatted_date = yyyymmdd_to_date(date)
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO market_regime_daily (
                date, us_prev_sentiment, kr_sentiment, us_preopen_sentiment,
                final_regime, us_metrics, kr_metrics, us_preopen_metrics, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            formatted_date,
            data.get('us_prev_regime', 'neutral'),
            data.get('kr_regime', 'neutral'), 
            data.get('us_preopen_flag', 'none'),
            data.get('final_regime', 'neutral'),
            json.dumps(data.get('us_metrics', {})),
            json.dumps(data.get('kr_metrics', {})),
            json.dumps(data.get('us_preopen_metrics', {})),
            'regime_v3'
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"장세 데이터 저장 완료: {date} -> {data.get('final_regime')}")
    except Exception as e:
        logger.error(f"장세 데이터 저장 실패 ({date}): {e}")
        raise

def load_regime(date: str) -> Optional[dict]:
    """
    주어진 date 에 해당하는 장세 레코드를 market_regime_daily 에서 읽어
    dict 형태로 반환. 없으면 None.
    """
    try:
        # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
        formatted_date = yyyymmdd_to_date(date)
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT us_prev_sentiment, kr_sentiment, us_preopen_sentiment,
                   final_regime, us_metrics, kr_metrics, us_preopen_metrics
            FROM market_regime_daily 
            WHERE date = ? AND version = 'regime_v3'
        """, (formatted_date,))
        
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'us_prev_regime': row['us_prev_sentiment'],
            'kr_regime': row['kr_sentiment'],
            'us_preopen_flag': row['us_preopen_sentiment'],
            'final_regime': row['final_regime'],
            'us_metrics': json.loads(row['us_metrics']) if row['us_metrics'] else {},
            'kr_metrics': json.loads(row['kr_metrics']) if row['kr_metrics'] else {},
            'us_preopen_metrics': json.loads(row['us_preopen_metrics']) if row['us_preopen_metrics'] else {}
        }
    except Exception as e:
        logger.error(f"장세 데이터 로드 실패 ({date}): {e}")
        return None

def upsert_regime(date: str, data: dict) -> None:
    """
    date 기준으로 있으면 update, 없으면 insert.
    """
    try:
        # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
        formatted_date = yyyymmdd_to_date(date)
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT OR REPLACE INTO market_regime_daily (
                date, us_prev_sentiment, kr_sentiment, us_preopen_sentiment,
                final_regime, us_metrics, kr_metrics, us_preopen_metrics, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            formatted_date,
            data.get('us_prev_regime', 'neutral'),
            data.get('kr_regime', 'neutral'),
            data.get('us_preopen_flag', 'none'),
            data.get('final_regime', 'neutral'),
            json.dumps(data.get('us_metrics', {})),
            json.dumps(data.get('kr_metrics', {})),
            json.dumps(data.get('us_preopen_metrics', {})),
            'regime_v3'
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"장세 데이터 upsert 완료: {date} -> {data.get('final_regime')}")
    except Exception as e:
        logger.error(f"장세 데이터 upsert 실패 ({date}): {e}")
        raise