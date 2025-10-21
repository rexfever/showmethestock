# 관리자 기능 점검 보고서

**점검일:** 2025-10-20  
**프로젝트:** ShowMeTheStock (스톡인사이트)

---

## 1. 관리자 기능 개요

### 1.1 구성 요소

**백엔드:**
- `admin_service.py` - 관리자 비즈니스 로직
- `main.py` - 관리자 API 엔드포인트 (5개)
- `auth_models.py` - 관리자 데이터 모델

**프론트엔드:**
- `pages/admin.js` - 관리자 대시보드 (React)
- `admin_scanner/index.html` - 관리자 스캐너 HTML 버전

**데이터베이스:**
- `users` 테이블에 `is_admin` 필드 (BOOLEAN)

---

## 2. 관리자 API 엔드포인트

### 2.1 엔드포인트 목록

| 메서드 | 경로 | 기능 | 인증 |
|--------|------|------|------|
| GET | `/admin/stats` | 관리자 통계 조회 | ✅ |
| GET | `/admin/users` | 전체 사용자 목록 | ✅ |
| GET | `/admin/users/{user_id}` | 특정 사용자 조회 | ✅ |
| PUT | `/admin/users/{user_id}` | 사용자 정보 수정 | ✅ |
| DELETE | `/admin/users/{user_id}` | 사용자 삭제 | ✅ |

### 2.2 인증 체계

**2단계 인증 구조:**

```python
# 1단계: 사용자 인증
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    token_data = auth_service.verify_token(token)  # JWT 토큰 검증
    user = auth_service.get_user_by_email(token_data.email)
    return user

# 2단계: 관리자 권한 확인
def get_admin_user(current_user: User = Depends(get_current_user)):
    if not admin_service.is_admin(current_user.id):  # DB에서 is_admin 확인
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    return current_user
```

**모든 관리자 API는 `Depends(get_admin_user)`로 보호됨 ✅**

---

## 3. 관리자 서비스 기능

### 3.1 사용자 관리

**파일:** `backend/admin_service.py`

```python
class AdminService:
    def is_admin(user_id: int) -> bool          # 관리자 권한 확인
    def get_all_users(limit, offset) -> List    # 사용자 목록 (페이지네이션)
    def get_user_by_id(user_id) -> Dict         # 단일 사용자 조회
    def update_user(user_id, updates) -> bool   # 사용자 정보 업데이트
    def delete_user(user_id) -> bool            # 사용자 삭제 (관련 데이터 포함)
    def get_admin_stats() -> AdminStatsResponse # 통계 대시보드
```

### 3.2 통계 정보 (AdminStatsResponse)

```python
- total_users: int              # 총 사용자 수
- free_users: int               # 무료 사용자
- premium_users: int            # 프리미엄 사용자
- vip_users: int                # VIP 사용자
- active_subscriptions: int     # 활성 구독 수
- total_revenue: int            # 총 수익
- recent_users: List[Dict]      # 최근 가입자 10명
```

### 3.3 수정 가능한 사용자 필드

**AdminUserUpdateRequest:**
- `membership_tier` - 등급 (free/premium/vip)
- `subscription_status` - 구독 상태 (active/inactive/cancelled)
- `subscription_expires_at` - 구독 만료일
- `is_admin` - 관리자 권한 부여/해제

---

## 4. 프론트엔드 UI

### 4.1 관리자 대시보드 (admin.js)

**주요 기능:**
- 📊 통계 대시보드
  - 사용자 수 (총/등급별)
  - 구독 현황
  - 총 수익
  - 최근 가입자

- 👥 사용자 관리
  - 사용자 목록 조회
  - 사용자 정보 수정
  - 사용자 삭제
  - 관리자 권한 부여

- 🔍 스캔 관리
  - 스캔 날짜 선택
  - 재스캔 실행
  - 스캔 결과 삭제

- 📈 종목 분석
  - URL 파라미터로 종목 분석 (`?analyze=TICKER`)

**접근 제어:**
```javascript
useEffect(() => {
  if (!isAuthenticated()) {
    router.push('/login');  // 미인증 시 로그인 페이지
    return;
  }
  
  if (!user?.is_admin) {
    alert('관리자 권한이 필요합니다.');
    router.push('/customer-scanner');  // 일반 사용자는 고객 페이지로
    return;
  }
  
  fetchAdminData();
}, [isAuthenticated, user]);
```

### 4.2 관리자 스캐너 (admin_scanner/index.html)

**기능:**
- 🔄 관리자 데이터 새로고침 버튼
- 📊 스캔 실행
- 📈 시스템 모니터링
- ⚙️ 설정 관리
- 🎯 고객 스캐너로 이동 링크

---

## 5. 보안 점검 결과

### ✅ 잘된 점

1. **인증/권한 분리:**
   - JWT 토큰 인증 (`get_current_user`)
   - 관리자 권한 확인 (`get_admin_user`)
   - 2단계 보안 체계

2. **API 보호:**
   - 모든 관리자 API에 `Depends(get_admin_user)` 적용
   - 403 Forbidden 에러 처리

3. **프론트엔드 보호:**
   - 클라이언트 사이드 권한 확인
   - 미인증/무권한 사용자 리다이렉트

4. **자기 삭제 방지:**
   ```python
   if user_id == admin_user.id:
       raise HTTPException(detail="자기 자신을 삭제할 수 없습니다")
   ```

5. **삭제 확인:**
   ```python
   if not request.confirm:
       raise HTTPException(detail="사용자 삭제를 확인해주세요")
   ```

### ⚠️ 개선 필요 사항

#### 1. 로깅 부재 (높은 우선순위)

**문제:**
```python
# admin_service.py
except Exception as e:
    print(f"관리자 권한 확인 오류: {e}")  # print() 사용
    return False
```

**개선안:**
```python
import logging
logger = logging.getLogger(__name__)

try:
    # ...
except Exception as e:
    logger.error(f"관리자 권한 확인 오류: user_id={user_id}, error={e}")
    return False
```

**영향:**
- 관리자 작업 감사 로그 없음
- 보안 이벤트 추적 불가
- 사용자 삭제/수정 이력 미기록

#### 2. 감사 로그 미구현 (높은 우선순위)

**필요한 감사 로그:**
- 관리자 로그인/로그아웃
- 사용자 정보 수정 (누가, 언제, 무엇을, 어떻게)
- 사용자 삭제
- 권한 변경 (일반 사용자 → 관리자)
- 구독 상태 변경

**구현 제안:**
```python
# audit_log 테이블 생성
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    admin_user_id INTEGER,
    action TEXT,            -- 'UPDATE_USER', 'DELETE_USER', etc.
    target_user_id INTEGER,
    changes TEXT,           -- JSON 형태로 변경 내용
    ip_address TEXT,
    created_at TIMESTAMP
)
```

#### 3. 최초 관리자 생성 메커니즘 없음 (중간 우선순위)

**문제:**
- 데이터베이스에 관리자가 없으면 관리자를 만들 수 없음
- `is_admin` 필드 기본값이 0 (False)

**해결 방안:**

**옵션 A: 환경변수 설정**
```python
# config.py
INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "admin@sohntech.ai.kr")

# main.py
@app.on_event("startup")
async def setup_initial_admin():
    admin = auth_service.get_user_by_email(INITIAL_ADMIN_EMAIL)
    if admin:
        # 첫 번째 사용자를 자동으로 관리자로 설정
        admin_service.update_user(admin.id, {"is_admin": True})
```

**옵션 B: CLI 커맨드**
```bash
# 관리자 생성 스크립트
python scripts/create_admin.py --email admin@example.com
```

**옵션 C: 데이터베이스 직접 수정**
```sql
UPDATE users SET is_admin = 1 WHERE email = 'your-email@example.com';
```

#### 4. 페이지네이션 개선 (낮은 우선순위)

**현재:**
```python
def get_all_users(self, limit: int = 100, offset: int = 0)
```

**문제:**
- 사용자 수가 많아지면 성능 저하
- 프론트엔드에서 페이지네이션 UI 없음

**개선안:**
- 총 사용자 수 반환
- 페이지 정보 포함
```python
return {
    "users": users,
    "total": total_count,
    "page": offset // limit + 1,
    "per_page": limit,
    "total_pages": (total_count + limit - 1) // limit
}
```

#### 5. 에러 메시지 일관성 (낮은 우선순위)

**현재:**
- 한글 에러 메시지
- 상세 에러 정보 노출 (`detail=f"... 중 오류가 발생했습니다: {str(e)}"`)

**보안 고려:**
```python
# 프로덕션 환경에서는 상세 에러 숨기기
if config.is_production:
    detail = "요청 처리 중 오류가 발생했습니다"
else:
    detail = f"오류 상세: {str(e)}"
```

#### 6. Rate Limiting 없음 (중간 우선순위)

**문제:**
- 관리자 API에 Rate Limiting 없음
- 무차별 대입 공격(Brute Force) 가능

**개선안:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/admin/stats")
@limiter.limit("10/minute")  # 분당 10회 제한
async def get_admin_stats(...):
    ...
```

#### 7. 관리자 권한 레벨 부재 (낮은 우선순위)

**현재:**
- is_admin: Boolean (관리자 O/X만 있음)

**개선 제안:**
```python
admin_role: str  # 'super_admin', 'admin', 'moderator'

# 권한 레벨별 차등 적용
- super_admin: 모든 권한
- admin: 사용자 관리, 통계 조회
- moderator: 통계 조회만 가능
```

---

## 6. 데이터베이스 스키마

### users 테이블

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,              -- 'email', 'kakao', 'naver', 'toss'
    provider_id TEXT NOT NULL,
    password_hash TEXT,                  -- 이메일 로그인 시만 사용
    is_email_verified BOOLEAN DEFAULT 0, -- 이메일 인증 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    membership_tier TEXT DEFAULT 'free', -- 'free', 'premium', 'vip'
    subscription_status TEXT DEFAULT 'active',
    subscription_expires_at TEXT,
    payment_method TEXT,
    is_admin BOOLEAN DEFAULT 0,          -- 관리자 권한
    UNIQUE(provider, provider_id)
)
```

**관리자 확인 쿼리:**
```sql
SELECT is_admin FROM users WHERE id = ?
```

---

## 7. 테스트 상태

### 테스트 파일 확인

**발견된 테스트:**
- `backend/test_integration_admin.py` - 관리자 통합 테스트

**테스트 커버리지:**
- ⚠️ 관리자 API 단위 테스트 필요
- ⚠️ 권한 체크 테스트 필요
- ⚠️ 자기 삭제 방지 테스트 필요

**추천 테스트:**
```python
# tests/test_admin_api.py
def test_admin_stats_requires_auth():
    """인증 없이 관리자 API 호출 시 401 반환"""
    
def test_admin_stats_requires_admin():
    """일반 사용자가 관리자 API 호출 시 403 반환"""
    
def test_cannot_delete_self():
    """관리자가 자기 자신 삭제 시도 시 400 반환"""
    
def test_update_user_membership():
    """사용자 등급 변경 테스트"""
```

---

## 8. 보안 체크리스트

### ✅ 구현됨

- [x] JWT 토큰 인증
- [x] 관리자 권한 체크 (is_admin)
- [x] API 레벨 권한 보호 (Depends)
- [x] 프론트엔드 권한 체크
- [x] 자기 삭제 방지
- [x] 삭제 확인 (confirm 필드)
- [x] HTTPS (프로덕션)
- [x] CORS 설정

### ❌ 미구현 (권장)

- [ ] 감사 로그 (Audit Log)
- [ ] 로깅 프레임워크
- [ ] Rate Limiting
- [ ] IP 화이트리스트
- [ ] 2FA (Two-Factor Authentication)
- [ ] 세션 타임아웃
- [ ] 비밀번호 정책 (복잡도)
- [ ] 계정 잠금 (로그인 실패 시)

---

## 9. 사용자 시나리오

### 9.1 최초 관리자 설정

**현재 방법:**
```sql
-- 데이터베이스 직접 접근
sqlite3 backend/snapshots.db
UPDATE users SET is_admin = 1 WHERE email = 'your-email@example.com';
```

**권장 방법:**
```bash
# CLI 도구 생성
python scripts/make_admin.py --email admin@sohntech.ai.kr
```

### 9.2 사용자 등급 변경

**API 호출:**
```bash
curl -X PUT https://sohntech.ai.kr/backend/admin/users/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "membership_tier": "premium",
    "subscription_expires_at": "2026-12-31T23:59:59"
  }'
```

### 9.3 관리자 권한 부여

**API 호출:**
```bash
curl -X PUT https://sohntech.ai.kr/backend/admin/users/456 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_admin": true
  }'
```

---

## 10. 개선 우선순위 및 일정

### Phase 1: 긴급 (1주)
1. **감사 로그 구현**
   - audit_logs 테이블 생성
   - 모든 관리자 작업 로깅
   - 파일: `backend/audit_service.py`

2. **로깅 프레임워크 도입**
   - print() → logging
   - 파일: `backend/core/logger.py`

3. **최초 관리자 생성 스크립트**
   - CLI 도구
   - 파일: `scripts/make_admin.py`

### Phase 2: 중요 (2주)
4. **Rate Limiting 적용**
   - slowapi 도입
   - 관리자 API 보호

5. **테스트 작성**
   - 관리자 API 단위 테스트
   - 권한 체크 테스트

6. **페이지네이션 개선**
   - 프론트엔드 UI 추가
   - API 응답 형식 개선

### Phase 3: 개선 (1개월)
7. **권한 레벨 구현**
   - super_admin, admin, moderator 구분
   - 역할 기반 접근 제어 (RBAC)

8. **2FA 구현** (선택)
   - TOTP 기반 2단계 인증
   - 관리자 계정 보안 강화

---

## 11. 결론

### 종합 평가

**강점:**
- ✅ 기본적인 관리자 기능 잘 구현됨
- ✅ 인증/권한 체계 2단계로 안전
- ✅ 자기 삭제 방지 등 기본 보안 적용
- ✅ React 기반 관리자 대시보드 완성도 높음

**개선 필요:**
- ⚠️ 감사 로그 미구현 (보안 이슈)
- ⚠️ 로깅 체계 부재 (운영 이슈)
- ⚠️ 최초 관리자 생성 메커니즘 없음
- ⚠️ Rate Limiting 없음

### 보안 등급: **B+ (양호)**

**평가 근거:**
- 인증/권한 체계: A
- API 보호: A
- 감사 로그: D (미구현)
- 로깅: D (print 사용)
- 전체: B+

### 권장 조치

**즉시:**
1. 최초 관리자 계정 설정 (데이터베이스 직접 수정)
2. 감사 로그 구현 계획 수립

**1주 내:**
1. 로깅 프레임워크 도입
2. 관리자 생성 CLI 도구 작성

**1개월 내:**
1. 감사 로그 시스템 구현
2. 테스트 코드 작성
3. Rate Limiting 적용

---

**보고서 작성자:** AI Assistant  
**검토 일자:** 2025-10-20  
**다음 점검 예정:** 2025-11-20

