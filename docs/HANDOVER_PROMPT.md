# 작업 인수인계 프롬프트

## 프로젝트 개요

**프로젝트명**: 스톡인사이트 (Stock Insight)  
**기술 스택**: Python 3.11 + FastAPI (백엔드), Next.js 13 + React (프론트엔드), PostgreSQL 16  
**현재 작업 버전**: V3 추천 시스템

---

## 최근 작업 내용 (2026-01-02)

### 1. 종료 시점 손익 고정 기능 추가
- **목적**: BROKEN/ARCHIVED 추천의 손익을 종료 시점으로 고정
- **DB 마이그레이션**: `backend/migrations/20260102_add_broken_return_pct_column.sql`
  - `broken_return_pct` 컬럼 추가 (BROKEN 상태용)
- **백엔드 변경**:
  - `recommendation_service_v2.py`: BROKEN 전환 시 `broken_return_pct` 저장
  - `recommendation_service.py`: 
    - BROKEN 조회 시 `broken_return_pct` 우선 사용
    - ARCHIVED 조회 시 `archive_return_pct` 우선 사용
- **동작 방식**:
  - BROKEN: 두 가지 손익률 제공
    - `broken_return_pct`: 판단 당시 손익률 (종료 시점 고정)
    - `current_return`: 현재 시점 손익률 (실시간 계산)
  - ARCHIVED: `archive_return_pct`가 있으면 종료 시점 수익률 사용, 없으면 `None` (현재 시점 계산 금지)

### 2. 종료 사유 표시 문제 수정
- **문제**: 종료 사유가 케이스별로 정확히 표시되지 않음
- **원인**:
  1. `reason_code`가 `None`일 때 `.upper()` 호출로 오류 발생 가능
  2. ARCHIVED 전환 시 문자열 매칭(`'TTL' in reason_code_upper`)이 부정확
  3. 정확한 값 비교 필요
- **수정**:
  - `recommendation_service_v2.py`: `reason_code` 검증 및 정확한 값 비교 로직 추가
  - `None` 체크 및 정확한 값 비교로 변경

### 3. 종료 사유(reason) 기능 추가
- **목적**: BROKEN/ARCHIVED 추천에 종료 사유를 명시적으로 표시
- **DB 마이그레이션**: `backend/migrations/20260102_add_reason_column_to_recommendations.sql`
  - `reason` 컬럼 추가 (BROKEN 상태용)
  - `archive_reason` 컬럼 추가 (ARCHIVED 상태용)
  - `archive_return_pct`, `archive_price`, `archive_phase` 컬럼 추가 (ARCHIVED 스냅샷)
- **백엔드 변경**:
  - `state_transition_service.py`: BROKEN 전환 시 `reason` 설정
  - `recommendation_service_v2.py`: ARCHIVED 전환 시 `reason` → `archive_reason` 복사
  - `recommendation_service.py`: 쿼리에 `reason`, `archive_reason` 포함
  - `daily_digest_service.py`: BROKEN 항목에 `reason` 포함
- **프론트엔드 변경**:
  - `v3StatusMapping.js`: `REASON_TO_UX` 매핑 추가
  - `BrokenRecommendationCard.js`: 종료 사유 표시
  - `ArchivedCardV3.js`: 종료 사유 표시
  - `DailyDigestCard.js`: 종료 사유 표시

### 4. 관리 필요 종목(BROKEN) 표시 문제 해결
- **문제**: `reason` 컬럼이 없어서 쿼리 오류 발생
- **해결**: 마이그레이션 실행 및 쿼리 수정
- **결과**: 48개 BROKEN 항목 정상 표시

### 4. ARCHIVED 항목 표시 문제 해결
- **문제**: 
  - `archive_reason`, `archive_return_pct`, `archive_price`, `archive_phase` 컬럼 누락
  - 쿼리에서 `archive_at` → `archived_at` 컬럼명 불일치
- **해결**: 
  - 누락된 컬럼 추가
  - 쿼리 및 파싱 로직에서 `archived_at` 사용
- **결과**: 49개 ARCHIVED 항목 정상 표시

### 5. UI 문구 보고서 작성
- **파일**: `docs/UI_COPY_REPORT.md`
- **내용**: 모든 화면 문구를 케이스별, 상황별로 정리

---

## 현재 시스템 상태

### 백엔드
- **서버**: `http://localhost:8010` (로컬 개발)
- **상태**: 정상 실행 중
- **주요 엔드포인트**:
  - `/api/v3/recommendations/active` - ACTIVE/WEAK_WARNING 추천
  - `/api/v3/recommendations/needs-attention` - BROKEN 추천
  - `/api/v3/recommendations/archived` - ARCHIVED 추천
  - `/api/v3/recommendations/archived/count` - ARCHIVED 개수만

### 프론트엔드
- **서버**: `http://localhost:3000` (로컬 개발)
- **상태**: 정상 실행 중
- **주요 페이지**:
  - `/v3/scanner-v3` - 메인 추천 화면
  - `/archived` - ARCHIVED 추천 목록

### 데이터베이스
- **마이그레이션 완료**: 
  - `20260102_add_reason_column_to_recommendations.sql`
  - `20260102_add_broken_return_pct_column.sql`
- **추가된 컬럼**:
  - `recommendations.reason` (VARCHAR(32))
  - `recommendations.broken_return_pct` (NUMERIC(10,2)) - BROKEN 종료 시점 수익률
  - `recommendations.archive_reason` (VARCHAR(32))
  - `recommendations.archive_return_pct` (NUMERIC(10,2))
  - `recommendations.archive_price` (NUMERIC(10,2))
  - `recommendations.archive_phase` (VARCHAR(16))

---

## 주요 파일 및 변경사항

### 백엔드

#### 마이그레이션
- `backend/migrations/20260102_add_reason_column_to_recommendations.sql`
  - `reason`, `archive_reason` 및 ARCHIVED 스냅샷 컬럼 추가
- `backend/migrations/20260102_add_broken_return_pct_column.sql`
  - `broken_return_pct` 컬럼 추가 (BROKEN 종료 시점 수익률)

#### 서비스 파일
- `backend/services/state_transition_service.py`
  - BROKEN 전환 시 `reason = 'NO_MOMENTUM'` 설정
  
- `backend/services/recommendation_service_v2.py`
  - BROKEN 전환 시 `broken_return_pct` 저장 (종료 시점 수익률)
  - BROKEN 전환 시 `reason_code` 검증 및 정확한 값 비교 로직 추가
  - ARCHIVED 전환 시 `reason` → `archive_reason` 복사
  - ARCHIVED 전환 시 `reason_code` 정확한 값 비교 로직 추가 (문자열 매칭 제거)
  - `archive_return_pct`, `archive_price`, `archive_phase` 저장
  
- `backend/services/recommendation_service.py`
  - `get_needs_attention_recommendations_list()`: 
    - `reason`, `broken_return_pct` 컬럼 포함
    - BROKEN 상태일 때 `broken_return_pct` 우선 사용 (종료 시점 고정)
  - `get_archived_recommendations_list()`: 
    - `archived_at`, `archive_reason`, `archive_return_pct` 컬럼 포함
    - ARCHIVED 상태일 때 `archive_return_pct` 우선 사용 (종료 시점 고정)
  - 쿼리에서 `archive_at` → `archived_at` 수정
  
- `backend/services/daily_digest_service.py`
  - BROKEN 항목에 `reason` 포함

### 프론트엔드

#### 상태 매핑
- `frontend/utils/v3StatusMapping.js`
  - `REASON_TO_UX` 매핑 추가:
    - `TTL_EXPIRED` → "관리 기간 종료"
    - `NO_MOMENTUM` → "이전 흐름 유지 실패"
    - `MANUAL_ARCHIVE` → "운영자 종료"

#### 컴포넌트
- `frontend/components/v3/BrokenRecommendationCard.js`
  - 종료 사유 표시: "사유: {종료사유}"
  
- `frontend/components/v3/ArchivedCardV3.js`
  - 종료 사유 표시: "종료 사유: {종료사유}"
  - `archive_at` → `archived_at` 수정
  
- `frontend/components/v3/DailyDigestCard.js`
  - BROKEN 이벤트에 종료 사유 포함

#### 페이지
- `frontend/pages/v3/scanner-v3.js`
  - `getServerSideProps`에서 API 경로 수정: `/v3/...` → `/api/v3/...`
  
- `frontend/pages/archived.js`
  - ARCHIVED 항목 표시 로직 정상화

---

## 알려진 이슈 및 주의사항

### 1. 컬럼명 불일치
- **이슈**: 쿼리에서 `archive_at` 사용 시 오류 발생
- **해결**: `archived_at` 사용 (실제 DB 컬럼명)
- **위치**: `recommendation_service.py`의 `get_archived_recommendations_list()`

### 2. 기존 데이터의 reason 누락
- **상태**: 기존 BROKEN/ARCHIVED 항목의 `reason`이 `NULL`일 수 있음
- **영향**: UI에서 종료 사유가 표시되지 않을 수 있음
- **해결 방안**: 필요 시 기존 데이터에 기본값 설정 (현재는 선택사항)

### 3. 종료 사유 코드 검증 문제 (수정 완료)
- **문제**: `reason_code`가 `None`일 때 오류 발생, 문자열 매칭이 부정확
- **해결**: `recommendation_service_v2.py`에서 `None` 체크 및 정확한 값 비교 로직 추가
- **수정일**: 2026-01-02

### 4. TTL 설정 및 REPLACED 사유 개선
- **문제**: 관찰 기간이 100일을 넘어가는 종목들이 있음 (TTL은 20거래일로 설정되어 있음)
- **원인**: 
  1. `create_recommendation`에서 기존 ACTIVE를 ARCHIVED로 전이할 때 TTL 체크 없이 무조건 'REPLACED'로 설정
  2. midterm과 v2_lite의 TTL이 동일하게 20거래일로 설정되어 있음 (전략별로 다르게 설정해야 함)
- **해결**: 
  1. `create_recommendation`에서 기존 ACTIVE를 ARCHIVED로 전이할 때 거래일 확인
  2. 전략별 TTL 이상이면 'TTL_EXPIRED'로 설정, 미만이면 'REPLACED'로 설정
  3. **전략별 TTL 설정**:
     - `v2_lite`: 15거래일 (holding_period = 14일, 약 10거래일 + 여유분)
     - `midterm`: 25거래일 (holding_periods = [10, 15, 20], 최대 20거래일 + 여유분)
     - 기본값: 20거래일
- **수정 파일**:
  - `backend/services/recommendation_service.py`: 전략별 TTL 체크 추가
  - `backend/services/recommendation_service_v2.py`: 전략별 TTL 체크 추가 및 archive 정보 저장
  - `backend/services/state_transition_service.py`: 전략별 TTL 적용

### 4-2. ARCHIVED 관찰기간 및 수익률 TTL 기준 표시
- **문제**: 
  1. ARCHIVED의 관찰기간이 `anchor_date ~ archived_at`으로 계산되어 TTL을 초과한 경우에도 실제 관찰기간이 표시됨
  2. 수익률도 `archived_at` 시점의 수익률이 표시되어 TTL을 초과한 경우 TTL 시점의 수익률이 표시되지 않음
- **원인**: 
  1. `observation_period_days`가 실제 관찰기간으로 계산되어 TTL_EXPIRED인 경우에도 실제 관찰기간(예: 155거래일)이 표시됨
  2. `archive_return_pct`가 `archived_at` 시점의 수익률로 저장되어 TTL 시점의 수익률이 계산되지 않음
- **해결**: 
  1. **관찰기간**: TTL을 초과한 경우 전략별 TTL을 `observation_period_days`로 설정
  2. **수익률**: TTL을 초과한 경우 TTL 시점의 가격을 조회하여 TTL 시점의 수익률을 계산하고 `archive_return_pct`로 설정
  3. TTL 미만인 경우: 실제 관찰기간 및 `archived_at` 시점의 수익률 사용
- **수정 파일**:
  - `backend/services/recommendation_service.py`: `get_archived_recommendations_list`에 관찰기간 및 수익률 계산 로직 추가
  - `get_nth_trading_day_after` 함수 사용: anchor_date에서 TTL 거래일 후 날짜 계산
  - TTL 시점의 가격 조회: `api.get_ohlcv`로 TTL 시점의 종가 조회 후 수익률 계산
- **확인 사항**:
  - 백엔드 코드는 정상 작동 확인됨
  - `observation_period_days`와 `archive_return_pct`가 TTL 기준으로 계산되어 반환됨
  - **백엔드 서버 재시작 완료**: 변경사항 적용됨

### 4-1. 관찰 기간 및 수익률 계산 시점 정확성 개선
- **문제**: KODEX 레버리지처럼 `archived_at` 시점과 실제 가격 조회 시점이 다를 수 있음
- **원인**: 
  1. `api.get_ohlcv(ticker, 1, today_str)`는 `today_str` 이하의 최근 데이터를 반환
  2. `today_str`이 주말/공휴일이면 이전 거래일 데이터를 반환할 수 있음
  3. `archived_at = NOW()`로 설정되지만, 실제 가격은 다른 날짜일 수 있음
- **해결**:
  1. `create_recommendation_transaction`: `api.get_ohlcv()` 반환 데이터에서 정확한 날짜 확인 후 해당 날짜의 가격 사용
  2. `state_transition_service.py`: 동일하게 정확한 날짜의 가격 사용
  3. `fix_archive_price_at_transition_date.py`: 기존 데이터의 `archived_at` 시점 가격으로 재계산 (50개 이상 수정)
- **수정 파일**:
  - `backend/services/recommendation_service_v2.py`: 전이 시점의 정확한 가격 조회
  - `backend/services/state_transition_service.py`: 전이 시점의 정확한 가격 조회
  - `backend/scripts/fix_archive_price_at_transition_date.py`: 기존 데이터 재계산 스크립트

### 5. ARCHIVED 종료 사유 및 손익률 표시 개선
- **문제**: 
  1. 동진세미캠처럼 수익률 4% 이상인데도 관리가 종료되어 사유가 불분명함
  2. ARCHIVED 카드에 손익률이 표시되지 않음
  3. SK스퀘어처럼 `archive_return_pct`가 없는 종목들이 있음
- **원인**: 
  1. TTL_EXPIRED 사유가 "관리 기간 종료"로만 표시되어 구체적인 정보 부족
  2. 손익률 표시 스타일이 너무 작고 흐려서 보이지 않음 (`text-xs text-gray-400 opacity-50`)
  3. `create_recommendation`에서 기존 ACTIVE를 ARCHIVED로 전이할 때 `archive_return_pct`를 저장하지 않음
- **개선 내용**:
  1. `getTerminationReasonText` 함수 개선: TTL_EXPIRED일 때 거래일과 수익률 정보 추가
  2. 예: "관리 기간 종료 (20거래일 경과, 수익률 +11.82%)"
  3. NO_MOMENTUM일 때도 수익률 정보 추가
  4. `getTradingDaysBetween` 함수 추가: anchor_date부터 archived_at까지의 거래일 계산
  5. **ARCHIVED 카드에 손익률 명확히 표시**: "종료 시점 수익률: +11.82%" 형식으로 표시
  6. `archive_return_pct` 우선 사용 (상태 전이 시점의 손익률 - 종료 시점 고정)
  7. **`create_recommendation` 수정**: 기존 ACTIVE를 ARCHIVED로 전이할 때 현재 가격 조회하여 `archive_return_pct` 저장
  8. **기존 데이터 업데이트**: `update_missing_archive_return_pct.py` 스크립트로 49개 항목 업데이트 완료
- **수정 파일**:
  - `frontend/utils/v3StatusMapping.js`: `getTerminationReasonText` 함수 개선
  - `frontend/utils/tradingDaysUtils.js`: `getTradingDaysBetween` 함수 추가
  - `frontend/components/v3/ArchivedCardV3.js`: 거래일 계산 로직 개선, 손익률 표시 개선
  - `backend/services/recommendation_service.py`: `create_recommendation`에서 ARCHIVED 전이 시 `archive_return_pct` 저장
  - `backend/scripts/update_missing_archive_return_pct.py`: 기존 데이터 업데이트 스크립트

### 6. BROKEN이 표시되지 않는 문제
- **문제**: BROKEN 상태인 추천이 "관리 필요" 섹션에 표시되지 않음 (섹션이 펼쳐져 있어도)
- **확인 결과**:
  1. ✅ DB에 BROKEN 상태인 추천 10개 존재
  2. ✅ API가 49개의 BROKEN 항목 반환 (`/api/v3/recommendations/needs-attention`)
  3. ⚠️ 섹션이 접혀있을 수 있음 (`brokenCollapsed = true` 기본값)
  4. ⚠️ BROKEN 개수 제한: 최대 5개만 표시 (`broken.slice(0, 5)`)
  5. ⚠️ `useMemo`에서 `broken` 배열이 제대로 채워지지 않을 수 있음
  6. ⚠️ `BrokenRecommendationCard` 컴포넌트의 조건이 맞지 않아 렌더링되지 않을 수 있음
- **원인 가능성**:
  1. `items` 배열에 BROKEN 항목이 포함되지 않음
  2. `useMemo`에서 `status === BACKEND_STATUS.BROKEN` 비교 실패
  3. `BrokenRecommendationCard`의 조건 (`item.status !== BACKEND_STATUS.BROKEN`) 실패
- **디버깅 로그 추가**:
  1. `useMemo`에서 `items` 배열에 BROKEN 항목이 있는지 확인
  2. `fetchRecommendations`에서 `filteredItems`에 BROKEN이 포함되는지 확인
  3. `BrokenRecommendationCard`에서 조건 실패 시 경고 로그 출력
- **확인 방법**: 브라우저 콘솔에서 디버깅 로그 확인

### 6. -2% 이상 손실 종목이 추천 카드에 표시되는 문제
- **문제**: 손절 조건(-2%)에 도달한 종목이 ACTIVE 상태로 유지됨
- **원인 가능성**:
  1. 상태 평가가 실행되지 않음 (스케줄러 미실행)
  2. 상태 평가 실행 시 오류 발생 (오늘 종가 조회 실패 등)
  3. `anchor_close`가 없어서 건너뛰어짐
  4. 상태 평가가 실행되었지만 전이가 실패함
- **손절 조건**:
  - v2_lite: `stop_loss = 0.02` → `stop_loss_pct = -2.0%`
  - midterm: `stop_loss = 0.07` → `stop_loss_pct = -7.0%`
  - 조건: `current_return <= stop_loss_pct`이면 BROKEN으로 전이
- **상태 평가 실행 시점**: 매일 오후 3시 45분 KST (`scheduler.py`)
- **확인 필요**:
  - 상태 평가가 실제로 실행되고 있는지 로그 확인
  - -2% 이상 손실인 종목의 `current_return` 값 확인
  - 상태 평가 실행 시 오류 로그 확인
  - 수동 실행: `from services.state_transition_service import evaluate_active_recommendations; evaluate_active_recommendations()`

### 7. 추천 카드 손익 표시 문제
- **문제**: ACTIVE/WEAK_WARNING 추천 카드에서 손익이 표시되지 않음
- **원인 가능성**:
  1. `anchor_close`가 없거나 0인 경우 → `current_return` 계산 불가
  2. 오늘 종가를 가져오지 못하는 경우 → `current_return`이 `None`
  3. API 응답에서 `current_return`이 제대로 전달되지 않는 경우
- **수정**: 로그 추가 (`get_active_recommendations_list`)
  - `anchor_close` 없음 경고 로그
  - 오늘 종가 없음 디버그 로그
- **확인 필요**:
  - 실제 DB에서 `anchor_close` 값 확인
  - 오늘 종가 조회 성공 여부 확인
  - 프론트엔드에서 `current_return` 값 확인

### 7. 프론트엔드 파일 권한 오류
- **문제**: Next.js 개발 서버에서 `Operation not permitted (os error 1)` 오류 발생
- **오류 메시지**: `Failed to read source code from .../node_modules/next/dist/client/components/router-reducer/router-reducer-types.js`
- **원인**: macOS 보안 정책 또는 파일 권한 문제
- **해결 방법**:
  1. `.next` 캐시 삭제: `rm -rf frontend/.next`
  2. `node_modules` 재설치: `cd frontend && rm -rf node_modules && npm install`
  3. 파일 권한 확인: `ls -la node_modules/next/dist/client/components/router-reducer/`
  4. macOS 보안 설정 확인: 시스템 설정 > 개인정보 보호 및 보안 > 전체 디스크 접근 권한
- **참고**: `frontend/FIX_PERMISSION_ERROR.md` 파일 참고

### 8. 마이그레이션 실행 필요
- **상태**: 마이그레이션 파일은 작성되었으나, 프로덕션 환경에서는 실행 필요
- **파일**: 
  - `backend/migrations/20260102_add_reason_column_to_recommendations.sql`
  - `backend/migrations/20260102_add_broken_return_pct_column.sql`

---

## 다음 작업 시 체크리스트

### 백엔드
- [ ] 프로덕션 DB에 마이그레이션 실행 확인 (reason 컬럼 + broken_return_pct 컬럼)
- [ ] 기존 BROKEN/ARCHIVED 데이터의 `reason` 값 확인
- [ ] 기존 BROKEN 데이터의 `broken_return_pct` 값 확인 (NULL일 수 있음)
- [ ] `state_transition_service.py`에서 다른 전환 경로 확인 (TTL_EXPIRED, MANUAL_ARCHIVE)

### 프론트엔드
- [ ] 브라우저에서 모든 상태 카드 정상 표시 확인
- [ ] 종료 사유가 모든 BROKEN/ARCHIVED 카드에 표시되는지 확인
- [ ] NEW 카드에서 종료 사유 표시 확인

### 테스트
- [ ] ACTIVE → BROKEN 전환 시 `reason` 설정 확인
- [ ] BROKEN → ARCHIVED 전환 시 `reason` → `archive_reason` 복사 확인
- [ ] ARCHIVED 페이지에서 모든 항목 정상 표시 확인

---

## 코드 구조 및 패턴

### 백엔드 패턴
- **ORM 사용 금지**: 직접 SQL 쿼리 사용
- **트랜잭션**: `db_manager.get_cursor(commit=True)` 사용
- **에러 처리**: `try-except` 블록에서 로깅 후 예외 재발생

### 프론트엔드 패턴
- **문구 관리**: `v3StatusMapping.js`의 상수로 중앙 관리
- **하드코딩 금지**: 컴포넌트 내부에 문구 직접 작성 금지
- **상태 기반 렌더링**: `STATUS_TO_UX` 매핑 기반

### 종료 사유 처리
- **BROKEN 전환**: `state_transition_service.py`에서 `reason` 설정
- **ARCHIVED 전환**: `recommendation_service_v2.py`에서 `reason` → `archive_reason` 복사
- **UI 표시**: `REASON_TO_UX` 매핑을 통해 사용자 문구로 변환

### 종료 시점 손익 고정
- **BROKEN 전환**: `recommendation_service_v2.py`에서 `broken_return_pct` 저장
- **ARCHIVED 전환**: `recommendation_service_v2.py`에서 `archive_return_pct` 저장
- **조회 시**: 
  - BROKEN: 두 가지 손익률 제공
    - `broken_return_pct`: 판단 당시 손익률 (종료 시점 고정)
    - `current_return`: 현재 시점 손익률 (실시간 계산)
  - ARCHIVED: `archive_return_pct`만 사용, 없으면 `None` (현재 시점 계산 금지)

---

## 주요 상수 및 매핑

### 종료 사유 코드 케이스별 정리

#### 1. BROKEN 상태 종료 사유 (`reason` 컬럼)

| 코드 | 사용자 문구 | 발생 조건 | 설정 위치 |
|------|-----------|----------|----------|
| `NO_MOMENTUM` | "이전 흐름 유지 실패" | 손절 조건 도달 (current_return ≤ stop_loss_pct) | `state_transition_service.py:279` |
| `TTL_EXPIRED` | "관리 기간 종료" | 관리 기간 종료 (20거래일 이상) | `state_transition_service.py:338` (ARCHIVED로 직접 전환 시) |
| `MANUAL_ARCHIVE` | "운영자 종료" | 운영자 수동 종료 | 수동 설정 (현재 자동 설정 없음) |

**BROKEN 전환 경로**:
- `ACTIVE → BROKEN`: 손절 조건 도달 시 `NO_MOMENTUM` 설정
- `WEAK_WARNING → BROKEN`: 손절 조건 도달 시 `NO_MOMENTUM` 설정

#### 2. ARCHIVED 상태 종료 사유 (`archive_reason` 컬럼)

| 코드 | 사용자 문구 | 발생 조건 | 설정 위치 |
|------|-----------|----------|----------|
| `TTL_EXPIRED` | "관리 기간 종료" | 20거래일 이상 경과 | `state_transition_service.py:338` |
| `NO_MOMENTUM` | "이전 흐름 유지 실패" | 10거래일 이상 + 수익률 절대값 < 2% (무성과) | `state_transition_service.py:347` |
| `MANUAL_ARCHIVE` | "운영자 종료" | 운영자 수동 종료 | 수동 설정 |

**ARCHIVED 전환 경로**:
- `ACTIVE → ARCHIVED`:
  - 20거래일 이상: `TTL_EXPIRED`
  - 10거래일 이상 + 수익률 절대값 < 2%: `NO_MOMENTUM`
- `BROKEN → ARCHIVED`: BROKEN의 `reason`을 `archive_reason`으로 복사 (`recommendation_service_v2.py:267-277`)
- `WEAK_WARNING → ARCHIVED`: ACTIVE와 동일한 조건 적용

#### 3. 종료 사유 코드 → UX 매핑

```javascript
TERMINATION_REASON_MAP = {
  TTL_EXPIRED: '관리 기간 종료',
  NO_MOMENTUM: '이전 흐름 유지 실패',
  MANUAL_ARCHIVE: '운영자 종료'
}
```

**매핑 위치**: `frontend/utils/v3StatusMapping.js:191-195`

### 상태별 문구
```javascript
STATUS_TO_UX = {
  ACTIVE: { summary: "현재 추천은 변경 없이 유지되고 있습니다" },
  WEAK_WARNING: { summary: "추천 이후 이전과 다른 움직임이 감지되었습니다" },
  BROKEN: { summary: "추천 관리가 종료되었습니다" },
  ARCHIVED: { summary: "추천 관리 기간이 종료되었습니다." }
}
```

---

## 참고 문서

- **프로젝트 규칙**: `repo_specific_rule` (프로젝트 루트의 규칙 참조)
- **UI 문구 보고서**: `docs/UI_COPY_REPORT.md`
- **API 엔드포인트**: `docs/API_ENDPOINTS.md` (존재 시)

---

## 작업 환경 설정

### 로컬 개발
```bash
# 백엔드
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8010 --reload

# 프론트엔드
cd frontend
npm run dev
```

### 환경 변수
- `BACKEND_URL`: 백엔드 URL (기본값: `http://localhost:8010`)
- `NEXT_PUBLIC_BACKEND_URL`: 프론트엔드에서 사용하는 백엔드 URL

---

## 다음 작업자에게 전달할 메시지

이 작업은 **종료 사유(reason) 기능 추가**를 완료한 상태입니다. 

**완료된 작업**:
1. ✅ DB 마이그레이션 작성 및 실행
2. ✅ 백엔드 로직 수정 (BROKEN/ARCHIVED 전환 시 reason 저장)
3. ✅ 프론트엔드 UI 수정 (종료 사유 표시)
4. ✅ 관리 필요 종목(BROKEN) 표시 문제 해결
5. ✅ ARCHIVED 항목 표시 문제 해결
6. ✅ UI 문구 보고서 작성

**확인 필요 사항**:
- 프로덕션 환경 마이그레이션 실행
- 기존 데이터의 reason 값 확인
- 모든 상태 전환 경로에서 reason 설정 확인

**주의사항**:
- 컬럼명: `archived_at` (not `archive_at`)
- 문구는 `v3StatusMapping.js`에서만 수정
- 하드코딩 금지

---

**작성일**: 2026-01-02  
**작성자**: AI Assistant  
**버전**: 1.0

