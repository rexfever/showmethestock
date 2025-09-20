"""
구독 플랜 정의 및 관리
"""
from auth_models import SubscriptionPlan, MembershipTier
from typing import List

# 구독 플랜 정의
SUBSCRIPTION_PLANS = {
    "premium_monthly": SubscriptionPlan(
        id="premium_monthly",
        name="프리미엄 월간",
        tier=MembershipTier.PREMIUM,
        price=9900,  # 9,900원
        duration_days=30,
        features=[
            "무제한 스캔",
            "실시간 알림",
            "포트폴리오 관리",
            "고급 분석 도구",
            "우선 고객 지원"
        ]
    ),
    "premium_yearly": SubscriptionPlan(
        id="premium_yearly",
        name="프리미엄 연간",
        tier=MembershipTier.PREMIUM,
        price=99000,  # 99,000원 (월 8,250원)
        duration_days=365,
        features=[
            "무제한 스캔",
            "실시간 알림",
            "포트폴리오 관리",
            "고급 분석 도구",
            "우선 고객 지원",
            "연간 구독 20% 할인"
        ]
    ),
    "vip_monthly": SubscriptionPlan(
        id="vip_monthly",
        name="VIP 월간",
        tier=MembershipTier.VIP,
        price=19900,  # 19,900원
        duration_days=30,
        features=[
            "모든 프리미엄 기능",
            "개인 맞춤 분석",
            "전화 상담 지원",
            "우선 신호 알림",
            "전용 VIP 채널"
        ]
    ),
    "vip_yearly": SubscriptionPlan(
        id="vip_yearly",
        name="VIP 연간",
        tier=MembershipTier.VIP,
        price=199000,  # 199,000원 (월 16,583원)
        duration_days=365,
        features=[
            "모든 프리미엄 기능",
            "개인 맞춤 분석",
            "전화 상담 지원",
            "우선 신호 알림",
            "전용 VIP 채널",
            "연간 구독 20% 할인"
        ]
    )
}

def get_plan(plan_id: str) -> SubscriptionPlan:
    """플랜 ID로 구독 플랜 조회"""
    return SUBSCRIPTION_PLANS.get(plan_id)

def get_plans_by_tier(tier: MembershipTier) -> List[SubscriptionPlan]:
    """등급별 구독 플랜 조회"""
    return [plan for plan in SUBSCRIPTION_PLANS.values() if plan.tier == tier]

def get_all_plans() -> List[SubscriptionPlan]:
    """모든 구독 플랜 조회"""
    return list(SUBSCRIPTION_PLANS.values())

# 등급별 권한 정의
MEMBERSHIP_PERMISSIONS = {
    MembershipTier.FREE: {
        "daily_scans": 3,
        "portfolio_items": 5,
        "notifications": False,
        "advanced_analysis": False,
        "priority_support": False
    },
    MembershipTier.PREMIUM: {
        "daily_scans": -1,  # 무제한
        "portfolio_items": -1,  # 무제한
        "notifications": True,
        "advanced_analysis": True,
        "priority_support": True
    },
    MembershipTier.VIP: {
        "daily_scans": -1,  # 무제한
        "portfolio_items": -1,  # 무제한
        "notifications": True,
        "advanced_analysis": True,
        "priority_support": True,
        "personal_consultation": True,
        "vip_channel": True
    }
}

def get_user_permissions(tier: MembershipTier) -> dict:
    """사용자 등급별 권한 조회"""
    return MEMBERSHIP_PERMISSIONS.get(tier, MEMBERSHIP_PERMISSIONS[MembershipTier.FREE])

def check_permission(tier: MembershipTier, permission: str) -> bool:
    """특정 권한 확인"""
    permissions = get_user_permissions(tier)
    return permissions.get(permission, False)
