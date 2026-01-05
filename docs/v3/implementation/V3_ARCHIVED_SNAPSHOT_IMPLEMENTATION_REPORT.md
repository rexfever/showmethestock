# V3 ARCHIVED 스냅샷 기록 구현 작업 결과서

**작업 일자**: 2026-01-02  
**작업 범위**: V3 추천 시스템 - ARCHIVED 전환 스냅샷 기록, daily_digest 서버 집계, 리그레션 복구

---

## 목차

1. [작업 개요](#작업-개요)
2. [작업 1: V3 리그레션 복구 + ARCHIVED 전용 UX 완결](#작업-1-v3-리그레션-복구--archived-전용-ux-완결)
3. [작업 2: daily_digest 서버 집계 + 상태 전이 시점 기록](#작업-2-daily_digest-서버-집계--상태-전이-시점-기록)
4. [작업 3: ARCHIVED 전환 스냅샷 기록](#작업-3-archived-전환-스냅샷-기록)
5. [검증 결과](#검증-결과)
6. [변경 파일 목록](#변경-파일-목록)
7. [다음 단계](#다음-단계)

---

## 작업 개요

### 목표
1. **리그레션 복구**: ACTIVE/WEAK 카드에서 수익률 표시 복구 및 카드 컴포넌트 물리적 분리
2. **daily_digest 구현**: 서버에서 일관되게 일일 변화 집계 (신규 추천/BROKEN/ARCHIVED 건수)
3. **ARCHIVED 스냅샷**: ARCHIVED 전환 시점의 상태(손익/사유/시점)를 불변 스냅샷으로 저장

### 핵심 원칙
- **ARCHIVED = 추천 관리 종료** (성과와 무관)
- **스냅샷은 불변**: 이후 가격 변동과 무관하게 전환 시점 상태 유지
- **서버 기준 집계**: 클라이언트 계산 없이 서버에서 일관된 데이터 제공
- **KST 기준**: 모든 시간 계산은 KST(Asia/Seoul) 기준

---

## 작업 1: V3 리그레션 복구 + ARCHIVED 전용 UX 완결

### 목표
ARCHIVED 작업 중 발생한 리그레션을 복구하고, ACTIVE/WEAK/BROKEN과 분리된 ARCHIVED 전용 UX를 완결

### 구현 내용

#### 1.1 카드 컴포넌트 물리적 분리
- **기존**: `RecommendationCardV3` 하나로 모든 상태 처리
- **변경**: 상태별 독립 컴포넌트로 분리
  - `ActiveRecommendationCard.js` - ACTIVE 전용
  - `WeakRecommendationCard.js` - WEAK_WARNING 전용
  - `BrokenRecommendationCard.js` - BROKEN 전용
  - `ArchivedCardV3.js` - ARCHIVED 전용 (기존)

#### 1.2 ACTIVE 카드 리그레션 복구
- **수익률 표시 복구**: 보조 정보로만 표시 (강조 색상/큰 폰트 금지)
- **추천일 + 경과 거래일 표시 유지**
- **행동 유도 문구 제거**: "관찰 중인 추천입니다" (매수/진입/기회 문구 없음)

#### 1.3 ARCHIVED 전용 UX 완성
- **섹션명**: "정리된 추천" (고정)
- **섹션 상단 설명**: "아래는 일정 기간 관찰 후 추천 관리가 종료된 기록입니다."
- **배지**: "관찰 종료"
- **요약**: "추천 관리 기간이 종료되었습니다."
- **보조 설명**: "성과와 무관하게 추천 관찰이 마무리되었습니다."
- **메타 정보**: "추천일 YYYY.MM.DD · 관찰 N거래일" (필수)
- **수익률**: 표시 가능하나 강조 금지 (opacity-50, text-gray-400)
- **CTA**: 없음

### 변경 파일
- `frontend/components/v3/ActiveRecommendationCard.js` (신규)
- `frontend/components/v3/WeakRecommendationCard.js` (신규)
- `frontend/components/v3/BrokenRecommendationCard.js` (신규)
- `frontend/components/v3/ArchivedCardV3.js` (수정: 배지 "관찰 종료")
- `frontend/pages/v3/scanner-v3.js` (수정: 상태별 컴포넌트 사용)
- `frontend/utils/v3StatusMapping.js` (수정: ARCHIVED header "관찰 종료")

### 검증 결과
- ✅ ACTIVE 카드에 수익률이 다시 보임 (보조 정보로만)
- ✅ 수익률은 상태/날짜보다 시각적 우선순위가 낮음
- ✅ ACTIVE 카드 문구에 행동 유도 없음
- ✅ ARCHIVED 섹션이 화면에 존재함
- ✅ 섹션 상단 설명 문구가 있음
- ✅ ARCHIVED 카드에 CTA/행동 유도 없음
- ✅ ARCHIVED 카드가 실패처럼 보이지 않음
- ✅ Active/Archived 카드가 물리적으로 분리된 컴포넌트
- ✅ ARCHIVED 작업이 ACTIVE UI에 영향을 주지 않음

---

## 작업 2: daily_digest 서버 집계 + 상태 전이 시점 기록

### 목표
메인 UX 상단에 노출될 "오늘의 변화(NEW 요약 카드)"를 클라이언트 계산 없이, 서버에서 일관되게 생성

### 구현 내용

#### 2.1 상태 전이 시점 기록 (`status_changed_at`)
- **마이그레이션**: `backend/migrations/20260101_add_status_changed_at_to_recommendations.sql`
  - `status_changed_at TIMESTAMPTZ` 컬럼 추가
  - 기존 레코드 초기화: `created_at`을 기본값으로 사용
  - 인덱스 추가: 일일 집계 쿼리 성능 향상

- **상태 전이 로직 수정**:
  - `transition_recommendation_status_transaction`: 상태 변경 시 `status_changed_at = NOW()` 갱신
  - `create_recommendation_transaction`: 신규 추천 생성 시 `status_changed_at = NOW()` 설정
  - REPLACED 전이 시에도 `status_changed_at` 갱신

#### 2.2 daily_digest 서버 집계 로직
- **새 파일**: `backend/services/daily_digest_service.py`
  - `calculate_daily_digest()` 함수 구현
  - KST 기준 집계
  - 윈도우 구분: `PRE_1535`, `POST_1535`, `HOLIDAY`
  - 집계 항목:
    - 신규 추천 수: `anchor_date = todayKST`, `status IN ('ACTIVE','WEAK_WARNING')`
    - 신규 BROKEN 수: `status = 'BROKEN'`, `status_changed_at >= todayKST 00:00`
    - 신규 ARCHIVED 수: `status = 'ARCHIVED'`, `status_changed_at >= todayKST 00:00`

#### 2.3 메인 API 응답에 daily_digest 포함
- **수정 파일**: `backend/main.py`
  - `/api/v3/recommendations/active` 엔드포인트에 `daily_digest` 추가
  - 응답 구조:
    ```json
    {
      "ok": true,
      "data": {
        "items": [...],
        "count": 0
      },
      "daily_digest": {
        "date_kst": "2026-01-02",
        "as_of": "2026-01-02T12:50:08+09:00",
        "window": "PRE_1535",
        "new_recommendations": 0,
        "new_broken": 0,
        "new_archived": 0,
        "has_changes": false
      }
    }
    ```

### 변경 파일
- `backend/migrations/20260101_add_status_changed_at_to_recommendations.sql` (신규)
- `backend/services/recommendation_service_v2.py` (수정: status_changed_at 업데이트)
- `backend/services/daily_digest_service.py` (신규)
- `backend/main.py` (수정: daily_digest 포함)
- `backend/scripts/verify_daily_digest.sql` (신규)
- `backend/scripts/run_status_changed_at_migration.py` (신규)

### 검증 결과
- ✅ `status_changed_at` 컬럼 추가 완료 (1081개 레코드 초기화)
- ✅ NOT NULL 제약 설정 완료
- ✅ 기본값 `NOW()` 설정 완료
- ✅ 인덱스 2개 생성 완료
- ✅ API 응답에 `daily_digest` 포함 확인
- ✅ `daily_digest` 구조 검증 완료

---

## 작업 3: ARCHIVED 전환 스냅샷 기록

### 목표
ARCHIVED 전환 시점의 상태(손익/사유/시점)를 반드시 스냅샷으로 저장하여 이후 UX의 기준으로 사용

### 구현 내용

#### 3.1 recommendations 테이블 확장
- **마이그레이션**: `backend/migrations/20260102_add_archived_snapshot_columns.sql`
  - `archive_at TIMESTAMPTZ` - ARCHIVED 전환 시점
  - `archive_reason VARCHAR(32)` - ARCHIVED 사유 (TTL_EXPIRED, NO_MOMENTUM, MANUAL_ARCHIVE)
  - `archive_return_pct NUMERIC(6,2)` - ARCHIVED 전환 시점의 수익률 (%)
  - `archive_price NUMERIC` - ARCHIVED 전환 시점 가격
  - `archive_phase VARCHAR(16)` - 전환 시 국면 (PROFIT, LOSS, FLAT)
  - 인덱스 추가: `idx_recommendations_archive_reason`, `idx_recommendations_archive_at`

#### 3.2 ARCHIVED 전환 로직 수정
- **수정 파일**: `backend/services/recommendation_service_v2.py`
  - `transition_recommendation_status_transaction` 함수에 스냅샷 저장 로직 추가
  - ARCHIVED 전환 시:
    - `archive_at = NOW()`
    - `archive_reason` 결정 (TTL_EXPIRED, NO_MOMENTUM, MANUAL_ARCHIVE)
    - `archive_return_pct` 계산
    - `archive_price` 저장
    - `archive_phase` 결정 (PROFIT/LOSS/FLAT)

- **수정 파일**: `backend/services/state_transition_service.py`
  - `evaluate_active_recommendations` 함수에서 ARCHIVED 전환 시 `current_price`와 `anchor_close`를 metadata에 포함

- **수정 파일**: `backend/scripts/batch_archive_old_recommendations.py`
  - 배치 스크립트에서도 스냅샷 정보 포함

#### 3.3 기존 ARCHIVED 데이터 보정
- **새 파일**: `backend/scripts/migrate_existing_archived_snapshots.py`
  - 기존 ARCHIVED 레코드의 스냅샷 보정
  - `archive_at`: `status_changed_at` > `archived_at` > `updated_at` 우선순위
  - `archive_reason`: TTL 기준으로 추정 (20일 이상 → TTL_EXPIRED, 그 외 → NO_MOMENTUM)
  - `archive_price`/`archive_return_pct`: 과거 가격 데이터로 계산 시도

### 변경 파일
- `backend/migrations/20260102_add_archived_snapshot_columns.sql` (신규)
- `backend/services/recommendation_service_v2.py` (수정: 스냅샷 저장 로직)
- `backend/services/state_transition_service.py` (수정: 스냅샷 정보 포함)
- `backend/scripts/batch_archive_old_recommendations.py` (수정: 스냅샷 정보 포함)
- `backend/scripts/migrate_existing_archived_snapshots.py` (신규)
- `backend/scripts/verify_archived_snapshots.sql` (신규)
- `backend/scripts/run_archived_snapshot_migration.py` (신규)

### 검증 SQL
- `backend/scripts/verify_archived_snapshots.sql`:
  - ARCHIVED 스냅샷 누락 여부 확인
  - ARCHIVED 사유 분포
  - ARCHIVED 수익률 분포
  - ARCHIVED phase 분포
  - 컬럼 존재 확인
  - 스냅샷 완전성 확인

---

## 검증 결과

### 작업 1: 리그레션 복구 + ARCHIVED UX
- ✅ ACTIVE 카드에 수익률 표시 복구 (보조 정보로만)
- ✅ 카드 컴포넌트 물리적 분리 완료
- ✅ ARCHIVED UX 완성 (섹션, 배지, 문구, 메타 정보)

### 작업 2: daily_digest + status_changed_at
- ✅ `status_changed_at` 컬럼 추가 및 초기화 완료 (1081개 레코드)
- ✅ 상태 전이 로직에 `status_changed_at` 업데이트 추가
- ✅ `daily_digest` 계산 함수 구현 완료
- ✅ API 응답에 `daily_digest` 포함 확인
- ✅ 테스트 결과:
  ```json
  {
    "date_kst": "2026-01-02",
    "as_of": "2026-01-02T12:50:08+09:00",
    "window": "PRE_1535",
    "new_recommendations": 0,
    "new_broken": 0,
    "new_archived": 0,
    "has_changes": false
  }
  ```

### 작업 3: ARCHIVED 스냅샷
- ✅ ARCHIVED 스냅샷 컬럼 추가 마이그레이션 준비 완료
- ✅ ARCHIVED 전환 로직에 스냅샷 저장 추가
- ✅ 기존 ARCHIVED 데이터 보정 스크립트 준비 완료
- ⚠️ 마이그레이션 실행 필요 (다음 단계 참조)

---

## 변경 파일 목록

### 프론트엔드
1. `frontend/components/v3/ActiveRecommendationCard.js` (신규)
2. `frontend/components/v3/WeakRecommendationCard.js` (신규)
3. `frontend/components/v3/BrokenRecommendationCard.js` (신규)
4. `frontend/components/v3/ArchivedCardV3.js` (수정)
5. `frontend/pages/v3/scanner-v3.js` (수정)
6. `frontend/utils/v3StatusMapping.js` (수정)

### 백엔드 - 마이그레이션
7. `backend/migrations/20260101_add_status_changed_at_to_recommendations.sql` (신규)
8. `backend/migrations/20260102_add_archived_snapshot_columns.sql` (신규)

### 백엔드 - 서비스
9. `backend/services/recommendation_service_v2.py` (수정)
10. `backend/services/state_transition_service.py` (수정)
11. `backend/services/daily_digest_service.py` (신규)
12. `backend/main.py` (수정)

### 백엔드 - 스크립트
13. `backend/scripts/run_status_changed_at_migration.py` (신규)
14. `backend/scripts/verify_daily_digest.sql` (신규)
15. `backend/scripts/migrate_existing_archived_snapshots.py` (신규)
16. `backend/scripts/verify_archived_snapshots.sql` (신규)
17. `backend/scripts/run_archived_snapshot_migration.py` (신규)
18. `backend/scripts/batch_archive_old_recommendations.py` (수정)

---

## 다음 단계

### 1. ARCHIVED 스냅샷 마이그레이션 실행
```bash
cd backend
python scripts/run_archived_snapshot_migration.py
```

### 2. 기존 ARCHIVED 데이터 보정 (dry-run)
```bash
python scripts/migrate_existing_archived_snapshots.py
```

### 3. 기존 ARCHIVED 데이터 보정 (실행)
```bash
python scripts/migrate_existing_archived_snapshots.py --execute
```

### 4. 검증 SQL 실행
```bash
psql -d your_database -f backend/scripts/verify_archived_snapshots.sql
```

### 5. 백엔드 재시작 (ARCHIVED 스냅샷 기능 활성화)
```bash
cd /Users/rex/workspace/showmethestock
pkill -f "uvicorn.*main:app"
cd backend && source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8010 > /tmp/backend.log 2>&1 &
```

---

## 주의사항

1. **ARCHIVED 스냅샷은 불변**: 전환 시점 이후 가격 변동과 무관하게 유지
2. **UX는 스냅샷만 사용**: ARCHIVED 카드에서 `archive_return_pct`만 참조, 현재 가격 재계산 금지
3. **daily_digest는 서버 기준**: 클라이언트에서 계산하지 않고 서버 응답만 사용
4. **KST 기준**: 모든 시간 계산은 KST(Asia/Seoul) 기준으로 수행

---

## 완료 기준

- ✅ ACTIVE/WEAK 카드에서 수익률 표시 복구
- ✅ 카드 컴포넌트 물리적 분리 완료
- ✅ ARCHIVED 전용 UX 완성
- ✅ `status_changed_at` 컬럼 추가 및 초기화 완료
- ✅ `daily_digest` 서버 집계 구현 완료
- ✅ API 응답에 `daily_digest` 포함 확인
- ✅ ARCHIVED 스냅샷 컬럼 추가 마이그레이션 준비 완료
- ✅ ARCHIVED 전환 로직에 스냅샷 저장 추가
- ✅ 기존 ARCHIVED 데이터 보정 스크립트 준비 완료
- ⚠️ ARCHIVED 스냅샷 마이그레이션 실행 필요 (다음 단계)

---

**작업 완료일**: 2026-01-02  
**작업자**: AI Assistant (Cursor)

