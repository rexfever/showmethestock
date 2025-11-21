# 스캐너 V1 vs V2 비교 가이드

## 개요

스캐너 V2는 V1의 개선된 버전으로, 핵심 알고리즘과 구조를 개선하여 더 정확하고 안정적인 스캔 결과를 제공합니다.

---

## 📊 주요 차이점 요약

| 항목 | V1 | V2 |
|------|----|----|
| **신호 처리** | 신호 미충족이어도 점수 10점 이상이면 매칭 | 신호 충족만 후보군 포함, 점수는 순위용 |
| **장세 분석** | 하루(전일 대비 당일)만 분석 | 멀티데이 트렌드 분석 (5일 가중 평균) |
| **전략 분류** | 점수 합계만으로 전략 결정 | 점수 구성(모멘텀/추세) 기반 전략 분류 |
| **RSI 필터** | 고정 임계값 (35) | 시장 상황별 동적 조정 |
| **구조** | 단일 파일 (scanner.py) | 모듈화된 구조 (scanner_v2/) |
| **설정 관리** | .env 파일만 사용 | DB 우선, .env fallback |

---

## 🔍 상세 비교

### 1. 신호 처리 방식

#### V1: 점수 우선 원칙

```python
# V1 로직 (scanner.py)
if signals_sufficient:
    flags["match"] = True
else:
    flags["match"] = False
    if score >= 10:  # ⚠️ 예외 처리: 점수가 높으면 매칭
        flags["match"] = True
```

**문제점:**
- 신호 미충족이어도 점수가 높으면 매칭
- 신호와 점수의 역할이 모호함
- 일관성 부족

#### V2: 신호 우선 원칙

```python
# V2 로직 (scanner_v2/core/filter_engine.py)
if signals_sufficient:
    flags["match"] = True
else:
    flags["match"] = False
    # 점수가 높아도 신호 미충족이면 제외 (신호 우선 원칙)
```

**개선점:**
- 신호 충족 = 후보군 포함 (점수 무관)
- 신호 미충족 = 제외 (점수 무관)
- 점수 = 후보군 내 순위 결정용
- 명확하고 일관된 기준

**예시:**
```
종목 A: 신호 2개, 점수 12점 → V1: 매칭 ✅, V2: 제외 ❌ (신호 부족)
종목 B: 신호 4개, 점수 8점  → V1: 매칭 ✅, V2: 매칭 ✅ (신호 충족)
```

---

### 2. 장세 분석 방식

#### V1: 단일 날짜 분석

```python
# V1 로직 (market_analyzer.py - 이전)
kospi_return = (today_close - yesterday_close) / yesterday_close

# 장세 판단
if kospi_return > 0.015:      # +1.5%
    market_sentiment = 'bull'
elif kospi_return < -0.015:   # -1.5%
    market_sentiment = 'bear'
```

**문제점:**
- 하루 변동성에 과민 반응
- 노이즈에 취약
- 단기 변동으로 인한 오판

#### V2: 멀티데이 트렌드 분석

```python
# V2 로직 (market_analyzer.py - 개선)
# 최근 5일 데이터 수집
lookback_days = 5
df = api.get_ohlcv("069500", lookback_days, date)

# 가중 평균 계산
weighted_3d = sum(returns_3d * weights_3d)  # [0.2, 0.3, 0.5]
weighted_5d = sum(returns_5d * weights_5d)  # [0.1, 0.15, 0.2, 0.25, 0.3]

# 최종 수익률 (가중 평균)
close_return = (
    weighted_3d * 0.5 +    # 단기 추세 50%
    weighted_5d * 0.3 +    # 중기 추세 30%
    daily_return * 0.2     # 당일 20%
)

# 장세 판단 (완화된 기준)
if close_return > 0.010:      # +1.0% (기존 +1.5%에서 완화)
    market_sentiment = 'bull'
elif close_return < -0.010:  # -1.0% (기존 -1.5%에서 완화)
    market_sentiment = 'bear'
```

**개선점:**
- 며칠간의 추세를 반영하여 안정성 향상
- 노이즈 제거
- 장기 추세 vs 단기 급락 구분

**예시:**
```
시나리오: 10일간 +0.3%씩 상승 후 당일 -4% 급락

V1 판단: bear (당일 -4%만 보고)
V2 판단: neutral 또는 bull (장기 추세 반영)
```

---

### 3. 전략 분류 방식

#### V1: 점수 합계만으로 전략 결정

```python
# V1 로직 (scanner.py)
if adjusted_score >= 10:
    strategy = "스윙"
elif adjusted_score >= 8:
    strategy = "포지션"
elif adjusted_score >= 6:
    strategy = "장기"
else:
    strategy = "관찰"
```

**문제점:**
- 점수 합계만으로 전략 결정
- 같은 점수라도 구성이 다르면 전략이 같음
- 모멘텀 vs 추세 구분 없음

**예시:**
```
종목 A: 골든크로스(3) + 거래량(2) + MACD(1) + RSI(1) = 7점 → 관찰
종목 B: TEMA(2) + OBV(2) + 연속상승(2) + DEMA(2) = 8점 → 포지션
→ 둘 다 8점이지만 구성이 완전히 다름
```

#### V2: 점수 구성 기반 전략 분류

```python
# V2 로직 (scanner_v2/core/strategy.py)
def determine_trading_strategy(flags, adjusted_score):
    # 모멘텀 지표 점수 (단기)
    momentum_score = sum([
        3 if flags.get("cross") else 0,
        2 if flags.get("vol_expand") else 0,
        1 if flags.get("macd_ok") else 0,
        1 if flags.get("rsi_ok") else 0
    ])
    
    # 추세 지표 점수 (중장기)
    trend_score = sum([
        2 if flags.get("tema_slope_ok") else 0,
        2 if flags.get("obv_slope_ok") else 0,
        2 if flags.get("above_cnt5_ok") else 0,
        2 if flags.get("dema_slope_ok") else 0
    ])
    
    # 전략 판단
    if adjusted_score >= 10:
        if flags.get("cross") and flags.get("vol_expand") and momentum_score >= 6:
            return "스윙"  # 모멘텀 중심
        elif trend_score >= 5:
            return "포지션"  # 추세 중심
```

**개선점:**
- 점수 구성(모멘텀/추세)에 따라 전략 결정
- 같은 점수라도 구성이 다르면 다른 전략
- 모멘텀 vs 추세 명확히 구분

**예시:**
```
종목 A: 모멘텀 7점, 추세 1점, 총 8점 → 스윙 (모멘텀 중심)
종목 B: 모멘텀 1점, 추세 7점, 총 8점 → 포지션 (추세 중심)
→ 같은 8점이지만 전략이 다름
```

---

### 4. RSI 필터

#### V1: 고정 임계값

```python
# V1 로직
RSI_THRESHOLD = 35  # 고정값
RSI_UPPER_LIMIT = 60  # 고정값

if rsi < RSI_THRESHOLD:
    # 매수 신호
```

**문제점:**
- 시장 상황과 무관하게 동일한 기준
- 상승장에서 너무 엄격
- 하락장에서 너무 느슨

#### V2: 동적 조정

```python
# V2 로직
if market_condition:
    rsi_threshold = market_condition.rsi_threshold  # 장세별 동적 조정
    rsi_upper_limit = rsi_threshold + 25.0
else:
    rsi_threshold = 35  # 기본값
    rsi_upper_limit = 60

if rsi < rsi_threshold:
    # 매수 신호
```

**개선점:**
- 시장 상황에 따라 RSI 임계값 동적 조정
- 상승장: 임계값 상향 (더 엄격)
- 하락장: 임계값 하향 (더 느슨)
- 더 많은 적합한 종목 발견

**예시:**
```
상승장 (bull): RSI < 40 (기존 35에서 상향)
중립장 (neutral): RSI < 35 (기존과 동일)
하락장 (bear): RSI < 30 (기존 35에서 하향)
```

---

### 5. 구조 및 모듈화

#### V1: 단일 파일 구조

```
backend/
└── scanner.py  (2000+ 줄)
    ├── compute_indicators()
    ├── match_stats()
    ├── score_conditions()
    ├── scan_one_symbol()
    └── scan_with_preset()
```

**문제점:**
- 모든 로직이 한 파일에 집중
- 테스트 어려움
- 유지보수 어려움
- 확장성 부족

#### V2: 모듈화된 구조

```
backend/scanner_v2/
├── __init__.py
├── config_v2.py
└── core/
    ├── scanner.py          # 메인 스캐너
    ├── indicator_calculator.py  # 지표 계산
    ├── filter_engine.py    # 필터링 엔진
    ├── scorer.py           # 점수 계산
    └── strategy.py         # 전략 분류
```

**개선점:**
- 기능별 명확한 분리
- 단위 테스트 용이
- 유지보수 용이
- 확장성 향상

---

### 6. 설정 관리

#### V1: .env 파일만 사용

```python
# V1 (config.py)
scanner_version = os.getenv("SCANNER_VERSION", "v1")
scanner_v2_enabled = os.getenv("SCANNER_V2_ENABLED", "false").lower() == "true"
```

**문제점:**
- 설정 변경 시 서버 재시작 필요
- 배포 없이 설정 변경 불가
- 변경 이력 관리 어려움

#### V2: DB 우선, .env fallback

```python
# V2 (config.py)
@property
def scanner_version(self) -> str:
    """스캐너 버전 (DB 우선, 없으면 .env)"""
    try:
        from scanner_settings_manager import get_scanner_version
        return get_scanner_version()
    except Exception:
        return os.getenv("SCANNER_VERSION", "v1")
```

**개선점:**
- DB에 저장되어 배포 없이 변경 가능
- 관리자 화면에서 실시간 변경
- 변경 이력 자동 관리
- .env fallback으로 안전성 보장

---

## 📈 성능 및 정확도 비교

### 신호 처리

| 항목 | V1 | V2 |
|------|----|----|
| **후보군 품질** | 점수 높은 종목 포함 (신호 부족해도) | 신호 충족 종목만 포함 |
| **일관성** | Step별 기준 불일치 가능 | 모든 Step에서 동일한 기준 |
| **정확도** | 신호 미충족 종목 포함으로 노이즈 증가 | 신호 충족만으로 품질 향상 |

### 장세 분석

| 항목 | V1 | V2 |
|------|----|----|
| **안정성** | 하루 변동성에 민감 | 며칠간 추세 반영으로 안정 |
| **노이즈** | 단기 변동에 과민 반응 | 노이즈 제거 |
| **정확도** | 단일 날짜로 오판 가능 | 멀티데이로 더 정확 |

### 전략 분류

| 항목 | V1 | V2 |
|------|----|----|
| **정확도** | 점수 합계만으로 판단 | 점수 구성 기반 판단 |
| **유연성** | 같은 점수 = 같은 전략 | 같은 점수라도 구성에 따라 다른 전략 |
| **적합성** | 모멘텀/추세 구분 없음 | 모멘텀/추세 명확히 구분 |

---

## 🔄 마이그레이션 가이드

### V1 → V2 전환

1. **DB 설정 확인**
   ```sql
   -- scanner_settings 테이블 자동 생성됨
   SELECT * FROM scanner_settings;
   ```

2. **관리자 화면에서 설정**
   - `/admin` 접속
   - "스캐너 설정" 섹션
   - 버전: V2 선택
   - V2 활성화: ON
   - 저장

3. **또는 .env 설정**
   ```bash
   SCANNER_VERSION=v2
   SCANNER_V2_ENABLED=true
   ```

4. **서버 재시작 (필요 시)**
   ```bash
   sudo systemctl restart stock-finder-backend
   ```

### V2 → V1 롤백

1. **관리자 화면에서 설정**
   - 버전: V1 선택
   - 저장

2. **또는 .env 설정**
   ```bash
   SCANNER_VERSION=v1
   # 또는
   SCANNER_V2_ENABLED=false
   ```

---

## ⚠️ 주의사항

### V2 사용 시

1. **신호 기준이 더 엄격함**
   - V1에서 매칭되던 종목 중 일부가 제외될 수 있음
   - 신호 충족이 필수이므로 후보군이 줄어들 수 있음

2. **장세 판단 기준 변경**
   - 멀티데이 트렌드로 판단하므로 V1과 다른 장세 판단 가능
   - 더 안정적이지만 즉각적인 반응은 느릴 수 있음

3. **전략 분류 변경**
   - 점수 구성 기반으로 분류하므로 V1과 다른 전략 제안 가능
   - 더 정확하지만 기대와 다를 수 있음

### 호환성

- ✅ **API 호환**: 동일한 `/scan` API 사용
- ✅ **스케줄링 호환**: 기존 스케줄러 그대로 사용
- ✅ **DB 호환**: 동일한 DB 스키마 사용
- ⚠️ **결과 차이**: 알고리즘 차이로 인해 결과가 다를 수 있음

---

## 📊 예상 효과

### V2 사용 시 기대 효과

1. **품질 향상**
   - 신호 충족 종목만 선택하여 품질 향상
   - 노이즈 감소

2. **안정성 향상**
   - 멀티데이 트렌드로 안정적인 장세 판단
   - 단기 변동성에 덜 민감

3. **정확도 향상**
   - 점수 구성 기반 전략 분류로 더 정확한 전략 제안
   - 모멘텀 vs 추세 명확히 구분

4. **유지보수성 향상**
   - 모듈화된 구조로 유지보수 용이
   - 테스트 용이

---

## 📝 결론

스캐너 V2는 V1의 모든 기능을 유지하면서 핵심 알고리즘을 개선한 버전입니다.

**V1을 사용해야 하는 경우:**
- 기존 로직이 만족스러운 경우
- 점수 우선 원칙을 선호하는 경우
- 단일 날짜 분석을 선호하는 경우

**V2를 사용해야 하는 경우:**
- 더 정확하고 안정적인 결과를 원하는 경우
- 신호 우선 원칙을 선호하는 경우
- 멀티데이 트렌드 분석을 원하는 경우
- 점수 구성 기반 전략 분류를 원하는 경우

두 버전 모두 동일한 API와 스케줄러를 사용하므로, 필요에 따라 자유롭게 전환할 수 있습니다.

