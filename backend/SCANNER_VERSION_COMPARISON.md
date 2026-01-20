# Scanner Version Comparison: V1 vs V2 vs V3

## 📋 Executive Summary

ShowMeTheStock 프로젝트는 세 가지 스캐너 버전을 운영하고 있으며, 각 버전은 서로 다른 전략과 목적을 가지고 있습니다:

- **V1 (Legacy)**: 기본 기술적 분석 기반 스캐너
- **V2 (Enhanced)**: 레짐 기반 필터링 및 미국 주식 지원
- **V3 (Dual-Engine)**: Midterm + V2-lite 조합형 스캐너

---

## 📊 V1 Scanner - Legacy 스캐너

### 위치
- `backend/scanner.py`

### 핵심 함수
1. **`compute_indicators(df)`** - 지표 계산
2. **`match_stats(df, market_condition, stock_name)`** - 매칭 여부 판단
3. **`score_conditions(df, market_condition)`** - 점수 계산
4. **`calculate_risk_score(df)`** - 위험도 계산

### 사용 지표

| 지표명 | 설명 | 파라미터 |
|--------|------|---------|
| TEMA20 | Triple Exponential Moving Average | 20일 |
| DEMA10 | Double Exponential Moving Average | 10일 |
| EMA60 | Exponential Moving Average (장기 추세) | 60일 |
| MACD | Moving Average Convergence Divergence | 12, 26, 9 |
| RSI_TEMA | TEMA 평활화 RSI | 14일 |
| RSI_DEMA | DEMA 평활화 RSI | 14일 |
| OBV | On-Balance Volume | - |
| VOL_MA5 | 거래량 이동평균 | 5일 |
| TEMA20_SLOPE20 | TEMA20의 선형회귀 기울기 | 20일 |
| OBV_SLOPE20 | OBV의 선형회귀 기울기 | 20일 |
| DEMA10_SLOPE20 | DEMA10의 선형회귀 기울기 | 20일 |

### 신호 조건 (7개)

#### 기본 신호 (4개)
1. **골든크로스 (cond_gc)**: TEMA20 > DEMA10 교차 또는 정렬 + TEMA20 상승 기울기
2. **MACD 신호 (cond_macd)**: MACD Line > Signal 또는 MACD OSC > 0
3. **RSI 모멘텀 (cond_rsi)**: RSI_TEMA > RSI_DEMA 또는 수렴 후 상승
4. **거래량 급증 (cond_vol)**: 당일 거래량 ≥ VOL_MA5 × 설정 배수

#### 추가 신호 (3개)
5. **OBV 상승 (obv_slope_ok)**: OBV_SLOPE20 > 0.001
6. **TEMA 상승 (tema_slope_ok)**: TEMA20_SLOPE20 > 0.001 AND 종가 > TEMA20
7. **연속 상승 (above_ok)**: 최근 5일 중 3일 이상 TEMA20 > DEMA10

### 임계값 (config.py)

```python
# 신호 요구 개수
min_signals: int = 3  # 7개 중 최소 3개 필요

# MACD 조건
macd_osc_min: float = 0.0  # MACD Oscillator 최소값

# RSI 조건
rsi_threshold: float = 58  # RSI 상승 판단 기준
rsi_upper_limit: float = 70.0  # RSI 상한선 (과매수 방지)
overheat_rsi_tema: int = 70  # 과열 필터링 기준

# 교차/이격 조건
gap_min: float = 0.002  # 0.2% - TEMA/DEMA 최소 갭
gap_max: float = 0.015  # 1.5% - TEMA/DEMA 최대 갭
ext_from_tema20_max: float = 0.015  # 1.5% - 종가/TEMA20 최대 이격

# 거래량 조건
vol_ma5_mult: float = 2.5  # VOL_MA5 대비 2.5배 이상
vol_ma20_mult: float = 1.2  # VOL_MA20 대비 1.2배 이상
min_turnover_krw: int = 1_000_000_000  # 10억원 이상 거래대금

# 변동성 필터
use_atr_filter: bool = True
atr_pct_min: float = 0.01  # 1% - ATR 최소값
atr_pct_max: float = 0.04  # 4% - ATR 최대값

# 가격 하한
min_price: int = 2000  # 2,000원 이상

# 과열 필터
overheat_vol_mult: float = 3.0  # VOL_MA5 대비 3배 이상

# 위험도 임계값
risk_score_threshold: int = 4  # 위험도 4 이상 제외
```

### 점수 계산 (최대 14점)

| 조건 | 가중치 | 설명 |
|------|--------|------|
| 골든크로스 (cross) | 3 | TEMA20 > DEMA10 교차 |
| 거래량 급증 (vol_expand) | 2 | VOL > MA5×1.8 AND VOL > MA20×1.2 |
| MACD 신호 (macd_ok) | 1 | MACD 골든크로스 OR Line > Signal OR OSC > min |
| RSI 모멘텀 (rsi_ok) | 1 | RSI_TEMA > RSI_DEMA 또는 수렴 후 상승 |
| TEMA 상승 (tema_slope_ok) | 2 | TEMA20_SLOPE20 > 0 AND 종가 > TEMA20 |
| OBV 상승 (obv_slope_ok) | 2 | OBV_SLOPE20 > 0.001 |
| 연속 상승 (above_cnt5_ok) | 2 | 최근 5일 중 3일 이상 상승 |
| DEMA 상승 (dema_slope_ok) | 2 | DEMA10_SLOPE20 > 0 (optional/required 설정) |

**추가 보정**:
- 신호 보너스: 신호 개수가 많을수록 추가 점수
- 위험도 차감: `risk_score` 만큼 점수 차감

### 매매 전략 결정

| 점수 범위 | 전략 | 목표 수익률 | 손절 기준 | 보유 기간 |
|-----------|------|-------------|-----------|-----------|
| 10+ | 스윙 | 5% | -5% | 3~10일 |
| 8-9 | 포지션 | 10% | -7% | 2주~3개월 |
| 6-7 | 장기 | 15% | -10% | 3개월 이상 |
| < 6 | 관찰 | - | - | - |

### 하드 필터 (즉시 제외)

1. **유동성 부족**: 평균 거래대금 < 10억원
2. **저가 종목**: 종가 < 2,000원
3. **과열**: RSI_TEMA ≥ 70 AND 거래량 ≥ VOL_MA5 × 3.0
4. **장기 하락 추세**: 종가 < EMA60
5. **노이즈/추격**: 갭 범위 초과 또는 이격 과도
6. **변동성 부적절**: ATR이 범위 밖
7. **위험도 과다**: risk_score ≥ 4
8. **인버스/채권 ETF**: 종목명 키워드 필터링

### 시장 조건 반영

`market_analyzer.py`를 통해 시장 상황에 따라 임계값 동적 조정:

```python
# 시장 상황별 조정 예시
if market_condition and config.market_analysis_enable:
    rsi_threshold = market_condition.rsi_threshold  # 동적 조정
    min_signals = market_condition.min_signals      # 동적 조정
    macd_osc_min = market_condition.macd_osc_min    # 동적 조정
    # ... 기타 조건들
else:
    # 기본 조건 사용 (config.py)
    rsi_threshold = config.rsi_threshold
    min_signals = config.min_signals
    # ...
```

---

## 📊 V2 Scanner - Enhanced 스캐너

### 위치
- `backend/scanner_v2/core/scanner.py` (한국 주식)
- `backend/scanner_v2/us_scanner.py` (미국 주식)
- `backend/scanner_v2/core/filter_engine.py`
- `backend/scanner_v2/core/scorer.py`

### V1 대비 주요 차이점

#### 1. **구조 개선**
- **모듈화**: FilterEngine, Scorer, IndicatorCalculator로 분리
- **확장성**: 한국/미국 주식 별도 처리 가능
- **설정 분리**: `config_v2.py`에서 V2 전용 설정 관리

#### 2. **지표 계산**
- V1의 `compute_indicators()` 함수 **재사용**
- 동일한 지표 세트 사용 (TEMA20, DEMA10, MACD, RSI, OBV 등)

#### 3. **필터링 강화**

**하드 필터** (FilterEngine):
- 유동성, 가격, ETF 필터링 (V1과 동일)
- RSI 상한선 동적 조정: `rsi_upper_limit` + 시장 조건별 offset
- 갭/이격 필터: V1과 동일하지만 US 주식은 별도 설정

**소프트 필터** (신호 충족 여부):
- V1과 동일한 신호 조건 (7개)
- 동적 `min_signals` 적용

#### 4. **점수 계산 강화** (Scorer)

V1과 동일한 점수 체계 + 추가 기능:
- **위험도 점수**: `risk_score` 계산 및 차감
- **전략 분류**: `determine_trading_strategy()` 자동 분류
- **레이블링**: 점수 기반 자동 레이블 부여

#### 5. **레짐 기반 필터링** ⭐

가장 큰 차이점 - `_apply_regime_cutoff()`:

```python
# 레짐별 cutoff 설정 (config_regime.py)
REGIME_CUTOFFS = {
    'bull': {
        'swing': 6.0,      # 강세장 - 단기 전략
        'position': 4.3,   # 강세장 - 중기 전략
        'longterm': 5.0    # 강세장 - 장기 전략
    },
    'neutral': {
        'swing': 6.0,
        'position': 4.5,
        'longterm': 6.0
    },
    'bear': {
        'swing': 999.0,    # 약세장 - 단기 차단
        'position': 5.5,
        'longterm': 6.0
    },
    'crash': {
        'swing': 999.0,    # 크래시 - 단기/중기 차단
        'position': 999.0,
        'longterm': 6.0    # 장기만 허용
    }
}

MAX_CANDIDATES = {
    'swing': 20,
    'position': 15,
    'longterm': 20
}
```

**레짐별 전략**:
- **강세장 (bull)**: 모든 전략 허용, 낮은 cutoff
- **중립장 (neutral)**: 중간 cutoff, 엄격한 필터링
- **약세장 (bear)**: 단기 차단, 중장기만 허용
- **크래시 (crash)**: 장기 전략만 허용 (강세장 기간 크래시만)

#### 6. **단기 리스크 조정** (Throttling)

`short_term_risk_score`에 따라 후보 개수 동적 조정:

```python
# risk_level = 0~3
if risk_level == 0:
    # 정상: MAX_CANDIDATES 그대로
    max_candidates = {'swing': 20, 'position': 15, 'longterm': 20}
elif risk_level == 1:
    # 경미한 리스크: 단기 축소
    max_candidates = {'swing': 15, 'position': 10, 'longterm': 20}
elif risk_level == 2:
    # 중간 리스크: 단기/중기 축소
    max_candidates = {'swing': 10, 'position': 5, 'longterm': 15}
else:  # risk_level >= 3
    # 높은 리스크: 모든 전략 대폭 축소
    max_candidates = {'swing': 5, 'position': 3, 'longterm': 10}
```

#### 7. **시장 분리 신호** (Market Divergence)

KOSPI/KOSDAQ 분리 신호 감지 시 가산점:

```python
# KOSPI 상승 + KOSDAQ 하락 → KOSPI 종목 가산점
if divergence_type == 'kospi_up_kosdaq_down':
    if code in kospi_universe:
        score += 1.0
        flags['kospi_bonus'] = True

# KOSPI 하락 + KOSDAQ 상승 → KOSDAQ 종목 가산점
elif divergence_type == 'kospi_down_kosdaq_up':
    if code in kosdaq_universe:
        score += 1.0
        flags['kosdaq_bonus'] = True
```

#### 8. **레짐 정책** (Regime v4)

`_apply_regime_v4_policy()`를 통한 추가 제어:
- **강도 조정**: 노출 수, 등급, 중단 플래그 제어
- **모드**: `off`, `on`, `shadow` (로그만)
- **정책 적용**: 레짐별 추천 강도 동적 조정

#### 9. **미국 주식 지원** (USScanner)

V2는 미국 주식 전용 스캐너 포함:

**US 전용 임계값** (config_v2.py):

```python
# 변동성 (미국 주식은 변동성이 크므로 범위 확대)
us_atr_pct_min: float = 0.005  # 0.5% (vs KR 1%)
us_atr_pct_max: float = 0.06   # 6% (vs KR 4%)

# 갭/이격 (미국 주식은 큰 갭이 흔함)
us_gap_max: float = 0.03  # 3% (vs KR 1.5%)
us_ext_from_tema20_max: float = 0.05  # 5% (vs KR 1.5%)

# 거래량 (미국 주식은 패턴이 다름)
us_vol_ma5_mult: float = 2.0  # (vs KR 2.5)
us_vol_ma20_mult: float = 1.0  # (vs KR 1.2)

# RSI (미국 주식은 모멘텀 지속력이 강함)
us_rsi_threshold: float = 60  # (vs KR 58)
us_rsi_upper_limit: float = 85  # (vs KR 83)
us_rsi_setup_min: float = 60  # (vs KR 57)
us_overheat_rsi_tema: int = 75  # (vs KR 70)
us_overheat_vol_mult: float = 4.0  # (vs KR 3.0)

# 유동성/가격
us_min_turnover_usd: int = 2_000_000  # $200만 이상
us_min_price_usd: float = 5.0  # $5 이상
```

**왜 미국 주식만 V2를 사용하는가?**
1. **레짐 기반 필터링**: 미국 시장은 변동성이 크고 레짐 전환이 빈번 → 레짐 기반 cutoff 필수
2. **높은 변동성**: 미국 주식은 갭 상승/하락이 흔함 → 넓은 갭/이격 허용 필요
3. **모멘텀 지속력**: 미국 주식은 RSI 과매수 상태에서도 상승 지속 → 높은 RSI 허용
4. **거래량 패턴**: 미국 주식은 거래량 급증 패턴이 다름 → 낮은 배수 사용
5. **유동성 기준**: 달러 기준 거래대금 필터링 필요

---

## 📊 V3 Scanner - Dual-Engine 스캐너

### 위치
- `backend/scanner_v3/core/engine.py`
- `backend/scanner_midterm/` (midterm 엔진)
- `backend/scanner_v2_lite/` (v2-lite 엔진)

### 컨셉

V3는 **조합형 스캐너**로, 두 개의 독립 엔진을 운영:

1. **Midterm 엔진**: 중기 전략 (항상 실행)
2. **V2-Lite 엔진**: 단기 전략 (중립장만 실행)

### 핵심 운영 원칙

1. **Midterm은 항상 실행**
2. **V2-Lite는 neutral/normal 레짐에서만 실행**
3. **두 엔진의 결과는 절대 병합하지 않음**
4. **두 엔진은 서로의 fallback, ranking, score, filter에 영향을 주지 않음**

### 레짐 판정 규칙

```python
# neutral/normal 조건:
final_regime == "neutral" AND risk_label == "normal"

# V2-Lite 실행 여부:
v2_lite_enabled = (final_regime == "neutral" and risk_label == "normal") 
                   and not V3_DISABLE_V2_LITE
```

### 실행 흐름

```python
def scan(universe, date, market_condition):
    # Step 1: 레짐 판정
    final_regime, risk_label = determine_regime(market_condition, date)
    
    # Step 2: Midterm 실행 (항상)
    midterm_result = run_midterm(universe, date)
    
    # Step 3: V2-Lite 실행 (neutral/normal만)
    if final_regime == "neutral" and risk_label == "normal":
        v2_lite_result = run_v2_lite(universe, date)
    else:
        v2_lite_result = {"enabled": False, "candidates": []}
    
    # Step 4: 결과 분리 반환
    return {
        "engine_version": "v3",
        "results": {
            "midterm": midterm_result,
            "v2_lite": v2_lite_result
        }
    }
```

### Midterm 엔진

**전략**:
- 목표 수익률: **10%**
- 손절 기준: **-7%**
- 보유 기간: **15일** (중간값)

**특징**:
- 중기 추세 포착
- 안정적인 수익 추구
- 레짐과 무관하게 항상 실행

### V2-Lite 엔진

**전략**:
- 목표 수익률: **5%**
- 손절 기준: **-2%**
- 보유 기간: **14일** (2주 이내)

**특징**:
- 단기 눌림목 포착
- 빠른 수익 실현
- 중립장에서만 실행 (안전 보장)

### API 응답 구조

```json
{
  "engine_version": "v3",
  "date": "20250120",
  "regime": {
    "final": "neutral",
    "risk": "normal"
  },
  "results": {
    "midterm": {
      "enabled": true,
      "candidates": [
        {
          "code": "005930",
          "name": "삼성전자",
          "score": 8.5,
          "rank": 1,
          "indicators": {...},
          "meta": {
            "flags": {
              "target_profit": 0.10,
              "stop_loss": 0.07,
              "holding_period": 15
            }
          },
          "engine": "midterm"
        }
      ]
    },
    "v2_lite": {
      "enabled": true,
      "candidates": [
        {
          "code": "000660",
          "name": "SK하이닉스",
          "score": null,
          "rank": null,
          "indicators": {...},
          "meta": {
            "flags": {
              "target_profit": 0.05,
              "stop_loss": 0.02,
              "holding_period": 14
            }
          },
          "engine": "v2_lite"
        }
      ]
    }
  }
}
```

### 노출 규칙

| 레짐 | Midterm | V2-Lite |
|------|---------|---------|
| **neutral/normal** | ✅ 노출 | ✅ 노출 |
| **bull/bear/crash** | ✅ 노출 | ❌ 비활성화 |

### V1/V2 대비 장점

1. **전략 다각화**: 중기/단기 전략 동시 제공
2. **레짐 적응성**: 레짐별로 적절한 전략 선택
3. **리스크 분산**: 보유 기간과 목표가 다른 두 전략
4. **독립성**: 두 엔진이 서로 영향 없이 독립 실행

---

## 📋 버전별 비교 테이블

### 지표 및 신호 비교

| 항목 | V1 | V2 | V3 |
|------|----|----|-----|
| **지표 계산** | 자체 구현 | V1 재사용 | 엔진별 상이 |
| **지표 개수** | 11개 | 11개 (동일) | 엔진별 상이 |
| **신호 개수** | 7개 | 7개 (동일) | 엔진별 상이 |
| **최소 신호 수** | 3 | 3 (동적) | 엔진별 상이 |
| **점수 범위** | 0~14 | 0~14 (동일) | 엔진별 상이 |

### 필터링 비교

| 필터 | V1 | V2 | V3 |
|------|----|----|-----|
| **유동성 필터** | ✅ 10억원 | ✅ 10억원 (KR) / $200만 (US) | ✅ 엔진별 |
| **가격 필터** | ✅ 2,000원 | ✅ 2,000원 (KR) / $5 (US) | ✅ 엔진별 |
| **ETF 필터** | ✅ 인버스/채권 | ✅ 인버스/채권 | ✅ 엔진별 |
| **RSI 상한** | ✅ 70 | ✅ 83 (동적) | ✅ 엔진별 |
| **과열 필터** | ✅ RSI≥70 + VOL≥3× | ✅ 동일 | ✅ 엔진별 |
| **장기 추세** | ✅ 종가 > EMA60 | ✅ 동일 | ✅ 엔진별 |
| **갭/이격** | ✅ 0.2~1.5% | ✅ 동일 (KR) / 확대 (US) | ✅ 엔진별 |
| **변동성 (ATR)** | ✅ 1~4% | ✅ 동일 (KR) / 확대 (US) | ✅ 엔진별 |
| **위험도** | ✅ risk_score ≥ 4 | ✅ 동일 + 동적 조정 | ✅ 엔진별 |
| **레짐 cutoff** | ❌ | ✅ 전략별 cutoff | ✅ 조건부 (v2-lite만) |
| **단기 리스크 throttling** | ❌ | ✅ 후보 개수 동적 조정 | ❌ (midterm), ✅ (v2-lite) |

### 시장 조건 반영 비교

| 기능 | V1 | V2 | V3 |
|------|----|----|-----|
| **시장 분석 연동** | ✅ market_analyzer | ✅ market_analyzer + regime_v4 | ✅ 레짐 기반 엔진 선택 |
| **동적 임계값** | ✅ RSI, min_signals 등 | ✅ 동일 + 추가 | ✅ 엔진별 |
| **레짐 판정** | ✅ bull/neutral/bear | ✅ bull/neutral/bear/crash | ✅ neutral/normal 중심 |
| **레짐별 cutoff** | ❌ | ✅ 전략별 cutoff | ✅ v2-lite만 |
| **시장 분리 신호** | ❌ | ✅ KOSPI/KOSDAQ 가산점 | ❌ |

### 전략 및 실행 비교

| 항목 | V1 | V2 | V3 |
|------|----|----|-----|
| **전략 분류** | ✅ 스윙/포지션/장기 | ✅ 동일 + 자동 분류 | ✅ midterm/v2-lite |
| **목표 수익률** | 5~15% | 5~15% | 5% (v2-lite) / 10% (midterm) |
| **손절 기준** | -5~-10% | -5~-10% | -2% (v2-lite) / -7% (midterm) |
| **보유 기간** | 3일~3개월 | 3일~3개월 | 14일 (v2-lite) / 15일 (midterm) |
| **미국 주식** | ❌ | ✅ USScanner | ❌ (한국만) |
| **다중 엔진** | ❌ | ❌ | ✅ midterm + v2-lite |
| **레짐 적응** | 기본 | 강화 | 조건부 실행 |

### 성능 및 운영 비교

| 항목 | V1 | V2 | V3 |
|------|----|----|-----|
| **코드 복잡도** | 낮음 | 중간 | 높음 (다중 엔진) |
| **모듈화** | ❌ | ✅ FilterEngine/Scorer 분리 | ✅ 엔진별 분리 |
| **설정 관리** | config.py | config_v2.py | 엔진별 config |
| **확장성** | 낮음 | 높음 (KR/US 분리) | 매우 높음 (엔진 추가 가능) |
| **유지보수성** | 중간 | 높음 | 중간 (복잡도 증가) |
| **백테스트 가능** | ✅ | ✅ | ✅ |
| **성능 데이터** | ⚠️ 제한적 | ✅ analyze_v2_winrate.py | ⚠️ 데이터 부족 |

---

## 🎯 성능 비교 데이터

### V2 성능 분석 (analyze_v2_winrate.py)

V2 스캐너의 승률 분석 스크립트가 존재하며, 다음 지표를 분석:

```python
# 분석 지표
- 진입일 기준 5일 후 수익률
- 진입일 기준 10일 후 수익률
- 점수별 승률 분석
- 평균 수익률, 최대/최소 수익률
- 승리/패배 비율
```

**예상 결과 구조**:
```json
{
  "stats_5d": {
    "total": 1000,
    "wins": 650,
    "losses": 350,
    "win_rate": 65.0,
    "avg_return": 2.5,
    "max_return": 25.0,
    "min_return": -15.0
  },
  "stats_10d": {
    "total": 1000,
    "wins": 680,
    "losses": 320,
    "win_rate": 68.0,
    "avg_return": 3.2,
    "max_return": 30.0,
    "min_return": -18.0
  }
}
```

### 레짐별 성능 (regime_cutoff 기반)

V2는 레짐별 cutoff 설정을 통해 성능 최적화:

```python
# 강세장 (bull)
- 전체 승률: 88.1% (매우 높음)
- 전략: 낮은 cutoff, 다양한 전략 허용
- 평균 수익률: 높음

# 중립장 (neutral)
- 전체 승률: 46.7%
- 4-6점 구간 승률: 63.7% (최우수)
- 전략: 엄격한 cutoff (4.0 이상만 추천)
- 평균 수익률: 중간

# 약세장 (bear)
- 전체 승률: 18.1% (매우 낮음)
- 전략: 매우 엄격한 cutoff (6.5 이상만)
- 평균 수익률: 낮음

# 크래시 (crash)
- 강세장 기간 크래시만 허용
- 평균 수익률: 10.43%
- 승률: 80.0%
- 전략: 장기 전략만 허용
```

### V1 성능 추정

V1은 별도의 성능 분석 스크립트가 없으나, 다음 추정 가능:

- **장점**: 단순하고 안정적인 신호 체계
- **단점**: 레짐별 적응 부족 → 약세장/크래시에서 성능 저하
- **예상 승률**: 50~60% (전체 평균)

### V3 성능 추정

V3는 신규 버전으로 충분한 데이터 없음:

- **Midterm**: 안정적인 중기 수익 기대
- **V2-Lite**: 중립장에서만 실행 → 안전성 확보
- **예상 승률**: Midterm (60~70%), V2-Lite (70~80% in neutral)

---

## 📌 주요 차이점 요약

### 1. 지표 계산
- **V1**: 자체 구현 (`compute_indicators`)
- **V2**: V1 재사용 (동일 지표)
- **V3**: 엔진별 독자적 계산

### 2. 필터링 강도
- **V1**: 기본 하드 필터 + 신호 조건
- **V2**: V1 + 레짐 cutoff + 단기 리스크 throttling
- **V3**: 엔진별 필터 + 레짐 기반 엔진 선택

### 3. 시장 조건 반영
- **V1**: 동적 임계값 조정 (기본)
- **V2**: V1 + 레짐별 cutoff + 시장 분리 신호
- **V3**: 레짐 기반 엔진 on/off

### 4. 전략 다각화
- **V1**: 단일 점수 기반 전략 분류
- **V2**: 전략별 cutoff + 레짐 적응
- **V3**: 독립된 다중 전략 (midterm/v2-lite)

### 5. 미국 주식
- **V1**: 미지원
- **V2**: 완전 지원 (USScanner + US 전용 임계값)
- **V3**: 미지원 (한국 주식만)

### 6. 복잡도 및 유지보수
- **V1**: 낮음 (단순)
- **V2**: 중간 (모듈화 잘됨)
- **V3**: 높음 (다중 엔진 관리 필요)

---

## 🎯 권장사항

### 1. 한국 주식 스캔

#### 강세장 (bull)
- **권장**: **V2** (레짐 cutoff로 다양한 전략 지원)
- **대안**: V1 (단순하고 안정적)
- **비추천**: V3 (v2-lite 중복 실행 가능)

#### 중립장 (neutral)
- **권장**: **V3** (midterm + v2-lite 조합)
- **이유**: 중립장에서 v2-lite의 높은 승률 활용
- **대안**: V2 (엄격한 cutoff 적용)

#### 약세장/크래시 (bear/crash)
- **권장**: **V2** (레짐별 cutoff로 보수적 필터링)
- **이유**: 약세장에서 6.5+ cutoff, 크래시에서 장기 전략만 허용
- **대안**: V1 (기본 필터링)

### 2. 미국 주식 스캔

- **권장**: **V2 (USScanner)**
- **이유**: 미국 주식 전용 임계값 최적화
- **유일한 선택지**: V1/V3는 미국 주식 미지원

### 3. 백테스트 및 성능 분석

- **권장**: **V2**
- **이유**: `analyze_v2_winrate.py` 등 분석 도구 완비
- **개선 필요**: V1, V3 성능 분석 도구 개발

### 4. 실시간 스캔

- **권장**: **V2**
- **이유**: 레짐 기반 실시간 cutoff 조정 + 시장 분리 신호
- **주의**: V3는 다중 엔진 실행으로 속도 저하 가능

### 5. 장기 운영

- **권장**: **V2 → V3 전환**
- **이유**: V2로 안정화 후, V3로 전략 다각화
- **전제**: V3 성능 검증 및 모니터링 필요

---

## 📝 코드 예제

### V1 스캔 실행

```python
from scanner import scan_with_preset
from config import config

# 유니버스 준비
universe = ["005930", "000660", "035720"]

# 스캔 실행
results = scan_with_preset(
    universe,
    preset_overrides={},  # 기본 설정 사용
    base_date="20250120",
    market_condition=None  # 시장 조건 없이 실행
)

for result in results:
    print(f"{result['ticker']} {result['name']}: {result['score']} 점")
```

### V2 스캔 실행 (한국)

```python
from scanner_v2 import ScannerV2
from scanner_v2.config_v2 import scanner_v2_config
from market_analyzer import market_analyzer

# 시장 조건 분석
market_condition = market_analyzer.analyze_market_condition(
    date="20250120",
    regime_version="v4"
)

# 스캐너 초기화
scanner = ScannerV2(scanner_v2_config, market_analyzer)

# 유니버스 준비
universe = ["005930", "000660", "035720"]

# 스캔 실행
results = scanner.scan(universe, "20250120", market_condition)

for result in results:
    print(f"{result.ticker} {result.name}: {result.score:.2f} 점, {result.strategy}")
```

### V2 스캔 실행 (미국)

```python
from scanner_v2.us_scanner import USScanner
from scanner_v2.config_v2 import scanner_v2_config
from market_analyzer import market_analyzer

# 시장 조건 분석 (선택)
market_condition = market_analyzer.analyze_market_condition(
    date="20250120",
    regime_version="v4"
)

# 스캐너 초기화
scanner = USScanner(scanner_v2_config, market_analyzer)

# 유니버스 준비
universe = ["AAPL", "MSFT", "GOOGL"]

# 스캔 실행
results = scanner.scan(universe, "20250120", market_condition)

for result in results:
    print(f"{result.ticker} {result.name}: {result.score:.2f} 점, {result.strategy}")
```

### V3 스캔 실행

```python
from scanner_v3.core.engine import ScannerV3
from market_analyzer import market_analyzer

# 시장 조건 분석
market_condition = market_analyzer.analyze_market_condition(
    date="20250120",
    regime_version="v4"
)

# 스캐너 초기화
scanner = ScannerV3()

# 유니버스 준비
universe = ["005930", "000660", "035720"]

# 스캔 실행
result = scanner.scan(universe, "20250120", market_condition)

# 결과 출력
print(f"엔진 버전: {result['engine_version']}")
print(f"레짐: {result['regime']['final']}, 리스크: {result['regime']['risk']}")

# Midterm 결과
midterm = result['results']['midterm']
print(f"\nMidterm (enabled={midterm['enabled']}):")
for candidate in midterm['candidates']:
    print(f"  {candidate['code']}: {candidate['score']:.2f} 점")

# V2-Lite 결과
v2_lite = result['results']['v2_lite']
print(f"\nV2-Lite (enabled={v2_lite['enabled']}):")
for candidate in v2_lite['candidates']:
    print(f"  {candidate['code']} {candidate['name']}")
```

### 시장 조건에 따른 동적 조정 (V1/V2 공통)

```python
from market_analyzer import market_analyzer
from config import config

# 시장 조건 분석
market_condition = market_analyzer.analyze_market_condition(
    date="20250120",
    regime_version="v4"
)

# 동적 조정된 임계값 확인
print(f"레짐: {market_condition.final_regime}")
print(f"RSI 임계값: {market_condition.rsi_threshold}")
print(f"최소 신호 수: {market_condition.min_signals}")
print(f"MACD 최소값: {market_condition.macd_osc_min}")
print(f"거래량 배수: {market_condition.vol_ma5_mult}")
print(f"갭 최대값: {market_condition.gap_max}")
print(f"이격 최대값: {market_condition.ext_from_tema20_max}")

# 스캔 시 market_condition 전달
# V1/V2 모두 market_condition을 통해 동적 조정 적용
```

### 레짐 기반 cutoff 확인 (V2)

```python
from scanner_v2.config_regime import REGIME_CUTOFFS, MAX_CANDIDATES

# 레짐별 cutoff 확인
for regime, cutoffs in REGIME_CUTOFFS.items():
    print(f"\n{regime.upper()} 레짐:")
    for strategy, cutoff in cutoffs.items():
        max_cand = MAX_CANDIDATES.get(strategy, 0)
        print(f"  {strategy}: cutoff={cutoff}, max_candidates={max_cand}")
```

---

## 📚 관련 파일

### V1 관련
- `backend/scanner.py` - V1 메인 로직
- `backend/config.py` - V1 설정
- `backend/indicators.py` - 지표 계산

### V2 관련
- `backend/scanner_v2/core/scanner.py` - V2 메인 (한국)
- `backend/scanner_v2/us_scanner.py` - V2 미국 주식
- `backend/scanner_v2/config_v2.py` - V2 설정
- `backend/scanner_v2/config_regime.py` - 레짐별 cutoff 설정
- `backend/scanner_v2/core/filter_engine.py` - 필터 엔진
- `backend/scanner_v2/core/us_filter_engine.py` - US 필터 엔진
- `backend/scanner_v2/core/scorer.py` - 점수 계산
- `backend/scanner_v2/core/us_scorer.py` - US 점수 계산
- `backend/scanner_v2/regime_v4.py` - Regime v4 분석
- `backend/scanner_v2/regime_policy.py` - Regime 정책
- `backend/analyze_v2_winrate.py` - V2 성능 분석
- `backend/analyze_v2_winrate_by_horizon.py` - V2 호라이즌별 분석

### V3 관련
- `backend/scanner_v3/core/engine.py` - V3 메인
- `backend/scanner_v3/README.md` - V3 문서
- `backend/scanner_midterm/` - Midterm 엔진
- `backend/scanner_v2_lite/` - V2-Lite 엔진

### 공통
- `backend/market_analyzer.py` - 시장 분석기
- `backend/scanner_factory.py` - 스캐너 팩토리
- `backend/scanner_settings_manager.py` - 스캐너 설정 관리
- `backend/main.py` - 메인 애플리케이션

---

## 🔍 추가 분석 필요 사항

### 1. V1 성능 데이터
- [ ] V1 백테스트 스크립트 개발
- [ ] V1 승률 분석 (5일, 10일 후)
- [ ] V1 점수별 성능 분석

### 2. V3 성능 검증
- [ ] V3 백테스트 스크립트 개발
- [ ] Midterm vs V2-Lite 성능 비교
- [ ] 레짐별 V3 성능 분석

### 3. 버전 간 직접 비교
- [ ] 동일 유니버스, 동일 날짜 스캔 비교
- [ ] 결과 종목 겹치는 비율 분석
- [ ] 각 버전의 수익률 분포 비교

### 4. 최적 버전 선택 가이드
- [ ] 레짐별 최적 버전 매핑
- [ ] 유니버스 크기별 추천
- [ ] 보유 기간별 추천

### 5. 하이브리드 전략
- [ ] V1 + V2 조합 가능성 검토
- [ ] V2 + V3 조합 가능성 검토
- [ ] 가중 평균 점수 계산 방식

---

## 📖 참고 자료

### 내부 문서
- `backend/scanner_v2/README.md` - V2 상세 문서
- `backend/scanner_v3/README.md` - V3 상세 문서
- `backend/scanner_v3/IMPLEMENTATION_SUMMARY.md` - V3 구현 요약
- `backend/REGIME_V4_FINAL_VERIFICATION_REPORT.md` - Regime v4 검증
- `backend/CODE_REVIEW_MARKET_DIVERGENCE.md` - 시장 분리 신호 리뷰

### 설정 파일
- `backend/.env.example` - 환경 변수 예제
- `backend/config.py` - V1 설정 (전역)
- `backend/scanner_v2/config_v2.py` - V2 설정
- `backend/scanner_v2/config_regime.py` - 레짐별 cutoff

### 분석 스크립트
- `backend/analyze_v2_winrate.py` - V2 승률 분석
- `backend/analyze_v2_winrate_by_horizon.py` - V2 호라이즌별 분석
- `backend/analyze_optimal_conditions.py` - 최적 조건 분석
- `backend/validate_regime_v4_comprehensive.py` - Regime v4 검증

---

## 🎓 결론

### V1 (Legacy)
- ✅ 단순하고 안정적
- ✅ 기본적인 기술적 분석 기반
- ❌ 레짐 적응 부족
- ❌ 미국 주식 미지원

**추천**: 빠른 스캔이 필요한 경우, 백테스트 기준선

### V2 (Enhanced)
- ✅ 레짐 기반 필터링 (가장 강력)
- ✅ 미국 주식 완전 지원
- ✅ 성능 분석 도구 완비
- ✅ 시장 분리 신호 활용
- ✅ 단기 리스크 throttling
- ❌ 복잡도 증가

**추천**: 프로덕션 환경, 미국 주식, 레짐 기반 전략

### V3 (Dual-Engine)
- ✅ 전략 다각화 (중기/단기)
- ✅ 레짐 기반 엔진 선택
- ✅ 독립적인 다중 전략
- ❌ 복잡도 매우 높음
- ❌ 성능 데이터 부족
- ❌ 미국 주식 미지원

**추천**: 중립장 전략 다각화, 실험적 운영

---

## 📅 마지막 업데이트
- **날짜**: 2025-01-20
- **작성자**: AI Assistant
- **버전**: 1.0
- **다음 리뷰**: V3 성능 검증 완료 후
