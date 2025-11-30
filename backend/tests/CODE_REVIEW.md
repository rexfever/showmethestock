# 코드 검토 보고서: 수익률 계산 및 목표 달성 표시

## 검토 범위

### 1. 백엔드 수익률 계산 로직 (`backend/services/returns_service.py`)

#### ✅ 검증 완료 사항

1. **DB close_price 우선 사용**
   ```python
   # Line 58-68: scan_price_from_db가 있으면 우선 사용
   if scan_price_from_db and scan_price_from_db > 0:
       scan_price = float(scan_price_from_db)
   else:
       # API로 조회
   ```
   - ✅ DB 값이 있으면 API 조회 없이 사용
   - ✅ DB 값이 없으면 API로 조회

2. **최고/최저 수익률 계산**
   ```python
   # Line 157-179: 기간 내 최고/최저가 기준 수익률 계산
   max_return = ((max_price - scan_price) / scan_price) * 100
   min_return = ((min_price - scan_price) / scan_price) * 100
   ```
   - ✅ 기간 내 모든 high/low 가격 포함
   - ✅ 현재가도 최고/최저 비교에 포함

3. **당일 스캔 처리**
   ```python
   # Line 85-110: days_diff == 0일 때 처리
   if days_diff == 0:
       if abs(current_price - scan_price) < 0.01:
           return 0.0  # 가격 차이 없으면 0%
   ```
   - ✅ 당일 스캔 시 올바른 처리

#### ⚠️ 개선 권장 사항

1. **에러 처리 강화**
   - `_get_cached_ohlcv` 실패 시 더 명확한 에러 메시지
   - 빈 DataFrame 처리 시 로깅 추가

2. **성능 최적화**
   - `_parse_cached_ohlcv` 호출 최소화
   - 캐시 히트율 모니터링

### 2. 백엔드 API 응답 로직 (`backend/main.py`)

#### ✅ 검증 완료 사항

1. **recommended_price 결정 로직**
   ```python
   # Line 1993-2016: recommended_price 우선순위
   recommended_price = current_price  # DB close_price
   if returns_info and returns_info.get('scan_price'):
       recommended_price = returns_info.get('scan_price')
   ```
   - ✅ `returns_info.scan_price` 우선
   - ✅ 없으면 DB `close_price` 사용
   - ✅ 일관성 보장

2. **scan_prices 추출**
   ```python
   # Line 1949-1957: DB에서 scan_prices 딕셔너리 생성
   scan_prices = {}
   for row in rows:
       close_price = row_data.get("current_price")
       if close_price and close_price > 0:
           scan_prices[code] = float(close_price)
   ```
   - ✅ 각 종목별로 올바른 가격 매핑
   - ✅ 0 이하 값 제외

3. **returns_info 유효성 검증**
   ```python
   # Line 2000-2016: returns_info 처리
   if returns_info and isinstance(returns_info, dict) and returns_info.get('current_return') is not None:
       # 유효한 경우만 사용
   else:
       # None으로 설정
   ```
   - ✅ `current_return`이 None이 아닐 때만 사용
   - ✅ 빈 딕셔너리 처리

#### ⚠️ 개선 권장 사항

1. **타입 안정성**
   - `current_price`가 float인지 확인
   - `returns_info` 타입 검증 강화

2. **로깅 추가**
   - `recommended_price` 결정 과정 로깅
   - `returns_info` 누락 시 경고 로깅

### 3. 프론트엔드 목표 달성 표시 (`frontend/v2/components/StockCardV2.js`)

#### ✅ 검증 완료 사항

1. **max_return, min_return 추출**
   ```javascript
   // Line 22-24: returns 객체에서 추출
   const max_return = returns.max_return || (current_return > 0 ? current_return : 0);
   const min_return = returns.min_return || (current_return < 0 ? current_return : 0);
   ```
   - ✅ `returns` 객체에서 추출
   - ✅ 없을 때 fallback 처리

2. **목표 달성 판단 로직**
   ```javascript
   // Line 184-195: 다양한 케이스 판단
   const isAchieved = current_return >= targetReturn;
   const wasAchievedButDeclined = max_return >= targetReturn && current_return < targetReturn;
   const isStopLossReached = stopLossValue && current_return <= stopLossValue;
   const hasDeclinedFromPeak = max_return > current_return && max_return >= targetReturn;
   ```
   - ✅ 우선순위: 손절 > 목표 달성 후 하락 > 목표 달성 > 목표 미달
   - ✅ 모든 케이스 커버

3. **UI 표시 정확성**
   ```javascript
   // Line 210-216: 상황별 메시지 표시
   {isStopLossReached 
     ? `⚠️ 손절 기준 도달`
     : wasAchievedButDeclined
     ? `⚠️ 목표 달성했으나 수익률 하락`
     : isAchieved 
     ? `✅ 목표 달성`
     : `목표까지`}
   ```
   - ✅ 각 상황별 올바른 메시지
   - ✅ 색상 및 아이콘 일관성

#### ⚠️ 개선 권장 사항

1. **에러 처리**
   - `max_return`이 `current_return`보다 작은 경우 처리
   - `targetProfit`이 음수인 경우 처리

2. **접근성**
   - 스크린 리더를 위한 aria-label 추가
   - 키보드 네비게이션 지원

## 테스트 커버리지

### 백엔드 테스트
- ✅ DB close_price 우선 사용
- ✅ API 조회 fallback
- ✅ 최고/최저 수익률 계산
- ✅ 배치 계산
- ✅ recommended_price 로직
- ✅ returns_info 유효성 검증

### 프론트엔드 테스트
- ✅ 목표 미달성
- ✅ 목표 달성
- ✅ 목표 초과 달성
- ✅ 목표 달성 후 하락
- ✅ 손절 기준 도달
- ✅ 복합 케이스
- ✅ 경계값 테스트
- ✅ 에러 처리

## 결론

### ✅ 강점
1. **데이터 정확성**: DB close_price 우선 사용으로 일관성 보장
2. **로직 명확성**: 각 케이스별 명확한 판단 기준
3. **UI 일관성**: 상황별 일관된 색상 및 메시지

### 🔄 개선 필요
1. **에러 처리**: 더 강화된 예외 처리 및 로깅
2. **성능**: 캐시 최적화 및 배치 처리 개선
3. **접근성**: 스크린 리더 및 키보드 네비게이션 지원

### 📊 전체 평가
- **코드 품질**: ⭐⭐⭐⭐ (4/5)
- **테스트 커버리지**: ⭐⭐⭐⭐ (4/5)
- **유지보수성**: ⭐⭐⭐⭐ (4/5)
- **사용자 경험**: ⭐⭐⭐⭐⭐ (5/5)

