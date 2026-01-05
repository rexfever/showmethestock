# v3 추천 시스템 핵심 구현 위치 정리

## 1. DB 스키마 DDL

### recommendations 테이블 생성
**위치**: `backend/migrations/20251215_create_recommendations_tables_v2.sql:43-85`
```sql
CREATE TABLE IF NOT EXISTS recommendations (
  recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  anchor_date DATE NOT NULL,
  anchor_close INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'WEAK_WARNING', 'BROKEN', 'ARCHIVED', 'REPLACED')),
  ...
);
```

### scan_results 테이블 생성
**위치**: `backend/migrations/20251215_create_recommendations_tables_v2.sql:12-22`
```sql
CREATE TABLE IF NOT EXISTS scan_results (
  scan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL,
  ticker TEXT NOT NULL,
  passed BOOLEAN NOT NULL,
  reason_codes TEXT[] NOT NULL,
  signals_raw JSONB NOT NULL
);
```

### recommendation_state_events 테이블 생성
**위치**: `backend/migrations/20251215_create_recommendations_tables_v2.sql:124-138`
```sql
CREATE TABLE IF NOT EXISTS recommendation_state_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_id UUID NOT NULL REFERENCES recommendations (recommendation_id),
  from_status TEXT NULL,
  to_status TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  ...
);
```

### Partial Unique Index (핵심 제약)
**위치**: `backend/migrations/20251215_create_recommendations_tables_v2.sql:90-92`
```sql
CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_recommendation_per_ticker
ON recommendations (ticker)
WHERE status = 'ACTIVE';
```

## 2. 추천 생성 트랜잭션

**위치**: `backend/services/recommendation_service_v2.py:17-133`

**함수**: `create_recommendation_transaction()`

**핵심 로직**:
1. 기존 ACTIVE를 FOR UPDATE로 잠금 (63-75줄)
2. 기존 ACTIVE를 REPLACED로 전환 (70-74줄)
3. 신규 ACTIVE 생성 (83-120줄)
4. 상태 이벤트 로그 기록 (122-129줄)

## 3. 상태 전이 로직

**위치**: `backend/services/recommendation_service_v2.py:136-235`

**함수**: `transition_recommendation_status_transaction()`

**핵심 검증** (175-195줄):
- ACTIVE → WEAK_WARNING, BROKEN, ARCHIVED 허용
- WEAK_WARNING → ACTIVE, BROKEN, ARCHIVED 허용
- BROKEN → ARCHIVED만 허용
- BROKEN → ACTIVE 금지
- ARCHIVED/REPLACED → 다른 상태 금지

## 4. Backfill 스크립트

**위치**: `backend/scripts/backfill_recommendations.py`

**함수**: `backfill_recommendations()` (143줄부터)

**로직**:
- ticker별로 그룹화
- 최신 ACTIVE 1개만 선택
- 나머지는 ARCHIVED/REPLACED 처리

## 5. 상태 전이 서비스 (기존)

**위치**: `backend/services/state_transition_service.py`

**함수**: `evaluate_active_recommendations()` (138줄부터)

**기능**: ACTIVE 추천을 평가하여 BROKEN으로 전이

