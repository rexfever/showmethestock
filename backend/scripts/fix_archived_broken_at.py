"""
ARCHIVED 데이터 중 broken_at이 None인데 broken_return_pct가 있는 경우 수정
정책: broken_return_pct가 있으면 broken_at도 설정되어야 함
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import get_kst_now, yyyymmdd_to_date
from datetime import datetime

def fix_archived_broken_at():
    """broken_at이 None인데 broken_return_pct가 있는 경우 수정"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # broken_at이 None인데 broken_return_pct가 있는 ARCHIVED 항목 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.strategy,
                    r.anchor_date,
                    r.broken_at,
                    r.broken_return_pct,
                    r.archive_return_pct,
                    r.archive_reason,
                    r.status_changed_at,
                    r.archived_at
                FROM recommendations r
                WHERE r.status IN ('ARCHIVED', 'REPLACED')
                AND r.scanner_version = 'v3'
                AND r.broken_at IS NULL
                AND r.broken_return_pct IS NOT NULL
                ORDER BY r.archived_at DESC NULLS LAST, r.status_changed_at DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("수정할 항목이 없습니다.")
                return
            
            print(f"수정 대상: {len(rows)}개\n")
            print("=" * 120)
            
            update_count = 0
            skip_count = 0
            
            for idx, row in enumerate(rows, 1):
                rec_id, ticker, name, strategy, anchor_date, broken_at, broken_return_pct, archive_return_pct, archive_reason, status_changed_at, archived_at = row
                
                if idx % 20 == 0:
                    print(f"[진행 중] {idx}/{len(rows)} 처리 중...")
                
                # broken_at 설정: status_changed_at 또는 archived_at 사용
                # REPLACED의 경우 status_changed_at이 REPLACED 전환 시점
                # ARCHIVED의 경우 archived_at이 ARCHIVED 전환 시점
                # 하지만 손절 조건 만족 시점은 그 이전일 수 있음
                # 정책상으로는 broken_return_pct가 설정된 시점이 broken_at이어야 함
                
                # status_changed_at 또는 archived_at 중 더 이른 날짜 사용
                target_date = None
                if archived_at:
                    if isinstance(archived_at, str):
                        target_date = archived_at[:8].replace('-', '')
                    elif isinstance(archived_at, datetime):
                        target_date = archived_at.strftime('%Y%m%d')
                    else:
                        target_date = str(archived_at)[:8].replace('-', '')
                elif status_changed_at:
                    if isinstance(status_changed_at, str):
                        target_date = status_changed_at[:8].replace('-', '')
                    elif isinstance(status_changed_at, datetime):
                        target_date = status_changed_at.strftime('%Y%m%d')
                    else:
                        target_date = str(status_changed_at)[:8].replace('-', '')
                
                if not target_date:
                    skip_count += 1
                    continue
                
                # broken_at 설정
                if update_count < 10:  # 처음 10개만 상세 로그
                    print(f"\n[{update_count + 1}] {ticker} ({name})")
                    print(f"    전략: {strategy}")
                    print(f"    현재: broken_at={broken_at}, broken_return_pct={broken_return_pct}%")
                    print(f"    수정: broken_at={target_date}")
                    print(f"    archive_return_pct={archive_return_pct}%, archive_reason={archive_reason}")
                
                with db_manager.get_cursor(commit=True) as update_cur:
                    update_cur.execute("""
                        UPDATE recommendations
                        SET broken_at = %s,
                            updated_at = NOW()
                        WHERE recommendation_id = %s
                    """, (target_date, rec_id))
                
                update_count += 1
            
            print(f"\n[결과]")
            print(f"  업데이트: {update_count}개")
            print(f"  스킵: {skip_count}개")
            print(f"  총: {len(rows)}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("ARCHIVED 데이터의 broken_at 설정 시작...")
    print("주의: 이 스크립트는 데이터베이스를 수정합니다.\n")
    fix_archived_broken_at()
    print("\n완료!")

