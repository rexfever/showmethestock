# v3 추천 시스템 2단계 - 트랜잭션 SQL 템플릿

## 개요

v3 추천 시스템의 핵심 트랜잭션 로직을 SQL 템플릿으로 제공합니다.

## 주요 트랜잭션

### 1. 추천 생성(승격) 트랜잭션

**정책**:
- 동일 ticker ACTIVE는 1개만 (partial unique index가 최후 방어)
- 기존 ACTIVE가 있으면 REPLACED로 전환 후 신규 ACTIVE 생성
- anchor_date/anchor_close는 생성 시점에 1회 고정 저장

**동시성 제어**:
- `FOR UPDATE`로 기존 ACTIVE를 잠금
- 트랜잭션 내에서 원자적으로 처리

**Python 구현**: `services/recommendation_service_v2.py::create_recommendation_transaction()`

### 2. 상태 전이(단방향) 트랜잭션

**정책**:
- ACTIVE -> WEAK_WARNING -> BROKEN -> ARCHIVED 단방향
- BROKEN -> ACTIVE 복귀 금지
- 상태 변경은 반드시 recommendation_state_events에 기록

**검증 로직**:
- 현재 상태와 목표 상태를 검증
- 유효한 전이만 허용
- 실제 업데이트가 일어났을 때만 로그 기록

**Python 구현**: `services/recommendation_service_v2.py::transition_recommendation_status_transaction()`

## 모니터링 쿼리

### 중복 ACTIVE 점검
```sql
SELECT ticker, COUNT(*)
FROM recommendations
WHERE status='ACTIVE'
GROUP BY ticker
HAVING COUNT(*) > 1;
```

**Python 구현**: `services/recommendation_service_v2.py::check_duplicate_active_recommendations()`

## 주의사항

1. **gen_random_uuid()**: `pgcrypto` 확장 필요
   - 마이그레이션 파일에 `CREATE EXTENSION IF NOT EXISTS "pgcrypto";` 포함
   - 없으면 애플리케이션에서 UUID 생성

2. **Partial Unique Index**: 
   - `uniq_active_recommendation_per_ticker`가 DB 레벨에서 ACTIVE 중복 차단
   - 최후 방어선 역할

3. **트랜잭션 격리 수준**:
   - `FOR UPDATE`로 동시성 제어
   - READ COMMITTED 이상 권장

## 사용 예시

### Python에서 추천 생성
```python
from services.recommendation_service_v2 import create_recommendation_transaction
from datetime import date

rec_id = create_recommendation_transaction(
    ticker="047810",
    anchor_date=date(2025, 12, 15),
    anchor_close=50000,  # INTEGER, 원 단위
    anchor_source="KRX_EOD",
    reason_code="RECOMMEND_CREATED"
)
```

### Python에서 상태 전이
```python
from services.recommendation_service_v2 import transition_recommendation_status_transaction
import uuid

success = transition_recommendation_status_transaction(
    recommendation_id=uuid.UUID("..."),
    to_status="BROKEN",
    reason_code="HARD_STOP_TOUCHED",
    reason_text="손절가 도달",
    metadata={"current_return": -5.0}
)
```

