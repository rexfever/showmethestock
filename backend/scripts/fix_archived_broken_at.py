"""
ARCHIVED 항목의 broken_at과 broken_return_pct 수정 스크립트

문제: ARCHIVED 항목들이 BROKEN 단계를 거치지 않고 직접 ARCHIVED로 전환되어
broken_at과 broken_return_pct가 None인 상태입니다.

해결: archived_at을 broken_at으로, archive_return_pct를 broken_return_pct로 설정합니다.
"""
import sys
import os
from datetime import datetime
import json
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_manager import db_manager

def fix_archived_broken_at():
    """
    ARCHIVED 항목의 broken_at과 broken_return_pct를 수정합니다.
    archived_at을 broken_at으로, archive_return_pct를 broken_return_pct로 설정합니다.
    """
    logger.info("ARCHIVED 항목의 broken_at과 broken_return_pct 수정 시작...")
    
    fixed_count = 0
    error_count = 0
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # broken_at이 None인 ARCHIVED 항목 조회
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, name, strategy,
                    anchor_date, anchor_close,
                    archived_at, archive_reason, archive_return_pct
                FROM recommendations
                WHERE status = 'ARCHIVED'
                AND broken_at IS NULL
            """)
            rows = cur.fetchall()
        
        logger.info(f"broken_at이 None인 ARCHIVED 항목 {len(rows)}개 발견")
        
        for row in rows:
            rec_id, ticker, name, strategy, anchor_date, anchor_close, archived_at, archive_reason, archive_return_pct = row
            
            try:
                # archived_at을 broken_at으로 사용
                if archived_at:
                    archived_at_str = archived_at.strftime('%Y%m%d') if hasattr(archived_at, 'strftime') else str(archived_at).replace('-', '')[:8]
                    broken_at = archived_at_str
                    broken_return_pct = archive_return_pct if archive_return_pct is not None else None
                    
                    # DB 업데이트
                    with db_manager.get_cursor(commit=True) as update_cur:
                        update_cur.execute("""
                            UPDATE recommendations
                            SET broken_at = %s,
                                broken_return_pct = %s,
                                updated_at = NOW()
                            WHERE recommendation_id = %s
                        """, (broken_at, broken_return_pct, rec_id))
                    
                    logger.info(f"✅ {ticker} ({name}): broken_at={broken_at}, broken_return_pct={broken_return_pct}")
                    fixed_count += 1
                else:
                    logger.warning(f"⚠️ {ticker} ({name}): archived_at이 없어서 수정 불가")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"❌ {ticker} ({name}) 수정 실패: {e}")
                error_count += 1
                
    except Exception as e:
        logger.error(f"❌ 전체 처리 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        error_count += 1
        
    logger.info(f"\n수정 완료: {fixed_count}개, 오류: {error_count}개")

if __name__ == "__main__":
    fix_archived_broken_at()
