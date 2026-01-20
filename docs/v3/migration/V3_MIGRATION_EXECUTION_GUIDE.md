# v3 추천 시스템 마이그레이션 실행 가이드

## 개요

이 가이드는 v3 추천 시스템의 DB 마이그레이션을 실제 환경에서 실행하는 방법을 설명합니다.

---

## 사전 준비

### 1. DB 연결 정보 확인

다음 환경 변수 중 하나가 설정되어 있어야 합니다:
- `DATABASE_URL`
- `POSTGRES_DSN`
- `DB_URL`

또는 `.env` 파일에 설정:
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

### 2. DB 연결 테스트

```bash
cd backend
python3 -c "from db_manager import db_manager; \
    with db_manager.get_cursor(commit=False) as cur: \
        cur.execute('SELECT version();'); \
        print('✅ DB 연결 성공:', cur.fetchone()[0])"
```

---

## 마이그레이션 실행 방법

### 방법 1: Python 스크립트 사용 (권장)

```bash
cd backend
python3 scripts/run_migration_v3.py
```

이 스크립트는:
- DB 연결 확인
- 기존 테이블 확인
- 마이그레이션 SQL 실행
- 마이그레이션 검증

### 방법 2: psql 직접 사용

```bash
psql $DATABASE_URL -f backend/migrations/20251215_create_recommendations_tables_v2.sql
```

또는:

```bash
psql -h localhost -U postgres -d showmethestock \
  -f backend/migrations/20251215_create_recommendations_tables_v2.sql
```

---

## 마이그레이션 후 검증

### 1. 테이블 생성 확인

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('recommendations', 'scan_results', 'recommendation_state_events')
ORDER BY table_name;
```

**기대 결과**: 3개 테이블 모두 존재

### 2. Partial Unique Index 확인

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'recommendations'
AND indexname = 'uniq_active_recommendation_per_ticker';
```

**기대 결과**: 인덱스 존재, `WHERE status = 'ACTIVE'` 조건 포함

### 3. 확장(Extension) 확인

```sql
SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgcrypto');
```

**기대 결과**: `uuid-ossp`, `pgcrypto` 확장 존재

---

## Backfill 실행

마이그레이션 후 기존 데이터를 새 테이블로 이전:

```bash
# Dry-run 먼저 실행
python3 backend/scripts/backfill_recommendations.py --dry-run

# 실제 실행
python3 backend/scripts/backfill_recommendations.py
```

---

## 통합 검증

```bash
# 통합 검증 스크립트 실행
python3 backend/scripts/verify_v3_implementation.py

# 제약 테스트 실행
cd backend && python3 -m unittest tests.test_v3_constraints
```

---

## 문제 해결

### DB 연결 실패

**증상**: `DATABASE_URL (or POSTGRES_DSN) is not configured`

**해결**:
1. 환경 변수 확인: `echo $DATABASE_URL`
2. `.env` 파일 확인: `cat backend/.env | grep DATABASE`
3. 환경 변수 설정: `export DATABASE_URL=postgresql://...`

### 마이그레이션 실패

**증상**: `permission denied` 또는 `relation already exists`

**해결**:
1. DB 사용자 권한 확인
2. 기존 테이블 확인: `\dt` (psql)
3. 필요시 기존 테이블 삭제 (주의: 데이터 손실)

### 확장(Extension) 오류

**증상**: `gen_random_uuid() does not exist`

**해결**:
```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

---

## 롤백 (필요시)

마이그레이션을 롤백하려면:

```sql
-- 테이블 삭제 (주의: 데이터 손실)
DROP TABLE IF EXISTS recommendation_state_events CASCADE;
DROP TABLE IF EXISTS recommendations CASCADE;
DROP TABLE IF EXISTS scan_results CASCADE;

-- 인덱스 삭제
DROP INDEX IF EXISTS uniq_active_recommendation_per_ticker;
```

---

## 다음 단계

마이그레이션 완료 후:

1. ✅ Backfill 실행 (기존 데이터 이전)
2. ✅ 통합 검증 실행
3. ✅ 제약 테스트 실행
4. ✅ API 엔드포인트 테스트

---

## 참고 문서

- `backend/docs/V3_VERIFICATION_COMPLETE.md` - 검증 완료 리포트
- `backend/docs/V3_VERIFICATION_FINAL_REPORT.md` - 최종 검증 리포트
- `backend/migrations/20251215_create_recommendations_tables_v2.sql` - 마이그레이션 SQL

