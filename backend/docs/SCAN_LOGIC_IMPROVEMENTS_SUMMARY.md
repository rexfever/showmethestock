# 최근 스캔 로직 개선 사항 요약

## 📅 개선 기간
2025년 11월 중순 ~ 현재

---

## 🎯 주요 개선 사항 4가지

### 1. 신호 우선 원칙 (Signal First Priority)

#### 핵심 원칙
**"신호 검색을 우선적으로 하고, 점수는 가점을 주는 것으로 종목간 순위를 매기는 것으로 사용"**

#### 변경 내용

**이전 방식:**
- 신호 미충족이어도 점수 10점 이상이면 매칭
- 신호와 점수의 역할이 모호함

**개선 후:**
- **신호 충족 = 후보군 포함 (점수 무관)**
  - 신호 개수 >= min_signals (장세별 2~4개)
  - 추세 조건 충족 (trend_ok)
  - 점수와 무관하게 후보군에 포함

- **신호 미충족 = 제외 (점수 무관)**
  - 점수가 높아도 제외
  - 예외 없음

- **점수 = 순위 매기기용**
  - 후보군 내에서 순위 결정
  - 레이블 구분 (강한 매수, 매수 후보, 관심 종목, 후보 종목)

#### 신호 개수

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

#### 코드 변경

**scanner.py:**
```python
# 이전
if signals_sufficient:
    flags["match"] = True
else:
    flags["match"] = False
    if score >= 10:  # 예외 처리
        flags["match"] = True

# 개선 후
if signals_sufficient:
    flags["match"] = True
else:
    flags["match"] = False
    # 점수가 높아도 신호 미충족이면 제외 (신호 우선 원칙)
```

**scan_service.py (모든 Step):**
```python
# 이전
if matched:  # 신호 충족
    step0_items_filtered.append(item)
elif score >= 10:  # 신호 미충족이지만 점수 높은 경우
    step0_items_filtered.append(item)

# 개선 후
if matched:  # 신호 충족만 포함
    step0_items_filtered.append(item)
# 신호 미충족은 점수와 무관하게 제외
```

#### 효과
- 명확한 기준: 신호 충족 = 후보군, 점수 = 순위
- 일관성: 모든 Step에서 동일한 원칙 적용
- 신호 중심: 기술적 신호가 우선

---

### 2. 멀티데이 트렌드 분석 (Multi-Day Trend Analysis)

#### 문제점
- 하루(전일 대비 당일)만 보고 장세 판단
- 단기 변동성에 민감하게 반응
- 노이즈에 취약

#### 개선 내용

**데이터 수집 확장:**
```python
# 최근 5일 데이터 수집
lookback_days = 5
df = api.get_ohlcv("069500", lookback_days, date)
```

**추세 계산 (가중 평균):**
- **단기 추세 (최근 3일)**: 가중치 [0.2, 0.3, 0.5] (최근일수록 높은 가중치)
- **중기 추세 (최근 5일)**: 가중치 [0.1, 0.15, 0.2, 0.25, 0.3]
- **당일 수익률**: 전일 대비 당일 수익률

**최종 수익률 계산:**
```python
close_return = (
    weighted_3d * 0.5 +    # 단기 추세 50%
    weighted_5d * 0.3 +    # 중기 추세 30%
    daily_return * 0.2     # 당일 20%
)
```

**장세 판단 기준 조정:**

| 장세 | 기존 (하루 기준) | 개선 (추세 반영) | 이유 |
|------|----------------|-----------------|------|
| **bull** | `> +1.5%` | `> +1.0%` | 며칠간의 추세가 +1.0%면 상당한 상승 |
| **neutral** | `-1.5% ~ +1.5%` | `-1.0% ~ +1.0%` | 범위 축소 |
| **bear** | `< -1.5%` | `< -1.0%` | 며칠간의 추세가 -1.0%면 하락세 |
| **crash** | `< -3.0%` | `< -2.5%` | 며칠간의 추세가 -2.5%면 급락 |

#### 장기 추세 vs 단기 급락 구분

**시나리오: 10일간 상승 후 당일 -4% 급락**

**조정 판단 로직:**
```python
# 장기 추세 (10일 평균, 당일 제외)
long_term_trend = sum(returns_10d) / len(returns_10d)
up_days_ratio = sum(1 for r in returns_10d if r > 0) / len(returns_10d)

# 조정 조건: 장기 상승 추세 + 단기 급락
is_adjustment = (
    long_term_trend > 0.005 and      # 장기 추세 상승 (+0.5% 이상)
    up_days_ratio >= 0.7 and          # 상승일 비율 70% 이상
    daily_return < -0.03             # 당일 급락 -3% 이상
)

if is_adjustment:
    # 조정으로 판단: 장기 추세 70% + 단기 급락 30%
    close_return = long_term_trend * 0.7 + daily_return * 0.3
```

#### 효과
- 안정성 향상: 하루 변동성에 덜 민감
- 정확성 향상: 며칠간의 추세를 반영하여 더 정확한 장세 판단
- 일관성 향상: 며칠간의 데이터로 판단하므로 일관된 결과

---

### 3. 점수 구성 기반 전략 분류 (Strategy by Score Composition)

#### 문제점
- 점수 합계만으로 전략 구분
- 점수 합계가 같아도 구성이 다르면 전략이 달라질 수 있음

#### 개선 내용

**점수 구성 분석:**

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

**전략 판단 로직:**
```python
def determine_trading_strategy(flags, adjusted_score):
    """점수 구성에 따라 매매 전략 결정"""
    
    # 모멘텀 지표 점수
    momentum_score = sum([
        3 if flags.get("cross") else 0,
        2 if flags.get("vol_expand") else 0,
        1 if flags.get("macd_ok") else 0,
        1 if flags.get("rsi_ok") else 0
    ])
    
    # 추세 지표 점수
    trend_score = sum([
        2 if flags.get("tema_slope_ok") else 0,
        2 if flags.get("obv_slope_ok") else 0,
        2 if flags.get("above_cnt5_ok") else 0,
        2 if flags.get("dema_slope_ok") else 0
    ])
    
    # 전략 판단
    if adjusted_score >= 10:
        # 스윙: 골든크로스 + 거래량 + 모멘텀 지표 중심
        if flags.get("cross") and flags.get("vol_expand") and momentum_score >= 6:
            return "스윙", 0.05, -0.05, "3~10일"
        # 포지션: 추세 지표 중심
        elif trend_score >= 5:
            return "포지션", 0.10, -0.07, "2주~3개월"
        else:
            return "스윙", 0.05, -0.05, "3~10일"
    
    elif adjusted_score >= 8:
        # 포지션: 골든크로스 + 추세 지표
        if flags.get("cross") and trend_score >= 4:
            return "포지션", 0.10, -0.07, "2주~3개월"
        # 스윙: 거래량 + 모멘텀
        elif flags.get("vol_expand") and momentum_score >= 5:
            return "스윙", 0.05, -0.05, "3~10일"
        else:
            return "포지션", 0.10, -0.07, "2주~3개월"
    
    elif adjusted_score >= 6:
        # 장기: 기본 신호 + 추세 지표
        if trend_score >= 2:
            return "장기", 0.15, -0.10, "3개월 이상"
        else:
            return "관찰", None, None, None
    
    else:
        return "관찰", None, None, None
```

#### 전략별 특징

**스윙 트레이딩:**
- 골든크로스 + 거래량 + 모멘텀 지표 중심
- 빠른 상승 가능성
- 목표: +5%, 손절: -5%, 보유: 3~10일

**포지션 트레이딩:**
- 골든크로스 + 추세 지표 또는 추세 지표 중심
- 안정적인 상승 추세
- 목표: +10%, 손절: -7%, 보유: 2주~3개월

**장기 투자:**
- 기본 신호 + 추세 지표
- 안정적인 기업
- 목표: +15%, 손절: -10%, 보유: 3개월 이상

#### 효과
- 정확한 전략 분류: 점수 구성에 따라 적합한 전략 제안
- 유연성: 같은 점수라도 구성이 다르면 다른 전략
- 명확성: 모멘텀 vs 추세 지표 구분

---

### 4. RSI 동적 조정 및 필터 개선

#### RSI 동적 조정

**이전:**
- RSI 임계값 고정 (35)
- 시장 상황과 무관하게 동일한 기준 적용

**개선 후:**
- 시장 상황에 따라 RSI 임계값 동적 조정
- `market_condition.rsi_threshold` 사용
- RSI 상한선도 동적 조정: `rsi_threshold + 25.0`

**적용 위치:**
- `match_stats`: RSI 모멘텀 조건
- `score_conditions`: RSI 모멘텀 조건
- `scan_one_symbol`: RSI 상한선 필터

#### 갭/이격 필터 개선

**갭 필터 (Gap):**
- TEMA20과 DEMA10의 거리 (추세 강도)
- 시장 상황에 따라 차별화:
  - bull: 3.0%
  - neutral: 2.5%
  - bear: 2.0%

**이격 필터 (Extension):**
- 현재 가격과 TEMA20의 거리 (과매수/과매도)
- 시장 상황과 무관하게 통일: 2.5%

**이유:**
- 갭: 추세 강도는 시장 상황에 따라 다름
- 이격: 과매수/과매도는 시장 상황과 무관하게 일정 기준 필요

---

## 📊 개선 효과

### 예상 효과

1. **신호 우선 원칙**
   - 더 확실한 신호만 선택
   - 품질 향상 기대

2. **멀티데이 트렌드 분석**
   - 더 안정적인 장세 판단
   - 노이즈 제거

3. **점수 구성 기반 전략 분류**
   - 더 정확한 전략 제안
   - 투자자 성향에 맞는 추천

4. **RSI 동적 조정**
   - 시장 상황에 맞는 필터링
   - 더 많은 적합한 종목 발견

---

## 📁 관련 파일

### 코드 파일
- `backend/scanner.py`: 신호 우선 원칙, 점수 구성 기반 전략 분류
- `backend/services/scan_service.py`: 모든 Step의 필터링 로직
- `backend/market_analyzer.py`: 멀티데이 트렌드 분석

### 문서 파일
- `backend/docs/strategy/SIGNAL_FIRST_PRIORITY.md`: 신호 우선 원칙 상세
- `backend/docs/analysis/MULTI_DAY_TREND_ANALYSIS.md`: 멀티데이 트렌드 분석 상세
- `backend/docs/strategy/STRATEGY_BY_SCORE_COMPOSITION.md`: 전략 분류 상세
- `backend/docs/work-logs/WORK_SUMMARY_20251117.md`: 작업 요약

---

## ✅ 완료 사항

1. ✅ 신호 우선 원칙 강화
2. ✅ 멀티데이 트렌드 분석 구현
3. ✅ 장기 추세 vs 단기 급락 구분
4. ✅ 점수 구성 기반 전략 분류
5. ✅ RSI 동적 조정
6. ✅ 갭/이격 필터 개선
7. ✅ 모든 Step에서 신호 우선 원칙 적용
8. ✅ 관련 문서 작성

---

## 🔄 다음 단계 (제안)

1. **서버 배포**: 변경 사항을 서버에 적용
2. **테스트**: 실제 스캔 결과 확인
3. **모니터링**: 며칠간의 추세 반영이 장세 판단에 미치는 영향 관찰
4. **튜닝**: 가중치나 기준값 조정 (필요 시)
5. **성과 분석**: 개선 전후 비교

---

## 📝 참고

- 모든 변경 사항은 GitHub에 커밋 및 푸시 완료
- 문서는 `backend/docs/` 디렉토리에 정리
- 코드 리뷰 및 테스트 완료

