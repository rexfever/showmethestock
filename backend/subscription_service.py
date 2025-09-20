"""
구독 관리 서비스
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List
from auth_models import User, MembershipTier, SubscriptionStatus
from subscription_plans import get_plan, get_user_permissions

class SubscriptionService:
    def __init__(self, db_path: str = "snapshots.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """구독 관련 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # 구독 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id TEXT NOT NULL,
                payment_id TEXT,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                cancelled_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # 결제 내역 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subscription_id INTEGER,
                payment_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                method TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
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
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO subscriptions (user_id, plan_id, payment_id, amount, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, plan_id, payment_id, amount, expires_at.isoformat()))
            
            subscription_id = cur.lastrowid
            
            # 결제 내역 저장
            cur.execute("""
                INSERT INTO payments (user_id, subscription_id, payment_id, amount, method, status)
                VALUES (?, ?, ?, ?, 'kakaopay', 'completed')
            """, (user_id, subscription_id, payment_id, amount))
            
            # 사용자 등급 업데이트
            plan = get_plan(plan_id)
            if plan:
                cur.execute("""
                    UPDATE users 
                    SET membership_tier = ?, subscription_status = ?, subscription_expires_at = ?, payment_method = 'kakaopay'
                    WHERE id = ?
                """, (plan.tier.value, SubscriptionStatus.ACTIVE.value, expires_at.isoformat(), user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"구독 생성 오류: {e}")
            return False
    
    def get_user_subscription(self, user_id: int) -> Optional[dict]:
        """사용자 구독 정보 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT s.*, u.membership_tier, u.subscription_status, u.subscription_expires_at
                FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                WHERE s.user_id = ? AND s.status = 'active'
                ORDER BY s.created_at DESC
                LIMIT 1
            """, (user_id,))
            
            row = cur.fetchone()
            conn.close()
            
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "plan_id": row[2],
                    "payment_id": row[3],
                    "amount": row[4],
                    "status": row[5],
                    "started_at": row[6],
                    "expires_at": row[7],
                    "cancelled_at": row[8],
                    "created_at": row[9],
                    "membership_tier": row[10],
                    "subscription_status": row[11],
                    "subscription_expires_at": row[12]
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
        
        expires_at = datetime.fromisoformat(subscription["expires_at"])
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
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # 구독 상태를 만료로 변경
            cur.execute("""
                UPDATE subscriptions 
                SET status = 'expired' 
                WHERE user_id = ? AND status = 'active'
            """, (user_id,))
            
            # 사용자 등급을 FREE로 변경
            cur.execute("""
                UPDATE users 
                SET membership_tier = 'free', subscription_status = 'expired'
                WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"구독 만료 처리 오류: {e}")
            return False
    
    def cancel_subscription(self, user_id: int) -> bool:
        """구독 취소"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # 구독 상태를 취소로 변경
            cur.execute("""
                UPDATE subscriptions 
                SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND status = 'active'
            """, (user_id,))
            
            # 사용자 등급을 FREE로 변경
            cur.execute("""
                UPDATE users 
                SET membership_tier = 'free', subscription_status = 'cancelled'
                WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
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
