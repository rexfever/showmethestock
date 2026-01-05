# v3 추천 시스템 최종 검증 리포트

**검증 일시**: 2025-01-XX  
**검증 범위**: 코드 레벨 검증 완료 (DB 연결 제외)

---

## ✅ 검증 완료 항목

### 1. 마이그레이션 파일 검증

#### `20251215_create_recommendations_tables_v2.sql`
- ✅ `pgcrypto` 확장 포함 (`CREATE EXTENSION IF NOT EXISTS "pgcrypto"`)
- ✅ `gen_random_uuid()` 사용 (3회 이상: scan_id, recommendation_id, event_id)
- ✅ Partial unique index 정의 (`uniq_active_recommendation_per_ticker`)
  - `WHERE status = 'ACTIVE'` 조건 포함
- ✅ `scan_results` 테이블 정의
  - UUID 기본키, `run_id`, `scanned_at`, `ticker`, `passed`, `reason_codes`, `signals_raw`
- ✅ `recommendations` 테이블 정의
  - UUID 기본키, `anchor_date`, `anchor_close`, `status`, `replaces_recommendation_id`, `replaced_by_recommendation_id`
- ✅ `recommendation_state_events` 테이블 정의
  - UUID 기본키, `recommendation_id` FK, `from_status`, `to_status`, `reason_code`
- ✅ `REPLACED` 상태 포함 (CHECK 제약)
- ✅ UUID 기본키 사용 (모든 테이블)

**결과**: ✅ **모든 필수 요소 포함**

---

### 2. Python 코드 구조 검증

#### 문법 검증
- ✅ `backend/services/recommendation_service_v2.py` - 문법 정상
- ✅ `backend/scripts/backfill_recommendations.py` - 문법 정상
- ✅ `backend/scripts/verify_v3_implementation.py` - 문법 정상
- ✅ `backend/tests/test_v3_constraints.py` - 문법 정상

**결과**: ✅ **모든 파일 문법 정상**

---

### 3. 핵심 함수 구현 검증

#### `recommendation_service_v2.py`
- ✅ `create_recommendation_transaction` 함수 존재
  - `FOR UPDATE` 사용 (기존 ACTIVE 잠금)
  - 기존 ACTIVE → REPLACED 전환 로직
  - 신규 ACTIVE 생성 로직
  - 상태 이벤트 로그 기록
- ✅ `transition_recommendation_status_transaction` 함수 존재
  - `FOR UPDATE` 사용 (현재 상태 잠금)
  - 단방향 전이 검증 로직
  - `BROKEN → ACTIVE` 금지 로직 (`WHEN from_status = 'BROKEN' AND %s = 'ACTIVE' THEN false`)
  - 상태 이벤트 로그 기록
- ✅ `get_active_recommendations` 함수 존재
- ✅ `check_duplicate_active_recommendations` 함수 존재

**결과**: ✅ **모든 핵심 함수 구현 완료**

---

### 4. 트랜잭션 안전성 검증

#### `create_recommendation_transaction`
```python
WITH current_active AS (
    SELECT recommendation_id
    FROM recommendations
    WHERE ticker = %s AND status = 'ACTIVE'
    FOR UPDATE  # ✅ 동시성 제어
)
UPDATE recommendations r
SET status = 'REPLACED',
    replaced_by_recommendation_id = %s
WHERE r.recommendation_id IN (SELECT recommendation_id FROM current_active)
```

- ✅ `FOR UPDATE` 사용으로 동시성 제어
- ✅ 기존 ACTIVE 자동 REPLACED 전환
- ✅ 신규 ACTIVE 생성 후 상태 이벤트 로그 기록

#### `transition_recommendation_status_transaction`
```python
WITH cur AS (
    SELECT recommendation_id, status AS from_status
    FROM recommendations
    WHERE recommendation_id = %s
    FOR UPDATE  # ✅ 동시성 제어
),
validate AS (
    SELECT ...,
    CASE
        WHEN from_status = 'BROKEN' AND %s = 'ACTIVE' THEN false  # ✅ 금지
        ...
    END AS ok
    FROM cur
)
```

- ✅ `FOR UPDATE` 사용으로 동시성 제어
- ✅ 단방향 전이 검증 로직
- ✅ `BROKEN → ACTIVE` 명시적 금지

**결과**: ✅ **트랜잭션 안전성 보장**

---

### 5. Backfill 스크립트 검증

#### `backfill_recommendations.py`
- ✅ `from services.recommendation_service_v2 import create_recommendation_transaction` 사용
- ✅ `create_recommendation_transaction` 함수 호출 (v2 서비스)
- ✅ UUID 기반 스키마 대응
- ✅ `anchor_date`/`anchor_close` 고정 저장

**결과**: ✅ **v2 스키마에 맞게 수정 완료**

---

### 6. 제약 조건 검증

#### Partial Unique Index
```sql
CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_recommendation_per_ticker
ON recommendations (ticker)
WHERE status = 'ACTIVE';
```
- ✅ 인덱스 정의 확인
- ✅ `WHERE status = 'ACTIVE'` 조건 포함
- ✅ DB 레벨에서 중복 ACTIVE 물리적 차단

#### 상태 전이 제약
- ✅ `BROKEN → ACTIVE` 금지 로직 확인
- ✅ 단방향 전이 검증 로직 확인
- ✅ `ARCHIVED`/`REPLACED` 상태에서 전이 금지

**결과**: ✅ **제약 조건 구현 확인**

---

### 7. 검증 스크립트 준비 상태

#### `verify_v3_implementation.py`
- ✅ `verify_table_exists` - 테이블 존재 확인
- ✅ `verify_partial_unique_index` - Partial unique index 검증
- ✅ `check_duplicate_active_recommendations` - 중복 ACTIVE 탐지
- ✅ `verify_kai_recommendations` - 047810 이력 확인
- ✅ `verify_state_events` - 상태 이벤트 로그 확인

#### `test_v3_constraints.py`
- ✅ `TestDuplicateActiveConstraint` - 중복 ACTIVE 방지 테스트
- ✅ `TestDBConstraintEnforcement` - DB 제약 강제 테스트
- ✅ `TestPastStateImmutability` - 과거 상태 불변 테스트

**결과**: ✅ **검증 스크립트 준비 완료**

---

## 📋 다음 단계 (실제 DB 환경에서 실행 필요)

### 필수 실행 항목

#### 1. DB 마이그레이션 실행
```bash
psql -h localhost -U postgres -d showmethestock \
  -f backend/migrations/20251215_create_recommendations_tables_v2.sql
```

**확인 사항**:
- `pgcrypto` 확장 활성화 확인
- 테이블 생성 확인 (`scan_results`, `recommendations`, `recommendation_state_events`)
- Partial unique index 생성 확인

#### 2. 검증 SQL 실행

**(A) 중복 ACTIVE 탐지**
```sql
SELECT ticker, COUNT(*) 
FROM recommendations 
WHERE status='ACTIVE' 
GROUP BY ticker 
HAVING COUNT(*) > 1;
```
**기대 결과**: 0행

**(B) 047810 이력 확인**
```sql
SELECT 
    recommendation_id, 
    anchor_date, 
    status, 
    created_at, 
    anchor_close
FROM recommendations 
WHERE ticker = '047810' 
ORDER BY created_at DESC;
```
**기대 결과**: ACTIVE 1개만 존재

**(C) 상태 이벤트 로그 확인**
```sql
SELECT 
    recommendation_id, 
    from_status, 
    to_status, 
    reason_code, 
    occurred_at
FROM recommendation_state_events 
WHERE recommendation_id = '<RECO_ID>'
ORDER BY occurred_at ASC;
```

#### 3. Backfill 실행

**Dry-run 먼저 실행**
```bash
python3 backend/scripts/backfill_recommendations.py --dry-run
```

**실제 실행**
```bash
python3 backend/scripts/backfill_recommendations.py
```

**확인 사항**:
- 047810의 중복 ACTIVE가 1개로 정리되는지
- `anchor_close`가 추천일 종가와 일치하는지

#### 4. 통합 검증 실행
```bash
python3 backend/scripts/verify_v3_implementation.py
```

#### 5. 제약 테스트 실행
```bash
cd backend && python3 -m unittest tests.test_v3_constraints
```

**확인 사항**:
- 동일 ticker로 ACTIVE 2개 생성 시 첫 번째가 REPLACED로 전환되는지
- DB 제약 위반 시 에러 발생하는지
- 과거 상태가 조회 시 재계산되지 않는지

---

## 🔍 핵심 계약 검증 결과

### 1. 스캔 ≠ 추천
- ✅ `scan_results` 테이블 (스캔 로그)
- ✅ `recommendations` 테이블 (추천 이벤트)
- ✅ 코드 레벨에서 분리 확인

### 2. 추천 이벤트 불변
- ✅ `anchor_date`/`anchor_close` 고정 저장 (INTEGER)
- ✅ 재계산 로직 없음 확인

### 3. ticker당 ACTIVE 1개
- ✅ Partial unique index (`uniq_active_recommendation_per_ticker`)
- ✅ 트랜잭션 레벨에서 기존 ACTIVE → REPLACED 전환
- ✅ 코드 레벨에서 중복 방지

### 4. 상태 단방향
- ✅ `ACTIVE → WEAK_WARNING → BROKEN → ARCHIVED` 단방향
- ✅ `BROKEN → ACTIVE` 금지 로직 확인

### 5. REPLACED/ARCHIVED 처리
- ✅ 트랜잭션에서 자동 REPLACED 전환
- ✅ `replaces_recommendation_id`/`replaced_by_recommendation_id` 관계 설정

---

## 📊 최종 평가

### 코드 레벨 검증 결과
- ✅ **마이그레이션 파일**: 모든 필수 요소 포함
- ✅ **Python 코드**: 문법 정상, 핵심 함수 구현 완료
- ✅ **트랜잭션 안전성**: `FOR UPDATE` 사용, 동시성 제어 구현
- ✅ **제약 조건**: Partial unique index, 상태 전이 제약 구현
- ✅ **Backfill 스크립트**: v2 스키마 대응 완료
- ✅ **검증 스크립트**: 준비 완료

### 결론
**코드 레벨에서 모든 핵심 계약이 구현되어 있음을 확인했습니다.**

다음 단계로 실제 DB 환경에서 마이그레이션 및 검증을 실행하여 운영 레벨 검증을 완료해야 합니다.

---

## 📝 참고 문서

- `backend/docs/V3_VERIFICATION_LOCATIONS.md` - 코드 위치 정리
- `backend/docs/V3_VERIFICATION_EXECUTION_GUIDE.md` - 실행 가이드
- `backend/docs/V3_VERIFICATION_EXECUTION_RESULTS.md` - 실행 결과
