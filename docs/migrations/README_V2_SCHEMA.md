# v3 추천 시스템 스키마 v2 변경사항

## 주요 변경사항

### 1. UUID 사용
- **이전**: `BIGSERIAL` (정수 ID)
- **변경**: `UUID` (고유 식별자)
- **이유**: 분산 환경에서 고유성 보장, 보안성 향상

### 2. scan_results 구조 변경
- **이전**: `scan_date`, `scan_run_id`, `name`, `score`, `score_label`, `strategy`, `indicators`, `flags`, `details`
- **변경**: `run_id` (UUID), `scanned_at`, `ticker`, `passed`, `reason_codes`, `signals_raw`
- **이유**: 더 간결하고 목적에 맞는 구조

### 3. recommendations 구조 변경
- **추가 필드**:
  - `replaces_recommendation_id`: 이 추천이 대체한 추천 ID
  - `replaced_by_recommendation_id`: 이 추천을 대체한 추천 ID
  - `cooldown_until`: 재진입 쿨다운 종료일
- **상태 추가**: `REPLACED` 상태 추가
- **anchor_close 타입**: `DOUBLE PRECISION` → `INTEGER` (원 단위)

### 4. recommendation_state_events 구조 변경
- **이전**: `id`, `recommendation_id` (BIGINT), `from_status`, `to_status`, `reason`, `metadata`, `created_at`
- **변경**: `event_id` (UUID), `recommendation_id` (UUID), `reason_code`, `reason_text`, `metadata`, `occurred_at`

## 마이그레이션 전략

### 옵션 1: 완전 교체 (권장)
- 기존 테이블 삭제 후 새 스키마로 재생성
- 백필 스크립트로 데이터 재마이그레이션

### 옵션 2: 점진적 마이그레이션
- 기존 테이블 유지
- 새 스키마 테이블 생성
- 데이터 점진적 이전

## 코드 수정 필요 사항

### 1. recommendation_service.py
- `create_recommendation()`: UUID 사용, `replaces_recommendation_id` 설정
- `save_scan_results()`: 새 스키마에 맞게 수정
- 반환 타입: `int` → `UUID` 또는 `str`

### 2. state_transition_service.py
- `transition_recommendation_status()`: UUID 사용
- `REPLACED` 상태 처리 추가

### 3. API 엔드포인트
- ID 타입 변경: `int` → `UUID` (문자열로 처리)

## 하위 호환성

새 스키마에 하위 호환 필드 추가:
- `name`, `score`, `score_label`, `strategy`, `indicators`, `flags`, `details`
- 기존 코드와의 호환성 유지

## 마이그레이션 실행

```bash
# 새 스키마 적용
psql -h localhost -U postgres -d showmethestock -f backend/migrations/20251215_create_recommendations_tables_v2.sql
```

