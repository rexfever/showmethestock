# 점수 구성에 따른 매매 전략 분류

## 문제점

**현재 구현:**
- 점수 합계만으로 전략 구분 (10점 이상 = 스윙, 8~9점 = 포지션, 6~7점 = 장기)
- 점수 합계가 같아도 구성이 다르면 전략이 달라질 수 있음

**예시:**
- 골든크로스(3) + 거래량(2) + MACD(1) + RSI(1) + TEMA(2) = 9점 → 포지션
- 골든크로스(3) + 거래량(2) + OBV(2) + 연속상승(2) = 9점 → 포지션
- 하지만 구성이 다르므로 전략이 달라질 수 있음

## 개선 방안: 점수 구성 기반 전략 분류

### 1. 스윙 트레이딩 특징

**핵심 요소:**
- 골든크로스 (3점) - 필수
- 거래량 급증 (2점) - 필수
- 모멘텀 지표 (MACD, RSI) - 선호
- 빠른 상승 가능성

**점수 구성 패턴:**
```
골든크로스(3) + 거래량(2) + 모멘텀(2점 이상) = 7점 이상
→ 스윙 전략
```

### 2. 포지션 트레이딩 특징

**핵심 요소:**
- 골든크로스 (3점) - 필수 또는 선택
- 추세 지표 (TEMA, OBV, 연속상승) - 필수
- 안정적인 상승 추세

**점수 구성 패턴:**
```
골든크로스(3) + 추세지표(5점 이상) = 8점 이상
또는
거래량(2) + 추세지표(6점 이상) = 8점 이상
→ 포지션 전략
```

### 3. 장기 투자 특징

**핵심 요소:**
- 기본 신호 충족 (골든크로스 또는 거래량)
- 추세 지표 일부 충족
- 안정적인 기업

**점수 구성 패턴:**
```
기본 신호(3~5점) + 추세지표(1~3점) = 6~7점
→ 장기 전략
```

## 점수 구성 분석

### 항목 분류

**모멘텀 지표 (단기):**
- 골든크로스 (cross): 3점
- 거래량 (volume): 2점
- MACD: 1점
- RSI: 1점
- **합계: 7점**

**추세 지표 (중장기):**
- TEMA slope: 2점
- OBV slope: 2점
- 연속 상승 (above_cnt5): 2점
- DEMA slope: 2점
- **합계: 8점**

### 전략 판단 로직

```python
def determine_strategy(flags, score):
    """점수 구성에 따라 전략 결정"""
    
    # 모멘텀 지표 점수
    momentum_score = 0
    if flags.get("cross"):
        momentum_score += 3
    if flags.get("vol_expand"):
        momentum_score += 2
    if flags.get("macd_ok"):
        momentum_score += 1
    if flags.get("rsi_ok"):
        momentum_score += 1
    
    # 추세 지표 점수
    trend_score = 0
    if flags.get("tema_slope_ok"):
        trend_score += 2
    if flags.get("obv_slope_ok"):
        trend_score += 2
    if flags.get("above_cnt5_ok"):
        trend_score += 2
    if flags.get("dema_slope_ok"):
        trend_score += 2
    
    # 전략 판단
    if score >= 10:
        # 스윙: 골든크로스 + 거래량 + 모멘텀 지표
        if flags.get("cross") and flags.get("vol_expand") and momentum_score >= 6:
            return "스윙"
        # 포지션: 추세 지표 중심
        elif trend_score >= 5:
            return "포지션"
        else:
            return "스윙"  # 기본값
    
    elif score >= 8:
        # 포지션: 골든크로스 + 추세 지표
        if flags.get("cross") and trend_score >= 4:
            return "포지션"
        # 스윙: 거래량 + 모멘텀
        elif flags.get("vol_expand") and momentum_score >= 5:
            return "스윙"
        else:
            return "포지션"  # 기본값
    
    elif score >= 6:
        # 장기: 기본 신호 + 추세 지표
        if trend_score >= 2:
            return "장기"
        else:
            return "관찰"
    
    else:
        return "관찰"
```

## 구체적인 예시

### 예시 1: 스윙 트레이딩

**점수 구성:**
- 골든크로스: ✅ (3점)
- 거래량: ✅ (2점)
- MACD: ✅ (1점)
- RSI: ✅ (1점)
- TEMA slope: ✅ (2점)
- **총점: 9점**

**분석:**
- 모멘텀 점수: 7점 (골든크로스 + 거래량 + MACD + RSI)
- 추세 점수: 2점 (TEMA slope)
- **전략: 스윙** (모멘텀 중심)

### 예시 2: 포지션 트레이딩

**점수 구성:**
- 골든크로스: ✅ (3점)
- 거래량: ❌
- MACD: ❌
- RSI: ❌
- TEMA slope: ✅ (2점)
- OBV slope: ✅ (2점)
- 연속 상승: ✅ (2점)
- **총점: 9점**

**분석:**
- 모멘텀 점수: 3점 (골든크로스만)
- 추세 점수: 6점 (TEMA + OBV + 연속상승)
- **전략: 포지션** (추세 중심)

### 예시 3: 장기 투자

**점수 구성:**
- 골든크로스: ❌
- 거래량: ✅ (2점)
- MACD: ✅ (1점)
- RSI: ✅ (1점)
- TEMA slope: ✅ (2점)
- **총점: 6점**

**분석:**
- 모멘텀 점수: 4점 (거래량 + MACD + RSI)
- 추세 점수: 2점 (TEMA slope)
- **전략: 장기** (기본 신호 + 추세)

## 개선된 구현

### 코드 수정

```python
def determine_trading_strategy(flags, adjusted_score):
    """점수 구성에 따라 매매 전략 결정"""
    
    # 모멘텀 지표 점수
    momentum_score = 0
    if flags.get("cross"):
        momentum_score += 3
    if flags.get("vol_expand"):
        momentum_score += 2
    if flags.get("macd_ok"):
        momentum_score += 1
    if flags.get("rsi_ok"):
        momentum_score += 1
    
    # 추세 지표 점수
    trend_score = 0
    if flags.get("tema_slope_ok"):
        trend_score += 2
    if flags.get("obv_slope_ok"):
        trend_score += 2
    if flags.get("above_cnt5_ok"):
        trend_score += 2
    if flags.get("dema_slope_ok"):
        trend_score += 2
    
    # 전략 판단
    if adjusted_score >= 10:
        # 스윙: 골든크로스 + 거래량 + 모멘텀 지표 중심
        if flags.get("cross") and flags.get("vol_expand") and momentum_score >= 6:
            return "스윙", 0.05, -0.05, "3~10일"
        # 포지션: 추세 지표 중심
        elif trend_score >= 5:
            return "포지션", 0.10, -0.07, "2주~3개월"
        else:
            return "스윙", 0.05, -0.05, "3~10일"  # 기본값
    
    elif adjusted_score >= 8:
        # 포지션: 골든크로스 + 추세 지표
        if flags.get("cross") and trend_score >= 4:
            return "포지션", 0.10, -0.07, "2주~3개월"
        # 스윙: 거래량 + 모멘텀
        elif flags.get("vol_expand") and momentum_score >= 5:
            return "스윙", 0.05, -0.05, "3~10일"
        else:
            return "포지션", 0.10, -0.07, "2주~3개월"  # 기본값
    
    elif adjusted_score >= 6:
        # 장기: 기본 신호 + 추세 지표
        if trend_score >= 2:
            return "장기", 0.15, -0.10, "3개월 이상"
        else:
            return "관찰", None, None, None
    
    else:
        return "관찰", None, None, None
```

## 장점

1. **정확한 전략 분류**: 점수 구성에 따라 적합한 전략 제안
2. **유연성**: 같은 점수라도 구성이 다르면 다른 전략
3. **명확성**: 모멘텀 vs 추세 지표 구분

## 요약

**핵심:**
- 점수 합계가 아니라 **점수 구성**에 따라 전략 결정
- 모멘텀 지표 중심 = 스윙
- 추세 지표 중심 = 포지션
- 기본 신호 + 추세 = 장기

**구현:**
- 모멘텀 점수와 추세 점수를 별도로 계산
- 점수 범위와 구성 패턴을 조합하여 전략 결정

