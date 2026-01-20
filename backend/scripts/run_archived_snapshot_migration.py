#!/usr/bin/env python3
"""
ARCHIVED 스냅샷 컬럼 추가 마이그레이션 실행
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 현재 디렉토리를 backend로 변경
os.chdir(backend_dir)

from db_manager import db_manager

def main():
    # 마이그레이션 SQL 읽기
    migration_file = backend_dir / 'migrations' / '20260102_add_archived_snapshot_columns.sql'
    
    if not migration_file.exists():
        print(f"❌ 마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
        return 1
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print("=" * 60)
    print("마이그레이션 실행: recommendations 테이블에 ARCHIVED 스냅샷 컬럼 추가")
    print("=" * 60)
    print("\n마이그레이션 SQL:")
    print("-" * 60)
    print(migration_sql)
    print("-" * 60)
    
    # 마이그레이션 실행
    try:
        with db_manager.get_cursor(commit=True) as cur:
            # SQL을 세미콜론으로 분리하여 각각 실행
            statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
            
            for i, statement in enumerate(statements, 1):
                if statement:
                    print(f"\n[{i}/{len(statements)}] 실행 중...")
                    try:
                        cur.execute(statement)
                        print(f"✅ 완료")
                    except Exception as e:
                        # IF NOT EXISTS로 인해 이미 존재하는 경우는 무시
                        if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                            print(f"⚠️ 이미 존재함 (무시): {e}")
                        else:
                            raise
            
            print("\n" + "=" * 60)
            print("✅ 마이그레이션 실행 완료!")
            print("=" * 60)
            
            # 검증: 컬럼이 추가되었는지 확인
            print("\n[검증] ARCHIVED 스냅샷 컬럼 확인 중...")
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'recommendations' 
                AND column_name LIKE 'archive%'
                ORDER BY column_name
            """)
            results = cur.fetchall()
            if results:
                for result in results:
                    if isinstance(result, (list, tuple)):
                        print(f"✅ {result[0]} ({result[1]}, nullable: {result[2]})")
                    else:
                        print(f"✅ {result.get('column_name')} ({result.get('data_type')})")
            else:
                print("❌ ARCHIVED 스냅샷 컬럼이 없습니다!")
                return 1
                
            # 인덱스 확인
            print("\n[검증] 인덱스 확인 중...")
            cur.execute("""
                SELECT indexname
                FROM pg_indexes 
                WHERE tablename = 'recommendations' 
                AND indexname LIKE '%archive%'
            """)
            idx_results = cur.fetchall()
            if idx_results:
                for idx_result in idx_results:
                    if isinstance(idx_result, (list, tuple)):
                        print(f"✅ 인덱스: {idx_result[0]}")
                    else:
                        print(f"✅ 인덱스: {idx_result.get('indexname')}")
            else:
                print("⚠️ 인덱스가 없습니다 (이미 존재하거나 생성 실패)")
            
            # 기존 ARCHIVED 레코드 수 확인
            print("\n[검증] 기존 ARCHIVED 레코드 확인 중...")
            cur.execute("""
                SELECT COUNT(*) as total
                FROM recommendations
                WHERE status = 'ARCHIVED'
                  AND scanner_version = 'v3'
            """)
            count_result = cur.fetchone()
            if count_result:
                if isinstance(count_result, (list, tuple)):
                    total = count_result[0]
                else:
                    total = count_result.get('total')
                print(f"✅ 총 ARCHIVED 레코드: {total}개")
                print(f"   (스냅샷 보정은 migrate_existing_archived_snapshots.py로 실행)")
            
            return 0
                
    except Exception as e:
        print(f"\n❌ 마이그레이션 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())



