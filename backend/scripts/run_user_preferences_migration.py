#!/usr/bin/env python3
"""
user_preferences 테이블 생성 마이그레이션 실행 스크립트
"""
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import db_manager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_migration():
    """user_preferences 테이블 생성 마이그레이션 실행"""
    migration_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'migrations',
        '20260127_create_user_preferences_table.sql'
    )
    
    if not os.path.exists(migration_file):
        logger.error(f"❌ 마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
        return False
    
    logger.info("=" * 60)
    logger.info("user_preferences 테이블 생성 마이그레이션 실행")
    logger.info("=" * 60)
    
    try:
        # SQL 파일 읽기
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # 마이그레이션 실행
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute(sql)
        
        logger.info("✅ 마이그레이션 완료")
        
        # 테이블 확인
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'user_preferences'
                );
            """)
            exists = cur.fetchone()[0]
            
            if exists:
                logger.info("✅ user_preferences 테이블이 생성되었습니다.")
                
                # 인덱스 확인
                cur.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'user_preferences'
                """)
                indexes = [row[0] for row in cur.fetchall()]
                logger.info(f"✅ 인덱스: {', '.join(indexes)}")
            else:
                logger.error("❌ user_preferences 테이블이 생성되지 않았습니다.")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 마이그레이션 실행 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """메인 함수"""
    if not run_migration():
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("✅ 모든 작업 완료!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

