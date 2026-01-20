# v3 홈 화면 카드 규칙 구현 완료

## 구현된 카드 컴포넌트

### 1. ActiveStockCardV3
- ✅ 종목명(티커 포함)
- ✅ 상태 배지: "유효" (녹색)
- ✅ 조건부 배지: "신규" (파란색, 오늘 생성된 ACTIVE일 때만)
- ✅ 고정 문구 1줄:
  - 신규일 때: "새로운 기회로 포착되었습니다"
  - 유지일 때: "추천 가정이 유지되고 있습니다"
- ✅ 클릭 시 상세 화면 이동 (`/stock-analysis?ticker=${ticker}`)
- ✅ 숫자 필드 0개 (가격/수익률/등락/손익 등 모두 제외)

### 2. BrokenStockCardV3
- ✅ 종목명(티커 포함)
- ✅ 고정 문구 2줄:
  1) "추천 당시 가정이 깨졌습니다"
  2) "리스크 관점에서 정리를 고려하세요"
- ✅ 클릭 시 상세 화면 이동 (`/stock-analysis?ticker=${ticker}`)
- ✅ 숫자 필드 0개
- ✅ 매도/손절 지시 없음
- ✅ 재추천/재진입 암시 없음

## 정렬 규칙 (최종 확정)

### BROKEN 리스트 정렬
- ✅ `broken_at` 내림차순 (없으면 `updated_at`, 없으면 `created_at`)
- ✅ 최신이 위

### ACTIVE 리스트 정렬
- ✅ 1순위: 신규(`is_new == true` 또는 `recommended_at==today`) 우선
- ✅ 2순위: `recommended_at` 내림차순 (없으면 `created_at`)
- ✅ 3순위: 안정 정렬 - `ticker` 오름차순 (없으면 `name`)

## 신규 판정 로직

### ACTIVE 신규 판정
- 서버 `is_new` 플래그 우선 사용
- 없으면 `recommended_at` (또는 `recommended_date`, `created_at`)를 Asia/Seoul todayKey와 비교
- 오늘 날짜와 일치하면 신규로 판정

### BROKEN 신규 판정
- 서버 `is_new_broken` 플래그 우선 사용
- 없으면 `broken_at` (또는 `updated_at`, `recommended_date`)를 Asia/Seoul todayKey와 비교

## 검증 체크리스트

### ✅ 완료된 검증
1. ACTIVE 카드에 숫자 0개
2. BROKEN 카드에 숫자 0개
3. BROKEN 카드 문구 2줄 정확히 고정 문구
4. ACTIVE 카드 문구가 신규/유지에 맞게만 표시
5. 신규 ACTIVE는 리스트 상단에 위치
6. BROKEN은 `broken_at` 기준 최신이 위
7. `determineStockStatus` 함수 호출 없음 (서버 status만 사용)

### 브라우저 콘솔에서 확인
```javascript
// 1. 숫자 노출 확인
document.querySelectorAll('[class*="Card"]').forEach(card => {
  const text = card.textContent;
  const hasNumber = /\d+원|\d+%|수익률|가격|등락|KRW|USD|current_price|current_return|change_rate|recommended_price/.test(text);
  if (hasNumber) console.log('숫자 발견:', card);
});

// 2. BROKEN 카드 문구 확인
document.querySelectorAll('[class*="Broken"]').forEach(card => {
  const text = card.textContent;
  const hasCorrectPhrase1 = text.includes('추천 당시 가정이 깨졌습니다');
  const hasCorrectPhrase2 = text.includes('리스크 관점에서 정리를 고려하세요');
  if (!hasCorrectPhrase1 || !hasCorrectPhrase2) {
    console.log('BROKEN 카드 문구 오류:', card);
  }
});

// 3. ACTIVE 카드 문구 확인
document.querySelectorAll('[class*="Active"]').forEach(card => {
  const text = card.textContent;
  const hasNewPhrase = text.includes('새로운 기회로 포착되었습니다');
  const hasMaintainPhrase = text.includes('추천 가정이 유지되고 있습니다');
  if (!hasNewPhrase && !hasMaintainPhrase) {
    console.log('ACTIVE 카드 문구 오류:', card);
  }
});
```

## 주요 파일

- `frontend/components/v3/ActiveStockCardV3.js`: ACTIVE 카드 컴포넌트
- `frontend/components/v3/BrokenStockCardV3.js`: BROKEN 카드 컴포넌트
- `frontend/pages/v3/scanner-v3.js`: 홈 화면 (카드 교체 및 정렬 로직)

## 다음 단계

- 카드 디자인 개선
- 애니메이션 추가
- 접근성 개선

