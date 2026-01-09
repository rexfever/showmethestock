"""
기존 ARCHIVED 추천 중 archive_return_pct가 없는 항목 업데이트
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from kiwoom_api import api
from date_helper import get_kst_now
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_missing_archive_return_pct():
    """archive_return_pct가 없는 ARCHIVED 추천 업데이트"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # archive_return_pct가 없는 ARCHIVED 추천 조회
            cur.execute("""
                SELECT recommendation_id, ticker, name, anchor_date, anchor_close, archived_at
                FROM recommendations
                WHERE status = 'ARCHIVED'
                AND scanner_version = 'v3'
                AND (archive_return_pct IS NULL OR archive_reason IS NULL)
                ORDER BY created_at DESC
            """)
            
            rows = cur.fetchall()
            logger.info(f"업데이트 대상: {len(rows)}개")
            
            if not rows:
                logger.info("업데이트할 항목이 없습니다.")
                return
            
            updated_count = 0
            failed_count = 0
            
            today_str = get_kst_now().strftime('%Y%m%d')
            
            for row in rows:
                if isinstance(row, dict):
                    rec_id = row.get('recommendation_id')
                    ticker = row.get('ticker')
                    name = row.get('name')
                    anchor_date = row.get('anchor_date')
                    anchor_close = row.get('anchor_close')
                    archived_at = row.get('archived_at')
                else:
                    rec_id = row[0]
                    ticker = row[1]
                    name = row[2]
                    anchor_date = row[3]
                    anchor_close = row[4]
                    archived_at = row[5] if len(row) > 5 else None
                
                if not ticker or not anchor_close or anchor_close <= 0:
                    logger.warning(f"스킵: {ticker} ({name}) - anchor_close 없음")
                    continue
                
                try:
                    # 현재 가격 조회 (archived_at이 있으면 그 날짜 기준, 없으면 오늘)
                    target_date = today_str
                    if archived_at:
                        try:
                            if isinstance(archived_at, str):
                                target_date = archived_at.replace('-', '')[:8]
                            else:
                                target_date = archived_at.strftime('%Y%m%d')
                        except:
                            pass
                    
                    df = api.get_ohlcv(ticker, 1, target_date)
                    if df.empty:
                        logger.warning(f"가격 데이터 없음: {ticker} ({name}) - {target_date}")
                        failed_count += 1
                        continue
                    
                    if 'close' in df.columns:
                        current_price = float(df.iloc[-1]['close'])
                    else:
                        current_price = float(df.iloc[-1].values[0])
                    
                    # archive_return_pct 계산
                    archive_return_pct = round(((current_price - float(anchor_close)) / float(anchor_close)) * 100, 2)
                    archive_price = current_price
                    
                    # archive_phase 결정
                    if archive_return_pct > 2:
                        archive_phase = 'PROFIT'
                    elif archive_return_pct < -2:
                        archive_phase = 'LOSS'
                    else:
                        archive_phase = 'FLAT'
                    
                    # archive_reason 결정 (없는 경우만)
                    archive_reason = 'REPLACED'  # 기본값
                    
                    # 업데이트
                    with db_manager.get_cursor(commit=True) as update_cur:
                        update_cur.execute("""
                            UPDATE recommendations
                            SET archive_return_pct = %s,
                                archive_price = %s,
                                archive_phase = %s,
                                archive_reason = COALESCE(archive_reason, %s),
                                archived_at = COALESCE(archived_at, NOW())
                            WHERE recommendation_id = %s
                        """, (archive_return_pct, archive_price, archive_phase, archive_reason, rec_id))
                    
                    updated_count += 1
                    logger.info(f"업데이트 완료: {ticker} ({name}) - archive_return_pct: {archive_return_pct}%")
                    
                except Exception as e:
                    logger.error(f"업데이트 실패: {ticker} ({name}) - {e}")
                    failed_count += 1
            
            logger.info(f"업데이트 완료: 성공 {updated_count}개, 실패 {failed_count}개")
            
    except Exception as e:
        logger.error(f"업데이트 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    print("=" * 60)
    print("기존 ARCHIVED 추천의 archive_return_pct 업데이트 시작")
    print("=" * 60)
    update_missing_archive_return_pct()
    print("=" * 60)
    print("업데이트 완료")
    print("=" * 60)

