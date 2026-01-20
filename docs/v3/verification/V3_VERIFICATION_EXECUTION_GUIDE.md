# v3 추천 시스템 검증 실행 가이드

## 🎯 검증 목표

운영 관점에서 v3의 핵심 계약이 DB/코드 레벨에서 깨지지 않는지 증명:
1. 스캔 ≠ 추천 (분리)
2. 추천 이벤트 불변 (anchor_date/anchor_close 고정)
3. ticker당 ACTIVE 1개 (물리적 불가능)
4. 상태 단방향 전이 (BROKEN → ACTIVE 금지)
5. REPLACED/ARCHIVED 처리

---

## 📋 검증 체크리스트

### 1단계: 코드베이스 위치 확인 ✅
- [x] recommendations 테이블 DDL: `backend/migrations/20251215_create_recommendations_tables_v2.sql:43-85`
- [x] scan_results 테이블 DDL: `backend/migrations/20251215_create_recommendations_tables_v2.sql:12-22`
- [x] recommendation_state_events 테이블 DDL: `backend/migrations/20251215_create_recommendations_tables_v2.sql:124-138`
- [x] Partial unique index: `backend/migrations/20251215_create_recommendations_tables_v2.sql:90-92`
- [x] 추천 생성 트랜잭션: `backend/services/recommendation_service_v2.py:17-133`
- [x] 상태 전이 로직: `backend/services/recommendation_service_v2.py:154-260`
- [x] Backfill 스크립트: `backend/scripts/backfill_recommendations.py:143-276`

### 2단계: DB 마이그레이션 실행
```bash
# 마이그레이션 실행
psql -h localhost -U postgres -d showmethestock \
  -f backend/migrations/20251215_create_recommendations_tables_v2.sql

# 확장 확인
psql -h localhost -U postgres -d showmethestock -c "
SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgcrypto');
"
```

**예상 결과**:
- `uuid-ossp`: 존재
- `pgcrypto`: 존재
- 테이블 3개 생성됨
- 인덱스 생성됨

### 3단계: 검증 SQL 실행 (Backfill 전)

#### (A) 중복 ACTIVE 탐지
```sql
SELECT ticker, COUNT(*) as count
FROM recommendations
WHERE status = 'ACTIVE'
GROUP BY ticker
HAVING COUNT(*) > 1;
```

**기대 결과**: 0행

#### (B) 047810 이력 확인
```sql
SELECT 
    recommendation_id,
    anchor_date,
    status,
    created_at,
    anchor_close,
    replaces_recommendation_id,
    replaced_by_recommendation_id
FROM recommendations
WHERE ticker = '047810'
ORDER BY created_at DESC;
```

**기대 결과**: 
- ACTIVE는 최대 1개
- 나머지는 REPLACED 또는 ARCHIVED

#### (C) 상태 이벤트 로그 확인
```sql
-- 먼저 047810의 recommendation_id 하나 선택
SELECT recommendation_id FROM recommendations WHERE ticker = '047810' LIMIT 1;

-- 해당 ID의 이벤트 로그 확인
SELECT 
    event_id,
    recommendation_id,
    from_status,
    to_status,
    reason_code,
    occurred_at
FROM recommendation_state_events
WHERE recommendation_id = '<위에서 조회한 ID>'
ORDER BY occurred_at ASC;
```

**기대 결과**: 모든 상태 변경이 로그에 기록됨

### 4단계: Backfill Dry-Run
```bash
python3 backend/scripts/backfill_recommendations.py --dry-run
```

**예상 출력**:
- 조회된 scan_rank 데이터 수
- ticker별 그룹화 결과
- 선택된 추천 목록
- 047810의 경우: 여러 날짜 중 최신 1개만 ACTIVE로 선택

### 5단계: Backfill 실제 실행
```bash
python3 backend/scripts/backfill_recommendations.py
```

**예상 결과**:
- 생성된 recommendations 수
- 건너뛴 recommendations 수
- 오류 수

### 6단계: Backfill 후 재검증

#### (A) 중복 ACTIVE 재확인
```sql
SELECT ticker, COUNT(*) as count
FROM recommendations
WHERE status = 'ACTIVE'
GROUP BY ticker
HAVING COUNT(*) > 1;
```

**기대 결과**: 0행 (중복 없음)

#### (B) 047810 재확인
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

**기대 결과**: ACTIVE 1개만

### 7단계: DB 제약 강제 테스트
```bash
cd backend
python3 -m unittest tests.test_v3_constraints.TestDuplicateActiveConstraint
```

**예상 결과**:
- ✅ 첫 번째 ACTIVE 생성 성공
- ✅ 두 번째 ACTIVE 생성 시 첫 번째가 REPLACED로 전환
- ✅ ACTIVE는 1개만 존재

### 8단계: anchor_close 불변성 테스트
```bash
cd backend
python3 -m unittest tests.test_v3_constraints.TestAnchorCloseImmutability
```

**예상 결과**:
- ✅ anchor_close가 변경되지 않음
- ✅ anchor_date가 변경되지 않음

### 9단계: 통합 검증 스크립트 실행
```bash
python3 backend/scripts/verify_v3_implementation.py
```

**예상 출력**:
- 테이블 존재 확인: ✅
- Partial unique index: ✅
- 중복 ACTIVE 없음: ✅
- 제약 강제 테스트: ✅
- 불변성 테스트: ✅

---

## 📊 검증 결과 템플릿

### 마이그레이션 실행 로그
```
✅ uuid-ossp 확장 활성화
✅ pgcrypto 확장 활성화
✅ scan_results 테이블 생성
✅ recommendations 테이블 생성
✅ recommendation_state_events 테이블 생성
✅ uniq_active_recommendation_per_ticker 인덱스 생성
✅ 트리거 생성
```

### Backfill 전 검증 결과
```
(A) 중복 ACTIVE: X행 (X > 0이면 문제)
(B) 047810 ACTIVE: X개 (X > 1이면 문제)
```

### Backfill 후 검증 결과
```
(A) 중복 ACTIVE: 0행 ✅
(B) 047810 ACTIVE: 1개 ✅
```

### 제약 테스트 결과
```
✅ 첫 번째 ACTIVE 생성 성공
✅ 두 번째 ACTIVE 생성 시 첫 번째가 REPLACED로 전환
✅ ACTIVE는 1개만 존재
```

### 불변성 테스트 결과
```
✅ anchor_close 불변: 50000 → 50000
✅ anchor_date 불변: 2025-12-15 → 2025-12-15
```

---

## 🔧 문제 해결 가이드

### 마이그레이션 실패 시

#### 문제 1: 확장 권한 없음
```sql
-- 권한 확인
SELECT has_database_privilege(current_user, 'showmethestock', 'CREATE');

-- 수동 확장 생성
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

#### 문제 2: 테이블 이미 존재
```sql
-- 기존 테이블 확인
SELECT tablename FROM pg_tables WHERE schemaname = 'public' 
  AND tablename IN ('recommendations', 'scan_results', 'recommendation_state_events');

-- 필요시 삭제 후 재생성 (주의: 데이터 손실)
DROP TABLE IF EXISTS recommendation_state_events CASCADE;
DROP TABLE IF EXISTS recommendations CASCADE;
DROP TABLE IF EXISTS scan_results CASCADE;
```

### 중복 ACTIVE 발견 시

#### 원인 분석
```sql
-- 중복 ACTIVE 상세 확인
SELECT 
    recommendation_id,
    ticker,
    status,
    created_at,
    anchor_date
FROM recommendations
WHERE ticker IN (
    SELECT ticker
    FROM recommendations
    WHERE status = 'ACTIVE'
    GROUP BY ticker
    HAVING COUNT(*) > 1
)
AND status = 'ACTIVE'
ORDER BY ticker, created_at;
```

#### 수동 정리
```sql
-- 최신 ACTIVE만 남기고 나머지 REPLACED로 전환
WITH latest_active AS (
    SELECT DISTINCT ON (ticker) recommendation_id
    FROM recommendations
    WHERE status = 'ACTIVE'
    ORDER BY ticker, created_at DESC
)
UPDATE recommendations
SET status = 'REPLACED',
    updated_at = NOW()
WHERE status = 'ACTIVE'
AND recommendation_id NOT IN (SELECT recommendation_id FROM latest_active);
```

---

## 📝 최종 산출물 체크리스트

- [ ] 마이그레이션 실행 로그
- [ ] Backfill 전 검증 SQL 결과 (A)(B)(C)
- [ ] Backfill dry-run 출력
- [ ] Backfill 실행 로그
- [ ] Backfill 후 검증 SQL 결과 (A)(B)
- [ ] 제약 강제 테스트 결과
- [ ] 불변성 테스트 결과
- [ ] 통합 검증 스크립트 출력
- [ ] 발견된 문제 및 수정 사항

---

**준비 상태**: ✅ 완료  
**실행 대기**: 실제 DB 환경에서 실행 필요

