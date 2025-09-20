from pydantic import BaseModel
from typing import Optional, Literal, List
from datetime import datetime
from enum import Enum

class MembershipTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    VIP = "vip"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"

class PaymentMethod(str, Enum):
    KAKAOPAY = "kakaopay"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"

class UserBase(BaseModel):
    email: str
    name: str
    provider: str  # 'kakao', 'naver', 'toss', 'local'
    provider_id: str
    # 필수 정보
    birth_year: Optional[int] = None
    kakao_account: Optional[str] = None  # 전화번호
    # 선택 정보
    gender: Optional[str] = None
    age_group: Optional[str] = None
    birthday: Optional[str] = None
    is_profile_complete: bool = False
    # 회원 등급 정보
    membership_tier: MembershipTier = MembershipTier.FREE
    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    subscription_expires_at: Optional[datetime] = None
    payment_method: Optional[PaymentMethod] = None
    # 관리자 권한
    is_admin: bool = False
    # 활성 상태
    is_active: bool = True

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class TokenData(BaseModel):
    email: Optional[str] = None

class SocialLoginRequest(BaseModel):
    provider: str  # 'kakao', 'naver', 'toss'
    access_token: str
    user_info: dict

class EmailSignupRequest(BaseModel):
    email: str
    password: str
    name: str
    birth_year: Optional[int] = None
    gender: Optional[str] = None
    age_group: Optional[str] = None
    birthday: Optional[str] = None

class EmailLoginRequest(BaseModel):
    email: str
    password: str

class EmailVerificationRequest(BaseModel):
    email: str
    verification_code: str

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirmRequest(BaseModel):
    email: str
    verification_code: str
    new_password: str

# 결제 및 구독 관련 모델
class SubscriptionPlan(BaseModel):
    id: str
    name: str
    tier: MembershipTier
    price: int  # 원 단위
    duration_days: int
    features: List[str]

class PaymentRequest(BaseModel):
    plan_id: str
    payment_method: PaymentMethod
    return_url: str
    cancel_url: str

class PaymentResponse(BaseModel):
    payment_id: str
    payment_url: str
    amount: int
    status: str

class KakaoPayRequest(BaseModel):
    cid: str = "TC0ONETIME"  # 테스트용 CID
    partner_order_id: str
    partner_user_id: str
    item_name: str
    quantity: int = 1
    total_amount: int
    tax_free_amount: int = 0
    approval_url: str
    cancel_url: str
    fail_url: str

class KakaoPayResponse(BaseModel):
    tid: str
    next_redirect_pc_url: str
    next_redirect_mobile_url: str
    next_redirect_app_url: str
    android_app_scheme: str
    ios_app_scheme: str
    created_at: str

# 관리자 관련 모델
class AdminUserUpdateRequest(BaseModel):
    user_id: int
    membership_tier: Optional[MembershipTier] = None
    subscription_status: Optional[SubscriptionStatus] = None
    subscription_expires_at: Optional[datetime] = None
    is_admin: Optional[bool] = None

class AdminUserDeleteRequest(BaseModel):
    user_id: int
    confirm: bool = False

class AdminStatsResponse(BaseModel):
    total_users: int
    free_users: int
    premium_users: int
    vip_users: int
    active_subscriptions: int
    total_revenue: int
    recent_users: List[User]
