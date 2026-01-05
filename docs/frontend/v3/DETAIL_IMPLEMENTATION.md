# v3 종목 상세 화면 구현 완료

## 구현된 기능

### 1. 추천 기준 종가(기준점) 섹션
- ✅ 라벨: "추천 기준 종가(기준점)"
- ✅ 값: `anchor_date` + `anchor_close`
- ✅ 표시 형식:
  - 날짜: YYYY-MM-DD
  - 가격: 통화 포맷 (원/USD)
- ✅ anchor 정보가 없을 때: "기준점 정보가 없습니다" 표시
- ✅ anchor 값은 서버에서만 사용 (프론트 계산 금지)

### 2. 개인 매수가 섹션
- ✅ 라벨: "내 매수가(개인 참고)"
- ✅ 값이 없으면: "미입력"
- ✅ 버튼/액션:
  - 미입력: "입력" 버튼
  - 입력됨: "수정", "삭제" 버튼
- ✅ 입력 방식:
  - 숫자 입력 필드
  - "저장" 클릭 시 1회 호출 (자동 저장 금지)
- ✅ 고정 문구 (항상 표시):
  "개인 참고용이며 추천 판단과 무관합니다"
- ✅ 에러/성공 메시지 표시

### 3. API 연동
- ✅ `positionService.js`: 서비스 레이어 분리
- ✅ API 스펙 (TODO: 백엔드 구현 필요):
  - GET  `/me/positions/{ticker}`  -> `{ avg_buy_price }` 또는 null
  - PUT  `/me/positions/{ticker}`  body `{ avg_buy_price }`
  - DELETE `/me/positions/{ticker}`
- ✅ 임시: API가 없으면 localStorage 사용 (백엔드 붙이면 끝나게 구조화)

### 4. v3 홈에서 상세 화면 이동
- ✅ ACTIVE 카드 클릭: `/stock-analysis?ticker=${ticker}&from=v3`
- ✅ BROKEN 카드 클릭: `/stock-analysis?ticker=${ticker}&from=v3`
- ✅ `from=v3` 플래그로 v3 상세 컴포넌트 표시

## 검증 체크리스트

### ✅ 완료된 검증
1. 홈 카드에는 여전히 숫자 0개 (회귀 확인)
2. 상세 화면에서 `anchor_date`/`anchor_close` 표시
3. anchor는 프론트 계산 없이 서버 값만 사용
4. 개인 매수가:
   - 없으면 "미입력"
   - 입력/수정/삭제 동작
   - 고정 문구 항상 표시
5. 개인 매수가 값이 status/섹션 분기에 영향 없음

## 주요 파일

- `frontend/components/v3/StockDetailV3.js`: v3 상세 화면 컴포넌트
- `frontend/services/positionService.js`: 개인 매수가 서비스 레이어
- `frontend/pages/stock-analysis.js`: 상세 화면 페이지 (v3 컴포넌트 통합)
- `frontend/components/v3/ActiveStockCardV3.js`: ACTIVE 카드 (v3 플래그 추가)
- `frontend/components/v3/BrokenStockCardV3.js`: BROKEN 카드 (v3 플래그 추가)

## 다음 단계

- 백엔드 API 구현 (`/me/positions/{ticker}`)
- anchor 정보를 `/analyze-friendly` API에 추가
- 에러 처리 개선
- 로딩 상태 개선

