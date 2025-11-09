# ShowMeTheStock 프로젝트 리팩토링 계획

## 주요 문제점

### 1. 코드 중복 및 일관성

- API 엔드포인트 중복 정의 (scan_positions, auto_add_positions가 각 3번씩)
- 모듈 구조 불일치 (auth_service가 2곳에 존재)
- 임시/백업 파일 방치 (temp_*.py, *.bak, *.backup)
- 테스트 디렉토리 중복 (backend/test_*.py, backend/tests/, backend/tests/tests/)
- RSI 설정 6개 중복 (rsi_threshold, rsi_setup_min, rsi_overheat 등)

### 2. 아키텍처 문제

- 로깅 체계 부재 (print() 390회 사용)
- 프론트엔드 API URL 관리 불일치 (config.js vs 각 함수에 하드코딩)
- 데이터베이스 초기화 로직이 여러 곳에 분산
- 스캔 로직 분산 (scanner.py, services/scan_service.py, scan_service_refactored.py)
- 에러 처리 패턴 4가지 혼재 (빈 문자열, None, dict, HTTPException)

### 3. 파일 구조 문제

- backend/backend/ 중첩 폴더 (reports만 존재)
- nginx 설정 4개 버전 (nginx_config*)
- export_data와 export_data_full 중복
- HTML 파일이 backend/에 혼재

## 우선순위별 개선 계획

### Phase 1: 긴급 (P0) - Week 1

#### 1.1 API 엔드포인트 중복 제거

**파일:** `backend/main.py`

**문제:**

```python
# 라인 963, 1130, 1281 - 3번 중복
@app.get('/scan_positions')

# 라인 1031, 1198, 1349 - 3번 중복
@app.post('/auto_add_positions')
```

**작업:**

1. 세 버전의 코드 비교
2. 가장 완전한 버전 선택 (보통 마지막 버전)
3. 나머지 2개 삭제
4. 단위 테스트로 기능 검증

**영향:** API 호출 경로 동일하므로 프론트엔드 영향 없음

#### 1.2 auth_service 모듈 통합

**현재 구조:**

- `backend/auth_service.py` (348줄 - AuthService 클래스)
- `backend/services/auth_service.py` (124줄 - process_kakao_callback만)
- 순환 import 위험

**목표 구조:**

```
backend/auth/
  ├── __init__.py
  ├── service.py       # AuthService 클래스 (기존 auth_service.py)
  ├── social.py        # 소셜 로그인 (services/auth_service.py 통합)
  └── models.py        # auth_models.py 이동
```

**작업:**

1. `backend/auth/` 디렉토리 생성
2. 파일 이동 및 통합
3. import 경로 업데이트 (main.py, social_auth.py, payment_service.py 등)
4. 기존 파일 삭제

### Phase 2: 중요 (P1) - Week 2-3

#### 2.1 로깅 체계 구축

**문제:** print() 390회 사용, 로깅 프레임워크 없음

**작업:**

1. 로깅 설정 모듈 생성
```python
# backend/core/logger.py
import logging
from datetime import datetime

def setup_logger(name: str, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 파일 핸들러
    fh = logging.FileHandler(f'logs/{name}_{datetime.now():%Y%m%d}.log')
    fh.setLevel(logging.DEBUG)
    
    # 콘솔 핸들러
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger
```

2. 모든 print()를 logger로 변경
```python
# 변경 전
print(f"스캔 시작: {date}")

# 변경 후
logger.info(f"스캔 시작: {date}")
```

#### 2.2 임시/백업 파일 삭제

**삭제 대상:**

- `backend/temp_save_function.py`
- `backend/temp_latest_scan_api.py`
- `backend/temp_db_function.py`
- `backend/scan_service_refactored.py` (사용 안 함 확인 후)
- `backend/models.py.bak`
- `backend/services/scan_service.py.backup`
- `frontend/temp.js`

**작업:**

1. 각 파일 사용 여부 grep으로 확인
2. 사용 안 하면 삭제
3. Git history에 남으므로 안전

#### 2.3 테스트 디렉토리 재구성

**현재:**

- `backend/test_*.py` (7개 - 루트에 산재)
- `backend/tests/test_*.py` (8개)
- `backend/tests/tests/test_*.py` (2개 - 중복)

**목표:**

```
backend/tests/
  ├── conftest.py              # pytest 공통 설정
  ├── unit/
  │   ├── test_scanner.py      # 스캔 로직
  │   ├── test_indicators.py   # 기술 지표
  │   └── test_models.py       # 데이터 모델
  ├── integration/
  │   ├── test_api_endpoints.py
  │   └── test_portfolio.py
  └── fixtures/
      └── sample_data.json
```

#### 2.4 RSI 설정 통합

**현재:** config.py에 RSI 관련 설정 6개 중복

**목표:**

```python
# backend/config.py
@dataclass
class RSIConfig:
    """RSI 필터링 설정 - 역할별 명확한 구분"""
    # TEMA 기반 (메인 필터)
    tema_threshold: float = 58.0      # 기본 임계값
    tema_overheat: float = 70.0       # 과매수 상한선
    
    # DEMA 기반 (Setup/Trigger 패턴)
    dema_setup_min: float = 58.0      # Setup 구간 하한
    dema_setup_max: float = 75.0      # Setup 구간 상한
    dema_trigger_min: float = 50.0    # Trigger 기준
    
    # 시장 상황별 동적 조정
    bull_market: float = 65.0         # 강세장
    neutral_market: float = 58.0      # 중립장
    bear_market: float = 45.0         # 약세장

@dataclass
class Config:
    rsi: RSIConfig = field(default_factory=RSIConfig)
    # ... 기존 설정
```

**작업:**

1. RSIConfig 클래스 생성
2. 기존 변수를 RSIConfig로 이동
3. scanner.py, main.py에서 참조 업데이트
4. 환경변수 매핑 추가
5. CONFIG.md 문서 작성

### Phase 3: 개선 (P2) - Week 4-5

#### 3.1 프론트엔드 API URL 관리 통합

**문제:** config.js 있지만, lib/api.js 각 함수마다 URL 하드코딩

**작업:**

1. API 클라이언트 클래스 생성
```javascript
// frontend/lib/apiClient.js
import getConfig from '../config';

class APIClient {
  constructor() {
    this.config = getConfig();
    this.baseURL = this.config.backendUrl;
  }
  
  async get(endpoint) {
    const response = await fetch(`${this.baseURL}${endpoint}`);
    return response.json();
  }
  
  async post(endpoint, data) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  }
}

export const apiClient = new APIClient();
```

2. lib/api.js 리팩토링
```javascript
// 변경 전
export async function fetchLatestScan() {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8010';
  const response = await fetch(`${base}/latest-scan`);
  return response.json();
}

// 변경 후
import { apiClient } from './apiClient';

export async function fetchLatestScan() {
  return apiClient.get('/latest-scan');
}
```

#### 3.2 데이터베이스 초기화 통합

**현재:** create_scan_rank_table, _init_positions_table이 여러 곳에서 호출

**목표:**

```python
# backend/core/database.py
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def init_all_tables(self):
        """앱 시작 시 모든 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        self._create_scan_rank_table(cur)
        self._create_positions_table(cur)
        self._create_users_table(cur)
        
        conn.commit()
        conn.close()
    
    def _create_scan_rank_table(self, cur): ...
    def _create_positions_table(self, cur): ...
    def _create_users_table(self, cur): ...

# backend/main.py
db_manager = DatabaseManager(_db_path())

@app.on_event("startup")
async def startup():
    db_manager.init_all_tables()
```

#### 3.3 에러 처리 표준화

**현재:** 4가지 패턴 혼재

**목표:**

```python
# backend/core/exceptions.py
class AppException(Exception):
    """앱 공통 예외"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ScanError(AppException):
    """스캔 관련 오류"""
    pass

class AuthError(AppException):
    """인증 관련 오류"""
    pass

# backend/main.py
@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error": exc.message}
    )

# 사용 예
if not matched:
    raise ScanError("매칭 조건 미충족", status_code=400)
```

#### 3.4 파일 구조 정리

**작업:**

1. nginx 설정 통합
   - nginx_config 4개 중 최신 버전 확인
   - nginx.conf로 통일
   - 나머지 삭제 또는 archive/로 이동

2. backend/backend/ 중첩 제거
   - backend/reports/로 이동
   - backend/backend/ 삭제

3. HTML 파일 정리
   - backend/customer_scanner.html → landing/
   - backend/index.html → landing/ 또는 삭제

4. export_data 통합
   - export_data와 export_data_full 비교
   - 하나로 통합 또는 명확한 역할 구분

## 예상 효과

### 코드 품질

- 중복 코드 제거로 유지보수성 50% 향상
- 테스트 커버리지 증가 (현재 30% → 60%)
- 버그 추적 용이성 증가

### 개발 생산성

- 명확한 모듈 구조로 신규 개발자 온보딩 시간 단축
- 로깅 체계로 디버깅 시간 60% 감소
- 설정 관리 통합으로 환경별 배포 오류 감소

### 시스템 안정성

- 에러 처리 표준화로 예외 상황 대응 향상
- 데이터베이스 초기화 안정화
- API 일관성으로 프론트엔드 통합 안정화

## 리스크 및 대응

### 고위험 작업

1. auth_service 통합 - 순환 import 가능성
   - 대응: 점진적 마이그레이션, 각 단계마다 테스트

2. 에러 처리 변경 - 기존 에러 핸들링 영향
   - 대응: 기존 패턴과 병행 운영, 점진적 전환

### 롤백 계획

- 각 Phase마다 Git 태그 생성
- 배포 전 스테이징 환경 검증
- 프로덕션 배포 시 블루-그린 배포 활용

## 일정

- Week 1: Phase 1 (P0) - API 중복, auth 통합
- Week 2-3: Phase 2 (P1) - 로깅, 파일 정리, 테스트, RSI
- Week 4-5: Phase 3 (P2) - API 클라이언트, DB, 에러, 구조
- Week 6: 통합 테스트 및 문서화

## 체크리스트

### Phase 1 (P0)
- [ ] API 엔드포인트 중복 제거 (scan_positions, auto_add_positions)
- [ ] auth_service 모듈 통합 (backend/auth/ 구조 생성)

### Phase 2 (P1)
- [ ] 로깅 체계 구축 (print 390개를 logger로 변경)
- [ ] 임시/백업 파일 삭제 (temp_*.py, *.bak)
- [ ] 테스트 디렉토리 재구성 (unit/integration 분리)
- [ ] RSI 설정 통합 (RSIConfig 클래스 생성)

### Phase 3 (P2)
- [ ] 프론트엔드 API URL 관리 통합 (apiClient 클래스)
- [ ] 데이터베이스 초기화 통합 (DatabaseManager)
- [ ] 에러 처리 표준화 (AppException 체계)
- [ ] 파일 구조 정리 (nginx, backend/backend/, HTML 위치)

---

**작성일:** 2025-10-20  
**작성자:** AI Assistant  
**버전:** 1.0

