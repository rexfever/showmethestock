# v3 추천 시스템 UX 구현 요약

## 구현 완료 상태

✅ **백엔드 상태를 1:1로 번역하는 UX 구현 완료**

---

## 구현된 파일

### 1. 상태 매핑 상수
**파일**: `frontend/utils/v3StatusMapping.js`

- 백엔드 상태 → UX 매핑 정의
- 상태별 색상 클래스
- 렌더링 규칙 함수 (`shouldRenderStatus`, `getSectionType`)

### 2. 추천 카드 컴포넌트
**파일**: `frontend/components/v3/RecommendationCardV3.js`

- 백엔드 상태를 1:1로 번역하는 카드
- 숫자, 점수, 엔진명, 추천 횟수 노출 금지
- REPLACED, ARCHIVED 자동 필터링

### 3. 스캐너 페이지
**파일**: `frontend/pages/v3/scanner-v3.js`

- API 호출: `/api/v3/recommendations/active`, `/api/v3/recommendations/needs-attention`
- `scan_results` 테이블 사용하지 않음
- 상태별 섹션 분리
- ticker당 ACTIVE/WEAK_WARNING 1개 보장

---

## 백엔드 상태 → UX 매핑

### ACTIVE
- **헤더**: "추천 유효"
- **요약**: "추천 당시 가정이 유지되고 있습니다"
- **행동 가이드**: "계획대로 관찰하거나 진입을 고려하세요"
- **보조 설명**: "현재 흐름은 추천 기준과 크게 달라지지 않았습니다"
- **색상**: 초록 계열
- **섹션**: "유효한 추천"

### WEAK_WARNING
- **헤더**: "흐름 약화"
- **요약**: "추천 당시 흐름이 약해지고 있습니다"
- **행동 가이드**: "변동성 확대에 유의하세요"
- **보조 설명**: "단기 움직임이 불안정해지고 있습니다"
- **색상**: 노랑/주황 계열
- **섹션**: "유효한 추천" (ACTIVE와 동일)

### BROKEN
- **헤더**: "관리 필요"
- **요약**: "추천 당시 가정이 깨졌습니다"
- **행동 가이드**: "리스크 관점에서 정리를 고려하세요"
- **보조 설명**: "현재 흐름은 추천 기준과 다르게 전개되고 있습니다"
- **색상**: 빨강/주황 계열
- **섹션**: "관리 필요 종목"

### ARCHIVED
- **헤더**: "종료됨"
- **요약**: "해당 추천은 종료되었습니다"
- **렌더링**: 기본 화면 비노출 (히스토리에서만)

### REPLACED
- **렌더링**: 절대 노출하지 않음

---

## 핵심 구현 사항

### ✅ 1. 백엔드 상태 1:1 매핑
- 판단/해석 없이 번역만 수행
- `STATUS_TO_UX` 상수로 정의

### ✅ 2. 숫자 노출 금지
- 추천 가격, 수익률, 손절 퍼센트 표시하지 않음
- 점수, 엔진명, 추천 횟수 노출하지 않음

### ✅ 3. 중복 방지
- ticker당 ACTIVE/WEAK_WARNING 최대 1개만 표시
- REPLACED 필터링
- anchor_date 기준으로 최신 것만 유지

### ✅ 4. 섹션 분리
- ACTIVE/WEAK_WARNING: "유효한 추천" 섹션
- BROKEN: "관리 필요 종목" 섹션
- ARCHIVED/REPLACED: 기본 화면 비노출

### ✅ 5. 데이터 소스
- `recommendations` 테이블만 사용
- `scan_results` 테이블 절대 사용하지 않음

---

## 검증 체크리스트

- [x] ACTIVE 추천은 메인 추천 영역에만 표시
- [x] WEAK_WARNING은 ACTIVE와 동일 섹션에 표시
- [x] BROKEN은 관리 필요 섹션에만 표시
- [x] ARCHIVED는 기본 화면에 노출하지 않음
- [x] REPLACED는 절대 노출하지 않음
- [x] ticker당 ACTIVE/WEAK_WARNING은 최대 1개만 표시
- [x] 숫자, 점수, 엔진명, 추천 횟수 노출하지 않음
- [x] `scan_results` 테이블을 사용하지 않음
- [x] `recommendations` 테이블만 사용
- [x] 백엔드 상태를 1:1로 번역만 수행

---

## 사용 방법

### API 호출
```javascript
// ACTIVE 추천 조회
GET /api/v3/recommendations/active

// 관리 필요 추천 조회 (WEAK_WARNING, BROKEN)
GET /api/v3/recommendations/needs-attention
```

### 컴포넌트 사용
```javascript
import RecommendationCardV3 from '../components/v3/RecommendationCardV3';

<RecommendationCardV3 
  item={recommendationItem} 
  isNew={isNew} 
/>
```

### 상태 매핑 사용
```javascript
import { STATUS_TO_UX, BACKEND_STATUS, getSectionType } from '../utils/v3StatusMapping';

const ux = STATUS_TO_UX[BACKEND_STATUS.ACTIVE];
const sectionType = getSectionType(status);
```

---

## 참고 문서

- `frontend/docs/V3_UX_IMPLEMENTATION.md` - 상세 구현 가이드
- `backend/docs/V3_BACKFILL_EXECUTION_RESULTS.md` - 백엔드 마이그레이션 결과

