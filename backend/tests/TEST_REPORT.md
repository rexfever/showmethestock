# 수익률 계산 및 목표 달성 표시 테스트 보고서

## 테스트 범위

### 1. 백엔드 수익률 계산 로직 (`test_returns_calculation.py`)

#### 테스트 케이스
1. **DB close_price 우선 사용 검증**
   - `scan_price_from_db` 파라미터가 전달되면 DB 값을 우선 사용
   - API로 조회한 값과 다를 때도 DB 값 사용 확인

2. **DB close_price 없을 때 API 조회**
   - `scan_price_from_db`가 None이면 API로 조회
   - 조회한 값을 scan_price로 사용

3. **최고/최저 수익률 계산 정확성**
   - `max_return`: 기간 내 최고가 기준 수익률
   - `min_return`: 기간 내 최저가 기준 수익률
   - 계산 공식: `((price - scan_price) / scan_price) * 100`

4. **배치 계산 시 scan_prices 전달**
   - `calculate_returns_batch`가 각 ticker에 대해 `scan_price_from_db` 전달 확인

### 2. recommended_price 로직 (`test_main_returns_integration.py`)

#### 테스트 케이스
1. **scan_prices 추출 로직**
   - DB에서 `close_price`를 `scan_prices` 딕셔너리로 추출
   - 각 종목 코드별로 올바른 가격 매핑

2. **recommended_price 결정 로직**
   - `returns_info.scan_price` 우선 사용
   - 없으면 DB `close_price` 사용
   - `current_price`가 0이면 None

3. **returns_info 유효성 검증**
   - `current_return`이 None이 아닐 때만 사용
   - 빈 딕셔너리나 None 처리

4. **current_return None 처리**
   - `returns_info`가 없거나 유효하지 않으면 None 반환
   - `max_return`, `min_return`도 함께 None

### 3. 프론트엔드 목표 달성 표시 (`StockCardV2.test.js`)

#### 테스트 케이스
1. **목표 미달성 상태**
   - "목표까지 X.XX%" 표시
   - 파란색 진행 바

2. **목표 달성 상태**
   - "✅ 목표 달성" 표시
   - 초록색 진행 바

3. **목표 초과 달성**
   - "✅ 목표 달성 (+X.XX% 초과)" 표시
   - "🎉 목표 대비 XX% 초과 달성!" 메시지

4. **목표 달성 후 수익률 감소**
   - "⚠️ 목표 달성했으나 수익률 하락" 표시
   - 최고 수익률과 현재 수익률 비교 표시
   - 주황색 진행 바

5. **목표 달성 중이지만 최고점에서 하락**
   - "✅ 목표 달성" + "최고 X.XX%에서 X.XX% 하락" 표시
   - 초록색 진행 바

6. **손절 기준 도달**
   - "⚠️ 손절 기준 도달" 표시
   - "🛑 손절 기준(X%) 도달 - 매도 고려 권장" 메시지
   - 빨간색 진행 바

7. **복합 케이스**
   - 목표 달성 후 손절 기준 도달 (손절 우선 표시)
   - 목표 미달이지만 최고점에서 하락 (목표 달성 후 하락으로 표시 안 됨)

8. **경계값 테스트**
   - 목표와 정확히 같음 (5.00%)
   - 목표보다 0.01% 높음 (5.01%)
   - 손절 기준과 정확히 같음 (-3.00%)

9. **에러 처리**
   - `returns` 객체가 없는 경우
   - `max_return`이 없는 경우
   - `targetProfit`이 없는 경우

## 핵심 검증 사항

### 1. 데이터 정확성
- ✅ DB `close_price`가 `recommended_price`로 정확히 사용됨
- ✅ `scan_price_from_db`가 수익률 계산에 우선 사용됨
- ✅ `max_return`, `min_return`이 기간 내 최고/최저가 기준으로 계산됨

### 2. 로직 정확성
- ✅ `recommended_price` 결정 우선순위: `returns_info.scan_price` > DB `close_price` > None
- ✅ `returns_info` 유효성 검증 정확
- ✅ 목표 달성/손절 기준 판단 로직 정확

### 3. UI 표시 정확성
- ✅ 각 상황별 올바른 색상 및 메시지 표시
- ✅ 우선순위: 손절 > 목표 달성 후 하락 > 목표 달성 > 목표 미달
- ✅ 경계값 처리 정확

## 실행 방법

### 백엔드 테스트
```bash
cd backend
source venv/bin/activate
pytest tests/test_returns_calculation.py -v
pytest tests/test_main_returns_integration.py -v
```

### 프론트엔드 테스트
```bash
cd frontend
npm test
```

## 개선 사항

1. **통합 테스트 추가**
   - 실제 DB 연결을 통한 end-to-end 테스트
   - 실제 API 응답을 통한 프론트엔드 통합 테스트

2. **성능 테스트**
   - 배치 계산 성능 측정
   - 대량 데이터 처리 시 메모리 사용량 확인

3. **에러 케이스 확장**
   - 네트워크 오류 시나리오
   - DB 연결 실패 시나리오
   - 잘못된 데이터 형식 처리
