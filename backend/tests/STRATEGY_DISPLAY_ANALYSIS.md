# 전략 표시 문제 분석 보고서

## 문제 상황
프론트엔드에서 전략 배지에 아이콘만 표시되고 전략 이름(텍스트)이 표시되지 않음

## 데이터 흐름 분석

### 1. 백엔드 데이터 구조
- `scan_rank` 테이블에는 `strategy` 컬럼이 없음 (v2 스캐너)
- `flags` JSON 필드에 `trading_strategy`가 저장됨
- 예: `{"trading_strategy": "포지션", "label": "매수 후보", ...}`

### 2. 백엔드 API 로직 (main.py)
```python
# 1. DB에서 strategy 컬럼 읽기 (보통 None)
strategy = data.get("strategy")  # None

# 2. flags JSON 파싱
flags_dict = json.loads(flags) if isinstance(flags, str) else {}

# 3. flags에서 trading_strategy 추출
if not strategy and flags_dict:
    strategy = flags_dict.get('trading_strategy')

# 4. API 응답에 포함
item = {
    "strategy": strategy,  # "포지션" 또는 None
    "flags": flags_dict    # {"trading_strategy": "포지션", ...}
}
```

### 3. 프론트엔드 로직 (StockCardV2.js)
```javascript
// 1. item에서 strategy와 flags 추출
const strategy = item.strategy;  // null 또는 "포지션"
const flags = item.flags || {};   // {trading_strategy: "포지션", ...}

// 2. flags.trading_strategy 확인
const strategyFromFlags = flags?.trading_strategy || null;

// 3. 정규화 (우선순위: strategy > flags.trading_strategy > "관찰")
const normalizedStrategy = strategy || strategyFromFlags || '관찰';

// 4. 전략 정보 가져오기
const strategyInfo = strategyConfig[normalizedStrategy] || strategyConfig.관찰;

// 5. 렌더링
<span>
  <span>{strategyInfo.icon}</span>  {/* ⏳ */}
  <span>{normalizedStrategy}</span> {/* "관찰" */}
</span>
```

## 테스트 결과

### 백엔드 테스트
- ✅ `test_strategy_extraction_from_flags`: flags에서 trading_strategy 추출 성공
- ✅ `test_strategy_in_api_response`: API 응답에 strategy 포함 확인
- ✅ `test_strategy_fallback_to_observation`: 기본값 "관찰" 처리 확인
- ✅ `test_all_strategy_types`: 모든 전략 타입 추출 확인

### 통합 테스트
- ✅ `test_scan_by_date_strategy_field`: API 응답 구조 확인
- ✅ `test_strategy_with_null_flags`: flags가 null인 경우 처리
- ✅ `test_strategy_with_empty_trading_strategy`: trading_strategy가 없는 경우 처리

### End-to-End 테스트
- ✅ `test_end_to_end_strategy_display`: 전체 데이터 흐름 확인
- ✅ `test_end_to_end_with_null_strategy`: strategy가 null인 경우
- ✅ `test_end_to_end_with_no_strategy`: 둘 다 없는 경우

## 발견된 문제점

### 1. 빈 문자열 처리
- `strategy`가 빈 문자열(`""`)인 경우 `||` 연산자가 제대로 작동하지 않을 수 있음
- 해결: `trim()` 후 빈 문자열 체크 추가

### 2. 타입 체크 부족
- `strategy`가 문자열이 아닌 경우 처리 필요
- 해결: `typeof` 체크 추가

### 3. 렌더링 안정성
- React에서 조건부 렌더링 시 빈 값 처리 필요
- 해결: `normalizedStrategy || '관찰'` 추가

## 수정 사항

1. **빈 문자열 처리 개선**
   ```javascript
   const strategyValue = (strategy && typeof strategy === 'string' && strategy.trim()) || null;
   const flagsStrategyValue = (strategyFromFlags && typeof strategyFromFlags === 'string' && strategyFromFlags.trim()) || null;
   ```

2. **렌더링 안정성 개선**
   ```javascript
   <span className="font-medium leading-tight">{normalizedStrategy || '관찰'}</span>
   ```

3. **디버깅 로그 추가**
   - 개발 환경에서 strategy 값 추적 가능

## 예상 원인

실제 문제는 다음 중 하나일 가능성이 높음:
1. **API 응답에서 strategy가 빈 문자열로 오는 경우**
2. **flags 객체가 제대로 파싱되지 않는 경우**
3. **CSS로 인해 텍스트가 숨겨지는 경우** (가능성 낮음)

## 다음 단계

1. 실제 API 응답 확인 (브라우저 개발자 도구)
2. 프론트엔드 콘솔 로그 확인
3. React DevTools로 props 확인

