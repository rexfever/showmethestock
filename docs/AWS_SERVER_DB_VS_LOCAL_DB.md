# AWS 서버 DB vs 로컬 DB 차이점

**작성일**: 2026-01-08  
**목적**: AWS 서버 DB와 로컬 DB의 차이점 및 사용 방법 정리

---

## 개요

프로젝트는 두 개의 데이터베이스를 사용합니다:
1. **AWS 서버 DB**: 프로덕션 환경에서 사용하는 운영 데이터베이스
2. **로컬 DB**: 개발 환경에서 사용하는 로컬 데이터베이스

---

## 연결 정보

### AWS 서버 DB

**위치**: AWS EC2 서버 (52.79.145.238)  
**접근 방법**: SSH 터널링을 통한 간접 접근

**연결 문자열**:
```bash
# SSH 터널을 통해 접근 (로컬 포트 5433)
postgresql://stockfinder:stockfinder_pass@localhost:5433/stockfinder

# 또는 직접 접근 (서버 내부)
postgresql://stockfinder:stockfinder_pass@localhost:5432/stockfinder
```

**SSH 터널 생성**:
```bash
# SSH 터널 생성 (로컬 포트 5433 -> 서버 localhost:5432)
ssh -f -N -L 5433:localhost:5432 stock-finder
# 또는
ssh -f -N -L 5433:localhost:5432 ubuntu@52.79.145.238
```

### 로컬 DB

**위치**: 로컬 머신 (localhost)  
**접근 방법**: 직접 접근

**연결 문자열**:
```bash
# .env 파일에서 설정
DATABASE_URL=postgresql://your_username@localhost/stockfinder
```

---

## 환경 감지

### 자동 감지

`backend/environment.py`에서 환경을 자동 감지합니다:

```python
class EnvironmentDetector:
    def _detect_environment(self) -> str:
        # 1. 환경변수로 명시적 설정
        env_var = os.getenv("ENVIRONMENT", "").lower()
        
        # 2. 호스트명으로 구분
        hostname = socket.gethostname().lower()
        
        # 3. 파일 경로로 구분
        if os.path.exists("/home/ubuntu/showmethestock"):
            return "server"
        elif os.path.exists("/Users/rexsmac/workspace/stock-finder"):
            return "local"
        
        # 4. IP 주소로 구분
        # ...
```

### 환경별 설정

**로컬 환경**:
```python
{
    "debug": True,
    "log_level": "DEBUG",
    "universe_kospi": 10,  # 적은 수로 테스트
    "universe_kosdaq": 10,
    "rate_limit_delay_ms": 100,  # 빠르게
}
```

**서버 환경**:
```python
{
    "debug": False,
    "log_level": "INFO",
    "universe_kospi": 100,  # 전체
    "universe_kosdaq": 100,
    "rate_limit_delay_ms": 250,  # 안전하게
}
```

---

## 데이터베이스 연결

### 연결 설정

`backend/config.py`에서 환경 변수로 연결:

```python
database_url: str = os.getenv(
    "DATABASE_URL",
    os.getenv("POSTGRES_DSN", os.getenv("DB_URL", "")),
)
```

### 연결 풀

`backend/db.py`에서 연결 풀 관리:

```python
_pool = ConnectionPool(
    conninfo=config.database_url,
    min_size=1,
    max_size=10,  # 최대 10개 연결
)
```

---

## 데이터 동기화

### AWS 서버 DB → 로컬 DB 동기화

**스크립트**: `backend/sync_aws_to_local.sh`

**사용법**:
```bash
cd backend
./sync_aws_to_local.sh
```

**동작**:
1. SSH 터널 생성 (로컬 포트 5433)
2. 서버 DB 연결 확인
3. 로컬 DB 연결 확인
4. 모든 테이블 동기화 (UPSERT 방식)

**동기화 테이블**:
- 모든 public 스키마 테이블
- FK 의존성 순서 고려 (users → scanner_settings → ...)

**주의사항**:
- UPSERT 방식으로 중복 방지
- Primary Key 또는 UNIQUE 제약조건 사용
- `updated_at` 컬럼은 자동 업데이트 제외

---

## 주요 차이점

### 1. 데이터

| 항목 | AWS 서버 DB | 로컬 DB |
|------|------------|---------|
| **데이터 소스** | 프로덕션 데이터 | 개발/테스트 데이터 |
| **데이터 양** | 전체 운영 데이터 | 선택적 데이터 |
| **업데이트** | 실시간 (스케줄러 실행) | 수동 동기화 |
| **백업** | 정기 백업 | 필요 시 수동 백업 |

### 2. 접근 방법

| 항목 | AWS 서버 DB | 로컬 DB |
|------|------------|---------|
| **접근 방식** | SSH 터널링 필요 | 직접 접근 |
| **포트** | 5433 (터널) 또는 5432 (서버 내부) | 5432 |
| **인증** | 서버 SSH 키 필요 | 로컬 인증 |
| **네트워크** | 인터넷 연결 필요 | 로컬 네트워크 |

### 3. 사용 목적

| 항목 | AWS 서버 DB | 로컬 DB |
|------|------------|---------|
| **용도** | 프로덕션 운영 | 개발/테스트 |
| **스케줄러** | 자동 실행 | 수동 실행 또는 비활성화 |
| **API 호출** | 실제 키움 API | 실제 또는 모의 API |
| **데이터 수정** | 제한적 (운영 데이터) | 자유롭게 테스트 |

### 4. 환경 설정

| 항목 | AWS 서버 DB | 로컬 DB |
|------|------------|---------|
| **환경 변수** | 서버 `.env` 파일 | 로컬 `.env` 파일 |
| **Universe 크기** | 100개 (KOSPI/KOSDAQ) | 10개 (테스트용) |
| **레이트 리밋** | 250ms (안전) | 100ms (빠름) |
| **디버그 모드** | False | True |

---

## 데이터 동기화 시나리오

### 시나리오 1: 최신 운영 데이터 가져오기

```bash
# 1. SSH 터널 생성
ssh -f -N -L 5433:localhost:5432 stock-finder

# 2. 환경 변수 설정
export SERVER_DATABASE_URL="postgresql://stockfinder:stockfinder_pass@localhost:5433/stockfinder"

# 3. 동기화 실행
cd backend
python3 sync_server_data.py
```

### 시나리오 2: 특정 테이블만 동기화

`sync_server_data.py`를 수정하여 특정 테이블만 동기화:

```python
# 동기화할 테이블 목록 수정
tables_to_sync = ['users', 'scanner_settings', 'scan_rank']
```

---

## 주의사항

### 1. 데이터 손실 방지

- **로컬 DB 수정 시**: AWS 서버 DB에 영향 없음
- **AWS 서버 DB 수정 시**: 프로덕션 데이터 손실 가능
- **동기화 시**: UPSERT 방식으로 기존 데이터 보존

### 2. SSH 터널 관리

- SSH 터널은 백그라운드로 실행됨
- 종료하려면: `kill $SSH_TUNNEL_PID`
- 또는: `pkill -f 'ssh.*5433:localhost:5432'`

### 3. 환경 변수

- **로컬**: `DATABASE_URL` (로컬 DB)
- **동기화 시**: `SERVER_DATABASE_URL` (서버 DB, SSH 터널)

---

## 사용 예시

### 로컬 개발 시

```bash
# 로컬 DB 사용 (기본)
export DATABASE_URL="postgresql://your_username@localhost/stockfinder"

# 백엔드 실행
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8010
```

### 서버 데이터 확인 시

```bash
# SSH 터널 생성
ssh -f -N -L 5433:localhost:5432 stock-finder

# 서버 DB 연결
export SERVER_DATABASE_URL="postgresql://stockfinder:stockfinder_pass@localhost:5433/stockfinder"

# psql로 직접 접근
psql "$SERVER_DATABASE_URL"
```

### 데이터 동기화 시

```bash
# 동기화 스크립트 실행
cd backend
./sync_aws_to_local.sh
```

---

## 관련 파일

### 스크립트
- `backend/sync_aws_to_local.sh`: AWS → 로컬 동기화 (SSH 터널 포함)
- `backend/sync_server_data.py`: 서버 DB → 로컬 DB 동기화
- `backend/sync_server_data_ssh.sh`: SSH 터널링을 통한 동기화

### 설정 파일
- `backend/config.py`: 데이터베이스 연결 설정
- `backend/environment.py`: 환경 감지 및 설정 오버라이드
- `backend/db.py`: 연결 풀 관리

### 문서
- `docs/deployment/LOCAL_DEVELOPMENT_SETUP.md`: 로컬 개발 환경 설정
- `docs/deployment/SERVER_OPERATION_MANUAL.md`: 서버 운영 메뉴얼

---

## 요약

### AWS 서버 DB
- **위치**: AWS EC2 서버
- **용도**: 프로덕션 운영
- **접근**: SSH 터널링 필요
- **데이터**: 전체 운영 데이터

### 로컬 DB
- **위치**: 로컬 머신
- **용도**: 개발/테스트
- **접근**: 직접 접근
- **데이터**: 선택적 데이터 (동기화 필요)

### 동기화
- **방법**: `sync_aws_to_local.sh` 스크립트 사용
- **방식**: UPSERT (중복 방지)
- **주의**: 프로덕션 데이터 손실 방지

---

**작성일**: 2026-01-08  
**최종 업데이트**: 2026-01-08  
**상태**: 문서화 완료

