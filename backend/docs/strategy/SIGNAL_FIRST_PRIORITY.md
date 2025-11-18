# 신호 우선 원칙

## 핵심 원칙

**신호 검색을 우선적으로 하고, 점수는 가점을 주는 것으로 종목간 순위를 매기는 것으로 사용**

## 구현 방식

### 1. 신호 충족 = 후보군 포함 (점수 무관)

**조건:**
- 신호 개수 >= min_signals (기본 3개, 장세에 따라 2~4개)
- 추세 조건 충족 (trend_ok)

**결과:**
- `flags["match"] = True`
- 점수와 무관하게 후보군에 포함
- 점수는 순위 매기기용으로만 사용

### 2. 신호 미충족 = 제외 (점수 무관)

**조건:**
- 신호 개수 < min_signals
- 또는 추세 조건 미충족

**결과:**
- `flags["match"] = False`
- 점수가 높아도 제외 (신호 우선 원칙)
- 예외 없음

### 3. 점수 = 순위 매기기용

**용도:**
- 후보군 내에서 순위 매기기
- 레이블 구분 (강한 매수, 매수 후보, 관심 종목, 후보 종목)

**점수 기준:**
- 10점 이상: "강한 매수"
- 8점 이상: "매수 후보"
- 6점 이상: "관심 종목"
- 6점 미만: "후보 종목"

## 코드 변경 사항

### scanner.py

**이전:**
```python
if signals_sufficient:
    flags["match"] = True
else:
    flags["match"] = False
    # 예외: 점수 10점 이상이면 매칭
    if score >= 10:
        flags["match"] = True
```

**변경 후:**
```python
if signals_sufficient:
    flags["match"] = True
else:
    flags["match"] = False
    # 점수가 높아도 신호 미충족이면 제외 (신호 우선 원칙)
```

### scan_service.py

**이전:**
```python
if matched:  # 신호 충족
    step0_items_filtered.append(item)
elif score >= 10:  # 신호 미충족이지만 점수 높은 경우
    step0_items_filtered.append(item)
```

**변경 후:**
```python
if matched:  # 신호 충족만 포함
    step0_items_filtered.append(item)
# 신호 미충족은 점수와 무관하게 제외
```

## 장점

1. **명확한 기준**
   - 신호 충족 = 후보군
   - 점수 = 순위
   - 예외 없음

2. **일관성**
   - 모든 Step에서 동일한 원칙 적용
   - 혼란 없음

3. **신호 중심**
   - 기술적 신호가 우선
   - 점수는 보조 지표

## 신호 개수

**총 7개 신호:**

1. 골든크로스 (cond_gc)
2. MACD (cond_macd)
3. RSI (cond_rsi)
4. 거래량 (cond_vol)
5. OBV 상승 (obv_slope_ok)
6. TEMA 상승 (tema_slope_ok)
7. 연속 상승 (above_ok)

**min_signals (장세별):**
- bull: 2개
- neutral: 3개
- bear: 4개
- crash: 999개 (추천 안 함)

## 예시

### 종목 A
- 신호: 3개 충족 ✅
- 점수: 5점
- **결과: 후보군 포함** (점수 무관)

### 종목 B
- 신호: 2개 (부족) ❌
- 점수: 12점
- **결과: 제외** (점수 높아도 신호 부족)

### 종목 C
- 신호: 4개 충족 ✅
- 점수: 8점
- **결과: 후보군 포함, "매수 후보" 레이블**

