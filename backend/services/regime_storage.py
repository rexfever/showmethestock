"""
Global Regime Model v3 데이터 저장/로드 서비스
"""
import json
import logging
from datetime import datetime
from typing import Dict, Optional

from db_manager import db_manager

logger = logging.getLogger(__name__)

def yyyymmdd_to_date(s: str) -> str:
    """YYYYMMDD -> YYYY-MM-DD 변환"""
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"

def date_to_yyyymmdd(s: str) -> str:
    """YYYY-MM-DD -> YYYYMMDD 변환"""
    return s.replace("-", "")

def save_regime(date: str, data: dict) -> None:
    """
    date (= 'YYYYMMDD') 를 기준으로 market_regime_daily 에 한 건 insert.
    이미 있으면 에러 발생.
    """
    try:
        # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
        formatted_date = yyyymmdd_to_date(date)
        
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO market_regime_daily (
                    date, us_prev_sentiment, kr_sentiment, us_preopen_sentiment,
                    final_regime, us_metrics, kr_metrics, us_preopen_metrics, version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT us_prev_sentiment, kr_sentiment, us_preopen_sentiment,
                       final_regime, us_metrics, kr_metrics, us_preopen_metrics
                FROM market_regime_daily 
                WHERE date = %s AND version = 'regime_v3'
            """, (formatted_date,))
            
            row = cur.fetchone()
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
        
        # v4 데이터인지 확인
        is_v4 = data.get('version') == 'regime_v4'
        
        with db_manager.get_cursor(commit=True) as cur:
            if is_v4:
                # v4 필드 포함 upsert
                cur.execute("""
                    INSERT INTO market_regime_daily (
                        date, us_prev_sentiment, kr_sentiment, us_preopen_sentiment,
                        final_regime, us_metrics, kr_metrics, us_preopen_metrics, 
                        us_futures_score, us_futures_regime, dxy, version, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date) DO UPDATE SET
                        us_prev_sentiment = EXCLUDED.us_prev_sentiment,
                        kr_sentiment = EXCLUDED.kr_sentiment,
                        us_preopen_sentiment = EXCLUDED.us_preopen_sentiment,
                        final_regime = EXCLUDED.final_regime,
                        us_metrics = EXCLUDED.us_metrics,
                        kr_metrics = EXCLUDED.kr_metrics,
                        us_preopen_metrics = EXCLUDED.us_preopen_metrics,
                        us_futures_score = EXCLUDED.us_futures_score,
                        us_futures_regime = EXCLUDED.us_futures_regime,
                        dxy = EXCLUDED.dxy,
                        version = EXCLUDED.version,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    formatted_date,
                    data.get('us_prev_regime', 'neutral'),
                    data.get('kr_regime', 'neutral'),
                    data.get('us_preopen_flag', 'none'),
                    data.get('final_regime', 'neutral'),
                    json.dumps(data.get('us_metrics', {})),
                    json.dumps(data.get('kr_metrics', {})),
                    json.dumps(data.get('us_preopen_metrics', {})),
                    data.get('us_futures_score', 0.0),
                    data.get('us_futures_regime', 'neutral'),
                    data.get('dxy', 0.0),
                    'regime_v4',
                    datetime.now()
                ))
            else:
                # v3 호환 upsert
                cur.execute("""
                    INSERT INTO market_regime_daily (
                        date, us_prev_sentiment, kr_sentiment, us_preopen_sentiment,
                        final_regime, us_metrics, kr_metrics, us_preopen_metrics, version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date) DO UPDATE SET
                        us_prev_sentiment = EXCLUDED.us_prev_sentiment,
                        kr_sentiment = EXCLUDED.kr_sentiment,
                        us_preopen_sentiment = EXCLUDED.us_preopen_sentiment,
                        final_regime = EXCLUDED.final_regime,
                        us_metrics = EXCLUDED.us_metrics,
                        kr_metrics = EXCLUDED.kr_metrics,
                        us_preopen_metrics = EXCLUDED.us_preopen_metrics,
                        run_timestamp = CURRENT_TIMESTAMP
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
        logger.info(f"장세 데이터 upsert 완료: {date} -> {data.get('final_regime')} ({data.get('version', 'v3')})")
    except Exception as e:
        logger.error(f"장세 데이터 upsert 실패 ({date}): {e}")
        raise