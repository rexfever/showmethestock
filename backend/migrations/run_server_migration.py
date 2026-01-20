#!/usr/bin/env python3
"""
서버 DB에 마이그레이션을 실행하는 스크립트
SSH 터널을 통해 서버 DB에 접근하여 마이그레이션을 실행합니다.
"""

import os
import sys
import subprocess

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_ssh_tunnel():
    """SSH 터널이 활성화되어 있는지 확인"""
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        if 'ssh.*5433:localhost:5432.*sohntech' in result.stdout:
            return True
    except:
        pass
    return False


def create_ssh_tunnel():
    """SSH 터널 생성"""
    print("🔗 SSH 터널 생성 중...")
    try:
        subprocess.run(
            ['ssh', '-f', '-N', '-L', '5433:localhost:5432', 'ubuntu@sohntech.ai.kr'],
            check=True
        )
        import time
        time.sleep(2)
        print("✅ SSH 터널 생성 완료")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ SSH 터널 생성 실패: {e}")
        return False


def run_migration_on_server():
    """서버 DB에 마이그레이션 실행"""
    # SSH 터널 확인 및 생성
    if not check_ssh_tunnel():
        if not create_ssh_tunnel():
            print("❌ SSH 터널을 생성할 수 없습니다.")
            return False
    
    # 서버 DB URL 설정
    server_db_url = "postgresql://stockfinder:stockfinder_pass@localhost:5433/stockfinder"
    os.environ['DATABASE_URL'] = server_db_url
    os.environ['SERVER_DATABASE_URL'] = server_db_url
    
    print("=" * 60)
    print("서버 DB 마이그레이션 실행")
    print("=" * 60)
    print(f"서버 DB URL: {server_db_url.split('@')[0]}@***")
    
    # db_manager 재로드
    if 'db_manager' in sys.modules:
        import importlib
        importlib.reload(sys.modules['db_manager'])
    
    # 1. returns 컬럼 JSONB 변환
    print("\n1️⃣ returns 컬럼 JSONB 변환...")
    try:
        from migrations.convert_returns_to_jsonb import convert_returns_to_jsonb
        if not convert_returns_to_jsonb():
            print("❌ returns 컬럼 변환 실패")
            return False
    except Exception as e:
        print(f"❌ returns 컬럼 변환 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. returns 데이터 업데이트
    print("\n2️⃣ returns 데이터 업데이트...")
    try:
        from migrations.update_returns_data import main as update_returns_main
        # 자동으로 'y' 입력
        import io
        import contextlib
        
        # 사용자 입력을 자동으로 'y'로 설정
        original_input = __builtins__['input']
        __builtins__['input'] = lambda prompt='': 'y'
        
        try:
            update_returns_main()
        finally:
            __builtins__['input'] = original_input
            
    except Exception as e:
        print(f"❌ returns 데이터 업데이트 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ 서버 DB 마이그레이션 완료!")
    return True


if __name__ == "__main__":
    success = run_migration_on_server()
    sys.exit(0 if success else 1)

