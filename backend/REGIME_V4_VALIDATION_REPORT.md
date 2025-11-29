# Regime v4 + Scanner v2 구조 검증 보고서

## 검증 일시
2025-11-29

## 검증 결과 요약

| 항목 | PASS | FAIL | 상태 |
|------|------|------|------|
| 1. market_analyzer.py 검증 | 1 | 7 | ❌ FAIL |
| 2. 단기 변동 조건 변경 검증 | 7 | 1 | ⚠️ 부분 FAIL |
| 3. scanner_v2/core/scanner.py 검증 | 1 | 3 | ❌ FAIL |
| 4. config_regime.py 검증 | 4 | 0 | ✅ PASS |
| 5. scan_service.py 검증 | 3 | 0 | ✅ PASS |
| 6. 테스트 검증 | 0 | 1 | ❌ FAIL |
| 7. FAIL 조건 확인 | 0 | 1 | ❌ CRITICAL FAIL |
| **총계** | **15** | **13** | **❌ FAIL** |

---

## 1. market_analyzer.py 검증

### ❌ FAIL 항목

#### (1) compute_long_regime() 구현 없음
- **요구사항**: 20~60일 기준 레짐 계산 함수
- **현재 상태**: 함수 없음
- **영향**: 장기 레짐 분석 불가

#### (2) compute_mid_regime() 구현 없음 ⚠️ **핵심**
- **요구사항**: 5~20일 기준 레짐 계산 함수 (스캔 조건의 핵심)
- **현재 상태**: 함수 없음
- **현재 구현**: `analyze_regime_v4()`에서 `final_regime`만 계산
- **영향**: **스캔 조건이 단기 변동에 영향받음**

#### (3) compute_short_term_risk() 구현 없음
- **요구사항**: 당일 KOSPI, 미국선물, VIX 기반 단기 리스크 점수 (0~3)
- **현재 상태**: 함수 없음
- **영향**: 단기 리스크 기반 후보 제거 불가

#### (4) compose_final_regime_v4() 구현 없음
- **요구사항**: midterm_regime을 final_regime으로 사용하는 함수
- **현재 상태**: 함수 없음
- **현재 구현**: `combine_global_regime_v4()`에서 직접 final_regime 계산
- **영향**: midterm_regime과 final_regime의 분리 불가

#### (5) MarketCondition 필드 부재
- **longterm_regime**: 없음
- **midterm_regime**: 없음 ⚠️ **핵심**
- **short_term_risk_score**: 없음

### ✅ PASS 항목
- `analyze_market_condition_v4()` 존재

---

## 2. 단기 변동이 스캔 조건을 변경하지 않는지 검증

### ✅ PASS 항목
- 당일 KOSPI 변동이 gap_max에 영향 없음
- 당일 KOSPI 변동이 ext_from_tema20_max에 영향 없음
- 당일 KOSPI 변동이 ATR에 영향 없음
- 당일 KOSPI 변동이 slope에 영향 없음
- 당일 KOSPI 변동이 min_signals에 영향 없음
- step override 로직 없음
- short_term_risk_score가 cutoff 변경 안 함

### ❌ FAIL 항목
- **scanner.py에서 midterm_regime 사용 안 함**
  - 현재: `final_regime` 사용
  - 요구: `midterm_regime` 사용
  - **문제**: final_regime은 단기 변동에 영향받을 수 있음

---

## 3. scanner_v2/core/scanner.py 검증

### ❌ FAIL 항목

#### (1) _apply_regime_cutoff가 midterm_regime 사용 안 함
```python
# 현재 구현 (scanner.py:227)
regime = market_condition.final_regime if market_condition.final_regime is not None else market_condition.market_sentiment
```
- **문제**: `final_regime` 사용 (단기 변동 영향 가능)
- **요구**: `midterm_regime` 사용

#### (2) short_term_risk_score가 risk_score에 가중 적용 안 함
- **현재 상태**: 코드에서 사용 안 함
- **요구사항**: `risk_score += short_term_risk_score` 형태로 가중 적용

#### (3) 후보 제거 기준이 (score - risk_score) < cutoff가 아님
- **현재 구현**: `score >= cutoff` 형태
- **요구사항**: `(score - risk_score) >= cutoff` 형태

### ✅ PASS 항목
- 당일 변동률이 gap/ext/ATR/slope 조정 안 함

---

## 4. config_regime.py 검증

### ✅ PASS 항목
- REGIME_CUTOFFS 존재
- crash에서 swing 999 차단
- crash에서 position 999 차단
- bear에서 swing 999 차단

---

## 5. scan_service.py 검증

### ✅ PASS 항목
- `analyze_market_condition_v4()` 호출
- fallback_presets에서 gap 조정 없음
- fallback에서 조건 변경 없음 (수량 확보만 담당)

---

## 6. 테스트 검증

### 테스트 결과

| 날짜 | midterm_regime | final_regime | short_term_risk_score | 스캔 결과 |
|------|----------------|--------------|----------------------|-----------|
| 20250723 | **None** | bull | **None** | 17개 |
| 20250917 | **None** | bull | **None** | 7개 |
| 20251022 | **None** | bull | **None** | 15개 |
| 20250820 | **None** | bull | **None** | 20개 |
| 20251105 | **None** | neutral | **None** | 0개 |

### ❌ FAIL 항목
- **midterm_regime이 없어 테스트 불가**
  - 모든 날짜에서 `midterm_regime = None`
  - `short_term_risk_score = None`
  - **결과**: midterm_regime이 동일한 날의 스캔 조건 일관성 검증 불가

---

## 7. FAIL 조건 확인

### ❌ CRITICAL FAIL
- **final_regime 대신 midterm_regime 비사용**
  - 현재: `_apply_regime_cutoff()`에서 `final_regime` 사용
  - 문제: `final_regime`은 단기 변동에 영향받을 수 있음
  - 요구: `midterm_regime` 사용 (5~20일 기준, 단기 변동 무관)

---

## 파일별 수정 필요사항

### 1. backend/market_analyzer.py

#### 추가 필요 함수:
```python
def compute_long_regime(self, date: str) -> str:
    """20~60일 기준 레짐 계산"""
    # 구현 필요

def compute_mid_regime(self, date: str) -> str:
    """5~20일 기준 레짐 계산 (스캔 조건의 핵심)"""
    # 구현 필요

def compute_short_term_risk(self, date: str) -> int:
    """당일 KOSPI/미국선물/VIX 기반 단기 리스크 점수 (0~3)"""
    # 구현 필요

def compose_final_regime_v4(self, midterm_regime: str, short_term_risk_score: int) -> str:
    """midterm_regime을 final_regime으로 사용"""
    # midterm_regime을 그대로 final_regime으로 사용
    # short_term_risk_score는 포함하되 final_regime 변경에 사용하지 않음
    return midterm_regime
```

#### MarketCondition 필드 추가:
```python
@dataclass
class MarketCondition:
    # ... 기존 필드 ...
    longterm_regime: Optional[str] = None
    midterm_regime: Optional[str] = None  # 스캔 조건의 핵심
    short_term_risk_score: Optional[int] = None  # 0~3, 후보 제거 목적
```

### 2. backend/scanner_v2/core/scanner.py

#### _apply_regime_cutoff 수정:
```python
def _apply_regime_cutoff(self, results: List[ScanResult], market_condition: MarketCondition) -> List[ScanResult]:
    # 현재: final_regime 사용
    # regime = market_condition.final_regime if market_condition.final_regime is not None else market_condition.market_sentiment
    
    # 수정: midterm_regime 사용
    regime = market_condition.midterm_regime if market_condition.midterm_regime is not None else market_condition.market_sentiment
    # ...
```

#### short_term_risk_score를 risk_score에 가중 적용:
```python
# 점수 계산 후
risk_score, risk_flags = self.scorer.calculate_score(df, market_condition)

# short_term_risk_score 가중 적용
if market_condition and hasattr(market_condition, 'short_term_risk_score'):
    risk_score += market_condition.short_term_risk_score

# 후보 제거 기준
if (score - risk_score) < cutoff:
    # 제거
```

### 3. backend/scanner_v2/config_regime.py

#### ✅ 현재 상태 양호
- REGIME_CUTOFFS 존재
- crash/bear 차단 로직 정상

---

## 개선 필요사항

### 1. **핵심 구조 미구현** ⚠️ **최우선**
- `compute_mid_regime()` 구현 필요 (5~20일 기준)
- `midterm_regime` 필드 추가 및 사용
- `short_term_risk_score` 필드 추가 및 사용

### 2. **cutoff 결정 로직 수정**
- `_apply_regime_cutoff()`에서 `final_regime` → `midterm_regime` 변경
- 단기 변동이 cutoff에 영향주지 않도록 보장

### 3. **후보 제거 기준 수정**
- 현재: `score >= cutoff`
- 요구: `(score - risk_score) >= cutoff`
- `risk_score`에 `short_term_risk_score` 가중 적용

### 4. **테스트 검증 불가**
- `midterm_regime`이 없어 동일 midterm_regime 날의 스캔 조건 일관성 검증 불가
- 구현 후 재검증 필요

---

## 결론

### ❌ **검증 FAIL**

**주요 문제점:**
1. **핵심 구조 미구현**: `compute_mid_regime()`, `midterm_regime` 필드 등 핵심 구조가 구현되지 않음
2. **단기 변동 영향 가능성**: `final_regime` 사용으로 인해 단기 변동이 스캔 조건에 영향을 줄 수 있음
3. **후보 제거 로직 미구현**: `short_term_risk_score` 기반 후보 제거 로직 없음

**즉시 수정 필요:**
- `compute_mid_regime()` 구현
- `MarketCondition.midterm_regime` 필드 추가
- `_apply_regime_cutoff()`에서 `midterm_regime` 사용
- `short_term_risk_score` 기반 후보 제거 로직 구현

**예상 작업 시간:** 4-6시간

