"""
관리자 서비스
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from auth_models import User, MembershipTier, SubscriptionStatus, AdminStatsResponse

class AdminService:
    def __init__(self, db_path: str = "snapshots.db"):
        self.db_path = db_path
    
    def is_admin(self, user_id: int) -> bool:
        """관리자 권한 확인"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # 먼저 사용자가 존재하는지 확인
            cur.execute("SELECT id, is_admin FROM users WHERE id = ?", (user_id,))
            result = cur.fetchone()
            conn.close()
            
            if not result:
                print(f"사용자 ID {user_id}를 찾을 수 없습니다")
                return False
            
            is_admin_value = result[1]
            print(f"사용자 ID {user_id}의 is_admin 값: {is_admin_value} (타입: {type(is_admin_value)})")
            
            # is_admin 값이 1 또는 True인 경우 관리자로 인정
            return is_admin_value == 1 or is_admin_value is True
        except Exception as e:
            print(f"관리자 권한 확인 오류: {e}")
            return False
    
    def get_all_users(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """모든 사용자 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, email, name, provider, membership_tier, subscription_status, 
                       subscription_expires_at, is_admin, created_at
                FROM users 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            users = []
            for row in cur.fetchall():
                users.append({
                    "id": row[0],
                    "email": row[1],
                    "name": row[2],
                    "provider": row[3],
                    "membership_tier": row[4],
                    "subscription_status": row[5],
                    "subscription_expires_at": row[6],
                    "is_admin": bool(row[7]),
                    "created_at": row[8]
                })
            
            conn.close()
            return users
        except Exception as e:
            print(f"사용자 목록 조회 오류: {e}")
            return []
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """특정 사용자 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, email, name, provider, membership_tier, subscription_status, 
                       subscription_expires_at, is_admin, created_at
                FROM users 
                WHERE id = ?
            """, (user_id,))
            
            row = cur.fetchone()
            conn.close()
            
            if row:
                return {
                    "id": row[0],
                    "email": row[1],
                    "name": row[2],
                    "provider": row[3],
                    "membership_tier": row[4],
                    "subscription_status": row[5],
                    "subscription_expires_at": row[6],
                    "is_admin": bool(row[7]),
                    "created_at": row[8]
                }
            return None
        except Exception as e:
            print(f"사용자 조회 오류: {e}")
            return None
    
    def update_user(self, user_id: int, updates: Dict) -> bool:
        """사용자 정보 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # 업데이트할 필드들 구성
            set_clauses = []
            values = []
            
            if "membership_tier" in updates:
                set_clauses.append("membership_tier = ?")
                values.append(updates["membership_tier"])
            
            if "subscription_status" in updates:
                set_clauses.append("subscription_status = ?")
                values.append(updates["subscription_status"])
            
            if "subscription_expires_at" in updates:
                set_clauses.append("subscription_expires_at = ?")
                values.append(updates["subscription_expires_at"])
            
            if "is_admin" in updates:
                set_clauses.append("is_admin = ?")
                values.append(1 if updates["is_admin"] else 0)
            
            if not set_clauses:
                return False
            
            values.append(user_id)
            # 안전한 쿼리 구성 - 미리 정의된 필드만 허용
            allowed_fields = {
                "membership_tier": "membership_tier = ?",
                "subscription_status": "subscription_status = ?", 
                "subscription_expires_at": "subscription_expires_at = ?",
                "is_admin": "is_admin = ?"
            }
            
            valid_clauses = [allowed_fields[field] for field in updates.keys() if field in allowed_fields]
            if not valid_clauses:
                return False
                
            query = f"UPDATE users SET {', '.join(valid_clauses)} WHERE id = ?"
            
            cur.execute(query, values)
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"사용자 업데이트 오류: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """사용자 삭제"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # 관련 데이터 삭제 (외래키 제약조건 고려)
            cur.execute("DELETE FROM payments WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"사용자 삭제 오류: {e}")
            return False
    
    def get_admin_stats(self) -> AdminStatsResponse:
        """관리자 통계 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # 전체 사용자 수
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()[0]
            
            # 등급별 사용자 수
            cur.execute("SELECT membership_tier, COUNT(*) FROM users GROUP BY membership_tier")
            tier_counts = dict(cur.fetchall())
            
            free_users = tier_counts.get('free', 0)
            premium_users = tier_counts.get('premium', 0)
            vip_users = tier_counts.get('vip', 0)
            
            # 활성 구독 수
            cur.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
            active_subscriptions = cur.fetchone()[0]
            
            # 총 수익
            cur.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed'")
            total_revenue = cur.fetchone()[0] or 0
            
            # 최근 가입 사용자
            cur.execute("""
                SELECT id, email, name, provider, membership_tier, created_at
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            
            recent_users = []
            for row in cur.fetchall():
                recent_users.append({
                    "id": row[0],
                    "email": row[1],
                    "name": row[2] or "이름 없음",  # None 값 처리
                    "provider": row[3] or "local",  # None 값 처리
                    "provider_id": f"{row[3] or 'local'}_{row[0]}",  # provider_id 추가
                    "membership_tier": row[4] or "free",  # None 값 처리
                    "subscription_status": "active",  # 기본값
                    "is_admin": False,  # 기본값
                    "is_active": True,  # 기본값
                    "created_at": row[5]
                })
            
            conn.close()
            
            return AdminStatsResponse(
                total_users=total_users,
                free_users=free_users,
                premium_users=premium_users,
                vip_users=vip_users,
                active_subscriptions=active_subscriptions,
                total_revenue=total_revenue,
                recent_users=recent_users
            )
        except Exception as e:
            print(f"관리자 통계 조회 오류: {e}")
            return AdminStatsResponse(
                total_users=0,
                free_users=0,
                premium_users=0,
                vip_users=0,
                active_subscriptions=0,
                total_revenue=0,
                recent_users=[]
            )

# 전역 인스턴스
admin_service = AdminService()
