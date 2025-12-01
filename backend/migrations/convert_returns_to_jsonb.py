#!/usr/bin/env python3
"""
scan_rank 테이블의 returns 컬럼을 TEXT에서 JSONB로 변환하는 마이그레이션 스크립트
"""

import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import db_manager


def check_returns_column_type():
    """returns 컬럼 타입 확인"""
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'scan_rank' AND column_name = 'returns'
        """)
        result = cur.fetchone()
        return result[0] if result else None


def convert_returns_to_jsonb():
    """returns 컬럼을 JSONB로 변환"""
    print("=" * 60)
    print("scan_rank 테이블 returns 컬럼 JSONB 변환")
    print("=" * 60)
    
    # 현재 타입 확인
    current_type = check_returns_column_type()
    print(f"\n현재 returns 컬럼 타입: {current_type}")
    
    if current_type == 'jsonb':
        print("✅ returns 컬럼이 이미 JSONB 타입입니다.")
        return True
    
    if current_type != 'text':
        print(f"⚠️ 예상치 못한 타입입니다: {current_type}")
        return False
    
    # 사용자 확인
    response = input("\nreturns 컬럼을 TEXT에서 JSONB로 변환하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("❌ 취소되었습니다.")
        return False
    
    try:
        print("\n🔄 변환 시작...")
        
        with db_manager.get_cursor(commit=True) as cur:
            # 1. 유효한 JSON이 아닌 데이터 확인
            print("  - 유효하지 않은 JSON 데이터 확인 중...")
            cur.execute("""
                SELECT COUNT(*) 
                FROM scan_rank 
                WHERE returns IS NOT NULL 
                  AND returns != '' 
                  AND returns != '{}' 
                  AND returns != 'null'
                  AND returns::jsonb IS NULL
            """)
            invalid_count = cur.fetchone()[0]
            
            if invalid_count > 0:
                print(f"  ⚠️ 유효하지 않은 JSON 데이터: {invalid_count}개")
                print("  - 빈 문자열로 변환합니다...")
                cur.execute("""
                    UPDATE scan_rank
                    SET returns = '{}'
                    WHERE returns IS NOT NULL 
                      AND returns != '' 
                      AND returns != '{}' 
                      AND returns != 'null'
                      AND returns::jsonb IS NULL
                """)
            
            # 2. 빈 문자열을 NULL로 변환
            print("  - 빈 문자열을 NULL로 변환 중...")
            cur.execute("""
                UPDATE scan_rank
                SET returns = NULL
                WHERE returns = '' OR returns = 'null'
            """)
            
            # 3. 컬럼 타입 변경
            print("  - 컬럼 타입을 JSONB로 변경 중...")
            cur.execute("""
                ALTER TABLE scan_rank
                ALTER COLUMN returns TYPE JSONB
                USING CASE 
                    WHEN returns IS NULL THEN NULL
                    WHEN returns = '' THEN NULL
                    WHEN returns = '{}' THEN '{}'::jsonb
                    WHEN returns = 'null' THEN NULL
                    ELSE returns::jsonb
                END
            """)
        
        print("\n✅ 변환 완료!")
        
        # 최종 타입 확인
        final_type = check_returns_column_type()
        print(f"변환 후 타입: {final_type}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 변환 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    convert_returns_to_jsonb()

