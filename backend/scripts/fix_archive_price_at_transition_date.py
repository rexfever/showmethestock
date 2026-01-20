"""
archived_at 시점의 정확한 가격으로 archive_price와 archive_return_pct 재계산
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from kiwoom_api import api
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_archive_price_at_transition_date():
    """archived_at 시점의 정확한 가격으로 재계산"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # archived_at이 있고 archive_price가 있는 항목 조회
            cur.execute("""
                SELECT recommendation_id, ticker, name, anchor_date, anchor_close, 
                       archived_at, archive_reason, archive_return_pct, archive_price, archive_phase
                FROM recommendations
                WHERE scanner_version = 'v3'
                AND status IN ('ARCHIVED', 'REPLACED')
                AND archived_at IS NOT NULL
                AND archive_price IS NOT NULL
                AND anchor_close IS NOT NULL
                AND anchor_close > 0
                ORDER BY archived_at DESC
            """)
            
            rows = cur.fetchall()
            logger.info(f"검증 대상: {len(rows)}개")
            
            if not rows:
                logger.info("검증할 항목이 없습니다.")
                return
            
            fixed_count = 0
            verified_count = 0
            failed_count = 0
            
            for row in rows:
                if isinstance(row, dict):
                    rec_id = row.get('recommendation_id')
                    ticker = row.get('ticker')
                    name = row.get('name')
                    anchor_date = row.get('anchor_date')
                    anchor_close = float(row.get('anchor_close'))
                    archived_at = row.get('archived_at')
                    archive_reason = row.get('archive_reason')
                    archive_return_pct = float(row.get('archive_return_pct')) if row.get('archive_return_pct') else None
                    archive_price = float(row.get('archive_price')) if row.get('archive_price') else None
                else:
                    rec_id = row[0]
                    ticker = row[1]
                    name = row[2]
                    anchor_date = row[3]
                    anchor_close = float(row[4])
                    archived_at = row[5]
                    archive_reason = row[6]
                    archive_return_pct = float(row[7]) if row[7] else None
                    archive_price = float(row[8]) if row[8] else None
                
                if not ticker or not anchor_close or anchor_close <= 0:
                    continue
                
                try:
                    # archived_at 시점의 정확한 가격 조회
                    archived_str = archived_at.strftime('%Y%m%d') if hasattr(archived_at, 'strftime') else str(archived_at).replace('-', '')[:8]
                    
                    df = api.get_ohlcv(ticker, 10, archived_str)
                    if df.empty:
                        logger.warning(f"가격 데이터 없음: {ticker} ({name}) - {archived_str}")
                        failed_count += 1
                        continue
                    
                    # archived_str과 일치하는 행 찾기
                    actual_price = None
                    if 'date' in df.columns:
                        df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                        df_filtered = df[df['date_str'] == archived_str]
                        if not df_filtered.empty:
                            actual_price = float(df_filtered.iloc[-1]['close'])
                        else:
                            # 가장 가까운 이전 거래일 데이터 사용
                            df_sorted = df.sort_values('date_str')
                            df_before = df_sorted[df_sorted['date_str'] <= archived_str]
                            if not df_before.empty:
                                actual_price = float(df_before.iloc[-1]['close'])
                            else:
                                actual_price = float(df.iloc[-1]['close']) if 'close' in df.columns else float(df.iloc[-1].values[0])
                    else:
                        actual_price = float(df.iloc[-1]['close']) if 'close' in df.columns else float(df.iloc[-1].values[0])
                    
                    if actual_price is None:
                        logger.warning(f"가격 추출 실패: {ticker} ({name}) - {archived_str}")
                        failed_count += 1
                        continue
                    
                    # 가격 비교
                    if archive_price and abs(actual_price - archive_price) > 0.01:
                        # 가격이 다르면 재계산
                        actual_return_pct = round(((actual_price - anchor_close) / anchor_close) * 100, 2)
                        
                        # archive_phase 재계산
                        if actual_return_pct > 2:
                            archive_phase = 'PROFIT'
                        elif actual_return_pct < -2:
                            archive_phase = 'LOSS'
                        else:
                            archive_phase = 'FLAT'
                        
                        # 업데이트
                        with db_manager.get_cursor(commit=True) as update_cur:
                            update_cur.execute("""
                                UPDATE recommendations
                                SET archive_price = %s,
                                    archive_return_pct = %s,
                                    archive_phase = %s
                                WHERE recommendation_id = %s
                            """, (actual_price, actual_return_pct, archive_phase, rec_id))
                        
                        fixed_count += 1
                        logger.info(f"수정: {ticker} ({name}) - 가격 {archive_price} → {actual_price}, 수익률 {archive_return_pct}% → {actual_return_pct}%")
                    else:
                        verified_count += 1
                        if verified_count % 100 == 0:
                            logger.debug(f"검증 완료: {verified_count}개...")
                    
                except Exception as e:
                    logger.error(f"처리 실패: {ticker} ({name}) - {e}")
                    failed_count += 1
            
            logger.info(f"완료: 수정 {fixed_count}개, 검증 {verified_count}개, 실패 {failed_count}개")
            
    except Exception as e:
        logger.error(f"오류: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    print("=" * 60)
    print("archived_at 시점의 정확한 가격으로 재계산 시작")
    print("=" * 60)
    fix_archive_price_at_transition_date()
    print("=" * 60)
    print("완료")
    print("=" * 60)


