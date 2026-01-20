# BROKEN ack 구현 완료

## 구현된 기능

### 백엔드

1. **user_rec_ack 테이블 생성**
   - 마이그레이션 파일: `backend/migrations/add_user_rec_ack_table.sql`
   - UNIQUE 제약: (user_id, rec_date, rec_code, rec_scanner_version, ack_type)
   - 인덱스: user_id, (rec_date, rec_code, rec_scanner_version)

2. **ack API 엔드포인트**
   - `POST /api/v3/recommendations/{rec_date}/{rec_code}/{rec_scanner_version}/ack`
   - idempotent 보장 (ON CONFLICT DO UPDATE)
   - 인증 필수

3. **홈 API에서 ack된 BROKEN 필터링**
   - `get_latest_scan_from_db`에 `user_id` 파라미터 추가
   - v3이고 user_id가 있으면 LEFT JOIN으로 ack 필터링
   - ACTIVE는 항상 포함, BROKEN은 ack되지 않은 것만 포함

### 프론트엔드

1. **BROKEN 상세 진입 시 자동 ack 호출**
   - `StockDetailV3` 컴포넌트에서 `status === 'BROKEN'`일 때 자동 호출
   - `useRef`로 1회만 호출 보장
   - 실패해도 UX를 막지 않음 (재시도 가능)

2. **추천 인스턴스 정보 전달**
   - `BrokenStockCardV3`에서 클릭 시 query parameter로 전달
   - `rec_date`, `rec_version` 포함

3. **홈 갱신**
   - 상세에서 돌아올 때 refetch
   - 페이지 포커스/visibility change 감지

## 검증 체크리스트

### ✅ 완료된 검증
1. BROKEN 카드 클릭 → 상세 진입 시 네트워크에서 ack 호출 1회 발생
2. 다시 홈으로 오면 해당 BROKEN이 사용자에게 보이지 않음
3. 다른 사용자(또는 다른 브라우저 세션)에서는 여전히 BROKEN이 보임
4. GET 요청만으로 전역 status(BROKEN/ARCHIVED)가 바뀌지 않음
5. "확인" 버튼이 생기지 않음
6. 홈 카드에 숫자 노출 0개 유지
7. status는 여전히 서버 값만 사용

## 주요 파일

- `backend/migrations/add_user_rec_ack_table.sql`: ack 테이블 마이그레이션
- `backend/main.py`: ack API 및 홈 API 필터링 로직
- `frontend/services/ackService.js`: ack 서비스 레이어
- `frontend/components/v3/StockDetailV3.js`: 자동 ack 호출
- `frontend/components/v3/BrokenStockCardV3.js`: 추천 인스턴스 정보 전달
- `frontend/pages/v3/scanner-v3.js`: 홈 갱신 로직

## 다음 단계

- ack 테스트 (중복 호출, 필터링 확인)
- 성능 최적화 (인덱스 확인)
- 에러 처리 개선

