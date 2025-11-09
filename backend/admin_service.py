"""
관리자 서비스
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from auth_models import User, MembershipTier, SubscriptionStatus, AdminStatsResponse
from db_manager import db_manager

class AdminService:
    def __init__(self):
        pass
    
    def is_admin(self, user_id: int) -> bool:
        """관리자 권한 확인"""
        try:
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("SELECT id, is_admin FROM users WHERE id = %s", (user_id,))
                result = cur.fetchone()

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
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                SELECT id, email, name, provider, membership_tier, subscription_status, 
                       subscription_expires_at, is_admin, created_at
                FROM users 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """, (limit, offset))
                rows = cur.fetchall()

            users = []
            for row in rows:
                created_at = row[8]
                if isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                users.append({
                    "id": row[0],
                    "email": row[1],
                    "name": row[2],
                    "provider": row[3],
                    "membership_tier": row[4],
                    "subscription_status": row[5],
                    "subscription_expires_at": row[6],
                    "is_admin": bool(row[7]),
                    "created_at": created_at
                })
            return users
        except Exception as e:
            print(f"사용자 목록 조회 오류: {e}")
            return []
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """특정 사용자 조회"""
        try:
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                SELECT id, email, name, provider, membership_tier, subscription_status, 
                       subscription_expires_at, is_admin, created_at
                FROM users 
                WHERE id = %s
            """, (user_id,))
                row = cur.fetchone()

            if row:
                created_at = row[8]
                if isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                return {
                    "id": row[0],
                    "email": row[1],
                    "name": row[2],
                    "provider": row[3],
                    "membership_tier": row[4],
                    "subscription_status": row[5],
                    "subscription_expires_at": row[6],
                    "is_admin": bool(row[7]),
                    "created_at": created_at
                }
            return None
        except Exception as e:
            print(f"사용자 조회 오류: {e}")
            return None
    
    def update_user(self, user_id: int, updates: Dict) -> bool:
        """사용자 정보 업데이트"""
        try:
            # 업데이트할 필드들 구성
            update_fields = []
            params = []
            
            if "membership_tier" in updates:
                update_fields.append("membership_tier = %s")
                params.append(updates["membership_tier"])
            
            if "subscription_status" in updates:
                update_fields.append("subscription_status = %s")
                params.append(updates["subscription_status"])
            
            if "subscription_expires_at" in updates:
                update_fields.append("subscription_expires_at = %s")
                params.append(updates["subscription_expires_at"])
            
            if "is_admin" in updates:
                update_fields.append("is_admin = %s")
                params.append(bool(updates["is_admin"]))
            
            if not update_fields:
                return False
            
            with db_manager.get_cursor() as cur:
                cur.execute(
                    f"UPDATE users SET {', '.join(update_fields + ['updated_at = NOW()'])} WHERE id = %s",
                    params + [user_id],
                )
            return True
        except Exception as e:
            print(f"사용자 업데이트 오류: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """사용자 삭제"""
        try:
            with db_manager.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM payments WHERE user_id = %s", (user_id,))
                cur.execute("DELETE FROM subscriptions WHERE user_id = %s", (user_id,))
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
            return True
        except Exception as e:
            print(f"사용자 삭제 오류: {e}")
            return False
    
    def get_admin_stats(self) -> AdminStatsResponse:
        """관리자 통계 조회"""
        try:
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]
                
                cur.execute("SELECT membership_tier, COUNT(*) FROM users GROUP BY membership_tier")
                tier_counts = dict(cur.fetchall())
            
            free_users = tier_counts.get('free', 0)
            premium_users = tier_counts.get('premium', 0)
            vip_users = tier_counts.get('vip', 0)
            
            # 활성 구독 수
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
                active_subscriptions = cur.fetchone()[0]
                
                cur.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed'")
                total_revenue = cur.fetchone()[0] or 0
                
                cur.execute("""
                SELECT id, email, name, provider, membership_tier, created_at
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
                rows = cur.fetchall()
            
            recent_users = []
            for row in rows:
                created_at = row[5]
                if isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                recent_users.append({
                    "id": row[0],
                    "email": row[1],
                    "name": row[2] or "이름 없음",
                    "provider": row[3] or "local",
                    "provider_id": f"{row[3] or 'local'}_{row[0]}",
                    "membership_tier": row[4] or "free",
                    "subscription_status": "active",
                    "is_admin": False,
                    "is_active": True,
                    "created_at": created_at
                })
            
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
