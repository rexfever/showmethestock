# 점수 산정 기준

## 📊 점수 계산 방식

점수는 각 조건별 가중치를 합산하여 계산됩니다.

## 1. 기본 점수 가중치

| 항목 | 가중치 | 조건 | 설명 |
|------|--------|------|------|
| **cross** (골든크로스) | **3점** | TEMA20 > DEMA10 교차 | 전일 TEMA20 ≤ DEMA10, 당일 TEMA20 > DEMA10 |
| **volume** (거래량) | **2점** | 거래량 급증 | 당일 거래량 >= MA5 × 배수 AND 당일 거래량 >= MA20 × 배수 |
| **macd** | **1점** | MACD 상승 신호 | MACD 골든크로스 OR MACD_LINE > MACD_SIGNAL OR MACD_OSC > 임계값 |
| **rsi** | **1점** | RSI 모멘텀 | RSI_TEMA > RSI_DEMA OR (수렴 후 상승) |
| **tema_slope** | **2점** | TEMA20 상승 추세 | TEMA20_SLOPE20 > 0.001 AND 주가 > TEMA20 |
| **obv_slope** | **2점** | OBV 상승 (자금 유입) | OBV_SLOPE20 > 0.001 |
| **above_cnt5** | **2점** | 연속 상승 | 최근 5일 중 3일 이상 TEMA20 > DEMA10 |
| **dema_slope** | **2점** | DEMA10 상승 추세 | DEMA10_SLOPE20 > 0 AND 주가 > DEMA10 (선택사항) |

**최대 가능 점수**: 약 14점 (dema_slope 포함 시 16점)

## 2. 점수 계산 로직

### 2.1 기본 점수 계산

```python
score = 0

# 각 조건이 충족되면 해당 가중치만큼 점수 추가
if cross:
    score += 3  # 골든크로스
if volx:
    score += 2  # 거래량
if macd_ok:
    score += 1  # MACD
if rsi_ok:
    score += 1  # RSI
if tema_slope_ok:
    score += 2  # TEMA slope
if obv_slope_ok:
    score += 2  # OBV slope
if above_ok:
    score += 2  # 연속 상승
if dema_slope_ok:  # 선택사항
    score += 2  # DEMA slope
```

### 2.2 신호 보너스

**신호 충족 시 추가 보너스:**

```python
if signals_sufficient:  # 신호 개수 >= min_signals
    # 추가 신호당 1점 보너스
    signal_bonus = max(0, (signals_true - min_signals) * 1)
    adjusted_score = score + signal_bonus
```

**예시:**
- 신호 3개 충족 (min_signals=3): 보너스 0점
- 신호 4개 충족 (min_signals=3): 보너스 1점
- 신호 5개 충족 (min_signals=3): 보너스 2점

### 2.3 위험도 점수 차감

**위험도 점수 계산:**

| 위험 요소 | 점수 | 조건 |
|----------|------|------|
| **RSI 과매수** | +2점 | RSI_TEMA > 80 |
| **거래량 급증** | +2점 | 거래량 > MA5 × 3.0 |
| **모멘텀 지속성 부족** | +1점 | MACD 상승 기간 < 3일 |
| **가격 급등 후 조정** | +1점 | 최근 5일 중 4일 이상 상승 |

**위험도 점수 차감:**

```python
if risk_score > 0:
    adjusted_score = max(0, score - risk_score)
```

**예시:**
- 원래 점수: 8점
- 위험도 점수: 2점 (RSI 과매수)
- 최종 점수: 6점 (8 - 2)

**위험도 임계값:**
- risk_score >= 3이면 종목 제외 (점수 0점 반환)

## 3. 최종 점수 계산

### 3.1 계산 순서

1. **기본 점수 계산**: 각 조건별 가중치 합산
2. **신호 보너스 추가**: 신호 충족 시 추가 보너스
3. **위험도 점수 차감**: 위험도 점수만큼 차감

### 3.2 최종 점수 공식

```python
# 1. 기본 점수
base_score = sum(조건별 가중치)

# 2. 신호 보너스
if signals_sufficient:
    signal_bonus = (signals_true - min_signals) * 1
    score_with_bonus = base_score + signal_bonus
else:
    score_with_bonus = base_score

# 3. 위험도 차감
if risk_score > 0:
    final_score = max(0, score_with_bonus - risk_score)
else:
    final_score = score_with_bonus
```

## 4. 점수 기준 (레이블 구분)

| 점수 범위 | 레이블 | 설명 |
|----------|--------|------|
| **10점 이상** | "강한 매수" | 매우 강한 매수 신호 |
| **8점 이상** | "매수 후보" | 강한 매수 신호 |
| **6점 이상** | "관심 종목" | 매수 고려 대상 |
| **6점 미만** | "후보 종목" | 약한 매수 신호 |

**참고:** 신호 충족 시에만 레이블이 적용됩니다. 신호 미충족이면 "신호부족(N/M)" 레이블이 표시됩니다.

## 5. 점수 계산 예시

### 예시 1: 완벽한 조건

**조건:**
- 골든크로스: ✅ (3점)
- 거래량: ✅ (2점)
- MACD: ✅ (1점)
- RSI: ✅ (1점)
- TEMA slope: ✅ (2점)
- OBV slope: ✅ (2점)
- above_cnt: ✅ (2점)

**계산:**
- 기본 점수: 3 + 2 + 1 + 1 + 2 + 2 + 2 = **13점**
- 신호: 7개 충족 (min_signals=3)
- 신호 보너스: (7 - 3) × 1 = **4점**
- 위험도: 0점
- **최종 점수: 17점** → "강한 매수"

### 예시 2: 일반적인 조건

**조건:**
- 골든크로스: ✅ (3점)
- 거래량: ✅ (2점)
- MACD: ✅ (1점)
- RSI: ❌
- TEMA slope: ❌
- OBV slope: ✅ (2점)
- above_cnt: ❌

**계산:**
- 기본 점수: 3 + 2 + 1 + 2 = **8점**
- 신호: 4개 충족 (min_signals=3)
- 신호 보너스: (4 - 3) × 1 = **1점**
- 위험도: 0점
- **최종 점수: 9점** → "매수 후보"

### 예시 3: 위험도 차감

**조건:**
- 골든크로스: ✅ (3점)
- 거래량: ✅ (2점)
- MACD: ✅ (1점)
- RSI: ✅ (1점)
- TEMA slope: ✅ (2점)
- OBV slope: ❌
- above_cnt: ❌
- **위험도: RSI 과매수 (+2점)**

**계산:**
- 기본 점수: 3 + 2 + 1 + 1 + 2 = **9점**
- 신호: 4개 충족 (min_signals=3)
- 신호 보너스: (4 - 3) × 1 = **1점**
- 위험도 차감: 2점
- **최종 점수: 8점** (9 + 1 - 2) → "매수 후보"

### 예시 4: 위험도로 제외

**조건:**
- 골든크로스: ✅ (3점)
- 거래량: ✅ (2점)
- MACD: ✅ (1점)
- **위험도: RSI 과매수 (+2점) + 거래량 급증 (+2점) = 4점**

**계산:**
- 기본 점수: 3 + 2 + 1 = **6점**
- 위험도: 4점 (임계값 3점 초과)
- **결과: 제외** (점수 0점 반환, "위험종목" 레이블)

## 6. 환경 변수 설정

점수 가중치는 환경 변수로 조정 가능합니다:

```bash
SCORE_W_CROSS=3          # 골든크로스 가중치
SCORE_W_VOL=2            # 거래량 가중치
SCORE_W_MACD=1           # MACD 가중치
SCORE_W_RSI=1            # RSI 가중치
SCORE_W_TEMA_SLOPE=2     # TEMA slope 가중치
SCORE_W_DEMA_SLOPE=2     # DEMA slope 가중치
SCORE_W_OBV_SLOPE=2      # OBV slope 가중치
SCORE_W_ABOVE_CNT=2      # 연속 상승 가중치

SCORE_LEVEL_STRONG=10    # "강한 매수" 기준
SCORE_LEVEL_WATCH=8       # "매수 후보" 기준

RISK_SCORE_THRESHOLD=3   # 위험도 임계값 (이상이면 제외)
VOL_SPIKE_THRESHOLD=3.0  # 거래량 급증 기준 (배수)
MOMENTUM_DURATION_MIN=3   # 모멘텀 지속성 최소 기간 (일)
```

## 7. 점수 vs 신호

**중요:** 점수와 신호는 별개입니다.

- **점수**: 각 조건별 가중치 합계 (가중 평균)
- **신호**: 각 조건이 충족되었는지 여부를 카운트 (개수)

**예시:**
- 골든크로스만 충족: **점수 3점**, **신호 1개**
- 거래량만 충족: **점수 2점**, **신호 1개**
- 골든크로스 + 거래량: **점수 5점**, **신호 2개**

**신호 우선 원칙:**
- 신호 충족 = 후보군 포함 (점수 무관)
- 신호 미충족 = 제외 (점수 무관)
- 점수 = 순위 매기기용

## 8. 요약

1. **기본 점수**: 각 조건별 가중치 합산 (최대 14점)
2. **신호 보너스**: 신호 충족 시 추가 보너스 (추가 신호당 1점)
3. **위험도 차감**: 위험도 점수만큼 차감 (최소 0점)
4. **위험도 임계값**: 3점 이상이면 제외
5. **최종 점수**: 기본 점수 + 신호 보너스 - 위험도 점수

**점수는 순위 매기기용으로만 사용되며, 신호 충족 여부가 우선입니다.**

