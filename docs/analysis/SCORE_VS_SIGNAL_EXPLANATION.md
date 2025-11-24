# 점수가 높은데 신호가 부족할 수 있는 이유

## 핵심 차이

**점수**: 각 조건별 가중치를 더한 합계 (가중 평균)
**신호**: 각 조건이 충족되었는지 여부를 카운트 (개수)

## 점수 가중치

| 항목 | 가중치 | 설명 |
|------|--------|------|
| **cross** (골든크로스) | **3점** | TEMA20 > DEMA10 교차 |
| **volume** (거래량) | **2점** | 거래량 급증 |
| **macd** | **1점** | MACD 상승 신호 |
| **rsi** | **1점** | RSI 모멘텀 |
| **tema_slope** | **2점** | TEMA20 상승 추세 |
| **obv_slope** | **2점** | OBV 상승 (자금 유입) |
| **above_cnt5** | **2점** | 연속 상승 |

**최대 가능 점수**: 약 14점

## 신호 개수

**총 7개 신호:**

1. **cond_gc** (골든크로스): TEMA20 > DEMA10 또는 최근 교차
2. **cond_macd**: MACD_LINE > MACD_SIGNAL 또는 MACD_OSC > 0
3. **cond_rsi**: RSI 모멘텀
4. **cond_vol**: 거래량 급증
5. **obv_slope_ok**: OBV_SLOPE20 > 0.001
6. **tema_slope_ok**: TEMA20_SLOPE20 > 0.001 AND 주가 > TEMA20
7. **above_ok**: above_cnt >= 3

**min_signals (장세별):**
- bull: 2개
- neutral: 3개
- bear: 4개

## 예시: 점수 높지만 신호 부족

### 예시 1: 골든크로스만 충족

**상황:**
- 골든크로스: ✅ (3점)
- 거래량: ❌
- MACD: ❌
- RSI: ❌
- TEMA slope: ❌
- OBV slope: ❌
- above_cnt: ❌

**결과:**
- **점수: 3점** (높음)
- **신호: 1개** (cond_gc만)
- **min_signals=3이면 신호 부족** ❌

### 예시 2: 거래량 + MACD + RSI + TEMA slope

**상황:**
- 골든크로스: ❌
- 거래량: ✅ (2점)
- MACD: ✅ (1점)
- RSI: ✅ (1점)
- TEMA slope: ✅ (2점)
- OBV slope: ❌
- above_cnt: ❌

**결과:**
- **점수: 6점** (높음)
- **신호: 4개** (cond_vol, cond_macd, cond_rsi, tema_slope_ok)
- **하지만 trend_ok가 False면 신호 부족** ❌
  - trend_ok = TEMA20_SLOPE20 > 0 AND OBV_SLOPE20 > 0 AND above_cnt >= 3
  - OBV slope는 있지만 0.001 미만이면 trend_ok = False

### 예시 3: 골든크로스 + 거래량 + MACD + RSI

**상황:**
- 골든크로스: ✅ (3점)
- 거래량: ✅ (2점)
- MACD: ✅ (1점)
- RSI: ✅ (1점)
- TEMA slope: ❌
- OBV slope: ❌
- above_cnt: ❌

**결과:**
- **점수: 7점** (높음)
- **신호: 4개** (cond_gc, cond_vol, cond_macd, cond_rsi)
- **하지만 trend_ok가 False면 신호 부족** ❌
  - trend_ok = TEMA20_SLOPE20 > 0 AND OBV_SLOPE20 > 0 AND above_cnt >= 3
  - 모든 조건이 충족되어야 함

### 예시 4: 골든크로스 + 거래량 (가장 흔한 경우)

**상황:**
- 골든크로스: ✅ (3점)
- 거래량: ✅ (2점)
- MACD: ❌
- RSI: ❌
- TEMA slope: ❌
- OBV slope: ❌
- above_cnt: ❌

**결과:**
- **점수: 5점** (높음)
- **신호: 2개** (cond_gc, cond_vol)
- **min_signals=3이면 신호 부족** ❌

## 왜 이런 차이가 발생하는가?

### 1. 점수는 가중치 합계

- 골든크로스만 충족해도 3점
- 거래량만 충족해도 2점
- 여러 조건이 충족되면 점수는 더 높아짐

### 2. 신호는 개수 카운트

- 각 조건이 충족되었는지 여부만 확인
- 골든크로스 1개 = 신호 1개
- 거래량 1개 = 신호 1개
- 가중치와 무관하게 개수만 카운트

### 3. trend_ok 조건

**신호 충족을 위해서는:**
- 신호 개수 >= min_signals
- **AND** trend_ok = True

**trend_ok 조건:**
- TEMA20_SLOPE20 > 0
- OBV_SLOPE20 > 0
- above_cnt >= 3

**의미:**
- 신호가 많아도 trend_ok가 False면 신호 부족
- 점수는 높아도 trend_ok가 False면 신호 부족

## 실제 시나리오

### 시나리오 A: 골든크로스 + 거래량 + MACD

**점수 계산:**
- 골든크로스: 3점
- 거래량: 2점
- MACD: 1점
- **총점: 6점** ✅

**신호 계산:**
- cond_gc: ✅
- cond_vol: ✅
- cond_macd: ✅
- cond_rsi: ❌
- obv_slope_ok: ❌ (OBV_SLOPE20 = 0.0005 < 0.001)
- tema_slope_ok: ❌
- above_ok: ❌ (above_cnt = 2 < 3)
- **신호: 3개** ✅

**trend_ok:**
- TEMA20_SLOPE20 > 0: ✅
- OBV_SLOPE20 > 0: ✅ (0.0005 > 0)
- above_cnt >= 3: ❌ (2 < 3)
- **trend_ok: False** ❌

**최종 결과:**
- **점수: 6점** (높음)
- **신호: 3개** (충족)
- **하지만 trend_ok = False** → **신호 부족** ❌

## 결론

**점수가 높아도 신호가 부족한 이유:**

1. **점수는 가중치 합계**: 골든크로스(3점)만 있어도 점수는 높음
2. **신호는 개수 카운트**: 골든크로스 1개 = 신호 1개
3. **trend_ok 조건**: 신호가 많아도 trend_ok가 False면 신호 부족
4. **가중치 차이**: 골든크로스(3점)는 점수에 크게 기여하지만, 신호는 1개로만 카운트

**따라서:**
- 점수 10점 이상이어도 신호가 2개만 있으면 신호 부족
- 점수 5점이어도 신호가 3개 이상 + trend_ok = True면 신호 충족

**신호 우선 원칙의 의미:**
- 신호 충족 = 후보군 포함 (점수 무관)
- 신호 미충족 = 제외 (점수 무관)
- 점수 = 순위 매기기용

