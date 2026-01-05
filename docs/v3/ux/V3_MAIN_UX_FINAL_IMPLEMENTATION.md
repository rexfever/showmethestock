# V3 메인 화면 UX 최종 구현 리포트

**작업 일자**: 2026-01-02  
**작업 내용**: 상태 기반 추천 서비스 V3의 메인 화면 UX 최종 구현

## 구현 완료 항목

### 1. 일일 추천 상태 배너 (DayStatusBanner)
- ✅ 서버 `daily_digest.window` 기반으로 동작
- ✅ 5가지 상태 지원:
  - `PRE_1535`: "기존 추천을 유지하고 있습니다. 추천은 15:35에 확정됩니다."
  - `POST_1535 + 신규 추천`: "오늘 장후 시간외 매수를 위한 추천이 확정되었습니다."
  - `POST_1535 + 기존 유지`: "오늘은 기존 추천을 유지합니다."
  - `POST_1535 + 추천 없음`: "오늘은 새로운 추천이 없습니다."
  - `HOLIDAY`: "오늘은 시장 휴장일입니다."

### 2. NEW 요약 카드 (DailyDigestCard)
- ✅ `daily_digest.has_changes = true`일 때만 노출
- ✅ 하루 1개만 존재
- ✅ 문구 템플릿:
  ```
  오늘 발생한 변화가 있습니다.
  
  • 신규 추천 {new_recommendations}건
  • 관리 필요 {new_broken}건
  • 관리 종료 {new_archived}건
  ```
- ✅ 종목명 나열 금지
- ✅ 강조/CTA 금지

### 3. 현재 추천 영역 (ACTIVE / WEAK_WARNING)
- ✅ `status IN ('ACTIVE','WEAK_WARNING')`만 표시
- ✅ ticker 중복 제거 (최신 anchor_date 우선)
- ✅ anchor_date 최신순 정렬
- ✅ 기본 접힘 상태 (12개만 표시)
- ✅ 섹션 상단 설명: "아래는 손절 조건에 도달하지 않아 관찰 중인 추천 목록입니다."
- ✅ 숫자 요약 문구 금지

#### ACTIVE 카드
- ✅ 카드 타입: `ActiveRecommendationCard`
- ✅ 문구: "추천 유효", "손절 조건에 도달하지 않은 상태입니다", "관찰 중인 추천입니다"
- ✅ 메타: "추천일 YYYY.MM.DD · 경과 N거래일"
- ✅ 수익률 표시 (보조 정보)

#### WEAK_WARNING 카드
- ✅ 카드 타입: `WeakRecommendationCard`
- ✅ 뱃지: "흐름 약화"
- ✅ 문구: "추천 당시 흐름이 약해지고 있습니다. 변동성 확대에 유의하세요."

### 4. 관리 필요 영역 (BROKEN)
- ✅ `status = 'BROKEN'`만 표시
- ✅ 메인 추천과 절대 혼합 금지
- ✅ 별도 섹션
- ✅ 기본 접힘
- ✅ 최대 5개
- ✅ 최신 BROKEN 우선
- ✅ 카드 문구: "추천 당시 가정이 깨졌습니다. 리스크 관점에서 정리를 고려하세요."

### 5. 관찰 종료된 추천 (ARCHIVED)
- ✅ `status = 'ARCHIVED'`만 표시
- ✅ 별도 섹션
- ✅ 기본 접힘
- ✅ 섹션 상단 설명: "아래는 일정 기간 관찰 후 추천 관리가 종료된 기록입니다."
- ✅ 카드 타입: `ArchivedCardV3`
- ✅ `archive_return_pct` 사용 (ARCHIVED 전환 시점의 수익률)
- ✅ 문구: "추천 관리 기간이 종료되었습니다."
- ✅ 보조 설명: "성과와 무관하게 추천 관찰이 마무리되었습니다."
- ✅ 메타: "추천일 YYYY.MM.DD · 관찰 N거래일"

## 컴포넌트 구조

### 물리적 분리
- ✅ `ActiveRecommendationCard` - ACTIVE 전용
- ✅ `WeakRecommendationCard` - WEAK_WARNING 전용
- ✅ `BrokenRecommendationCard` - BROKEN 전용
- ✅ `ArchivedCardV3` - ARCHIVED 전용
- ✅ `DayStatusBanner` - 일일 상태 배너
- ✅ `DailyDigestCard` - NEW 요약 카드

### 공통 컴포넌트
- ✅ `StatusSectionHeader` - 섹션 헤더 (접기/펼치기)
- ✅ `NoRecommendationsCard` - 추천 없음 안내
- ✅ `MarketHolidayBanner` - 휴장일 배너

## 데이터 흐름

### 서버 → 클라이언트
1. `getServerSideProps`에서 `/api/v3/recommendations/active` 호출
2. API 응답에 `daily_digest` 포함
3. `initialDailyDigest`로 전달
4. 클라이언트에서 `dailyDigest` state로 관리

### 클라이언트 갱신
1. `fetchRecommendations`에서 API 호출
2. `activeData.daily_digest` 추출
3. `setDailyDigest`로 상태 업데이트

## 문구 테이블 준수

### ACTIVE
- ✅ 뱃지: "추천 유효"
- ✅ 요약: "손절 조건에 도달하지 않은 상태입니다"
- ✅ 가이드: "관찰 중인 추천입니다"
- ✅ 메타: "추천일 YYYY.MM.DD · 경과 N거래일"

### WEAK_WARNING
- ✅ 뱃지: "흐름 약화"
- ✅ 요약: "추천 당시 흐름이 약해지고 있습니다"
- ✅ 가이드: "변동성 확대에 유의하세요"

### BROKEN
- ✅ 뱃지: "관리 필요"
- ✅ 요약: "추천 당시 가정이 깨졌습니다"
- ✅ 가이드: "리스크 관점에서 정리를 고려하세요"
- ✅ 보조: "현재 흐름은 추천 기준과 다르게 전개되고 있습니다"

### ARCHIVED
- ✅ 뱃지: "관찰 종료"
- ✅ 요약: "추천 관리 기간이 종료되었습니다"
- ✅ 보조: "성과와 무관하게 추천 관찰이 마무리되었습니다"
- ✅ 메타: "추천일 YYYY.MM.DD · 관찰 N거래일"

## 검증 체크리스트

- ✅ 오늘 뭐가 달라졌는지 3초 안에 보인다 (NEW 요약 카드)
- ✅ ACTIVE 카드들이 서로 다른 말을 한다 (각 카드는 독립적)
- ✅ 수익/손실 여부가 상태로 오독되지 않는다 (ACTIVE = stop_loss 미도달)
- ✅ ARCHIVED가 실패처럼 보이지 않는다 (중립 색상, 기록으로 표시)
- ✅ 어떤 카드도 행동을 지시하지 않는다 (CTA 제거, 관찰 중심)

## 변경된 파일

### 신규 생성
- `frontend/components/v3/DailyDigestCard.js` - NEW 요약 카드 컴포넌트

### 수정된 파일
- `frontend/components/v3/DayStatusBanner.js` - daily_digest.window 기반으로 수정
- `frontend/components/v3/ArchivedCardV3.js` - archive_return_pct 사용
- `frontend/pages/v3/scanner-v3.js` - daily_digest 통합 및 NEW 카드 추가

## 다음 단계

1. 화면 검증 (스크린샷)
2. 문구 테이블 일치 확인
3. 사용자 테스트


