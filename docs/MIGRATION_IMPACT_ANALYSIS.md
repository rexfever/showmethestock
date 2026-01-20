# 마이그레이션 영향 분석

**작성일**: 2026-01-08  
**목적**: 마이그레이션 실행 시 기존 로직에 미치는 영향 분석

---

## 개요

마이그레이션 실행 시 기존 로직이 붕괴될 수 있는지 확인한 결과, **일부 마이그레이션은 필수**이며, 실행하지 않으면 **기존 코드가 오류를 발생시킵니다**.

---

## 위험도 분석

### 🔴 높은 위험도: 필수 마이그레이션

다음 마이그레이션은 **코드에서 필수로 사용**하므로 반드시 실행해야 합니다:

1. **status_changed_at 컬럼** (20260101)
   - **사용 위치**: `recommendation_service.py`, `recommendation_service_v2.py`
   - **위험**: 마이그레이션 없이 실행 시 SQL 오류 발생
   - **안전성**: `IF NOT EXISTS` 사용, 기존 레코드는 `created_at`으로 초기화

2. **broken_return_pct 컬럼** (20260102)
   - **사용 위치**: `recommendation_service.py`
   - **위험**: 마이그레이션 없이 실행 시 SQL 오류 발생
   - **안전성**: `IF NOT EXISTS` 사용, NULL 허용

3. **archive_reason 컬럼** (20260102)
   - **사용 위치**: `recommendation_service.py`, `recommendation_service_v2.py`
   - **위험**: 마이그레이션 없이 실행 시 SQL 오류 발생
   - **안전성**: `IF NOT EXISTS` 사용, NULL 허용

4. **archived_snapshot 컬럼들** (20260102)
   - `archive_at`, `archived_close`, `archived_return_pct`, `archive_price`, `archive_phase`
   - **사용 위치**: `recommendation_service.py`, `recommendation_service_v2.py`
   - **위험**: 마이그레이션 없이 실행 시 SQL 오류 발생
   - **안전성**: `IF NOT EXISTS` 사용, NULL 허용

### 🟡 중간 위험도: 선택적 마이그레이션

다음 마이그레이션은 **코드에서 선택적으로 사용**하므로 실행하지 않아도 기존 로직은 동작합니다:

1. **user_preferences 테이블** (20260127)
   - **사용 위치**: 사용자 설정 기능 (선택적)
   - **위험**: 낮음 (기존 로직에 영향 없음)
   - **안전성**: `IF NOT EXISTS` 사용

### 🟢 낮은 위험도: 안전한 마이그레이션

다음 마이그레이션은 **기존 로직에 영향 없이 안전하게 실행**됩니다:

1. **인덱스 최적화** (20250127)
   - **위험**: 없음 (성능 향상만)
   - **안전성**: `IF NOT EXISTS` 사용

---

## 코드 의존성 분석

### 1. recommendation_service.py

**Line 378-390**: ARCHIVED 전환 시 다음 컬럼들을 **필수로 사용**:

```python
UPDATE recommendations
SET status = 'ARCHIVED',
    archived_at = NOW(),
    archive_reason = %s,           # 필수
    broken_at = %s,
    broken_return_pct = %s,         # 필수
    archive_return_pct = %s,        # 필수
    archive_price = %s,             # 필수
    archive_phase = %s,             # 필수
    updated_at = NOW(),
    status_changed_at = NOW()       # 필수
WHERE recommendation_id = %s
```

**위험**: 마이그레이션 없이 실행 시 `column does not exist` 오류 발생

### 2. recommendation_service_v2.py

**Line 513-530**: 상태 전이 시 다음 컬럼들을 **필수로 사용**:

```python
UPDATE recommendations
SET status = %s,
    updated_at = NOW(),
    status_changed_at = NOW(),      # 필수
    archived_at = NOW(),
    archive_reason = %s,             # 필수
    archive_return_pct = %s,         # 필수
    archive_price = %s,              # 필수
    archive_phase = %s               # 필수
WHERE recommendation_id = %s
```

**위험**: 마이그레이션 없이 실행 시 `column does not exist` 오류 발생

### 3. state_transition_service.py

**의존성**: `transition_recommendation_status` 함수를 호출하는데, 이 함수는 `recommendation_service_v2.py`의 `transition_recommendation_status_transaction`을 사용합니다.

**위험**: 마이그레이션 없이 실행 시 간접적으로 오류 발생

---

## 마이그레이션별 안전성 분석

### 1. status_changed_at (20260101)

**마이그레이션 단계**:
1. `ADD COLUMN IF NOT EXISTS` - 안전
2. 기존 레코드에 `created_at` 값으로 초기화 - 안전
3. `NOT NULL` 제약 추가 - **주의 필요**

**잠재적 문제**:
- 기존 레코드가 없거나 `created_at`이 NULL이면 `NOT NULL` 제약 추가 실패
- 하지만 마이그레이션에서 `created_at`으로 초기화하므로 안전

**결론**: ✅ 안전 (기존 레코드 초기화 후 NOT NULL 추가)

### 2. broken_return_pct (20260102)

**마이그레이션 단계**:
1. `ADD COLUMN IF NOT EXISTS` - 안전
2. NULL 허용 - 안전

**결론**: ✅ 안전

### 3. archive_reason (20260102)

**마이그레이션 단계**:
1. `ADD COLUMN IF NOT EXISTS` - 안전
2. NULL 허용 - 안전

**결론**: ✅ 안전

### 4. archived_snapshot 컬럼들 (20260102)

**마이그레이션 단계**:
1. `archive_at` 추가 시 `archived_at`이 있으면 복사 - 안전
2. `ADD COLUMN IF NOT EXISTS` - 안전
3. NULL 허용 - 안전

**결론**: ✅ 안전

---

## 마이그레이션 실행 전 체크리스트

### 필수 확인 사항

1. **데이터 백업**
   ```bash
   pg_dump -d stockfinder > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **기존 레코드 확인**
   ```sql
   SELECT COUNT(*) FROM recommendations;
   SELECT COUNT(*) FROM recommendations WHERE created_at IS NULL;
   ```

3. **현재 스키마 확인**
   ```sql
   \d recommendations
   ```

### 실행 순서

1. **기본 테이블 생성** (이미 있으면 건너뜀)
   ```bash
   psql -d stockfinder -f backend/migrations/20251215_create_recommendations_tables_v2.sql
   ```

2. **필수 컬럼 추가** (순서 중요)
   ```bash
   # status_changed_at (NOT NULL 제약 추가 전 초기화 필요)
   psql -d stockfinder -f backend/migrations/20260101_add_status_changed_at_to_recommendations.sql
   
   # broken_return_pct
   psql -d stockfinder -f backend/migrations/20260102_add_broken_return_pct_column.sql
   
   # reason, archive_reason
   psql -d stockfinder -f backend/migrations/20260102_add_reason_column_to_recommendations.sql
   
   # archived_snapshot 컬럼들
   psql -d stockfinder -f backend/migrations/20260102_add_archived_snapshot_columns.sql
   ```

3. **인덱스 최적화** (선택적)
   ```bash
   psql -d stockfinder -f backend/migrations/20250127_optimize_recommendations_query_indexes.sql
   ```

4. **기타 테이블** (선택적)
   ```bash
   psql -d stockfinder -f backend/migrations/20260127_create_user_preferences_table.sql
   ```

---

## 롤백 계획

### 마이그레이션 롤백

대부분의 마이그레이션은 **컬럼 추가만** 하므로, 롤백은 컬럼 삭제로 가능합니다:

```sql
-- 주의: 데이터 손실 가능
ALTER TABLE recommendations DROP COLUMN IF EXISTS status_changed_at;
ALTER TABLE recommendations DROP COLUMN IF EXISTS broken_return_pct;
ALTER TABLE recommendations DROP COLUMN IF EXISTS archive_reason;
-- ...
```

**권장**: 백업에서 복원

```bash
# 백업에서 복원
psql -d stockfinder < backup_YYYYMMDD_HHMMSS.sql
```

---

## 결론

### 마이그레이션 실행 필요성

✅ **필수**: 다음 마이그레이션은 반드시 실행해야 합니다:
- `20260101_add_status_changed_at_to_recommendations.sql`
- `20260102_add_broken_return_pct_column.sql`
- `20260102_add_reason_column_to_recommendations.sql`
- `20260102_add_archived_snapshot_columns.sql`

### 기존 로직 붕괴 가능성

**높음**: 마이그레이션 없이 실행 시:
- `recommendation_service.py`의 ARCHIVED 전환 로직 오류
- `recommendation_service_v2.py`의 상태 전이 로직 오류
- `state_transition_service.py`의 간접 오류

**낮음**: 마이그레이션 실행 후:
- 모든 마이그레이션은 `IF NOT EXISTS` 사용
- 기존 레코드는 안전하게 초기화
- NULL 허용 컬럼은 기존 로직에 영향 없음

### 권장 사항

1. **마이그레이션 실행 전 백업 필수**
2. **순서대로 실행** (의존성 고려)
3. **실행 후 검증** (`check_migration_status.py` 사용)
4. **문제 발생 시 백업에서 복원**

---

**작성일**: 2026-01-08  
**최종 업데이트**: 2026-01-08  
**상태**: 분석 완료

