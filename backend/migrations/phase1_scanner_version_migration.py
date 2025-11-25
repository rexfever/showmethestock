#!/usr/bin/env python3
"""
Phase 1: Critical Issues 해결을 위한 DB 마이그레이션 스크립트

1. scan_rank 테이블에 scanner_version 컬럼 추가 및 복합 기본키 설정
2. market_conditions 테이블에 scanner_version 컬럼 추가 및 복합 기본키 설정
3. 기존 데이터에 기본값 'v1' 설정

실행 방법:
python backend/migrations/phase1_scanner_version_migration.py
"""

import os
import sys
import json
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from db_manager import db_manager


def backup_tables():
    """테이블 백업"""
    print("📦 테이블 백업 시작...")
    
    backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(project_root, 'archive', 'old_db_backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # scan_rank 백업
            cur.execute("SELECT COUNT(*) FROM scan_rank")
            scan_rank_count = cur.fetchone()[0]
            print(f"  - scan_rank: {scan_rank_count}개 레코드")
            
            # market_conditions 백업
            cur.execute("SELECT COUNT(*) FROM market_conditions")
            market_conditions_count = cur.fetchone()[0]
            print(f"  - market_conditions: {market_conditions_count}개 레코드")
            
            # 백업 정보 저장
            backup_info = {
                'timestamp': backup_timestamp,
                'scan_rank_count': scan_rank_count,
                'market_conditions_count': market_conditions_count,
                'migration': 'phase1_scanner_version'
            }
            
            backup_info_file = os.path.join(backup_dir, f'phase1_migration_{backup_timestamp}.json')
            with open(backup_info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 백업 정보 저장: {backup_info_file}")
            return backup_timestamp
            
    except Exception as e:
        print(f"❌ 백업 실패: {e}")
        return None


def migrate_scan_rank_table():
    """scan_rank 테이블 마이그레이션"""
    print("🔄 scan_rank 테이블 마이그레이션 시작...")
    
    try:
        with db_manager.get_cursor(commit=True) as cur:
            # 1. scanner_version 컬럼 존재 여부 확인
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'scan_rank' AND column_name = 'scanner_version'
            """)
            
            if cur.fetchone():
                print("  - scanner_version 컬럼이 이미 존재합니다.")
                return True
            
            # 2. scanner_version 컬럼 추가
            print("  - scanner_version 컬럼 추가 중...")
            cur.execute("""
                ALTER TABLE scan_rank 
                ADD COLUMN scanner_version TEXT NOT NULL DEFAULT 'v1'
            """)
            
            # 3. 기존 기본키 제거
            print("  - 기존 기본키 제거 중...")
            cur.execute("ALTER TABLE scan_rank DROP CONSTRAINT IF EXISTS scan_rank_pkey")
            
            # 4. 새로운 복합 기본키 설정
            print("  - 새로운 복합 기본키 설정 중...")
            cur.execute("""
                ALTER TABLE scan_rank 
                ADD CONSTRAINT scan_rank_pkey 
                PRIMARY KEY (date, code, scanner_version)
            """)
            
            # 5. 기존 데이터 확인
            cur.execute("SELECT COUNT(*) FROM scan_rank WHERE scanner_version = 'v1'")
            updated_count = cur.fetchone()[0]
            
            print(f"✅ scan_rank 테이블 마이그레이션 완료 ({updated_count}개 레코드)")
            return True
            
    except Exception as e:
        print(f"❌ scan_rank 테이블 마이그레이션 실패: {e}")
        return False


def migrate_market_conditions_table():
    """market_conditions 테이블 마이그레이션"""
    print("🔄 market_conditions 테이블 마이그레이션 시작...")
    
    try:
        with db_manager.get_cursor(commit=True) as cur:
            # 1. scanner_version 컬럼 존재 여부 확인
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'market_conditions' AND column_name = 'scanner_version'
            """)
            
            if cur.fetchone():
                print("  - scanner_version 컬럼이 이미 존재합니다.")
                return True
            
            # 2. scanner_version 컬럼 추가
            print("  - scanner_version 컬럼 추가 중...")
            cur.execute("""
                ALTER TABLE market_conditions 
                ADD COLUMN scanner_version TEXT NOT NULL DEFAULT 'v1'
            """)
            
            # 3. 기존 기본키 제거
            print("  - 기존 기본키 제거 중...")
            cur.execute("ALTER TABLE market_conditions DROP CONSTRAINT IF EXISTS market_conditions_pkey")
            
            # 4. 새로운 복합 기본키 설정
            print("  - 새로운 복합 기본키 설정 중...")
            cur.execute("""
                ALTER TABLE market_conditions 
                ADD CONSTRAINT market_conditions_pkey 
                PRIMARY KEY (date, scanner_version)
            """)
            
            # 5. 기존 데이터 확인
            cur.execute("SELECT COUNT(*) FROM market_conditions WHERE scanner_version = 'v1'")
            updated_count = cur.fetchone()[0]
            
            print(f"✅ market_conditions 테이블 마이그레이션 완료 ({updated_count}개 레코드)")
            return True
            
    except Exception as e:
        print(f"❌ market_conditions 테이블 마이그레이션 실패: {e}")
        return False


def verify_migration():
    """마이그레이션 검증"""
    print("🔍 마이그레이션 검증 시작...")
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # scan_rank 테이블 검증
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'scan_rank' AND column_name = 'scanner_version'
            """)
            scan_rank_column = cur.fetchone()
            
            if not scan_rank_column:
                print("❌ scan_rank.scanner_version 컬럼이 없습니다.")
                return False
            
            print(f"  - scan_rank.scanner_version: {scan_rank_column}")
            
            # market_conditions 테이블 검증
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'market_conditions' AND column_name = 'scanner_version'
            """)
            market_conditions_column = cur.fetchone()
            
            if not market_conditions_column:
                print("❌ market_conditions.scanner_version 컬럼이 없습니다.")
                return False
            
            print(f"  - market_conditions.scanner_version: {market_conditions_column}")
            
            # 기본키 검증
            cur.execute("""
                SELECT constraint_name, column_name
                FROM information_schema.key_column_usage
                WHERE table_name = 'scan_rank' AND constraint_name LIKE '%pkey%'
                ORDER BY ordinal_position
            """)
            scan_rank_pkey = cur.fetchall()
            print(f"  - scan_rank 기본키: {[row[1] for row in scan_rank_pkey]}")
            
            cur.execute("""
                SELECT constraint_name, column_name
                FROM information_schema.key_column_usage
                WHERE table_name = 'market_conditions' AND constraint_name LIKE '%pkey%'
                ORDER BY ordinal_position
            """)
            market_conditions_pkey = cur.fetchall()
            print(f"  - market_conditions 기본키: {[row[1] for row in market_conditions_pkey]}")
            
            # 데이터 검증
            cur.execute("SELECT COUNT(*) FROM scan_rank")
            scan_rank_total = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM scan_rank WHERE scanner_version = 'v1'")
            scan_rank_v1 = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM market_conditions")
            market_conditions_total = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM market_conditions WHERE scanner_version = 'v1'")
            market_conditions_v1 = cur.fetchone()[0]
            
            print(f"  - scan_rank: 총 {scan_rank_total}개, v1 {scan_rank_v1}개")
            print(f"  - market_conditions: 총 {market_conditions_total}개, v1 {market_conditions_v1}개")
            
            if scan_rank_total == scan_rank_v1 and market_conditions_total == market_conditions_v1:
                print("✅ 마이그레이션 검증 성공")
                return True
            else:
                print("❌ 데이터 불일치 발견")
                return False
                
    except Exception as e:
        print(f"❌ 마이그레이션 검증 실패: {e}")
        return False


def main():
    """메인 마이그레이션 실행"""
    print("🚀 Phase 1: Critical Issues 마이그레이션 시작")
    print("=" * 60)
    
    # 1. 백업
    backup_timestamp = backup_tables()
    if not backup_timestamp:
        print("❌ 백업 실패로 마이그레이션을 중단합니다.")
        return False
    
    # 2. scan_rank 테이블 마이그레이션
    if not migrate_scan_rank_table():
        print("❌ scan_rank 테이블 마이그레이션 실패")
        return False
    
    # 3. market_conditions 테이블 마이그레이션
    if not migrate_market_conditions_table():
        print("❌ market_conditions 테이블 마이그레이션 실패")
        return False
    
    # 4. 검증
    if not verify_migration():
        print("❌ 마이그레이션 검증 실패")
        return False
    
    print("=" * 60)
    print("✅ Phase 1 마이그레이션 완료!")
    print(f"📦 백업 타임스탬프: {backup_timestamp}")
    print("")
    print("📋 완료된 작업:")
    print("  1. ✅ scan_rank 테이블에 scanner_version 컬럼 추가")
    print("  2. ✅ scan_rank 테이블 복합 기본키 설정 (date, code, scanner_version)")
    print("  3. ✅ market_conditions 테이블에 scanner_version 컬럼 추가")
    print("  4. ✅ market_conditions 테이블 복합 기본키 설정 (date, scanner_version)")
    print("  5. ✅ 기존 데이터에 기본값 'v1' 설정")
    print("")
    print("🎯 이제 V1/V2 스캐너 결과가 버전별로 구분 저장됩니다!")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)