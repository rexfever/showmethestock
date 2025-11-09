import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from auth_models import User, UserCreate, TokenData, EmailSignupRequest, EmailLoginRequest, MembershipTier, SubscriptionStatus
from psycopg.errors import UniqueViolation
from email_service import email_service, email_verification_service
from db_manager import db_manager

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7일 (10080분)

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self):
        self.init_db()
    
    def _row_to_user(self, row) -> Optional[User]:
        if not row:
            return None
        return User(
            id=row[0],
            email=row[1],
            name=row[2],
            provider=row[3],
            provider_id=row[4],
            membership_tier=MembershipTier(row[5]) if row[5] else MembershipTier.FREE,
            subscription_status=SubscriptionStatus(row[6]) if row[6] else SubscriptionStatus.ACTIVE,
            subscription_expires_at=row[7],
            payment_method=row[8],
            is_admin=bool(row[9]),
            created_at=row[10],
            last_login=row[11],
            is_active=bool(row[12]),
        )
    
    def init_db(self):
        """사용자 테이블 초기화"""
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    password_hash TEXT,
                    is_email_verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    membership_tier TEXT DEFAULT 'free',
                    subscription_status TEXT DEFAULT 'active',
                    subscription_expires_at TIMESTAMP,
                    payment_method TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    UNIQUE(provider, provider_id)
                )
            """)
    
    def create_user(self, user: UserCreate) -> User:
        """새 사용자 생성 또는 기존 사용자 업데이트"""
        try:
            # 먼저 이메일로 기존 사용자 확인
            existing_user = self.get_user_by_email(user.email)
            
            if existing_user:
                print(f"기존 사용자 발견: email={user.email}, provider={existing_user.provider}")
                
                # provider가 다르면 업데이트
                if existing_user.provider != user.provider:
                    print(f"provider 업데이트: {existing_user.provider} -> {user.provider}")
                    with db_manager.get_cursor() as cur:
                        cur.execute("""
                            UPDATE users SET provider = %s, provider_id = %s, name = %s
                            WHERE email = %s
                        """, (user.provider, user.provider_id, user.name, user.email))
                    print("사용자 정보 업데이트 완료")
                
                # 업데이트된 사용자 정보 반환
                result = self.get_user_by_email(user.email)
                print(f"업데이트된 사용자: {result}")
                return result
            else:
                # 새 사용자 생성
                print(f"새 사용자 생성: email={user.email}, name={user.name}, provider={user.provider}, provider_id={user.provider_id}")
                with db_manager.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO users (
                            email, name, provider, provider_id, membership_tier,
                            subscription_status, is_active, is_admin
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        user.email,
                        user.name,
                        user.provider,
                        user.provider_id,
                        user.membership_tier.value,
                        user.subscription_status.value,
                        user.is_active,
                        user.is_admin,
                    ))
                    user_id = cur.fetchone()[0]
                    conn.commit()
                print(f"새 사용자 생성 완료: user_id={user_id}")
                result = self.get_user_by_id(user_id)
                print(f"생성된 사용자: {result}")
                return result
                
        except UniqueViolation as e:
            print(f"IntegrityError 발생: {e}")
            # provider로 사용자 조회 시도
            result = self.get_user_by_provider(user.provider, user.provider_id)
            print(f"get_user_by_provider 결과: {result}")
            if result:
                return result
            else:
                # 이메일로 조회 시도
                result = self.get_user_by_email(user.email)
                print(f"get_user_by_email 결과: {result}")
                return result
        except Exception as e:
            print(f"기타 오류 발생: {e}")
            raise
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
            SELECT id, email, name, provider, provider_id, membership_tier, subscription_status, 
                   subscription_expires_at, payment_method, is_admin, created_at, last_login, is_active
            FROM users WHERE id = %s
        """, (user_id,))
            row = cur.fetchone()
        return self._row_to_user(row)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
            SELECT id, email, name, provider, provider_id, membership_tier, subscription_status, 
                   subscription_expires_at, payment_method, is_admin, created_at, last_login, is_active
            FROM users WHERE email = %s
        """, (email,))
            row = cur.fetchone()
        return self._row_to_user(row)
    
    def get_user_by_provider(self, provider: str, provider_id: str) -> Optional[User]:
        """소셜 로그인 제공자로 사용자 조회"""
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
            SELECT id, email, name, provider, provider_id, membership_tier, subscription_status, 
                   subscription_expires_at, payment_method, is_admin, created_at, last_login, is_active
            FROM users WHERE provider = %s AND provider_id = %s
        """, (provider, provider_id))
            row = cur.fetchone()
        return self._row_to_user(row)
    
    def update_last_login(self, user_id: int):
        """마지막 로그인 시간 업데이트"""
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE users SET last_login = NOW() WHERE id = %s",
                (user_id,),
            )
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """JWT 액세스 토큰 생성"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            sub_value = payload.get("sub")
            if sub_value is None:
                return None
            
            # sub 값이 숫자(사용자 ID)인지 이메일인지 확인
            try:
                user_id = int(sub_value)
                token_data = TokenData(user_id=user_id)
            except ValueError:
                # 이메일인 경우 사용자 조회 후 ID 반환
                user = self.get_user_by_email(sub_value)
                if user:
                    token_data = TokenData(user_id=user.id)
                else:
                    return None
            
            return token_data
        except JWTError:
            return None
    
    def authenticate_user(self, email: str) -> Optional[User]:
        """사용자 인증"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not user.is_active:
            return None
        return user
    
    def create_email_user(self, signup_request: EmailSignupRequest) -> bool:
        """이메일 가입 사용자 생성"""
        # 이메일 중복 확인
        if self.get_user_by_email(signup_request.email):
            return False
        
        # 비밀번호 해싱
        password_hash = pwd_context.hash(signup_request.password)
        
        try:
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO users (email, name, provider, provider_id, password_hash, is_email_verified)
                    VALUES (%s, %s, 'local', %s, %s, FALSE)
                """, (signup_request.email, signup_request.name, signup_request.email, password_hash))
            return True
        except UniqueViolation:
            return False
    
    def verify_email_user(self, email: str, password: str) -> Optional[User]:
        """이메일 로그인 사용자 인증"""
        user = self.get_user_by_email(email)
        if not user or user.provider != 'local':
            return None
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("SELECT password_hash FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
        
        if row and pwd_context.verify(password, row[0]):
            return user
        return None
    
    def send_verification_email(self, email: str) -> bool:
        """이메일 인증 코드 발송"""
        verification_code = email_service.generate_verification_code()
        
        # 인증 코드 저장
        if email_verification_service.store_verification_code(email, verification_code, 'signup'):
            # 이메일 발송
            return email_service.send_verification_email(email, verification_code)
        return False
    
    def verify_email_code(self, email: str, verification_code: str) -> bool:
        """이메일 인증 코드 검증"""
        if email_verification_service.verify_code(email, verification_code, 'signup'):
            # 이메일 인증 완료 처리
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE users SET is_email_verified = TRUE WHERE email = %s",
                    (email,),
                )
            return True
        return False
    
    def send_password_reset_email(self, email: str) -> bool:
        """비밀번호 재설정 이메일 발송"""
        user = self.get_user_by_email(email)
        if not user or user.provider != 'local':
            return False
        
        verification_code = email_service.generate_verification_code()
        
        # 인증 코드 저장
        if email_verification_service.store_verification_code(email, verification_code, 'password_reset'):
            # 이메일 발송
            return email_service.send_password_reset_email(email, verification_code)
        return False
    
    def reset_password(self, email: str, verification_code: str, new_password: str) -> bool:
        """비밀번호 재설정"""
        if email_verification_service.verify_code(email, verification_code, 'password_reset'):
            # 비밀번호 업데이트
            password_hash = pwd_context.hash(new_password)
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE email = %s",
                    (password_hash, email),
                )
            return True
        return False

# 전역 인증 서비스 인스턴스
auth_service = AuthService()
