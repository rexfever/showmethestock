# JWT 토큰 만료 시간 연장 시 보안 분석

## 현재 상태

- **토큰 만료 시간**: 7일 (30분에서 변경됨)
- **Refresh Token**: 없음
- **Token Revocation**: 없음
- **사용자 상태 실시간 반영**: 부분적 (verify_token에서만 체크)

---

## 보안 문제점

### 1. 토큰 탈취 시 장기간 유효

**문제**:
- 토큰이 탈취되면 최대 7일간 유효
- XSS 공격, 네트워크 스니핑 등으로 토큰 탈취 시 장기간 악용 가능

**위험도**: 🔴 높음

**완화 방안**:
- HTTPS 필수 사용 (현재 적용 중)
- XSS 방지 (CSP, 입력 검증)
- 토큰을 httpOnly 쿠키에 저장 (현재 localStorage 사용 중)

### 2. 토큰 무효화 불가능

**문제**:
- JWT는 stateless이므로 서버에서 토큰을 무효화할 수 없음
- 사용자가 비밀번호 변경, 계정 비활성화, 구독 취소해도 기존 토큰은 계속 유효
- 보안 사고 발생 시 즉시 대응 불가

**위험도**: 🔴 높음

**현재 코드**:
```python
def verify_token(self, token: str) -> Optional[TokenData]:
    # 토큰 검증만 수행, 사용자 상태는 별도로 체크
    # 하지만 모든 API에서 is_active를 체크하지 않을 수 있음
```

**개선 필요**:
- Token blacklist 구현 (Redis 등)
- 또는 모든 API에서 사용자 상태 재확인

### 3. 사용자 상태 변경 미반영

**문제**:
- 계정 비활성화 (`is_active = False`)
- 구독 만료 (`subscription_status = 'expired'`)
- 권한 변경 (`is_admin`, `membership_tier`)

위와 같은 변경이 발생해도 기존 토큰은 계속 유효

**위험도**: 🟡 중간

**현재 코드**:
```python
# verify_token에서는 사용자 조회만 하고 상태 체크는 하지 않음
# 각 API 엔드포인트에서 get_current_user()로 상태 체크
```

**개선 필요**:
- `verify_token`에서 사용자 상태도 함께 확인
- 또는 토큰에 상태 정보 포함 (하지만 상태 변경 시 반영 안 됨)

### 4. Refresh Token 부재

**문제**:
- Access Token이 만료되면 재로그인 필요
- 짧은 만료 시간(30분)과 긴 만료 시간(7일) 사이의 균형점 없음

**위험도**: 🟡 중간

**개선 방안**:
- Access Token: 짧은 만료 시간 (1시간)
- Refresh Token: 긴 만료 시간 (7일~30일)
- Refresh Token은 DB에 저장하여 무효화 가능

---

## 권장 개선 사항

### 우선순위 1: 즉시 적용 가능

#### 1. 토큰 검증 시 사용자 상태 확인 강화

```python
def verify_token(self, token: str) -> Optional[TokenData]:
    """JWT 토큰 검증 및 사용자 상태 확인"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub_value = payload.get("sub")
        if sub_value is None:
            return None
        
        # 사용자 조회
        user = self.get_user_by_email(sub_value) if "@" in str(sub_value) else self.get_user_by_id(int(sub_value))
        
        if not user:
            return None
        
        # 사용자 상태 확인
        if not user.is_active:
            return None  # 비활성화된 계정의 토큰은 무효
        
        return TokenData(user_id=user.id)
    except JWTError:
        return None
```

#### 2. 토큰을 httpOnly 쿠키에 저장

**프론트엔드**:
- localStorage 대신 httpOnly 쿠키 사용
- XSS 공격으로부터 토큰 보호

**백엔드**:
```python
from fastapi import Response

response = Response()
response.set_cookie(
    key="auth_token",
    value=access_token,
    httponly=True,
    secure=True,  # HTTPS만
    samesite="strict",
    max_age=60 * 60 * 24 * 7  # 7일
)
```

### 우선순위 2: 중기 개선

#### 3. Token Blacklist 구현

**Redis 사용 예시**:
```python
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def revoke_token(token: str, expires_in: int):
    """토큰을 blacklist에 추가"""
    jti = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get('jti')
    redis_client.setex(f"blacklist:{jti}", expires_in, "1")

def is_token_revoked(token: str) -> bool:
    """토큰이 blacklist에 있는지 확인"""
    jti = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get('jti')
    return redis_client.exists(f"blacklist:{jti}")
```

**사용 시나리오**:
- 비밀번호 변경 시 모든 토큰 무효화
- 로그아웃 시 토큰 무효화
- 보안 사고 발생 시 즉시 대응

#### 4. Refresh Token 도입

**구조**:
- Access Token: 1시간 (짧은 만료)
- Refresh Token: 7일~30일 (긴 만료, DB 저장)

**장점**:
- Access Token 탈취 시 피해 최소화 (1시간만 유효)
- 사용자 편의성 유지 (자동 갱신)
- Refresh Token은 DB에 저장하여 무효화 가능

### 우선순위 3: 장기 개선

#### 5. 토큰에 사용자 상태 포함 (선택적)

**주의**: 상태가 변경되면 반영되지 않으므로, 중요한 상태는 서버에서 재확인 필요

```python
# 토큰에 버전 번호 포함
to_encode = {
    "sub": user.email,
    "version": user.token_version,  # 상태 변경 시 증가
    "is_active": user.is_active
}

# 검증 시 버전 확인
if payload.get("version") != user.token_version:
    return None  # 토큰 무효
```

---

## 현재 시스템의 보안 강점

### ✅ 이미 적용된 보안 조치

1. **HTTPS 사용**: 네트워크 전송 중 암호화
2. **JWT 서명 검증**: 토큰 변조 방지
3. **사용자 상태 체크**: `get_current_user()`에서 `is_active` 확인
4. **비밀번호 해싱**: bcrypt 사용

---

## 권장 설정 (단계별)

### 단계 1: 즉시 적용 (낮은 위험)

```python
# auth_service.py
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 3  # 3일로 단축
```

**이유**: 7일보다 짧지만 여전히 편리함, 위험도 감소

### 단계 2: 토큰 검증 강화 (1주일 내)

- `verify_token`에서 사용자 상태 확인
- 모든 API에서 사용자 상태 재확인

### 단계 3: Refresh Token 도입 (1개월 내)

- Access Token: 1시간
- Refresh Token: 7일 (DB 저장)

### 단계 4: Token Blacklist (필요 시)

- Redis 기반 blacklist
- 로그아웃, 비밀번호 변경 시 토큰 무효화

---

## 결론

**현재 7일 설정의 위험도**: 🟡 중간

**즉시 조치 권장**:
1. ✅ 토큰 검증 시 사용자 상태 확인 강화
2. ✅ 토큰을 httpOnly 쿠키에 저장
3. ⚠️ 토큰 만료 시간을 3일로 단축 고려

**중기 조치 권장**:
1. Refresh Token 도입
2. Token Blacklist 구현

**장기 조치 권장**:
1. 토큰 버전 관리
2. 보안 모니터링 및 알림 시스템

---

**작성일**: 2026-01-08  
**최종 업데이트**: 2026-01-08

