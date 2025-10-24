#!/usr/bin/env python3
"""
관리자 사용자 설정 스크립트
특정 이메일을 가진 사용자를 관리자로 설정합니다.
"""

import sqlite3
import sys

def fix_admin_users():
    """관리자 사용자 설정"""
    # 관리자로 설정할 이메일 목록
    admin_emails = [
        "sohn@sohntech.ai.kr",
        "admin@sohntech.ai.kr",
        # 필요한 경우 여기에 추가 이메일 추가
    ]
    
    try:
        conn = sqlite3.connect('snapshots.db')
        cur = conn.cursor()
        
        # 현재 사용자 목록 확인
        cur.execute("SELECT id, email, name, is_admin FROM users")
        users = cur.fetchall()
        
        print("=== 현재 사용자 목록 ===")
        for user in users:
            print(f"ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, is_admin: {user[3]}")
        
        print("\n=== 관리자 권한 설정 ===")
        
        # 관리자 이메일 목록의 사용자들을 관리자로 설정
        for email in admin_emails:
            cur.execute("SELECT id, name FROM users WHERE email = ?", (email,))
            user = cur.fetchone()
            
            if user:
                user_id, name = user
                cur.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
                print(f"✅ {email} ({name}) - 관리자 권한 설정 완료")
            else:
                print(f"❌ {email} - 사용자를 찾을 수 없습니다")
        
        conn.commit()
        
        # 결과 확인
        print("\n=== 업데이트 후 관리자 목록 ===")
        cur.execute("SELECT id, email, name, is_admin FROM users WHERE is_admin = 1")
        admins = cur.fetchall()
        
        for admin in admins:
            print(f"ID: {admin[0]}, Email: {admin[1]}, Name: {admin[2]}, is_admin: {admin[3]}")
        
        conn.close()
        print("\n✅ 관리자 권한 설정이 완료되었습니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False
    
    return True

if __name__ == "__main__":
    fix_admin_users()