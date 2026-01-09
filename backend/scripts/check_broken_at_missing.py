"""
broken_at이 None인 항목 확인 스크립트
- broken_return_pct가 있는데 broken_at이 None인 항목 조회
- 최근 발생한 항목 우선 확인
"""
import sys
import os
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager


def check_broken_at_missing():
    """broken_at이 None인 항목 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # broken_return_pct가 있는데 broken_at이 None인 항목 조회
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, name, strategy, 
                    broken_return_pct, broken_at, archived_at, status,
                    archive_reason, archive_return_pct
                FROM recommendations
                WHERE broken_return_pct IS NOT NULL
                AND broken_at IS NULL
                AND scanner_version = 'v3'
                ORDER BY archived_at DESC NULLS LAST, recommendation_id DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("✅ broken_at이 None인 항목이 없습니다.")
                return
            
            print(f"⚠️ broken_at이 None인 항목: {len(rows)}개\n")
            print("=" * 150)
            
            # 상태별 분류
            by_status = {}
            for row in rows:
                rec_id, ticker, name, strategy, broken_return_pct, broken_at, \
                archived_at, status, archive_reason, archive_return_pct = row
                
                status_key = status or 'UNKNOWN'
                if status_key not in by_status:
                    by_status[status_key] = []
                
                by_status[status_key].append({
                    'rec_id': rec_id,
                    'ticker': ticker,
                    'name': name,
                    'strategy': strategy,
                    'broken_return_pct': broken_return_pct,
                    'archived_at': archived_at,
                    'archive_reason': archive_reason,
                    'archive_return_pct': archive_return_pct
                })
            
            # 결과 출력
            for status, items in sorted(by_status.items()):
                print(f"\n[{status}] {len(items)}개")
                print("-" * 150)
                for item in items:
                    print(f"  - {item['ticker']} ({item['name']})")
                    print(f"    전략: {item['strategy']}, broken_return_pct: {item['broken_return_pct']}%")
                    if item['archived_at']:
                        print(f"    archived_at: {item['archived_at']}, archive_reason: {item['archive_reason']}")
                        if item['archive_return_pct']:
                            print(f"    archive_return_pct: {item['archive_return_pct']}%")
                    print()
            
            # 통계
            print("\n📊 통계")
            print("=" * 150)
            print(f"전체: {len(rows)}개")
            for status, items in sorted(by_status.items()):
                print(f"  {status}: {len(items)}개")
            
            return rows
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("broken_at이 None인 항목 확인...")
    print("=" * 150)
    check_broken_at_missing()
    print("\n완료!")

