# V3 추천 시스템 구현 로직 문서

**작성일**: 2026-01-02  
**버전**: V3  
**목적**: 백엔드와 프론트엔드의 V3 구현 로직을 구분하여 정리

---

## 목차

1. [개요](#개요)
2. [백엔드 구현 로직](#백엔드-구현-로직)
3. [프론트엔드 구현 로직](#프론트엔드-구현-로직)
4. [데이터 흐름](#데이터-흐름)
5. [주요 파일 구조](#주요-파일-구조)

---

## 개요

V3 추천 시스템은 **스캔(로그) vs 추천(이벤트)**로 분리된 아키텍처를 기반으로 합니다.

### 핵심 원칙

1. **스캔 로그와 추천 이벤트 분리**: `scan_results` (로그) vs `recommendations` (이벤트)
2. **동일 ticker ACTIVE 1개만**: DB 제약 + 코드 레벨 보장
3. **anchor_close 고정 저장**: 생성 시점에 1회 확정, 재계산 금지
4. **상태 단방향 전이**: ACTIVE → WEAK_WARNING → BROKEN → ARCHIVED
5. **BROKEN → ACTIVE 금지**: 회복은 신규 추천 이벤트로만 처리

### 상태 정의

- **ACTIVE**: 추천 유효 (정상 추천)
- **WEAK_WARNING**: 흐름 약화 (경고 상태, ACTIVE로 복귀 가능)
- **BROKEN**: 관리 필요 (추천 가정 깨짐, 복귀 불가)
- **ARCHIVED**: 관찰 종료 (TTL 만료, 수동 종료 등)
- **REPLACED**: 대체됨 (내부 상태, UX 노출 금지)

---

## 백엔드 구현 로직

### 1. 추천 생성 로직

#### 파일: `backend/services/recommendation_service_v2.py`

**함수**: `create_recommendation_transaction()`

**동작 흐름**:

1. **트랜잭션 시작** (`FOR UPDATE`로 동시성 제어)
2. **기존 ACTIVE 확인**
   ```sql
   SELECT recommendation_id, anchor_date, anchor_close, strategy
   FROM recommendations
   WHERE ticker = %s AND status = 'ACTIVE'
   FOR UPDATE
   ```
3. **기존 ACTIVE가 있으면 REPLACED로 전환**
   - 전략별 TTL 계산 (v2_lite: 15거래일, midterm: 25거래일, 기본: 20거래일)
   - TTL 초과 시 `archive_reason = 'TTL_EXPIRED'`, 미만 시 `archive_reason = 'REPLACED'`
   - `archive_return_pct`, `archive_price`, `archive_phase` 저장
   - `archived_at` 타임스탬프 저장
4. **신규 ACTIVE 생성**
   - UUID 생성 (`recommendation_id`)
   - `anchor_date`, `anchor_close` 고정 저장 (재계산 금지)
   - `status = 'ACTIVE'` 초기 상태 설정
   - `strategy` 저장 (midterm 또는 v2_lite)

**주요 특징**:
- 트랜잭션으로 동시성 제어 (동일 ticker 중복 ACTIVE 방지)
- `anchor_close`는 생성 시점에만 저장, 이후 변경 금지
- 기존 ACTIVE는 자동으로 REPLACED로 전환

### 2. 상태 전이 로직

#### 파일: `backend/services/state_transition_service.py`

**함수**: `evaluate_active_recommendations()`

**동작 흐름**:

1. **ACTIVE 추천 조회**
   ```sql
   SELECT recommendation_id, ticker, anchor_date, anchor_close, strategy, status
   FROM recommendations
   WHERE status IN ('ACTIVE', 'WEAK_WARNING')
   AND scanner_version = 'v3'
   ```

2. **각 추천에 대해 상태 평가**:
   - **거래일 계산**: `get_trading_days_since(anchor_date)`
   - **전략별 TTL 확인**:
     - v2_lite: 15거래일
     - midterm: 25거래일
     - 기본: 20거래일
   - **현재 가격 조회**: `api.get_ohlcv(ticker, 10, today_str)`
   - **수익률 계산**: `((current_price - anchor_close) / anchor_close) * 100`

3. **상태 전이 판단**:
   - **TTL 종료** (`trading_days >= ttl_days`):
     - `archive_reason = 'TTL_EXPIRED'`
     - `status = 'ARCHIVED'`
   - **손실 과다** (`current_return < -2%`):
     - `reason = 'NO_MOMENTUM'`
     - `broken_return_pct = current_return`
     - `status = 'BROKEN'`
   - **흐름 약화** (`-2% <= current_return < 0%` 또는 기타 조건):
     - `status = 'WEAK_WARNING'`
   - **정상 유지**:
     - `status = 'ACTIVE'` 유지

4. **상태 전이 실행**:
   - `transition_recommendation_status_transaction()` 호출
   - 트랜잭션으로 안전하게 상태 변경
   - `status_changed_at` 갱신

**주요 특징**:
- 단방향 전이만 허용 (ACTIVE → WEAK_WARNING → BROKEN → ARCHIVED)
- TTL은 전략별로 다르게 적용
- `broken_return_pct`는 BROKEN 전환 시점에 고정 저장

### 3. API 엔드포인트

#### 파일: `backend/main.py`

**엔드포인트 목록**:

1. **`GET /api/v3/recommendations/active`**
   - ACTIVE 및 WEAK_WARNING 추천 조회
   - `recommendation_service.get_active_recommendations_list()` 호출
   - 실시간 수익률 계산 포함

2. **`GET /api/v3/recommendations/needs-attention`**
   - BROKEN 추천 조회
   - `recommendation_service.get_needs_attention_recommendations_list()` 호출
   - `broken_return_pct` (종료 시점) 및 `current_return` (실시간) 제공

3. **`GET /api/v3/recommendations/archived`**
   - ARCHIVED 추천 조회
   - `recommendation_service.get_archived_recommendations_list()` 호출
   - `archive_return_pct` (종료 시점)만 제공 (실시간 계산 금지)
   - TTL 초과 시 TTL 시점의 수익률로 재계산

4. **`GET /api/v3/recommendations/archived/count`**
   - ARCHIVED 개수만 조회 (성능 최적화)

5. **`GET /api/v3/recommendations/{recommendation_id}`**
   - 특정 추천 상세 조회

### 4. 데이터 조회 로직

#### 파일: `backend/services/recommendation_service.py`

**주요 함수**:

1. **`get_active_recommendations_list()`**
   - ACTIVE/WEAK_WARNING 추천 조회
   - 실시간 수익률 계산 (`current_return`)
   - `ticker`별 중복 제거 (최신 1개만)

2. **`get_needs_attention_recommendations_list()`**
   - BROKEN 추천 조회
   - `broken_return_pct` (종료 시점) 우선 사용
   - `current_return` (실시간) 추가 제공

3. **`get_archived_recommendations_list()`**
   - ARCHIVED 추천 조회
   - `archive_return_pct` (종료 시점)만 사용
   - TTL 초과 시 TTL 시점의 수익률로 재계산
   - `observation_period_days` 계산 (TTL 기준 또는 실제 관찰기간)

**특징**:
- ARCHIVED는 실시간 계산 금지 (`archive_return_pct`가 없으면 `None`)
- TTL 초과 항목은 TTL 시점의 수익률로 표시
- 관찰기간도 TTL 기준으로 표시 (TTL 초과 시)

### 5. 종료 사유 처리

**종료 사유 코드**:
- `TTL_EXPIRED`: 관리 기간 종료 (전략별 TTL 초과)
- `NO_MOMENTUM`: 이전 흐름 유지 실패 (손실 과다)
- `MANUAL_ARCHIVE`: 운영자 종료
- `REPLACED`: 새로운 추천으로 대체

**저장 위치**:
- `reason`: BROKEN 상태용
- `archive_reason`: ARCHIVED 상태용

---

## 프론트엔드 구현 로직

### 1. 메인 페이지

#### 파일: `frontend/pages/v3/scanner-v3.js`

**동작 흐름**:

1. **초기 데이터 로드** (SSR)
   - `getServerSideProps()`에서 3개 API 병렬 호출:
     - `/api/v3/recommendations/active`
     - `/api/v3/recommendations/needs-attention`
     - `/api/v3/recommendations/archived/count`

2. **상태별 분류**
   ```javascript
   const activeItems = items.filter(item => 
     item.status === BACKEND_STATUS.ACTIVE || 
     item.status === BACKEND_STATUS.WEAK_WARNING
   );
   
   const brokenItems = items.filter(item => 
     item.status === BACKEND_STATUS.BROKEN
   );
   ```

3. **렌더링 섹션**:
   - **유효한 추천**: ACTIVE + WEAK_WARNING
   - **관리 필요**: BROKEN
   - **종료된 추천 보기**: ARCHIVED (별도 페이지)

4. **자동 펼침/접힘**:
   - ACTIVE 섹션: 6개 이상이면 접힘 상태
   - BROKEN 섹션: 기본 접힘 상태
   - localStorage로 사용자 설정 저장

5. **실시간 갱신**:
   - `fetchRecommendations()` 함수로 주기적 갱신
   - `useEffect`로 마운트 시 자동 갱신

**주요 특징**:
- REPLACED 상태는 필터링하여 표시하지 않음
- ARCHIVED는 개수만 표시하고 별도 페이지로 이동
- 상태별로 다른 카드 컴포넌트 사용

### 2. 상태 매핑

#### 파일: `frontend/utils/v3StatusMapping.js`

**역할**: 백엔드 상태를 UX로 1:1 번역

**매핑 규칙**:

```javascript
export const STATUS_TO_UX = {
  [BACKEND_STATUS.ACTIVE]: {
    header: '추천 유효',
    summary: '현재 추천은 변경 없이 유지되고 있습니다',
    colorScheme: 'green',
    renderInMainSection: true
  },
  [BACKEND_STATUS.WEAK_WARNING]: {
    header: '흐름 약화',
    summary: '추천 이후 이전과 다른 움직임이 감지되었습니다',
    colorScheme: 'yellow',
    renderInMainSection: true
  },
  [BACKEND_STATUS.BROKEN]: {
    header: '관리 필요',
    summary: '추천 관리가 종료되었습니다',
    colorScheme: 'red',
    renderInMainSection: false  // 별도 섹션
  },
  [BACKEND_STATUS.ARCHIVED]: {
    header: '관찰 종료',
    summary: '추천 관리 기간이 종료되었습니다.',
    colorScheme: 'gray',
    renderInMainSection: false
  },
  [BACKEND_STATUS.REPLACED]: {
    // UX 노출 금지
    renderInMainSection: false
  }
};
```

**핵심 원칙**:
- 백엔드 상태를 정확히 번역만 수행
- 판단/해석 금지
- 숫자, 점수, 엔진명 노출 금지

### 3. 카드 컴포넌트

#### ACTIVE 카드: `frontend/components/v3/ActiveRecommendationCard.js`
- ACTIVE 상태 전용 카드
- 초록 계열 색상
- "추천 유효" 헤더

#### WEAK_WARNING 카드: `frontend/components/v3/WeakRecommendationCard.js`
- WEAK_WARNING 상태 전용 카드
- 노랑/주황 계열 색상
- "흐름 약화" 헤더

#### BROKEN 카드: `frontend/components/v3/BrokenRecommendationCard.js`
- BROKEN 상태 전용 카드
- 빨강 계열 색상
- "관리 필요" 헤더
- 종료 사유 표시 (`reason` 필드)

#### ARCHIVED 카드: `frontend/components/v3/ArchivedCardV3.js`
- ARCHIVED 상태 전용 카드
- 회색 계열 색상
- "관찰 종료" 헤더
- 종료 사유 표시 (`archive_reason` 필드)
- 종료 시점 수익률 표시 (`archive_return_pct`)
- 관찰기간 표시 (`observation_period_days`)

### 4. ARCHIVED 페이지

#### 파일: `frontend/pages/archived.js`

**동작 흐름**:

1. **SSR로 초기 데이터 로드**
   - `getServerSideProps()`에서 `/api/v3/recommendations/archived` 호출

2. **ARCHIVED 카드 렌더링**
   - `ArchivedCardV3` 컴포넌트 사용
   - 종료 사유, 수익률, 관찰기간 표시

3. **정렬**
   - `archived_at` 기준 내림차순 (최신순)

**레이아웃**:
- 상단 헤더: "스톡인사이트"
- 정보 배너: "관찰 종료된 추천"
- 하단 네비게이션 포함

### 5. 종료 사유 표시

#### 파일: `frontend/utils/v3StatusMapping.js`

**함수**: `getTerminationReasonText(reasonCode, options)`

**동작**:
- 종료 사유 코드를 사용자 문구로 변환
- `TTL_EXPIRED`: "관리 기간 종료 (N거래일 경과, 수익률 ±X.XX%)"
- `NO_MOMENTUM`: "이전 흐름 유지 실패 (수익률 ±X.XX%)"
- `MANUAL_ARCHIVE`: "운영자 종료"
- `REPLACED`: "새로운 추천으로 대체"

**옵션**:
- `returnPct`: 수익률 표시
- `tradingDays`: 거래일 표시

---

## 데이터 흐름

### 1. 추천 생성 흐름

```
스캔 실행 (scan_service.py)
  ↓
V3 엔진 실행 (scanner_v3/core/engine.py)
  ↓
추천 후보 생성
  ↓
create_recommendation_transaction() 호출
  ↓
기존 ACTIVE 확인 → REPLACED로 전환
  ↓
신규 ACTIVE 생성 (anchor_close 고정 저장)
  ↓
DB 저장 완료
```

### 2. 상태 전이 흐름

```
스케줄러 실행 (매일)
  ↓
evaluate_active_recommendations() 호출
  ↓
ACTIVE/WEAK_WARNING 추천 조회
  ↓
각 추천에 대해:
  - 거래일 계산
  - 현재 가격 조회
  - 수익률 계산
  - 상태 전이 판단
  ↓
상태 전이 실행 (트랜잭션)
  ↓
broken_return_pct 또는 archive_return_pct 저장
```

### 3. 프론트엔드 데이터 로드 흐름

```
페이지 로드 (SSR)
  ↓
getServerSideProps() 실행
  ↓
3개 API 병렬 호출:
  - /api/v3/recommendations/active
  - /api/v3/recommendations/needs-attention
  - /api/v3/recommendations/archived/count
  ↓
상태별 분류
  ↓
카드 컴포넌트 렌더링
  ↓
클라이언트 마운트 후 실시간 갱신
```

---

## 주요 파일 구조

### 백엔드

```
backend/
├── services/
│   ├── recommendation_service_v2.py      # 추천 생성 트랜잭션
│   ├── state_transition_service.py      # 상태 전이 엔진
│   ├── recommendation_service.py        # 추천 조회 서비스
│   └── daily_digest_service.py          # 일일 요약 서비스
├── main.py                               # API 엔드포인트
└── migrations/
    ├── 20260102_add_broken_return_pct_column.sql
    └── 20260102_add_reason_column_to_recommendations.sql
```

### 프론트엔드

```
frontend/
├── pages/
│   ├── v3/
│   │   └── scanner-v3.js                # 메인 페이지
│   └── archived.js                      # ARCHIVED 페이지
├── components/
│   └── v3/
│       ├── ActiveRecommendationCard.js
│       ├── WeakRecommendationCard.js
│       ├── BrokenRecommendationCard.js
│       ├── ArchivedCardV3.js
│       └── ...
└── utils/
    └── v3StatusMapping.js               # 상태 매핑
```

---

## 참고 문서

- [V3 추천 시스템 리팩터링 리포트](./implementation/V3_RECOMMENDATIONS_REFACTORING_REPORT.md)
- [V3 UX 구현 가이드](./ux/V3_UX_IMPLEMENTATION.md)
- [작업 인수인계 프롬프트](../HANDOVER_PROMPT.md)

---

**마지막 업데이트**: 2026-01-02


