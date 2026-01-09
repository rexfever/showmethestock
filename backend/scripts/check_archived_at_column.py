#!/usr/bin/env python3
"""
archived_at 컬럼 확인 및 추가
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

os.chdir(backend_dir)

from db_manager import db_manager

def main():
    print("=" * 60)
    print("archived_at 컬럼 확인")
    print("=" * 60)
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # archived_at 컬럼 확인
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'recommendations' 
                AND column_name IN ('archived_at', 'archive_at')
            """)
            results = cur.fetchall()
            
            has_archived_at = False
            has_archive_at = False
            
            for result in results:
                if isinstance(result, (list, tuple)):
                    col_name = result[0]
                else:
                    col_name = result.get('column_name')
                
                if col_name == 'archived_at':
                    has_archived_at = True
                    print(f"✅ archived_at 컬럼 존재: {result[1] if isinstance(result, (list, tuple)) else result.get('data_type')}")
                elif col_name == 'archive_at':
                    has_archive_at = True
                    print(f"✅ archive_at 컬럼 존재: {result[1] if isinstance(result, (list, tuple)) else result.get('data_type')}")
            
            if not has_archived_at and not has_archive_at:
                print("⚠️ archived_at 또는 archive_at 컬럼이 없습니다. 추가합니다...")
                with db_manager.get_cursor(commit=True) as update_cur:
                    update_cur.execute("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;")
                    print("✅ archived_at 컬럼 추가 완료")
            elif has_archived_at:
                print("✅ archived_at 컬럼이 이미 존재합니다.")
            elif has_archive_at:
                print("⚠️ archive_at 컬럼이 존재하지만 archived_at이 없습니다.")
                print("   코드에서 archived_at을 사용하므로 추가합니다...")
                with db_manager.get_cursor(commit=True) as update_cur:
                    update_cur.execute("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;")
                    # archive_at 데이터를 archived_at으로 복사
                    update_cur.execute("""
                        UPDATE recommendations
                        SET archived_at = archive_at
                        WHERE archived_at IS NULL AND archive_at IS NOT NULL
                    """)
                    print("✅ archived_at 컬럼 추가 및 데이터 복사 완료")
            
            return 0
            
    except Exception as e:
        print(f"\n❌ 확인 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())


