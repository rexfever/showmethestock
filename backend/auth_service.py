import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from auth_models import User, UserCreate, TokenData

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db_path: str = "snapshots.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """사용자 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(provider, provider_id)
            )
        """)
        conn.commit()
        conn.close()
    
    def create_user(self, user: UserCreate) -> User:
        """새 사용자 생성"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO users (email, name, provider, provider_id)
                VALUES (?, ?, ?, ?)
            """, (user.email, user.name, user.provider, user.provider_id))
            
            user_id = cur.lastrowid
            conn.commit()
            
            return self.get_user_by_id(user_id)
        except sqlite3.IntegrityError:
            # 이미 존재하는 사용자
            return self.get_user_by_provider(user.provider, user.provider_id)
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, email, name, provider, provider_id, created_at, last_login, is_active
            FROM users WHERE id = ?
        """, (user_id,))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row[0],
                email=row[1],
                name=row[2],
                provider=row[3],
                provider_id=row[4],
                created_at=datetime.fromisoformat(row[5]),
                last_login=datetime.fromisoformat(row[6]) if row[6] else None,
                is_active=bool(row[7])
            )
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, email, name, provider, provider_id, created_at, last_login, is_active
            FROM users WHERE email = ?
        """, (email,))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row[0],
                email=row[1],
                name=row[2],
                provider=row[3],
                provider_id=row[4],
                created_at=datetime.fromisoformat(row[5]),
                last_login=datetime.fromisoformat(row[6]) if row[6] else None,
                is_active=bool(row[7])
            )
        return None
    
    def get_user_by_provider(self, provider: str, provider_id: str) -> Optional[User]:
        """소셜 로그인 제공자로 사용자 조회"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, email, name, provider, provider_id, created_at, last_login, is_active
            FROM users WHERE provider = ? AND provider_id = ?
        """, (provider, provider_id))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row[0],
                email=row[1],
                name=row[2],
                provider=row[3],
                provider_id=row[4],
                created_at=datetime.fromisoformat(row[5]),
                last_login=datetime.fromisoformat(row[6]) if row[6] else None,
                is_active=bool(row[7])
            )
        return None
    
    def update_last_login(self, user_id: int):
        """마지막 로그인 시간 업데이트"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
        """, (user_id,))
        
        conn.commit()
        conn.close()
    
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
            email: str = payload.get("sub")
            if email is None:
                return None
            token_data = TokenData(email=email)
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

# 전역 인증 서비스 인스턴스
auth_service = AuthService()
