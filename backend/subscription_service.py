"""
구독 관리 서비스
"""
from datetime import datetime, timedelta
from typing import Optional, List
from auth_models import User, MembershipTier, SubscriptionStatus
from subscription_plans import get_plan, get_user_permissions
from db_manager import db_manager

class SubscriptionService:
    def __init__(self):
        self.init_db()
    
    def init_db(self):
        """구독 관련 테이블 초기화"""
        with db_manager.get_cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    plan_id TEXT NOT NULL,
                    payment_id TEXT,
                    amount INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    started_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP NOT NULL,
                    cancelled_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    subscription_id INTEGER REFERENCES subscriptions(id),
                    payment_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    method TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
    
    def create_subscription(
        self, 
        user_id: int, 
        plan_id: str, 
        payment_id: str, 
        amount: int,
        expires_at: datetime
    ) -> bool:
        """구독 생성"""
        try:
            with db_manager.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO subscriptions (user_id, plan_id, payment_id, amount, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, plan_id, payment_id, amount, expires_at))
                subscription_id = cur.fetchone()[0]
                
                cur.execute("""
                    INSERT INTO payments (user_id, subscription_id, payment_id, amount, method, status)
                    VALUES (%s, %s, %s, %s, 'kakaopay', 'completed')
                """, (user_id, subscription_id, payment_id, amount))
                
                plan = get_plan(plan_id)
                if plan:
                    cur.execute("""
                        UPDATE users 
                        SET membership_tier = %s,
                            subscription_status = %s,
                            subscription_expires_at = %s,
                            payment_method = 'kakaopay'
                        WHERE id = %s
                    """, (plan.tier.value, SubscriptionStatus.ACTIVE.value, expires_at, user_id))
                conn.commit()
            return True
            
        except Exception as e:
            print(f"구독 생성 오류: {e}")
            return False
    
    def get_user_subscription(self, user_id: int) -> Optional[dict]:
        """사용자 구독 정보 조회"""
        try:
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                SELECT s.*, u.membership_tier, u.subscription_status, u.subscription_expires_at
                FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                WHERE s.user_id = %s AND s.status = 'active'
                ORDER BY s.created_at DESC
                LIMIT 1
            """, (user_id,))
                row = cur.fetchone()
            
            if row:
                started_at = row[6]
                expires_at = row[7]
                cancelled_at = row[8]
                created_at = row[9]
                subscription_expires_at = row[12]

                if isinstance(started_at, datetime):
                    started_at = started_at.isoformat()
                if isinstance(expires_at, datetime):
                    expires_at = expires_at.isoformat()
                if isinstance(cancelled_at, datetime):
                    cancelled_at = cancelled_at.isoformat()
                if isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                if isinstance(subscription_expires_at, datetime):
                    subscription_expires_at = subscription_expires_at.isoformat()

                return {
                    "id": row[0],
                    "user_id": row[1],
                    "plan_id": row[2],
                    "payment_id": row[3],
                    "amount": row[4],
                    "status": row[5],
                    "started_at": started_at,
                    "expires_at": expires_at,
                    "cancelled_at": cancelled_at,
                    "created_at": created_at,
                    "membership_tier": row[10],
                    "subscription_status": row[11],
                    "subscription_expires_at": subscription_expires_at
                }
            return None
            
        except Exception as e:
            print(f"구독 정보 조회 오류: {e}")
            return None
    
    def check_subscription_status(self, user_id: int) -> dict:
        """구독 상태 확인"""
        subscription = self.get_user_subscription(user_id)
        
        if not subscription:
            return {
                "is_active": False,
                "tier": MembershipTier.FREE,
                "expires_at": None,
                "days_remaining": 0
            }
        
        expires_at = subscription["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        now = datetime.now()
        
        if expires_at > now:
            days_remaining = (expires_at - now).days
            return {
                "is_active": True,
                "tier": MembershipTier(subscription["membership_tier"]),
                "expires_at": expires_at,
                "days_remaining": days_remaining
            }
        else:
            # 구독 만료 처리
            self.expire_subscription(user_id)
            return {
                "is_active": False,
                "tier": MembershipTier.FREE,
                "expires_at": expires_at,
                "days_remaining": 0
            }
    
    def expire_subscription(self, user_id: int) -> bool:
        """구독 만료 처리"""
        try:
            with db_manager.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE subscriptions 
                    SET status = 'expired' 
                    WHERE user_id = %s AND status = 'active'
                """, (user_id,))
                
                cur.execute("""
                    UPDATE users 
                    SET membership_tier = 'free',
                        subscription_status = 'expired',
                        subscription_expires_at = NOW()
                    WHERE id = %s
                """, (user_id,))
                conn.commit()
            return True
            
        except Exception as e:
            print(f"구독 만료 처리 오류: {e}")
            return False
    
    def cancel_subscription(self, user_id: int) -> bool:
        """구독 취소"""
        try:
            with db_manager.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE subscriptions 
                    SET status = 'cancelled', cancelled_at = NOW()
                    WHERE user_id = %s AND status = 'active'
                """, (user_id,))
                
                cur.execute("""
                    UPDATE users 
                    SET membership_tier = 'free',
                        subscription_status = 'cancelled'
                    WHERE id = %s
                """, (user_id,))
                conn.commit()
            return True
            
        except Exception as e:
            print(f"구독 취소 오류: {e}")
            return False
    
    def get_user_permissions(self, user_id: int) -> dict:
        """사용자 권한 조회"""
        subscription_status = self.check_subscription_status(user_id)
        tier = subscription_status["tier"]
        return get_user_permissions(tier)
    
    def check_permission(self, user_id: int, permission: str) -> bool:
        """특정 권한 확인"""
        permissions = self.get_user_permissions(user_id)
        return permissions.get(permission, False)

# 전역 인스턴스
subscription_service = SubscriptionService()
