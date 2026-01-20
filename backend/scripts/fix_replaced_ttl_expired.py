"""
REPLACED 항목 중 전략별 TTL을 초과한 경우 TTL_EXPIRED로 수정
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from services.recommendation_service import get_trading_days_between
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_replaced_ttl_expired():
    """REPLACED 항목 중 전략별 TTL을 초과한 경우 TTL_EXPIRED로 수정"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # REPLACED 상태이고 archive_reason이 'REPLACED'인 항목 조회
            cur.execute("""
                SELECT recommendation_id, ticker, name, anchor_date, archived_at, 
                       archive_reason, strategy, scanner_version
                FROM recommendations
                WHERE scanner_version = 'v3'
                AND status = 'REPLACED'
                AND archive_reason = 'REPLACED'
                AND anchor_date IS NOT NULL
                AND archived_at IS NOT NULL
                ORDER BY archived_at DESC
            """)
            
            rows = cur.fetchall()
            logger.info(f"검증 대상: {len(rows)}개")
            
            if not rows:
                logger.info("검증할 항목이 없습니다.")
                return
            
            fixed_count = 0
            verified_count = 0
            
            for row in rows:
                if isinstance(row, dict):
                    rec_id = row.get('recommendation_id')
                    ticker = row.get('ticker')
                    name = row.get('name')
                    anchor_date = row.get('anchor_date')
                    archived_at = row.get('archived_at')
                    strategy = row.get('strategy')
                else:
                    rec_id = row[0]
                    ticker = row[1]
                    name = row[2]
                    anchor_date = row[3]
                    archived_at = row[4]
                    strategy = row[6] if len(row) > 6 else None
                
                if not anchor_date or not archived_at:
                    continue
                
                try:
                    # 전략별 TTL 설정
                    ttl_days = 20  # 기본값
                    if strategy == "v2_lite":
                        ttl_days = 15
                    elif strategy == "midterm":
                        ttl_days = 25
                    
                    # 거래일 계산
                    anchor_str = anchor_date.strftime('%Y%m%d') if hasattr(anchor_date, 'strftime') else str(anchor_date).replace('-', '')[:8]
                    archived_str = archived_at.strftime('%Y%m%d') if hasattr(archived_at, 'strftime') else str(archived_at).replace('-', '')[:8]
                    trading_days = get_trading_days_between(anchor_str, archived_str)
                    
                    # TTL 초과 확인
                    if trading_days >= ttl_days:
                        # TTL_EXPIRED로 수정
                        with db_manager.get_cursor(commit=True) as update_cur:
                            update_cur.execute("""
                                UPDATE recommendations
                                SET archive_reason = 'TTL_EXPIRED'
                                WHERE recommendation_id = %s
                            """, (rec_id,))
                        
                        fixed_count += 1
                        logger.info(f"수정: {ticker} ({name or 'N/A'}) - Strategy={strategy}, {trading_days}거래일 (TTL={ttl_days}) → TTL_EXPIRED")
                    else:
                        verified_count += 1
                        if verified_count % 100 == 0:
                            logger.debug(f"검증 완료: {verified_count}개...")
                    
                except Exception as e:
                    logger.error(f"처리 실패: {ticker} ({name or 'N/A'}) - {e}")
            
            logger.info(f"완료: 수정 {fixed_count}개, 검증 {verified_count}개")
            
    except Exception as e:
        logger.error(f"오류: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    print("=" * 60)
    print("REPLACED 항목 중 전략별 TTL 초과 항목을 TTL_EXPIRED로 수정 시작")
    print("=" * 60)
    fix_replaced_ttl_expired()
    print("=" * 60)
    print("완료")
    print("=" * 60)


