#!/usr/bin/env python3
"""
v3 추천 시스템 마이그레이션 실행 스크립트
실제 DB에 마이그레이션을 적용합니다.
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
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_existing_tables():
    """기존 테이블 존재 여부 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('recommendations', 'scan_results', 'recommendation_state_events')
                ORDER BY table_name;
            """)
            existing = cur.fetchall()
            if existing:
                logger.info(f"기존 테이블 발견: {[row[0] if isinstance(row, (list, tuple)) else row.get('table_name') for row in existing]}")
                return True
            return False
    except Exception as e:
        logger.error(f"테이블 확인 실패: {e}")
        return False


def run_migration():
    """마이그레이션 SQL 파일 실행"""
    migration_file = Path(__file__).parent.parent / "migrations" / "20251215_create_recommendations_tables_v2.sql"
    
    if not migration_file.exists():
        logger.error(f"마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
        return False
    
    logger.info(f"마이그레이션 파일 읽기: {migration_file}")
    sql_content = migration_file.read_text()
    
    # SQL 문을 세미콜론으로 분리 (간단한 분리)
    # 주의: 실제로는 더 정교한 파싱이 필요할 수 있음
    statements = []
    current_statement = []
    in_string = False
    string_char = None
    
    for line in sql_content.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('--'):
            continue
        
        # 문자열 내부 체크 (간단한 버전)
        if "'" in line or '"' in line:
            # 복잡한 문자열 처리는 생략하고 전체 라인을 포함
            pass
        
        current_statement.append(line)
        
        if line.strip().endswith(';'):
            statements.append('\n'.join(current_statement))
            current_statement = []
    
    if current_statement:
        statements.append('\n'.join(current_statement))
    
    logger.info(f"실행할 SQL 문 개수: {len(statements)}")
    
    try:
        with db_manager.get_cursor(commit=True) as cur:
            for i, statement in enumerate(statements, 1):
                if not statement.strip():
                    continue
                
                try:
                    logger.info(f"SQL 문 {i}/{len(statements)} 실행 중...")
                    cur.execute(statement)
                    logger.info(f"✅ SQL 문 {i} 실행 완료")
                except Exception as e:
                    logger.error(f"❌ SQL 문 {i} 실행 실패: {e}")
                    logger.error(f"실패한 SQL:\n{statement[:200]}...")
                    # 일부 실패는 무시할 수 있음 (IF NOT EXISTS 등)
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        logger.warning(f"  (이미 존재하는 객체로 무시: {e})")
                        continue
                    raise
        
        logger.info("✅ 마이그레이션 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_migration():
    """마이그레이션 검증"""
    logger.info("마이그레이션 검증 중...")
    
    tables = ['scan_results', 'recommendations', 'recommendation_state_events']
    all_exist = True
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            for table in tables:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    )
                """, (table,))
                exists = cur.fetchone()
                exists_val = exists[0] if isinstance(exists, (list, tuple)) else exists.get('exists') if isinstance(exists, dict) else exists
                
                if exists_val:
                    logger.info(f"  ✅ {table} 테이블 존재")
                else:
                    logger.error(f"  ❌ {table} 테이블 없음")
                    all_exist = False
            
            # Partial unique index 확인
            cur.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'recommendations'
                AND indexname = 'uniq_active_recommendation_per_ticker'
            """)
            index = cur.fetchone()
            if index:
                logger.info("  ✅ partial unique index 존재")
            else:
                logger.error("  ❌ partial unique index 없음")
                all_exist = False
    
    except Exception as e:
        logger.error(f"검증 실패: {e}")
        return False
    
    return all_exist


def main():
    """메인 함수"""
    print("=" * 80)
    print("v3 추천 시스템 마이그레이션 실행")
    print("=" * 80)
    print()
    
    # DB 연결 확인
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()
            logger.info(f"✅ DB 연결 성공: {version[0] if version else '확인 불가'}")
    except Exception as e:
        logger.error(f"❌ DB 연결 실패: {e}")
        logger.error("DATABASE_URL 또는 POSTGRES_DSN 환경 변수를 확인하세요.")
        return 1
    
    # 기존 테이블 확인
    has_existing = check_existing_tables()
    if has_existing:
        logger.warning("⚠️  기존 테이블이 발견되었습니다. 마이그레이션은 IF NOT EXISTS를 사용하므로 안전합니다.")
        response = input("계속하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            logger.info("마이그레이션 취소됨")
            return 0
    
    # 마이그레이션 실행
    if not run_migration():
        return 1
    
    # 검증
    if not verify_migration():
        logger.error("❌ 마이그레이션 검증 실패")
        return 1
    
    logger.info("=" * 80)
    logger.info("✅ 마이그레이션 및 검증 완료!")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

