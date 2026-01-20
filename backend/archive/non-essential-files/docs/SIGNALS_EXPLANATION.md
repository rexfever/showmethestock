# 신호 개수 및 종류 설명

## 총 신호 개수: 4개

### 1. 골든크로스 (cond_gc)

**조건:**
```python
cond_gc = (교차 발생 OR TEMA20 > DEMA10) AND TEMA20_SLOPE20 > 0
```

**의미:**
- 최근 5일 내 골든크로스 발생 또는
- 현재 TEMA20이 DEMA10 위에 있고
- TEMA20이 상승 추세 (SLOPE20 > 0)

**목적:** 가격 상승 추세 확인

### 2. MACD (cond_macd)

**조건:**
```python
cond_macd = (MACD_LINE > MACD_SIGNAL) OR (MACD_OSC > 0)
```

**의미:**
- MACD 라인이 시그널 라인 위에 있거나
- MACD 오실레이터가 양수

**목적:** 모멘텀 상승 확인

### 3. RSI (cond_rsi)

**조건:**
```python
cond_rsi = (RSI_TEMA > RSI_DEMA) OR (|RSI_TEMA - RSI_DEMA| < 3 AND RSI_TEMA > rsi_threshold)
```

**의미:**
- RSI_TEMA가 RSI_DEMA 위에 있거나
- RSI가 수렴 후 상승 (차이 < 3 AND RSI_TEMA > 임계값)

**목적:** 모멘텀 상승 확인

### 4. 거래량 (cond_vol)

**조건:**
```python
cond_vol = volume >= vol_ma5_mult * VOL_MA5
```

**의미:**
- 당일 거래량이 최근 5일 평균 거래량의 배수 이상

**목적:** 거래량 급증 확인 (자금 유입)

## 신호 개수 계산

```python
signals_true = sum([
    bool(cond_gc),    # 골든크로스
    bool(cond_macd),  # MACD
    bool(cond_rsi),   # RSI
    bool(cond_vol)    # 거래량
])
```

**최대:** 4개
**최소:** 0개

## 최소 신호 개수 (min_signals)

### 현재 설정

- **기본값**: 3개
- **동적 조정**: 시장 상황에 따라 변경
  - 강세장: 2개
  - 중립장: 3개
  - 약세장: 4개

### 조건

```python
if signals_true < min_signals:
    return False  # 매칭 실패
```

**의미:**
- `min_signals`개 이상의 신호가 필요
- 중립장에서는 3개 이상 필요

## 11월 17일 스캔 현황

### 신호 개수 분포 (예상)

- **0개**: 소수
- **1개**: 소수
- **2개**: 대부분 (문제!)
- **3개**: 소수
- **4개**: 매우 소수

### 문제점

- **대부분 종목이 2개만 충족**
- **min_signals: 3개 필요**
- **→ 대부분 종목이 "신호 부족"으로 차단**

## 추세 조건 (trend_ok)

**중요:** 신호 개수 외에도 추세 조건이 필요합니다.

```python
trend_ok = (
    TEMA20_SLOPE20 > 0  # 가격 상승
    AND OBV_SLOPE20 > 0  # 자금 유입
    AND above_cnt >= 3   # 연속 상승
)
```

**의미:**
- 신호 개수가 충분해도 `trend_ok`가 False면 실패
- 신호와 추세 조건 모두 충족해야 함

## 최종 매칭 조건

```python
if signals_true >= min_signals AND trend_ok:
    matched = True  # 매칭 성공
else:
    matched = False  # 매칭 실패
```

**필요 조건:**
1. 신호 개수: `min_signals`개 이상 (중립장: 3개)
2. 추세 조건: `trend_ok = True`

## 요약

- **총 신호: 4개** (골든크로스, MACD, RSI, 거래량)
- **최소 필요: 3개** (중립장 기준)
- **현재 문제: 대부분 종목이 2개만 충족**
- **해결 방안: min_signals를 3 → 2로 완화**

