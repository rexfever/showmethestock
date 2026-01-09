# 마이그레이션 상태 확인 가이드

**작성일**: 2026-01-08  
**목적**: 데이터베이스 마이그레이션 상태 확인 및 필요한 마이그레이션 식별

---

## 개요

프로젝트는 여러 마이그레이션 파일을 포함하고 있으며, 이들이 모두 적용되었는지 확인해야 합니다.

---

## 마이그레이션 상태 확인

### 자동 확인 스크립트

```bash
cd backend
python3 scripts/check_migration_status.py
```

이 스크립트는 다음을 확인합니다:

1. **user_preferences 테이블** (20260127)
   - 테이블 존재 여부
   - 인덱스 존재 여부

2. **recommendations 테이블 컬럼**
   - `status_changed_at` (20260101)
   - `broken_return_pct` (20260102)
   - `archive_reason` (20260102)
   - `archived_snapshot` 컬럼들 (20260102)
   - `name` (20251231)

3. **recommendations 테이블 인덱스 최적화** (20250127)

4. **user_rec_ack 테이블**

---

## 주요 마이그레이션 파일

### 최근 마이그레이션 (2026년)

1. **20260127_create_user_preferences_table.sql**
   - `user_preferences` 테이블 생성
   - 사용자별 추천 방식 설정 저장

2. **20260102_add_broken_return_pct_column.sql**
   - `broken_return_pct` 컬럼 추가
   - BROKEN 상태일 때 종료 시점 수익률 저장

3. **20260102_add_reason_column_to_recommendations.sql**
   - `reason`, `archive_reason` 컬럼 추가
   - BROKEN/ARCHIVED 상태 종료 사유 저장

4. **20260102_add_archived_snapshot_columns.sql**
   - `archive_at`, `archived_close`, `archived_return_pct` 컬럼 추가
   - ARCHIVED 전환 시점 상태 스냅샷 저장

5. **20260101_add_status_changed_at_to_recommendations.sql**
   - `status_changed_at` 컬럼 추가
   - 상태 전이 시점 기록

### 이전 마이그레이션 (2025년)

6. **20251231_add_name_column_to_recommendations.sql**
   - `name` 컬럼 추가
   - 종목명 저장

7. **20251215_create_recommendations_tables_v2.sql**
   - `recommendations` 테이블 생성 (v2 스키마)
   - `scan_results`, `recommendation_state_events` 테이블 생성

8. **20250127_optimize_recommendations_query_indexes.sql**
   - recommendations 테이블 인덱스 최적화

---

## 마이그레이션 실행 방법

### 1. user_preferences 테이블

```bash
python3 backend/scripts/run_user_preferences_migration.py
```

또는 직접 SQL 실행:

```bash
psql -d stockfinder -f backend/migrations/20260127_create_user_preferences_table.sql
```

### 2. recommendations 테이블 (기본)

```bash
python3 backend/scripts/run_migration_v3.py
```

또는 직접 SQL 실행:

```bash
psql -d stockfinder -f backend/migrations/20251215_create_recommendations_tables_v2.sql
```

### 3. recommendations 테이블 컬럼 추가

각 마이그레이션 파일을 순서대로 실행:

```bash
# status_changed_at
psql -d stockfinder -f backend/migrations/20260101_add_status_changed_at_to_recommendations.sql

# broken_return_pct
psql -d stockfinder -f backend/migrations/20260102_add_broken_return_pct_column.sql

# reason, archive_reason
psql -d stockfinder -f backend/migrations/20260102_add_reason_column_to_recommendations.sql

# archived_snapshot 컬럼들
psql -d stockfinder -f backend/migrations/20260102_add_archived_snapshot_columns.sql

# name
psql -d stockfinder -f backend/migrations/20251231_add_name_column_to_recommendations.sql
```

### 4. 인덱스 최적화

```bash
psql -d stockfinder -f backend/migrations/20250127_optimize_recommendations_query_indexes.sql
```

### 5. user_rec_ack 테이블

```bash
psql -d stockfinder -f backend/migrations/add_user_rec_ack_table.sql
```

---

## 마이그레이션 순서

마이그레이션은 다음 순서로 실행해야 합니다:

1. **기본 테이블 생성**
   - `20251215_create_recommendations_tables_v2.sql`

2. **컬럼 추가 (순서 중요)**
   - `20251231_add_name_column_to_recommendations.sql`
   - `20260101_add_status_changed_at_to_recommendations.sql`
   - `20260102_add_broken_return_pct_column.sql`
   - `20260102_add_reason_column_to_recommendations.sql`
   - `20260102_add_archived_snapshot_columns.sql`

3. **인덱스 최적화**
   - `20250127_optimize_recommendations_query_indexes.sql`

4. **기타 테이블**
   - `20260127_create_user_preferences_table.sql`
   - `add_user_rec_ack_table.sql`

---

## 주의사항

### 1. IF NOT EXISTS 사용

대부분의 마이그레이션 파일은 `IF NOT EXISTS` 또는 `ADD COLUMN IF NOT EXISTS`를 사용하므로, 중복 실행해도 안전합니다.

### 2. 데이터 백업

마이그레이션 실행 전 데이터 백업을 권장합니다:

```bash
# 백업
pg_dump -d stockfinder > backup_$(date +%Y%m%d_%H%M%S).sql

# 복원 (필요 시)
psql -d stockfinder < backup_YYYYMMDD_HHMMSS.sql
```

### 3. 트랜잭션

각 마이그레이션 파일은 자체적으로 트랜잭션을 관리합니다. 실패 시 롤백됩니다.

### 4. 서버 마이그레이션

서버에 마이그레이션을 적용할 때는:

```bash
# SSH 터널 생성
ssh -f -N -L 5433:localhost:5432 stock-finder

# 환경 변수 설정
export SERVER_DATABASE_URL="postgresql://stockfinder:stockfinder_pass@localhost:5433/stockfinder"

# 마이그레이션 실행
psql "$SERVER_DATABASE_URL" -f backend/migrations/<파일명>.sql
```

---

## 마이그레이션 검증

마이그레이션 실행 후 검증:

```bash
# 상태 확인 스크립트 실행
python3 backend/scripts/check_migration_status.py

# 또는 직접 확인
psql -d stockfinder -c "\d recommendations"
psql -d stockfinder -c "\d user_preferences"
```

---

## 문제 해결

### 1. 마이그레이션 실패

- 오류 메시지 확인
- 데이터베이스 로그 확인
- 백업에서 복원 후 재시도

### 2. 컬럼 중복 오류

- `IF NOT EXISTS`를 사용하는 마이그레이션은 안전
- 직접 `ALTER TABLE` 실행 시 주의

### 3. 인덱스 생성 실패

- 기존 인덱스 확인: `\d+ recommendations`
- 필요 시 수동으로 인덱스 생성

---

## 관련 파일

### 마이그레이션 스크립트
- `backend/scripts/check_migration_status.py`: 마이그레이션 상태 확인
- `backend/scripts/run_user_preferences_migration.py`: user_preferences 마이그레이션
- `backend/scripts/run_migration_v3.py`: recommendations 기본 마이그레이션

### 마이그레이션 SQL 파일
- `backend/migrations/20260127_create_user_preferences_table.sql`
- `backend/migrations/20260102_*.sql`: recommendations 컬럼 추가
- `backend/migrations/20260101_add_status_changed_at_to_recommendations.sql`
- `backend/migrations/20251215_create_recommendations_tables_v2.sql`

---

**작성일**: 2026-01-08  
**최종 업데이트**: 2026-01-08  
**상태**: 문서화 완료

