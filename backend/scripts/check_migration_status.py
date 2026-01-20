#!/usr/bin/env python3
"""
마이그레이션 상태 확인 스크립트
어떤 마이그레이션이 적용되었는지, 어떤 마이그레이션이 필요한지 확인
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from db_manager import db_manager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_table_exists(table_name):
    """테이블 존재 여부 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (table_name,))
            result = cur.fetchone()
            return result[0] if result else False
    except Exception as e:
        logger.error(f"테이블 확인 실패 ({table_name}): {e}")
        return False


def check_column_exists(table_name, column_name):
    """컬럼 존재 여부 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = %s 
                    AND column_name = %s
                )
            """, (table_name, column_name))
            result = cur.fetchone()
            return result[0] if result else False
    except Exception as e:
        logger.error(f"컬럼 확인 실패 ({table_name}.{column_name}): {e}")
        return False


def check_index_exists(table_name, index_name):
    """인덱스 존재 여부 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE tablename = %s 
                    AND indexname = %s
                )
            """, (table_name, index_name))
            result = cur.fetchone()
            return result[0] if result else False
    except Exception as e:
        logger.error(f"인덱스 확인 실패 ({table_name}.{index_name}): {e}")
        return False


def check_migrations():
    """마이그레이션 상태 확인"""
    logger.info("=" * 80)
    logger.info("마이그레이션 상태 확인")
    logger.info("=" * 80)
    logger.info("")
    
    # DB 연결 확인
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()
            logger.info(f"✅ DB 연결 성공: {version[0] if version else '확인 불가'}")
            logger.info("")
    except Exception as e:
        logger.error(f"❌ DB 연결 실패: {e}")
        logger.error("DATABASE_URL 또는 POSTGRES_DSN 환경 변수를 확인하세요.")
        return False
    
    # 마이그레이션 체크리스트
    migrations = []
    
    # 1. user_preferences 테이블 (20260127)
    logger.info("📋 [1] user_preferences 테이블 (20260127)")
    user_prefs_exists = check_table_exists('user_preferences')
    if user_prefs_exists:
        logger.info("   ✅ user_preferences 테이블 존재")
        idx_exists = check_index_exists('user_preferences', 'idx_user_preferences_user_id')
        if idx_exists:
            logger.info("   ✅ idx_user_preferences_user_id 인덱스 존재")
        else:
            logger.warning("   ⚠️  idx_user_preferences_user_id 인덱스 없음")
            migrations.append("20260127_create_user_preferences_table.sql")
    else:
        logger.warning("   ⚠️  user_preferences 테이블 없음 - 마이그레이션 필요")
        migrations.append("20260127_create_user_preferences_table.sql")
    logger.info("")
    
    # 2. recommendations 테이블 컬럼 확인
    logger.info("📋 [2] recommendations 테이블 컬럼 확인")
    rec_table_exists = check_table_exists('recommendations')
    if not rec_table_exists:
        logger.warning("   ⚠️  recommendations 테이블 없음 - 기본 마이그레이션 필요")
        migrations.append("20251215_create_recommendations_tables_v2.sql")
        logger.info("")
    else:
        logger.info("   ✅ recommendations 테이블 존재")
        
        # status_changed_at (20260101)
        status_changed_at = check_column_exists('recommendations', 'status_changed_at')
        if status_changed_at:
            logger.info("   ✅ status_changed_at 컬럼 존재")
        else:
            logger.warning("   ⚠️  status_changed_at 컬럼 없음 - 마이그레이션 필요")
            migrations.append("20260101_add_status_changed_at_to_recommendations.sql")
        
        # broken_return_pct (20260102)
        broken_return_pct = check_column_exists('recommendations', 'broken_return_pct')
        if broken_return_pct:
            logger.info("   ✅ broken_return_pct 컬럼 존재")
        else:
            logger.warning("   ⚠️  broken_return_pct 컬럼 없음 - 마이그레이션 필요")
            migrations.append("20260102_add_broken_return_pct_column.sql")
        
        # archive_reason (20260102)
        archive_reason = check_column_exists('recommendations', 'archive_reason')
        if archive_reason:
            logger.info("   ✅ archive_reason 컬럼 존재")
        else:
            logger.warning("   ⚠️  archive_reason 컬럼 없음 - 마이그레이션 필요")
            migrations.append("20260102_add_reason_column_to_recommendations.sql")
        
        # archived_snapshot 컬럼들 (20260102)
        archive_at = check_column_exists('recommendations', 'archive_at')
        archived_close = check_column_exists('recommendations', 'archived_close')
        archived_return_pct = check_column_exists('recommendations', 'archived_return_pct')
        if archive_at and archived_close and archived_return_pct:
            logger.info("   ✅ archived_snapshot 컬럼들 존재 (archive_at, archived_close, archived_return_pct)")
        else:
            logger.warning("   ⚠️  archived_snapshot 컬럼들 없음 - 마이그레이션 필요")
            if "20260102_add_archived_snapshot_columns.sql" not in migrations:
                migrations.append("20260102_add_archived_snapshot_columns.sql")
        
        # name 컬럼 (20251231)
        name_col = check_column_exists('recommendations', 'name')
        if name_col:
            logger.info("   ✅ name 컬럼 존재")
        else:
            logger.warning("   ⚠️  name 컬럼 없음 - 마이그레이션 필요")
            migrations.append("20251231_add_name_column_to_recommendations.sql")
        
        logger.info("")
    
    # 3. 인덱스 최적화 (20250127)
    logger.info("📋 [3] recommendations 테이블 인덱스 최적화 (20250127)")
    if rec_table_exists:
        idx1 = check_index_exists('recommendations', 'idx_recommendations_status_created_at')
        idx2 = check_index_exists('recommendations', 'idx_recommendations_ticker_status')
        idx3 = check_index_exists('recommendations', 'idx_recommendations_user_id_status')
        if idx1 and idx2 and idx3:
            logger.info("   ✅ 최적화 인덱스들 존재")
        else:
            logger.warning("   ⚠️  최적화 인덱스들 없음 - 마이그레이션 필요")
            migrations.append("20250127_optimize_recommendations_query_indexes.sql")
    else:
        logger.warning("   ⚠️  recommendations 테이블이 없어 인덱스 확인 불가")
    logger.info("")
    
    # 4. user_rec_ack 테이블
    logger.info("📋 [4] user_rec_ack 테이블")
    user_rec_ack_exists = check_table_exists('user_rec_ack')
    if user_rec_ack_exists:
        logger.info("   ✅ user_rec_ack 테이블 존재")
    else:
        logger.warning("   ⚠️  user_rec_ack 테이블 없음 - 마이그레이션 필요")
        migrations.append("add_user_rec_ack_table.sql")
    logger.info("")
    
    # 요약
    logger.info("=" * 80)
    if migrations:
        logger.warning(f"⚠️  필요한 마이그레이션: {len(migrations)}개")
        logger.info("")
        logger.info("다음 마이그레이션을 실행해야 합니다:")
        for i, migration in enumerate(migrations, 1):
            logger.info(f"   {i}. {migration}")
        logger.info("")
        logger.info("마이그레이션 실행 방법:")
        logger.info("   python3 backend/scripts/run_user_preferences_migration.py  # user_preferences")
        logger.info("   python3 backend/scripts/run_migration_v3.py  # recommendations 기본")
        logger.info("   또는 직접 SQL 파일 실행: psql -d stockfinder -f backend/migrations/<파일명>")
    else:
        logger.info("✅ 모든 마이그레이션이 적용되었습니다!")
    logger.info("=" * 80)
    
    return len(migrations) == 0


def main():
    """메인 함수"""
    try:
        success = check_migrations()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

