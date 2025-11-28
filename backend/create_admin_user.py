#!/usr/bin/env python3
"""
관리자 계정 생성/설정 스크립트
"""
import sys
from db_manager import db_manager

def create_or_update_admin(email: str, name: str = None, password: str = None):
    """관리자 계정 생성 또는 업데이트"""
    try:
        with db_manager.get_cursor(commit=True) as cur:
            # 기존 사용자 확인
            cur.execute("SELECT id, email, name, is_admin FROM users WHERE email = %s", (email,))
            existing = cur.fetchone()
            
            if existing:
                # 기존 사용자를 관리자로 설정
                cur.execute("UPDATE users SET is_admin = true WHERE email = %s", (email,))
                print(f"✅ 기존 사용자를 관리자로 설정: {email} (ID: {existing[0]})")
                return existing[0]
            else:
                # 새 관리자 계정 생성
                if not name:
                    name = email.split('@')[0]
                
                cur.execute("""
                    INSERT INTO users (email, name, provider, provider_id, is_admin, is_email_verified, is_active)
                    VALUES (%s, %s, 'local', %s, true, true, true)
                    RETURNING id
                """, (email, name, email))
                
                user_id = cur.fetchone()[0]
                print(f"✅ 새 관리자 계정 생성: {email} (ID: {user_id})")
                return user_id
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

def list_admins():
    """관리자 목록 조회"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, email, name, is_admin, created_at 
                FROM users 
                WHERE is_admin = true
                ORDER BY created_at DESC
            """)
            admins = cur.fetchall()
            
            if admins:
                print("\n✅ 관리자 계정 목록:")
                for admin in admins:
                    print(f"   - ID: {admin[0]}, Email: {admin[1]}, Name: {admin[2]}, Created: {admin[4]}")
                return admins
            else:
                print("\n❌ 관리자 계정이 없습니다.")
                return []
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return []

if __name__ == "__main__":
    if len(sys.argv) > 1:
        email = sys.argv[1]
        name = sys.argv[2] if len(sys.argv) > 2 else None
        create_or_update_admin(email, name)
    else:
        print("사용법:")
        print("  python3 create_admin_user.py <email> [name]")
        print("")
        print("예시:")
        print("  python3 create_admin_user.py admin@example.com '관리자'")
        print("")
    
    list_admins()

