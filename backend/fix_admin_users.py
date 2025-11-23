#!/usr/bin/env python3
"""
관리자 사용자 설정 스크립트
특정 이메일을 가진 사용자를 관리자로 설정합니다.
"""

import sys
from db_manager import db_manager

def fix_admin_users():
    """관리자 사용자 설정"""
    # 관리자로 설정할 이메일 목록
    admin_emails = [
        "sohn@sohntech.ai.kr",
        "admin@sohntech.ai.kr",
        # 필요한 경우 여기에 추가 이메일 추가
    ]
    
    try:
        with db_manager.get_cursor(commit=True) as cur:
        cur.execute("SELECT id, email, name, is_admin FROM users")
        users = cur.fetchall()
        
        print("=== 현재 사용자 목록 ===")
        for user in users:
            print(f"ID: {user['id']}, Email: {user['email']}, Name: {user['name']}, is_admin: {user['is_admin']}")
        
        print("\n=== 관리자 권한 설정 ===")
        
        # 관리자 이메일 목록의 사용자들을 관리자로 설정
        with db_manager.get_cursor(commit=True) as cur:
        for email in admin_emails:
                cur.execute("SELECT id, name FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            
            if user:
                    user_id = user["id"]
                    name = user["name"]
                    cur.execute("UPDATE users SET is_admin = TRUE WHERE id = %s", (user_id,))
                print(f"✅ {email} ({name}) - 관리자 권한 설정 완료")
            else:
                print(f"❌ {email} - 사용자를 찾을 수 없습니다")
        
        with db_manager.get_cursor(commit=False) as cur:
        print("\n=== 업데이트 후 관리자 목록 ===")
            cur.execute("SELECT id, email, name, is_admin FROM users WHERE is_admin = TRUE")
        admins = cur.fetchall()
        
        for admin in admins:
            print(f"ID: {admin['id']}, Email: {admin['email']}, Name: {admin['name']}, is_admin: {admin['is_admin']}")
        
        print("\n✅ 관리자 권한 설정이 완료되었습니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False
    
    return True

if __name__ == "__main__":
    fix_admin_users()