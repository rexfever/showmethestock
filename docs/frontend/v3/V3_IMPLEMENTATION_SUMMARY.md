# V3 화면 구현 요약

## 변경/추가된 파일 목록

### 백엔드
1. `backend/main.py`
   - `/scan-by-date/{date}` 엔드포인트: v3일 때 `v3_case_info` 필드 추가
   - `get_latest_scan_from_db()` 함수: v3일 때 `v3_case_info` 필드 추가

### 프론트엔드
1. `frontend/components/v3/V3MarketRegimeCard.js` (신규)
   - V3 전용 장세 카드 컴포넌트
   - 케이스 A/B/C/D에 따라 다른 문구 표시

2. `frontend/components/v3/V3DateSection.js` (신규)
   - V3 전용 날짜별 섹션 컴포넌트
   - 케이스 D일 때 Empty State 섹션 표시
   - 케이스 A/B/C일 때 추천 종목 리스트 표시

3. `frontend/pages/v3/scanner-v3.js` (수정)
   - `v3CaseInfo` 상태 관리 추가
   - 개발용 mockCaseType 기능 추가
   - `V3DateSection` 컴포넌트 사용

## 개발용 케이스 테스트 방법

### 방법 1: 브라우저 개발자 도구 사용 (권장)

1. 브라우저에서 v3 화면(`/v3/scanner-v3`) 접속
2. 개발 모드에서 상단에 노란색 배너가 표시됨
3. 드롭다운에서 원하는 케이스 선택:
   - "케이스 A (v2-lite + midterm)"
   - "케이스 B (v2-lite만)"
   - "케이스 C (midterm만)"
   - "케이스 D (둘 다 없음)"
4. 선택한 케이스에 맞는 장세 카드와 UI가 즉시 표시됨
5. "실제 데이터 사용"을 선택하면 API 응답 데이터 사용

### 방법 2: 로컬 스토리지 직접 설정

브라우저 콘솔에서:
```javascript
// 케이스 1 강제 설정 (v2-lite + midterm)
localStorage.setItem('v3_mock_case', '1');
location.reload();

// 케이스 2 강제 설정 (midterm만)
localStorage.setItem('v3_mock_case', '2');
location.reload();

// 케이스 3 강제 설정 (v2-lite만)
localStorage.setItem('v3_mock_case', '3');
location.reload();

// 케이스 4 강제 설정 (둘 다 없음)
localStorage.setItem('v3_mock_case', '4');
location.reload();

// 실제 데이터 사용
localStorage.removeItem('v3_mock_case');
location.reload();
```

## API 응답 구조

### v3_case_info 필드 (optional)

```json
{
  "ok": true,
  "data": {
    "items": [...],
    "v3_case_info": {
      "has_recommendations": true,
      "active_engines": ["v2lite", "midterm"],
      "scan_date": "2025-12-26",
      "engine_labels": {
        "v2lite": "단기 반응형",
        "midterm": "중기 추세형"
      }
    }
  }
}
```

## 케이스별 동작 (사용자 친화적 표현, 기술 용어 제거)

### 케이스 1: v2-lite & midterm 둘 다 있음
- 장세 카드: "📈 오늘은 흐름이 이어질 가능성이 있는 종목이 있습니다"
  - 며칠 이상 이어질 수 있는 흐름을 기준으로 종목을 골랐습니다.
  - 오늘 안에 가격이 흔들릴 수 있지만, 전체 방향이 더 중요합니다.
  - 당장 결정하지 않아도, 추세가 유지되는지 지켜보는 전략이 적합합니다.
- 추천 종목 리스트 표시
- Empty State 숨김

### 케이스 2: midterm만 있음
- 장세 카드: "📊 오늘은 천천히 이어지는 흐름을 보는 날입니다"
  - 단기적인 변동보다, 며칠 이상 이어질 가능성을 기준으로 선별했습니다.
  - 하루 이틀의 움직임에 반응할 필요는 없습니다.
  - 중간에 흔들림이 있어도 흐름이 유지되는지가 핵심입니다.
- 추천 종목 리스트 표시
- Empty State 숨김

### 케이스 3: v2-lite만 있음
- 장세 카드: "⏱ 오늘은 하루 안에서도 판단이 필요한 날입니다"
  - 짧은 시간 안에 가격 변동이 커질 수 있습니다.
  - 신호가 자주 나오지 않도록 제한적으로 선별되었습니다.
  - 무리한 진입보다는 가볍게 관찰하거나 소액 대응이 적합합니다.
- 추천 종목 리스트 표시
- Empty State 숨김

### 케이스 4: 둘 다 없음
- 장세 카드: "☕ 오늘은 굳이 판단하지 않아도 됩니다"
  - 뚜렷한 방향이 보이지 않는 상태입니다.
  - 지금은 움직이지 않는 것이 더 유리할 수 있습니다.
  - 다음 기회를 기다려도 늦지 않습니다.
- Empty State 섹션 표시:
  - 카드 1: "오늘은 굳이 판단하지 않아도 됩니다"
  - 카드 2: "오늘 할 일(체크리스트)"
  - 버튼: "지난 추천 보기"
- 과거 추천은 인피니티 스크롤에서 자동으로 표시됨

## 관리자 라우팅

- 관리자 화면에서 "V3 엔진" 선택 시:
  - `active_engine = 'v3'`로 DB 저장
  - `/bottom-nav-link` API가 `link_url: "/v3/scanner-v3"` 반환
  - 사용자가 "스캐너 시작하기" 버튼 클릭 시 v3 화면으로 이동
- 백엔드 API 엔드포인트:
  - `GET /bottom-nav-link`: 공개 API, `active_engine`에 따라 링크 반환
  - `GET /admin/bottom-nav-link`: 관리자 전용, 설정 조회
  - `POST /admin/bottom-nav-link`: 관리자 전용, 설정 업데이트

## Empty State 동작

### 케이스 D (추천 없음)
1. 장세 카드 표시: "오늘은 추천이 없습니다"
2. Empty State 섹션 표시:
   - "오늘은 추천이 없습니다" 카드
   - "오늘 할 일" 체크리스트 카드
   - "지난 추천 보기" 버튼
3. "지난 추천 보기" 버튼 클릭 시:
   - 다음 날짜 섹션(과거 추천)으로 스크롤
   - 인피니티 스크롤로 과거 추천 자동 로드

### 케이스 A/B/C (추천 있음)
1. 장세 카드 표시: 케이스별 문구
2. 추천 종목 리스트 표시
3. Empty State 숨김

## 주의사항

- v1/v2 화면과 완전히 분리되어 있음
- v2 화면 컴포넌트는 수정하지 않음
- v3 전용 컴포넌트만 사용 (`V3DateSection`, `V3MarketRegimeCard`)
- 뉴스/외부 링크/AI 요약 기능 없음
- 기술 용어 제거 (단기/중기/빠른 움직임/민첩한 대응 등 사용 안 함)
- 투자 경험이 없는 사용자도 이해할 수 있는 문장만 사용
- "오늘 사용자가 어떻게 행동해야 하는지"가 드러나는 문구
- 상승/하락 예측, 수익 보장 표현 금지
