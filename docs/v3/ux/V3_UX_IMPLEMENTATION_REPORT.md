# v3 추천 시스템 UX 구현 리포트

**작성일**: 2025-12-30  
**담당**: UX 구현 담당 개발자  
**목적**: 백엔드 상태를 1:1로 번역하는 UX 구현

---

## 1. 구현 개요

### 1.1 목표
- 백엔드 상태(ACTIVE, WEAK_WARNING, BROKEN, ARCHIVED, REPLACED)를 사용자에게 보여줄 "추천 카드 UX 문구"로 정확히 매핑
- UX는 판단하거나 해석하지 않음
- 숫자, 점수, 엔진명, 추천 횟수 노출 금지
- 중복 추천, 과거 상태 변경, 스캔 결과 노출 방지

### 1.2 핵심 원칙
1. **백엔드 상태를 정확히 번역만 수행** - 판단/해석 금지
2. **데이터 소스**: `recommendations` 테이블만 사용, `scan_results` 절대 사용하지 않음
3. **렌더링 규칙**: 상태별 섹션 분리, ticker당 ACTIVE/WEAK_WARNING 1개 보장

---

## 2. 구현된 파일

### 2.1 상태 매핑 상수
**파일**: `frontend/utils/v3StatusMapping.js`

**주요 내용**:
- `BACKEND_STATUS`: 백엔드 상태 타입 정의
- `STATUS_TO_UX`: 백엔드 상태 → UX 매핑
- `STATUS_COLOR_CLASSES`: 상태별 색상 클래스
- `shouldRenderStatus()`: 렌더링 가능 여부 확인 함수
- `getSectionType()`: 상태별 섹션 분류 함수

**매핑 규칙**:
```javascript
ACTIVE → {
  header: '추천 유효',
  summary: '추천 당시 가정이 유지되고 있습니다',
  actionGuide: '계획대로 관찰하거나 진입을 고려하세요',
  helperText: '현재 흐름은 추천 기준과 크게 달라지지 않았습니다',
  colorScheme: 'green',
  renderInMainSection: true
}

WEAK_WARNING → {
  header: '흐름 약화',
  summary: '추천 당시 흐름이 약해지고 있습니다',
  actionGuide: '변동성 확대에 유의하세요',
  helperText: '단기 움직임이 불안정해지고 있습니다',
  colorScheme: 'yellow',
  renderInMainSection: true
}

BROKEN → {
  header: '관리 필요',
  summary: '추천 당시 가정이 깨졌습니다',
  actionGuide: '리스크 관점에서 정리를 고려하세요',
  helperText: '현재 흐름은 추천 기준과 다르게 전개되고 있습니다',
  colorScheme: 'red',
  renderInMainSection: false
}
```

### 2.2 추천 카드 컴포넌트
**파일**: `frontend/components/v3/RecommendationCardV3.js`

**주요 기능**:
- 백엔드 상태를 1:1로 번역하여 카드 렌더링
- REPLACED, ARCHIVED 자동 필터링
- 상태별 색상 및 문구 자동 적용
- 숫자, 점수, 엔진명 노출하지 않음

**렌더링 구조**:
```
┌─────────────────────────────────────┐
│ 종목명 (티커)        [상태 배지]     │
├─────────────────────────────────────┤
│ 상태 요약                           │
│ 행동 가이드                         │
│ 보조 설명 (선택)                    │
└─────────────────────────────────────┘
```

### 2.3 스캐너 페이지
**파일**: `frontend/pages/v3/scanner-v3.js`

**주요 변경사항**:
1. **API 호출 변경**
   - 기존: `/latest-scan?scanner_version=v3` (scan_results 사용)
   - 변경: `/api/v3/recommendations/active`, `/api/v3/recommendations/needs-attention` (recommendations만 사용)

2. **상태 분류 로직**
   - `getSectionType()` 함수 사용
   - ACTIVE/WEAK_WARNING → 'active' 섹션
   - BROKEN → 'needs-attention' 섹션
   - ARCHIVED/REPLACED → 필터링

3. **중복 방지 로직**
   - ticker당 ACTIVE/WEAK_WARNING 1개만 유지
   - `anchor_date` 기준으로 최신 것만 유지

---

## 3. 백엔드 상태 → UX 매핑 상세

### 3.1 ACTIVE
| 항목 | 값 |
|------|-----|
| 카드 헤더 | "추천 유효" |
| 상태 요약 | "추천 당시 가정이 유지되고 있습니다" |
| 행동 가이드 | "계획대로 관찰하거나 진입을 고려하세요" |
| 보조 설명 | "현재 흐름은 추천 기준과 크게 달라지지 않았습니다" |
| 색상 | 초록 계열 (bg-green-50, border-green-200) |
| 섹션 | "유효한 추천" |
| CTA | 신규 진입 허용 |
| 제약 | ticker당 최대 1개만 렌더링 |

### 3.2 WEAK_WARNING
| 항목 | 값 |
|------|-----|
| 카드 헤더 | "흐름 약화" |
| 상태 요약 | "추천 당시 흐름이 약해지고 있습니다" |
| 행동 가이드 | "변동성 확대에 유의하세요" |
| 보조 설명 | "단기 움직임이 불안정해지고 있습니다" |
| 색상 | 노랑/주황 계열 (bg-yellow-50, border-yellow-200) |
| 섹션 | "유효한 추천" (ACTIVE와 동일) |
| CTA | 신규 진입 유지 |
| 특징 | 회복 시 ACTIVE로 복귀 가능 |
| 제약 | ticker당 최대 1개만 렌더링 |

### 3.3 BROKEN
| 항목 | 값 |
|------|-----|
| 카드 헤더 | "관리 필요" |
| 상태 요약 | "추천 당시 가정이 깨졌습니다" |
| 행동 가이드 | "리스크 관점에서 정리를 고려하세요" |
| 보조 설명 | "현재 흐름은 추천 기준과 다르게 전개되고 있습니다" |
| 색상 | 빨강/주황 계열 (bg-red-50, border-red-200) |
| 섹션 | "관리 필요 종목" (별도 섹션) |
| CTA | 신규 진입 금지 |
| 특징 | BROKEN 상태는 복귀하지 않음 |
| 제약 | ticker당 여러 개 가능 (이력 추적) |

### 3.4 ARCHIVED
| 항목 | 값 |
|------|-----|
| 카드 헤더 | "종료됨" |
| 상태 요약 | "해당 추천은 종료되었습니다" |
| 렌더링 | 기본 화면에 노출하지 않음 |
| 접근 | 히스토리/상세 화면에서만 접근 가능 |

### 3.5 REPLACED
| 항목 | 값 |
|------|-----|
| 렌더링 | 절대 노출하지 않음 |
| 용도 | 내부 상태로만 사용 |
| 규칙 | 사용자는 항상 최신 추천만 보도록 처리 |

---

## 4. API 엔드포인트

### 4.1 ACTIVE 추천 조회
```
GET /api/v3/recommendations/active
```

**응답 형식**:
```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "recommendation_id": "uuid",
        "ticker": "047810",
        "name": "한국항공우주",
        "status": "ACTIVE",
        "anchor_date": "2025-12-15",
        "anchor_close": 112800,
        "created_at": "2025-12-15T...",
        ...
      }
    ],
    "count": 1
  }
}
```

### 4.2 관리 필요 추천 조회
```
GET /api/v3/recommendations/needs-attention
```

**응답 형식**:
```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "recommendation_id": "uuid",
        "ticker": "047810",
        "status": "BROKEN",
        "anchor_date": "2025-12-10",
        "broken_at": "2025-12-20T...",
        ...
      }
    ],
    "count": 1
  }
}
```

**포함 상태**: WEAK_WARNING, BROKEN

---

## 5. 렌더링 규칙

### 5.1 섹션 분리
```
┌─────────────────────────────────────┐
│ 관리 필요 종목 (BROKEN)              │
│ ┌─────────────────────────────────┐ │
│ │ [BROKEN 카드들]                 │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 유효한 추천 (ACTIVE/WEAK_WARNING)    │
│ ┌─────────────────────────────────┐ │
│ │ [ACTIVE 카드들]                 │ │
│ │ [WEAK_WARNING 카드들]           │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 5.2 중복 방지 로직
```javascript
// ticker당 ACTIVE/WEAK_WARNING 1개만 유지
.reduce((acc, item) => {
  if (item.status === BACKEND_STATUS.ACTIVE || 
      item.status === BACKEND_STATUS.WEAK_WARNING) {
    const existing = acc.find(i => 
      i.ticker === item.ticker && 
      (i.status === BACKEND_STATUS.ACTIVE || 
       i.status === BACKEND_STATUS.WEAK_WARNING)
    );
    if (existing) {
      // anchor_date 기준으로 최신 것만 유지
      const itemDate = item.anchor_date || item.created_at || '';
      const existingDate = existing.anchor_date || existing.created_at || '';
      if (itemDate > existingDate) {
        acc[acc.indexOf(existing)] = item;
      }
    } else {
      acc.push(item);
    }
  } else {
    acc.push(item);
  }
  return acc;
}, []);
```

### 5.3 필터링 규칙
1. **REPLACED**: 절대 노출하지 않음
2. **ARCHIVED**: 기본 화면에 노출하지 않음
3. **ACTIVE/WEAK_WARNING**: 메인 추천 영역에 표시
4. **BROKEN**: 관리 필요 섹션에 표시

---

## 6. 금지 사항 구현

### 6.1 숫자 노출 금지
- ✅ 추천 가격 표시하지 않음
- ✅ 수익률 표시하지 않음
- ✅ 손절 퍼센트 표시하지 않음
- ✅ 점수 표시하지 않음
- ✅ 엔진명 표시하지 않음
- ✅ 추천 횟수 표시하지 않음

### 6.2 중복 표현 금지
- ✅ "또 추천됨", "여러 번 추천" 같은 표현 사용하지 않음
- ✅ ticker당 ACTIVE/WEAK_WARNING 1개만 표시

### 6.3 스캔 결과 노출 금지
- ✅ `scan_results` 테이블을 UI에 사용하지 않음
- ✅ `recommendations` 테이블만 사용

### 6.4 과거 상태 변경 금지
- ✅ 과거 카드의 상태가 현재 시세로 바뀌는 로직 없음
- ✅ `anchor_date`, `anchor_close` 고정값 사용

---

## 7. 구현 검증

### 7.1 코드 레벨 검증
- ✅ `v3StatusMapping.js`: 모든 상태 매핑 정의 완료
- ✅ `RecommendationCardV3.js`: 상태별 카드 렌더링 구현
- ✅ `scanner-v3.js`: API 호출 및 상태 분류 로직 구현

### 7.2 기능 검증
- ✅ ACTIVE 추천은 메인 추천 영역에만 표시
- ✅ WEAK_WARNING은 ACTIVE와 동일 섹션에 표시
- ✅ BROKEN은 관리 필요 섹션에만 표시
- ✅ ARCHIVED는 기본 화면에 노출하지 않음
- ✅ REPLACED는 절대 노출하지 않음
- ✅ ticker당 ACTIVE/WEAK_WARNING은 최대 1개만 표시

### 7.3 데이터 소스 검증
- ✅ `recommendations` 테이블만 사용
- ✅ `scan_results` 테이블 사용하지 않음
- ✅ API 엔드포인트: `/api/v3/recommendations/*` 사용

---

## 8. 파일 구조

```
frontend/
├── utils/
│   └── v3StatusMapping.js          # 상태 매핑 상수
├── components/
│   └── v3/
│       ├── RecommendationCardV3.js # 추천 카드 컴포넌트
│       └── StatusSectionHeader.js   # 섹션 헤더 (기존)
├── pages/
│   └── v3/
│       └── scanner-v3.js            # 스캐너 페이지
└── docs/
    ├── V3_UX_IMPLEMENTATION.md       # 구현 가이드
    ├── V3_UX_IMPLEMENTATION_SUMMARY.md # 구현 요약
    └── V3_UX_IMPLEMENTATION_REPORT.md # 구현 리포트 (본 문서)
```

---

## 9. 사용 예시

### 9.1 카드 컴포넌트 사용
```javascript
import RecommendationCardV3 from '../components/v3/RecommendationCardV3';

// ACTIVE 추천
<RecommendationCardV3 
  item={{
    ticker: '047810',
    name: '한국항공우주',
    status: 'ACTIVE',
    recommendation_id: 'uuid',
    anchor_date: '2025-12-15',
    anchor_close: 112800
  }}
  isNew={true}
/>

// WEAK_WARNING 추천
<RecommendationCardV3 
  item={{
    ticker: '047810',
    name: '한국항공우주',
    status: 'WEAK_WARNING',
    recommendation_id: 'uuid',
    anchor_date: '2025-12-15',
    anchor_close: 112800
  }}
/>

// BROKEN 추천
<RecommendationCardV3 
  item={{
    ticker: '047810',
    name: '한국항공우주',
    status: 'BROKEN',
    recommendation_id: 'uuid',
    anchor_date: '2025-12-10',
    broken_at: '2025-12-20T...'
  }}
/>
```

### 9.2 상태 매핑 사용
```javascript
import { STATUS_TO_UX, BACKEND_STATUS, getSectionType } from '../utils/v3StatusMapping';

// 상태별 UX 정보 가져오기
const ux = STATUS_TO_UX[BACKEND_STATUS.ACTIVE];
console.log(ux.header); // "추천 유효"
console.log(ux.summary); // "추천 당시 가정이 유지되고 있습니다"

// 섹션 타입 확인
const sectionType = getSectionType('ACTIVE'); // 'active'
const sectionType2 = getSectionType('BROKEN'); // 'needs-attention'
```

---

## 10. 주의사항

### 10.1 백엔드 상태 변경 시
- `v3StatusMapping.js`의 `STATUS_TO_UX` 객체를 업데이트해야 함
- 새로운 상태 추가 시 `STATUS_COLOR_CLASSES`에도 추가 필요

### 10.2 API 응답 형식 변경 시
- `scanner-v3.js`의 `fetchRecommendations` 함수 수정 필요
- 응답 데이터 구조 변경 시 필터링 로직도 함께 수정

### 10.3 문구 변경 시
- `v3StatusMapping.js`의 `STATUS_TO_UX` 객체만 수정하면 됨
- 컴포넌트 코드 수정 불필요

---

## 11. 향후 개선 사항

### 11.1 히스토리 화면
- ARCHIVED 상태 추천을 히스토리 화면에서 표시
- `shouldRenderStatus(status, isHistoryView=true)` 활용

### 11.2 알림 기능
- WEAK_WARNING 상태 변경 시 알림 (동일 추천 이벤트에서 1회만)
- BROKEN 상태 변경 시 알림

### 11.3 성능 최적화
- 대량의 추천 데이터 처리 시 가상 스크롤링 고려
- 메모이제이션 적용 검토

---

## 12. 결론

v3 추천 시스템의 UX 구현이 완료되었습니다. 백엔드 상태를 1:1로 번역하는 역할만 수행하며, 판단이나 해석을 하지 않습니다. 모든 금지 사항(숫자 노출, 중복 표현, 스캔 결과 노출 등)이 준수되었으며, 상태별 섹션 분리와 중복 방지 로직이 구현되었습니다.

**핵심 성과**:
- ✅ 백엔드 상태를 정확히 번역하는 UX 구현
- ✅ 숫자, 점수, 엔진명 노출 금지
- ✅ 중복 추천 방지 (ticker당 ACTIVE/WEAK_WARNING 1개)
- ✅ `recommendations` 테이블만 사용, `scan_results` 사용하지 않음
- ✅ 상태별 섹션 분리 (ACTIVE/WEAK_WARNING, BROKEN)

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-12-30

