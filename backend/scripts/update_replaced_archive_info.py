"""
기존 REPLACED 상태 추천 중 archive 정보가 없는 항목 업데이트
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
from services.state_transition_service import get_trading_days_since
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_replaced_archive_info():
    """REPLACED 상태인데 archive 정보가 없는 추천 업데이트"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # REPLACED 상태인데 archive_reason이 없는 추천 조회
            cur.execute("""
                SELECT recommendation_id, ticker, name, anchor_date, anchor_close, 
                       archived_at, updated_at, status_changed_at
                FROM recommendations
                WHERE status = 'REPLACED'
                AND scanner_version = 'v3'
                AND (archive_reason IS NULL OR archive_return_pct IS NULL)
                ORDER BY anchor_date ASC
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
                    updated_at = row.get('updated_at')
                    status_changed_at = row.get('status_changed_at')
                else:
                    rec_id = row[0]
                    ticker = row[1]
                    name = row[2]
                    anchor_date = row[3]
                    anchor_close = row[4]
                    archived_at = row[5] if len(row) > 5 else None
                    updated_at = row[6] if len(row) > 6 else None
                    status_changed_at = row[7] if len(row) > 7 else None
                
                if not ticker or not anchor_close or anchor_close <= 0:
                    logger.warning(f"스킵: {ticker} ({name}) - anchor_close 없음")
                    continue
                
                try:
                    # 거래일 계산
                    trading_days = 0
                    archive_reason = 'REPLACED'
                    
                    if anchor_date:
                        trading_days = get_trading_days_since(anchor_date)
                        # TTL 체크: 20거래일 이상이면 TTL_EXPIRED로 설정
                        if trading_days >= 20:
                            archive_reason = 'TTL_EXPIRED'
                        else:
                            archive_reason = 'REPLACED'
                    
                    # REPLACED된 시점의 가격 조회
                    # archived_at이 있으면 archived_at 시점의 가격을 조회 (전이 시점)
                    # archived_at이 없으면 status_changed_at 또는 updated_at 시점의 가격 조회
                    target_date = today_str
                    if archived_at:
                        # archived_at이 있으면 전이 시점의 가격 조회
                        try:
                            if isinstance(archived_at, str):
                                target_date = archived_at.replace('-', '')[:8]
                            else:
                                target_date = archived_at.strftime('%Y%m%d')
                        except:
                            pass
                    elif status_changed_at:
                        # archived_at이 없으면 status_changed_at 시점의 가격 조회
                        try:
                            if isinstance(status_changed_at, str):
                                target_date = status_changed_at.replace('-', '')[:8]
                            else:
                                target_date = status_changed_at.strftime('%Y%m%d')
                        except:
                            if updated_at:
                                try:
                                    if isinstance(updated_at, str):
                                        target_date = updated_at.replace('-', '')[:8]
                                    else:
                                        target_date = updated_at.strftime('%Y%m%d')
                                except:
                                    pass
                    elif updated_at:
                        # 마지막으로 updated_at 시점의 가격 조회
                        try:
                            if isinstance(updated_at, str):
                                target_date = updated_at.replace('-', '')[:8]
                            else:
                                target_date = updated_at.strftime('%Y%m%d')
                        except:
                            pass
                    
                    # target_date의 정확한 가격 조회
                    # base_dt를 지정하면 해당 날짜 이하의 데이터를 반환하므로, 충분한 count로 조회 후 필터링
                    df = api.get_ohlcv(ticker, 10, target_date)
                    if df.empty:
                        logger.warning(f"가격 데이터 없음: {ticker} ({name}) - {target_date}")
                        failed_count += 1
                        continue
                    
                    # target_date와 일치하는 행 찾기
                    current_price = None
                    if 'date' in df.columns:
                        # date 컬럼이 있는 경우
                        df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                        target_date_str = target_date.replace('-', '')[:8]
                        df_filtered = df[df['date_str'] == target_date_str]
                        if not df_filtered.empty:
                            row = df_filtered.iloc[-1]  # 가장 최근 것
                            current_price = float(row['close']) if 'close' in row else float(row.values[0])
                        else:
                            # 정확히 일치하는 날짜가 없으면 가장 가까운 이전 거래일 데이터 사용
                            df_sorted = df.sort_values('date_str')
                            df_before = df_sorted[df_sorted['date_str'] <= target_date_str]
                            if not df_before.empty:
                                row = df_before.iloc[-1]
                                current_price = float(row['close']) if 'close' in row else float(row.values[0])
                            else:
                                # 마지막 행 사용
                                current_price = float(df.iloc[-1]['close']) if 'close' in df.columns else float(df.iloc[-1].values[0])
                    else:
                        # date 컬럼이 없으면 마지막 행 사용 (base_dt 이하의 최근 데이터)
                        current_price = float(df.iloc[-1]['close']) if 'close' in df.columns else float(df.iloc[-1].values[0])
                    
                    if current_price is None:
                        logger.warning(f"가격 추출 실패: {ticker} ({name}) - {target_date}")
                        failed_count += 1
                        continue
                    
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
                    
                    # archived_at은 이미 있으면 유지, 없으면 status_changed_at 또는 updated_at 사용
                    archived_at_value = archived_at if archived_at else (status_changed_at if status_changed_at else updated_at)
                    
                    # 업데이트
                    with db_manager.get_cursor(commit=True) as update_cur:
                        if archived_at_value:
                            update_cur.execute("""
                                UPDATE recommendations
                                SET archive_reason = %s,
                                    archive_return_pct = %s,
                                    archive_price = %s,
                                    archive_phase = %s,
                                    archived_at = COALESCE(archived_at, %s)
                                WHERE recommendation_id = %s
                            """, (archive_reason, archive_return_pct, archive_price, archive_phase, archived_at_value, rec_id))
                        else:
                            update_cur.execute("""
                                UPDATE recommendations
                                SET archive_reason = %s,
                                    archive_return_pct = %s,
                                    archive_price = %s,
                                    archive_phase = %s,
                                    archived_at = COALESCE(archived_at, NOW())
                                WHERE recommendation_id = %s
                            """, (archive_reason, archive_return_pct, archive_price, archive_phase, rec_id))
                    
                    updated_count += 1
                    logger.info(f"업데이트 완료: {ticker} ({name}) - {trading_days}거래일, archive_reason: {archive_reason}, archive_return_pct: {archive_return_pct}%")
                    
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
    print("기존 REPLACED 추천의 archive 정보 업데이트 시작")
    print("=" * 60)
    update_replaced_archive_info()
    print("=" * 60)
    print("업데이트 완료")
    print("=" * 60)

