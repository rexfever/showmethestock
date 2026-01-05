# v3 홈 화면 상태 기반 리팩토링 완료

## 변경 사항

### 1. 날짜별 인피니티 스크롤 제거
- ✅ `InfiniteScrollContainer` 제거
- ✅ `V3DateSection` 제거
- ✅ `dateSections` 상태 제거
- ✅ `fetchScanByDate` 함수 제거
- ✅ `handleLoadMore` 함수 제거
- ✅ `getPreviousTradingDate` 함수 제거
- ✅ 날짜별 데이터 구조 제거

### 2. 상태 기반 데이터 모델
- ✅ `items` 배열로 단순화
- ✅ 서버 `status` 필드 사용 (ACTIVE/BROKEN/ARCHIVED)
- ✅ ARCHIVED 자동 필터링
- ✅ 프론트에서 status 판정 로직 없음

### 3. 2개 섹션 구조
- ✅ **관리 필요 종목** 섹션: `status === 'BROKEN'`
- ✅ **유효한 추천** 섹션: `status === 'ACTIVE'`
- ✅ ARCHIVED는 홈에서 렌더링하지 않음
- ✅ BROKEN과 ACTIVE는 완전히 분리된 섹션

### 4. 임시 카드 컴포넌트
- ✅ `StatusBasedCard` 컴포넌트 생성
- ✅ 숫자 필드 절대 노출 안 함:
  - ❌ current_price
  - ❌ current_return
  - ❌ change_rate
  - ❌ recommended_price
  - ❌ 수익률/가격/등락 관련 모든 숫자
- ✅ 최소 표시:
  - 종목명/티커
  - 상태 라벨 (ACTIVE, BROKEN)

### 5. 정렬 규칙
- ✅ BROKEN: `recommended_date` 내림차순 (TODO: `broken_at` 필드 추가 필요)
- ✅ ACTIVE: `recommended_date` 내림차순 (TODO: `recommended_at` 필드 추가 필요)

## 검증 체크리스트

### ✅ 완료된 검증
1. 날짜별 인피니티 스크롤 UI 제거됨
2. 상태 기반 데이터 모델로 재구성됨
3. BROKEN/ACTIVE 2개 섹션 구현됨
4. ARCHIVED 숨김 처리됨
5. 숫자 노출 0개 (StatusBasedCard 확인)

### 🔍 추가 검증 필요
- 실제 API 호출로 동일 추천 인스턴스가 BROKEN/ACTIVE 섹션에 동시에 나오지 않는지 확인
- ARCHIVED가 홈에 렌더링되지 않는지 확인
- 카드에 숫자가 전혀 표시되지 않는지 확인

## 다음 단계
- 섹션 접힘/펼침 기능
- 배지 (신규/업데이트 등)
- 요약줄
- 자동 펼침
- 카드 디자인 개선

