#!/usr/bin/env python3
"""
DB 연결 상태 확인 스크립트
"""
import sys
import os

# backend 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def check_db_connection():
    """DB 연결 상태 확인"""
    try:
        from config import config
        print(f"📊 DB 연결 정보 확인")
        print(f"DATABASE_URL: {config.database_url}")
        
        if not config.database_url:
            print("❌ DATABASE_URL이 설정되지 않았습니다.")
            return False
        
        # DB 연결 테스트
        from db import get_connection
        
        print("🔄 DB 연결 테스트 중...")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()
                print(f"✅ PostgreSQL 연결 성공: {version[0]}")
        
        # market_regime_daily 테이블 존재 확인
        print("🔄 market_regime_daily 테이블 확인 중...")
        from db import fetch_one
        
        result = fetch_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'market_regime_daily'
            );
        """)
        
        if result and result[0]:
            print("✅ market_regime_daily 테이블 존재")
            
            # 테이블 구조 확인
            from db import fetch_all
            columns = fetch_all("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'market_regime_daily'
                ORDER BY ordinal_position;
            """)
            
            print("📋 테이블 구조:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]}")
        else:
            print("❌ market_regime_daily 테이블이 존재하지 않습니다.")
            print("💡 마이그레이션을 실행하세요: python backend/migrations/create_market_regime_daily.py")
        
        return True
        
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        print("💡 DB 설정을 확인하세요:")
        print("   1. PostgreSQL 서버가 실행 중인지 확인")
        print("   2. .env 파일의 DATABASE_URL 확인")
        print("   3. DB 사용자 권한 확인")
        return False

def check_env_file():
    """환경 변수 파일 확인"""
    print("\n📁 환경 변수 파일 확인:")
    
    # 루트 .env
    root_env = "/Users/rexsmac/workspace/stock-finder/.env"
    if os.path.exists(root_env):
        print(f"✅ 루트 .env 존재: {root_env}")
    else:
        print(f"❌ 루트 .env 없음: {root_env}")
    
    # backend/.env
    backend_env = "/Users/rexsmac/workspace/stock-finder/backend/.env"
    if os.path.exists(backend_env):
        print(f"✅ backend .env 존재: {backend_env}")
        
        # DATABASE_URL 확인
        with open(backend_env, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith('DATABASE_URL') or line.startswith('POSTGRES_DSN'):
                    print(f"   {line.strip()}")
    else:
        print(f"❌ backend .env 없음: {backend_env}")

if __name__ == "__main__":
    check_env_file()
    check_db_connection()