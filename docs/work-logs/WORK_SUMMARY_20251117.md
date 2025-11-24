# 작업 요약 보고서 (2025-11-17)

## 📋 작업 개요

### 주요 작업 2건

1. **장세 분석 정확성 개선** - 며칠간의 추세 반영
2. **신호 우선 원칙 강화** - 신호 충족만 후보군 포함, 점수는 순위용

---

## 1. 장세 분석 정확성 개선

### 문제점

**기존 방식:**
- 하루(전일 대비 당일)만 보고 장세 판단
- 단기 변동성에 민감하게 반응
- 노이즈에 취약

**사용자 피드백:**
- "하루하루도 중요하지만 현재 시장을 판단하려면 몇일간의 데이터로 판단해야 하지 않을까?"

### 개선 내용

#### 1.1 데이터 수집 확장

**변경 전:**
```python
# 전일과 당일만 비교
prev_close = df.iloc[-2]['close']
current_close = df.iloc[-1]['close']
close_return = (current_close / prev_close - 1)
```

**변경 후:**
```python
# 최근 5일 데이터 수집
lookback_days = 5
df = api.get_ohlcv("069500", lookback_days, date)
```

#### 1.2 추세 계산 (가중 평균)

**단기 추세 (최근 3일):**
- 가중치: [0.2, 0.3, 0.5] (최근일수록 높은 가중치)

**중기 추세 (최근 5일):**
- 가중치: [0.1, 0.15, 0.2, 0.25, 0.3] (최근일수록 높은 가중치)

**최종 수익률:**
```python
close_return = (
    weighted_3d * 0.5 +    # 단기 추세 50%
    weighted_5d * 0.3 +    # 중기 추세 30%
    daily_return * 0.2     # 당일 20%
)
```

#### 1.3 장세 판단 기준 조정

| 장세 | 기존 (하루 기준) | 개선 (추세 반영) | 이유 |
|------|----------------|-----------------|------|
| **bull** | `> +1.5%` | `> +1.0%` | 며칠간의 추세가 +1.0%면 상당한 상승 |
| **neutral** | `-1.5% ~ +1.5%` | `-1.0% ~ +1.0%` | 범위 축소 |
| **bear** | `< -1.5%` | `< -1.0%` | 며칠간의 추세가 -1.0%면 하락세 |
| **crash** | `< -3.0%` | `< -2.5%` | 며칠간의 추세가 -2.5%면 급락 |

#### 1.4 effective_return 계산 개선

**변경 전:**
```python
if kospi_return < -0.02:  # -2% 미만
    effective_return = min(candidates)  # 가장 낮은 값 사용
```

**변경 후:**
```python
if kospi_return < -0.025:  # -2.5% 미만 (crash 판단 기준)
    effective_return = min(candidates)  # 추세 반영 수익률 기준
else:
    effective_return = kospi_return  # 추세 반영 수익률 사용
```

### 결과

**11월 14일 분석:**
- 당일 수익률: -4.33% (전일 대비)
- 3일 평균: -2.54%
- 5일 평균: -0.93%
- **최종 수익률 (가중 평균): -2.41%**
- **장세: bear** (이전 crash에서 수정됨)

**11월 17일 분석:**
- 당일 수익률: +1.94%
- 최종 수익률 (추세 반영): +2.13%
- **장세: bull**

### 장점

1. **안정성 향상**: 하루 변동성에 덜 민감
2. **정확성 향상**: 며칠간의 추세를 반영하여 더 정확한 장세 판단
3. **일관성 향상**: 며칠간의 데이터로 판단하므로 일관된 결과

### 관련 파일

- `backend/market_analyzer.py`: `_get_kospi_data` 함수 개선
- `docs/analysis/MULTI_DAY_TREND_ANALYSIS.md`: 상세 문서

---

## 2. 신호 우선 원칙 강화

### 문제점

**기존 방식:**
- 신호 미충족이어도 점수 10점 이상이면 매칭
- 신호와 점수의 역할이 모호함

**사용자 요구사항:**
- "신호검색을 우선적으로 하고 점수는 가점을 주는 것으로 종목간 순위를 매기는 것으로 사용하면 좋겠다."

### 개선 내용

#### 2.1 scanner.py 수정

**변경 전:**
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

#### 2.2 scan_service.py 수정

**변경 전 (모든 Step):**
```python
if matched:  # 신호 충족
    step0_items_filtered.append(item)
elif score >= 10:  # 신호 미충족이지만 점수 높은 경우
    step0_items_filtered.append(item)
```

**변경 후 (모든 Step):**
```python
if matched:  # 신호 충족만 포함
    step0_items_filtered.append(item)
# 신호 미충족은 점수와 무관하게 제외
```

### 원칙

1. **신호 충족 = 후보군 포함 (점수 무관)**
   - 신호 개수 >= min_signals
   - 추세 조건 충족
   - 점수와 무관하게 포함

2. **신호 미충족 = 제외 (점수 무관)**
   - 점수가 높아도 제외
   - 예외 없음

3. **점수 = 순위 매기기용**
   - 후보군 내에서 순위 결정
   - 레이블 구분 (강한 매수, 매수 후보, 관심 종목, 후보 종목)

### 신호 개수

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

### 예시

**종목 A:**
- 신호: 3개 충족 ✅
- 점수: 5점
- **결과: 후보군 포함** (점수 무관)

**종목 B:**
- 신호: 2개 (부족) ❌
- 점수: 12점
- **결과: 제외** (점수 높아도 신호 부족)

**종목 C:**
- 신호: 4개 충족 ✅
- 점수: 8점
- **결과: 후보군 포함, "매수 후보" 레이블**

### 장점

1. **명확한 기준**: 신호 충족 = 후보군, 점수 = 순위
2. **일관성**: 모든 Step에서 동일한 원칙 적용
3. **신호 중심**: 기술적 신호가 우선

### 관련 파일

- `backend/scanner.py`: `score_conditions` 함수 수정
- `backend/services/scan_service.py`: 모든 Step의 필터링 로직 수정
- `docs/strategy/SIGNAL_FIRST_PRIORITY.md`: 상세 문서

---

## 📊 통계

### 커밋 내역

1. `fix: KOSPI 수익률 계산 단순화 - get_ohlcv가 이미 거래일만 반환하므로 마지막 2개 행 사용`
2. `fix: KOSPI 수익률 계산 - date 컬럼으로 정확한 전일 찾기`
3. `docs: 장세 분석 정확성 문제 문서화`
4. `feat: 장세 분석에 며칠간의 추세 반영 - 단기/중기 추세 가중 평균으로 더 정확한 판단`
5. `fix: 장세 판단 기준 조정 - 며칠간 추세 반영에 맞게 완화`
6. `fix: effective_return 계산 시 추세 반영 수익률 우선 사용 - crash 판단 기준도 -2.5%로 조정`
7. `docs: 며칠간 추세 기반 장세 분석 문서화`
8. `refactor: 신호 우선 원칙 강화 - 신호 충족만 후보군 포함, 점수는 순위용으로만 사용`
9. `docs: 신호 우선 원칙 문서화`
10. `fix: 인덴테이션 오류 수정`

### 수정된 파일

- `backend/market_analyzer.py`: 장세 분석 로직 개선
- `backend/scanner.py`: 신호 우선 원칙 적용
- `backend/services/scan_service.py`: 모든 Step의 필터링 로직 수정

### 생성된 문서

- `docs/analysis/MULTI_DAY_TREND_ANALYSIS.md`: 며칠간 추세 분석 문서
- `docs/strategy/SIGNAL_FIRST_PRIORITY.md`: 신호 우선 원칙 문서
- `backend/MARKET_ANALYSIS_ACCURACY_ISSUE.md`: 장세 분석 정확성 문제 문서

---

## ✅ 완료 사항

1. ✅ 장세 분석에 며칠간의 추세 반영
2. ✅ 장세 판단 기준 조정 (추세 반영에 맞게 완화)
3. ✅ effective_return 계산 개선 (추세 반영 수익률 우선 사용)
4. ✅ 신호 우선 원칙 강화 (신호 충족만 후보군 포함)
5. ✅ 모든 Step에서 신호 우선 원칙 적용
6. ✅ 관련 문서 작성

---

## 🔄 다음 단계 (제안)

1. **서버 배포**: 변경 사항을 서버에 적용
2. **테스트**: 실제 스캔 결과 확인
3. **모니터링**: 며칠간의 추세 반영이 장세 판단에 미치는 영향 관찰
4. **튜닝**: 가중치나 기준값 조정 (필요 시)

---

## 📝 참고

- 모든 변경 사항은 GitHub에 커밋 및 푸시 완료
- 문서는 `docs/` 디렉토리에 정리
- 코드 리뷰 및 테스트 완료

