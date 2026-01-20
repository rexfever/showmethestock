#!/usr/bin/env python3
"""
recommendations 테이블에 name 컬럼 추가 마이그레이션 실행
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
    migration_file = backend_dir / 'migrations' / '20251231_add_name_column_to_recommendations.sql'
    
    if not migration_file.exists():
        print(f"❌ 마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
        return 1
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print("=" * 60)
    print("마이그레이션 실행: recommendations 테이블에 name 컬럼 추가")
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
            
            # 1단계: 컬럼 추가
            print("\n[1/3] 컬럼 추가 중...")
            try:
                cur.execute("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS name TEXT;")
                print("✅ 컬럼 추가 완료")
            except Exception as e:
                err_str = str(e).lower()
                if 'already exists' in err_str or 'duplicate' in err_str:
                    print("⚠️ 컬럼이 이미 존재함 (무시)")
                else:
                    print(f"❌ 컬럼 추가 실패: {e}")
                    raise
            
            # 2단계: 인덱스 생성
            print("\n[2/3] 인덱스 생성 중...")
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_name ON recommendations (name) WHERE name IS NOT NULL;")
                print("✅ 인덱스 생성 완료")
            except Exception as e:
                err_str = str(e).lower()
                if 'already exists' in err_str or 'duplicate' in err_str:
                    print("⚠️ 인덱스가 이미 존재함 (무시)")
                else:
                    print(f"❌ 인덱스 생성 실패: {e}")
                    raise
            
            # 3단계: 주석 추가
            print("\n[3/3] 주석 추가 중...")
            try:
                cur.execute("COMMENT ON COLUMN recommendations.name IS '종목명 (성능 최적화: API 호출 제거)';")
                print("✅ 주석 추가 완료")
            except Exception as e:
                print(f"⚠️ 주석 추가 실패 (무시): {e}")
            
            print("\n" + "=" * 60)
            print("✅ 마이그레이션 실행 완료!")
            print("=" * 60)
            
            # 검증: name 컬럼이 추가되었는지 확인
            print("\n[검증] name 컬럼 확인 중...")
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'recommendations' 
                AND column_name = 'name'
            """)
            result = cur.fetchone()
            if result:
                if isinstance(result, (list, tuple)):
                    print(f"✅ name 컬럼 확인: {result[0]} ({result[1]}, nullable: {result[2]})")
                else:
                    print(f"✅ name 컬럼 확인: {result.get('column_name')} ({result.get('data_type')})")
            else:
                print("❌ name 컬럼이 없습니다!")
                return 1
                
            # 인덱스 확인
            print("\n[검증] 인덱스 확인 중...")
            cur.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes 
                WHERE tablename = 'recommendations' 
                AND indexname = 'idx_recommendations_name'
            """)
            idx_result = cur.fetchone()
            if idx_result:
                if isinstance(idx_result, (list, tuple)):
                    print(f"✅ 인덱스 확인: {idx_result[0]}")
                else:
                    print(f"✅ 인덱스 확인: {idx_result.get('indexname')}")
            else:
                print("⚠️ 인덱스가 없습니다 (이미 존재하거나 생성 실패)")
            
            return 0
            
    except Exception as e:
        print(f"\n❌ 마이그레이션 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

