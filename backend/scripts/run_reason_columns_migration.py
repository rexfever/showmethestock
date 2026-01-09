#!/usr/bin/env python3
"""
recommendations 테이블에 reason, archive_reason 컬럼 추가 마이그레이션 실행
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
    migration_file = backend_dir / 'migrations' / '20260102_add_reason_column_to_recommendations.sql'
    
    if not migration_file.exists():
        print(f"❌ 마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
        return 1
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print("=" * 60)
    print("마이그레이션 실행: reason, archive_reason 컬럼 추가")
    print("=" * 60)
    
    # 마이그레이션 실행
    try:
        with db_manager.get_cursor(commit=True) as cur:
            # 1단계: reason 컬럼 추가
            print("\n[1/6] reason 컬럼 추가 중...")
            try:
                cur.execute("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS reason VARCHAR(32);")
                print("✅ reason 컬럼 추가 완료")
            except Exception as e:
                err_str = str(e).lower()
                if 'already exists' in err_str or 'duplicate' in err_str:
                    print("⚠️ reason 컬럼이 이미 존재함 (무시)")
                else:
                    print(f"❌ reason 컬럼 추가 실패: {e}")
                    raise
            
            # 2단계: archive_reason 컬럼 추가
            print("\n[2/6] archive_reason 컬럼 추가 중...")
            try:
                cur.execute("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS archive_reason VARCHAR(32);")
                print("✅ archive_reason 컬럼 추가 완료")
            except Exception as e:
                err_str = str(e).lower()
                if 'already exists' in err_str or 'duplicate' in err_str:
                    print("⚠️ archive_reason 컬럼이 이미 존재함 (무시)")
                else:
                    print(f"❌ archive_reason 컬럼 추가 실패: {e}")
                    raise
            
            # 3단계: archive_return_pct 컬럼 추가
            print("\n[3/6] archive_return_pct 컬럼 추가 중...")
            try:
                cur.execute("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS archive_return_pct NUMERIC(10,2);")
                print("✅ archive_return_pct 컬럼 추가 완료")
            except Exception as e:
                err_str = str(e).lower()
                if 'already exists' in err_str or 'duplicate' in err_str:
                    print("⚠️ archive_return_pct 컬럼이 이미 존재함 (무시)")
                else:
                    print(f"❌ archive_return_pct 컬럼 추가 실패: {e}")
                    raise
            
            # 4단계: archive_price 컬럼 추가
            print("\n[4/6] archive_price 컬럼 추가 중...")
            try:
                cur.execute("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS archive_price NUMERIC(10,2);")
                print("✅ archive_price 컬럼 추가 완료")
            except Exception as e:
                err_str = str(e).lower()
                if 'already exists' in err_str or 'duplicate' in err_str:
                    print("⚠️ archive_price 컬럼이 이미 존재함 (무시)")
                else:
                    print(f"❌ archive_price 컬럼 추가 실패: {e}")
                    raise
            
            # 5단계: archive_phase 컬럼 추가
            print("\n[5/6] archive_phase 컬럼 추가 중...")
            try:
                cur.execute("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS archive_phase VARCHAR(16);")
                print("✅ archive_phase 컬럼 추가 완료")
            except Exception as e:
                err_str = str(e).lower()
                if 'already exists' in err_str or 'duplicate' in err_str:
                    print("⚠️ archive_phase 컬럼이 이미 존재함 (무시)")
                else:
                    print(f"❌ archive_phase 컬럼 추가 실패: {e}")
                    raise
            
            # 6단계: 주석 추가
            print("\n[6/6] 주석 추가 중...")
            try:
                cur.execute("COMMENT ON COLUMN recommendations.reason IS 'BROKEN 상태 종료 사유 (TTL_EXPIRED, NO_MOMENTUM, MANUAL_ARCHIVE)';")
                cur.execute("COMMENT ON COLUMN recommendations.archive_reason IS 'ARCHIVED 전환 시 종료 사유 (TTL_EXPIRED, NO_MOMENTUM, MANUAL_ARCHIVE)';")
                cur.execute("COMMENT ON COLUMN recommendations.archive_return_pct IS 'ARCHIVED 전환 시 수익률 (%)';")
                cur.execute("COMMENT ON COLUMN recommendations.archive_price IS 'ARCHIVED 전환 시 가격';")
                cur.execute("COMMENT ON COLUMN recommendations.archive_phase IS 'ARCHIVED 전환 시 단계 (PROFIT, LOSS, FLAT)';")
                print("✅ 주석 추가 완료")
            except Exception as e:
                print(f"⚠️ 주석 추가 실패 (무시): {e}")
            
            # 인덱스 생성
            print("\n[인덱스] 인덱스 생성 중...")
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_reason ON recommendations (reason) WHERE reason IS NOT NULL;")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_archive_reason ON recommendations (archive_reason) WHERE archive_reason IS NOT NULL;")
                print("✅ 인덱스 생성 완료")
            except Exception as e:
                print(f"⚠️ 인덱스 생성 실패 (무시): {e}")
            
            print("\n" + "=" * 60)
            print("✅ 마이그레이션 실행 완료!")
            print("=" * 60)
            
            # 검증
            print("\n[검증] 컬럼 확인 중...")
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'recommendations' 
                AND column_name IN ('reason', 'archive_reason', 'archive_return_pct', 'archive_price', 'archive_phase')
                ORDER BY column_name
            """)
            results = cur.fetchall()
            if results:
                for result in results:
                    if isinstance(result, (list, tuple)):
                        print(f"✅ {result[0]} 컬럼 확인: {result[1]}")
                    else:
                        print(f"✅ {result.get('column_name')} 컬럼 확인: {result.get('data_type')}")
            else:
                print("❌ 컬럼이 없습니다!")
                return 1
                
            return 0
            
    except Exception as e:
        print(f"\n❌ 마이그레이션 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

