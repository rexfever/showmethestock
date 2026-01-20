# v3 홈 화면 접힘/펼침 기능 구현 완료

## 구현된 기능

### 1. 상수/유틸 정의
- ✅ `ACTIVE_COLLAPSE_THRESHOLD = 6`
- ✅ `getTodayKey()`: Asia/Seoul 타임존 기준 오늘 날짜 (YYYY-MM-DD)
- ✅ localStorage 키:
  - `v3.section.broken.collapsed`
  - `v3.section.active.collapsed`
  - `v3.autoExpand.broken.lastDate`
  - `v3.autoExpand.active.lastDate`

### 2. 섹션 헤더 UI
- ✅ `StatusSectionHeader` 컴포넌트 생성
- ✅ 제목: "관리 필요 종목", "유효한 추천"
- ✅ BROKEN: 개수 배지 (빨간색)
- ✅ ACTIVE: "X개 (신규 Y)" 요약 텍스트
- ✅ 토글 버튼: chevron 아이콘 (접근성 고려)

### 3. 접힘 기본값 결정
- ✅ BROKEN: 기본 접힘 (true), localStorage 값 우선
- ✅ ACTIVE: 
  - `activeCount >= 6`이면 기본 접힘 (true)
  - `activeCount < 6`이면 기본 펼침 (false)
  - localStorage 값 우선

### 4. 신규 발생 시 당일 1회 자동 펼침
- ✅ 새 BROKEN 판정:
  - 서버 `is_new_broken` 플래그 우선
  - 없으면 `broken_at` 또는 `updated_at`이 오늘인지 확인
- ✅ 새 ACTIVE 판정:
  - 서버 `is_new` 플래그 우선
  - 없으면 `recommended_at` 또는 `recommended_date`가 오늘인지 확인
- ✅ 자동 펼침 규칙:
  - `lastDate !== todayKey`일 때만 실행
  - 실행 후 `lastDate = todayKey` 저장
  - `useRef`로 무한 루프 방지

### 5. 토글 동작
- ✅ 사용자 토글 시 `collapsed` 상태 변경
- ✅ 변경 즉시 localStorage 저장
- ✅ 자동 펼침과 충돌하지 않음 (자동 펼침은 최초 1회만)

### 6. 섹션 렌더링
- ✅ `collapsed === true`이면 리스트 숨김
- ✅ `collapsed === false`이면 리스트 렌더링
- ✅ 섹션이 비어있으면 섹션 자체 숨김

## 검증 체크리스트

### 브라우저 콘솔에서 확인
```javascript
// 1. BROKEN 개수 배지 확인
document.querySelector('[class*="bg-red-100"]')?.textContent

// 2. ACTIVE 요약줄 확인
document.querySelector('h3')?.nextElementSibling?.textContent

// 3. localStorage 확인
localStorage.getItem('v3.section.broken.collapsed')
localStorage.getItem('v3.section.active.collapsed')
localStorage.getItem('v3.autoExpand.broken.lastDate')
localStorage.getItem('v3.autoExpand.active.lastDate')

// 4. 숫자 노출 확인 (0개여야 함)
document.querySelectorAll('[class*="Card"]').forEach(card => {
  const text = card.textContent;
  const hasNumber = /\d+원|\d+%|수익률|가격|등락/.test(text);
  if (hasNumber) console.log('숫자 발견:', card);
});
```

## 주요 파일

- `frontend/pages/v3/scanner-v3.js`: 메인 페이지 (접힘/펼침 로직)
- `frontend/components/v3/StatusSectionHeader.js`: 섹션 헤더 컴포넌트
- `frontend/components/v3/StatusBasedCard.js`: 임시 카드 (숫자 없음)

## 다음 단계

- 섹션 접힘/펼침 애니메이션
- 배지 디자인 개선
- 요약줄 스타일 개선
- 카드 디자인 개선

