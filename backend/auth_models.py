from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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
