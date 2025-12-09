# 미국 시장 레짐 분석 필요성 검토

## 현재 상태

### 코드 구조

미국 주식 스캐너는 **레짐 분석을 사용할 수 있는 구조가 이미 준비되어 있습니다**:

1. **USScanner.scan()**: `market_condition` 파라미터를 받음
2. **`_apply_regime_cutoff()`**: 레짐 기반 점수 cutoff 적용
3. **USFilterEngine**: 레짐에 따라 필터링 조건 조정 가능

### 현재 구현 상태

```python
# backend/main.py - scan_us_stocks()
market_condition = None  # ❌ 레짐 분석 없음
if config.market_analysis_enable:
    try:
        # 미국 시장 레짐 분석 (추후 구현)  # ⚠️ 주석 처리됨
        # market_condition = market_analyzer.analyze_us_market_condition(today_as_of)
        pass
    except Exception as e:
        print(f"⚠️ 미국 시장 분석 실패: {e}")
```

---

## 레짐 분석 활용 현황

### 1. 레짐 기반 Cutoff 적용

**코드 위치**: `backend/scanner_v2/us_scanner.py`

```python
def _apply_regime_cutoff(self, results: List[ScanResult], market_condition: MarketCondition):
    """레짐 기반 cutoff 적용"""
    regime = getattr(market_condition, 'final_regime', 'neutral')
    cutoffs = REGIME_CUTOFFS.get(regime, REGIME_CUTOFFS['neutral'])
    
    # 레짐별 전략별 점수 기준:
    # bull: swing 6.0, position 4.3, longterm 5.0
    # neutral: swing 6.0, position 4.5, longterm 6.0
    # bear: swing 999.0, position 5.5, longterm 6.0
    # crash: swing 999.0, position 999.0, longterm 6.0
```

**효과**:
- 강세장(bull): 조건 완화 → 더 많은 종목 선정
- 약세장(bear): 조건 강화 → 보수적 선정
- 급락장(crash): 단기/중기 매매 비활성화 → 장기 투자만 허용

### 2. 필터링 조건 조정

**코드 위치**: `backend/scanner_v2/core/us_filter_engine.py`

```python
def apply_soft_filters(self, df, market_condition=None):
    # 레짐에 따라 동적 조건 조정
    if market_condition and self.market_analysis_enable:
        rsi_threshold = market_condition.rsi_threshold      # 레짐별 RSI 임계값
        min_signals = market_condition.min_signals        # 레짐별 최소 신호 개수
        vol_ma5_mult = market_condition.vol_ma5_mult      # 레짐별 거래량 배수
        
        # 강세장 판단
        is_bull_market = (
            (market_condition.market_sentiment == 'bull') or 
            (market_condition.final_regime == 'bull') or 
            (market_condition.global_trend_score > 1.0)
        )
        
        if is_bull_market:
            # 강세장: 조건 완화
            tema_slope_ok = df.iloc[-1]["TEMA20_SLOPE20"] > 0
            obv_slope_ok = df.iloc[-1]["OBV_SLOPE20"] > 0
            above_ok = above_cnt >= 2  # 3 → 2로 완화
```

**효과**:
- 레짐에 따라 RSI 임계값, 최소 신호 개수, 거래량 배수 등이 자동 조정
- 강세장에서는 필터링 조건 완화 → 더 많은 종목 통과
- 약세장에서는 필터링 조건 강화 → 엄격한 선정

### 3. RSI 상한선 조정

```python
def apply_hard_filters(self, df, market_condition=None):
    if market_condition and self.market_analysis_enable:
        rsi_upper_limit = market_condition.rsi_threshold + 25.0
    else:
        rsi_upper_limit = self.config.rsi_upper_limit  # 고정값
```

**효과**:
- 레짐에 따라 RSI 상한선이 동적으로 조정됨
- 레짐 분석 없으면 고정값 사용 (비효율적)

---

## 레짐 분석 필요성

### ✅ 필요하다고 판단되는 이유

#### 1. **한국 주식과 동일한 로직 적용**

한국 주식 스캔은 레짐 분석을 사용하여:
- 필터링 조건을 레짐에 따라 조정
- 레짐 기반 cutoff 적용
- 강세장/약세장에 따른 조건 완화/강화

미국 주식도 동일한 로직을 적용하면 **일관성**과 **정확도**가 향상됩니다.

#### 2. **Global Regime v4 활용 가능**

Global Regime v4는 이미 한국과 미국 데이터를 모두 사용합니다:
- 한국: KOSPI, KOSDAQ
- 미국: SPY, QQQ, VIX

따라서 **미국 시장 레짐 분석도 이미 가능한 상태**입니다.

#### 3. **레짐 기반 Cutoff의 효과**

현재 코드에 레짐 기반 cutoff 로직이 있지만, `market_condition = None`이면 작동하지 않습니다:

```python
# 현재: market_condition = None
# → _apply_regime_cutoff()가 호출되지 않음
# → 모든 레짐에서 동일한 기준 적용 (비효율적)

# 레짐 분석 적용 시:
# → bull: swing 6.0, position 4.3 (완화)
# → bear: swing 999.0, position 5.5 (강화)
# → crash: swing 999.0, position 999.0 (비활성화)
```

#### 4. **필터링 조건의 동적 조정**

레짐 분석 없이는:
- RSI 임계값: 고정값 사용
- 최소 신호 개수: 고정값 사용
- 거래량 배수: 고정값 사용
- 강세장 조건 완화: 적용 안 됨

레짐 분석 적용 시:
- 모든 조건이 레짐에 따라 자동 조정
- 강세장에서는 더 많은 종목 선정
- 약세장에서는 보수적 선정

---

## 구현 방안

### 옵션 1: Global Regime v4 활용 (권장)

**장점**:
- 이미 구현되어 있음
- 한국과 미국 데이터를 모두 고려
- 일관된 레짐 분석

**구현**:
```python
# backend/main.py - scan_us_stocks()
if config.market_analysis_enable:
    try:
        # Global Regime v4 사용 (한국+미국 통합 분석)
        market_condition = market_analyzer.analyze_market_condition(
            today_as_of, 
            regime_version='v4'
        )
    except Exception as e:
        print(f"⚠️ 미국 시장 분석 실패: {e}")
        market_condition = None
```

### 옵션 2: 미국 시장 전용 레짐 분석

**장점**:
- 미국 시장에 특화된 분석
- 미국 시장만의 특성 반영 가능

**단점**:
- 별도 구현 필요
- Global Regime과의 일관성 문제 가능

**구현**:
```python
# backend/services/us_regime_analyzer.py 활용
from services.us_regime_analyzer import USRegimeAnalyzer

us_regime_analyzer = USRegimeAnalyzer()
us_regime_result = us_regime_analyzer.analyze_us_market(today_as_of)
# MarketCondition 객체로 변환 필요
```

---

## 결론

### ✅ **미국 시장 레짐 분석이 필요합니다**

**이유**:
1. 코드 구조가 이미 준비되어 있음
2. 레짐 기반 cutoff와 필터링 조건 조정이 효과적
3. Global Regime v4 활용 가능
4. 한국 주식과의 일관성 확보

**권장 구현**:
- **Global Regime v4 활용** (옵션 1)
- `market_analyzer.analyze_market_condition(date, regime_version='v4')` 사용
- 이미 한국과 미국 데이터를 모두 고려하므로 적합

**예상 효과**:
- 레짐별 점수 cutoff 적용 → 더 정확한 종목 선정
- 레짐별 필터링 조건 조정 → 시장 상황에 맞는 선정
- 강세장/약세장 대응 → 리스크 관리 개선

---

## 다음 단계

1. **Global Regime v4를 미국 주식 스캔에 적용**
2. **테스트**: 레짐별 cutoff와 필터링 조건이 정상 작동하는지 확인
3. **성능 검증**: 레짐 분석 적용 전후 비교

