# Regime v4 + Scanner v2 최종 검증 보고서

## 검증 일시
2025-11-30

## [검증 1] market_analyzer.py

### 1) MarketCondition dataclass 필드 확인

**파일**: `backend/market_analyzer.py` (73-75줄)

```python
longterm_regime: Optional[str] = None  # 20~60일 기준 장기 레짐
midterm_regime: Optional[str] = None  # 5~20일 기준 중기 레짐 (스캔 조건의 핵심)
short_term_risk_score: Optional[int] = None  # 0~3, 당일 단기 리스크 점수
```

**결과**: ✅ **PASS**
- 모든 필드 존재 확인

### 2) 함수 존재 및 구현 확인

**파일**: `backend/market_analyzer.py`

- ✅ `compute_long_regime()` (464줄): 구현됨
- ✅ `compute_mid_regime()` (513줄): 구현됨
- ✅ `compute_short_term_risk()` (574줄): 구현됨
- ✅ `compose_final_regime_v4()` (668줄): 구현됨, `return midterm_regime`

**결과**: ✅ **PASS**

### 3) analyze_market_condition_v4() 구현 확인

**파일**: `backend/market_analyzer.py` (1327-1336줄)

```python
longterm_regime = self.compute_long_regime(date)
midterm_regime = self.compute_mid_regime(date)
short_term_risk_score = self.compute_short_term_risk(date)
final_regime = self.compose_final_regime_v4(midterm_regime)

base_condition.longterm_regime = longterm_regime
base_condition.midterm_regime = midterm_regime
base_condition.short_term_risk_score = short_term_risk_score
base_condition.final_regime = final_regime
```

**결과**: ✅ **PASS**
- 모든 필드 계산 및 할당 확인
- `final_regime = compose_final_regime_v4(midterm_regime)` 확인

---

## [검증 2] scanner_v2/core/scanner.py

### 1) _apply_regime_cutoff() - midterm_regime 우선 사용

**파일**: `backend/scanner_v2/core/scanner.py` (228-240줄)

```python
# v4 구조: midterm_regime 우선 사용 (스캔 조건의 핵심)
regime = None
if market_condition is not None:
    if getattr(market_condition, "midterm_regime", None) is not None:
        regime = market_condition.midterm_regime
    elif getattr(market_condition, "final_regime", None) is not None:
        regime = market_condition.final_regime
    else:
        regime = getattr(market_condition, "market_sentiment", None)
```

**결과**: ✅ **PASS**
- `midterm_regime` 우선 사용 확인
- fallback으로 `final_regime`, `market_sentiment` 순서 확인

### 2) short_term_risk_score 가중 적용

**파일**: `backend/scanner_v2/core/scanner.py` (268-272줄)

```python
# v4 구조: short_term_risk_score를 risk_score에 가중 적용
if market_condition is not None:
    short_term_risk = getattr(market_condition, "short_term_risk_score", None)
    if short_term_risk is not None:
        risk_score = (risk_score or 0) + short_term_risk
```

**결과**: ✅ **PASS**
- `risk_score = (risk_score or 0) + short_term_risk_score` 구현 확인

### 3) 후보 제거 기준

**파일**: `backend/scanner_v2/core/scanner.py` (274-275줄)

```python
# effective_score = score - risk_score
effective_score = (score or 0) - (risk_score or 0)
```

**파일**: `backend/scanner_v2/core/scanner.py` (278, 282, 286줄)

```python
if effective_score >= regime_cutoffs['swing']:
    filtered_results['swing'].append(result)
if effective_score >= regime_cutoffs['position']:
    filtered_results['position'].append(result)
if effective_score >= regime_cutoffs['longterm']:
    filtered_results['longterm'].append(result)
```

**결과**: ✅ **PASS**
- `(score - risk_score) >= cutoff` 기준 사용 확인

### 4) config_regime.py cutoff 동작 확인

**파일**: `backend/scanner_v2/core/scanner.py` (257줄)

```python
regime_cutoffs = cutoffs.get(regime, cutoffs['neutral'])
```

**결과**: ✅ **PASS**
- `config_regime.py`의 `REGIME_CUTOFFS` 사용 확인

---

## [검증 3] config_regime.py

**파일**: `backend/scanner_v2/config_regime.py` (22-26줄)

```python
'crash': {
    'swing': 999.0,    # 급락장에서 단기 매매 비활성화
    'position': 999.0, # 급락장에서 중기 포지션 비활성화
    'longterm': 6.0    # 급락장에서 장기 투자만 조건부 허용
}
```

**결과**: ✅ **PASS**
- `swing`: 999.0 ✅
- `position`: 999.0 ✅
- `longterm`: 6.0 ✅
- 기존 `longterm=999` 흔적 없음 ✅

---

## [검증 4] scan_service.py

### 1) crash_detected 시 스캔 중단 없음

**파일**: `backend/services/scan_service.py` (316-330줄)

```python
# 급락장/crash 감지 로그 (스캔은 계속 진행, cutoff로 제어)
crash_detected = False
if market_condition:
    # ... (로그만 출력)
    
# crash여도 스캔은 진행 (cutoff로 swing/position 차단, longterm만 허용)
```

**결과**: ✅ **PASS**
- crash 감지 후 `return [], None` 코드 없음
- 스캔 계속 진행

### 2) crash_detected는 로그 출력만

**파일**: `backend/services/scan_service.py` (321, 324, 328줄)

```python
print(f"🔴 Global Regime v4 급락장 감지 - longterm horizon만 허용")
print(f"🔴 급락장 감지 (midterm_regime=crash) - longterm horizon만 허용")
print(f"🔴 급락장 감지 (KOSPI: {kospi_return:.2f}%) - longterm horizon만 허용")
```

**결과**: ✅ **PASS**
- 로그만 출력, 스캔 중단 없음

### 3) 스캔은 항상 진행

**파일**: `backend/services/scan_service.py` (330줄 이후)

**결과**: ✅ **PASS**
- crash 감지 후에도 스캔 로직 계속 진행

### 4) horizon별 필터링은 scanner_v2에서 처리

**파일**: `backend/scanner_v2/core/scanner.py` (222-300줄)

**결과**: ✅ **PASS**
- `_apply_regime_cutoff()`에서 horizon별 필터링 처리

### 5) crash 감지 후 return [], None 코드 검색

**검색 결과**: `backend/services/scan_service.py`
- 361줄: `return [], None, current_scanner_version` (스캔 오류 시)
- 380줄: `return [], None, current_scanner_version` (Step 0 스캔 오류 시)
- 407줄: `return [], None, current_scanner_version` (fallback_presets 인덱스 오류 시)
- 411줄: `return [], None, current_scanner_version` (Step 1 스캔 오류 시)

**분석**: 모두 오류 처리용이며, crash 감지와 무관

**결과**: ✅ **PASS**
- crash 감지 후 빈 리스트 반환 코드 없음

---

## [검증 5] end-to-end 테스트

**테스트 스크립트**: `backend/tests/test_regime_v4_final_verification.py`

**실행 필요**: 실제 스캔 수행 (로컬 환경 의존성 필요)

**검증 기준**:
- crash: swing=0, position=0, longterm ≥ 0
- bear: swing=0, position ≤ 8
- neutral/bull: swing ≤ 20, position ≤ 15

**상태**: ⚠️ **테스트 스크립트 작성 완료, 실행 대기**

---

## [검증 6] fallback 로직 확인

**검색 결과**: `backend/services/scan_service.py`

**검색 패턴**: `gap.*=|ext.*=|atr.*=|min_signals.*=`

**결과**: ✅ **PASS**
- fallback 단계에서 gap/ext/ATR/min_signals 변경 코드 없음
- fallback은 수량 확보 목적만 담당

---

## [검증 7] 소스코드 일관성 검사

### 1) final_regime을 cutoff에 사용하는 코드

**검색 결과**: `backend/scanner_v2/core/scanner.py` (235줄)

```python
elif getattr(market_condition, "final_regime", None) is not None:
    regime = market_condition.final_regime
```

**분석**: fallback으로만 사용, `midterm_regime` 우선

**결과**: ✅ **PASS**
- `midterm_regime` 우선 사용, `final_regime`은 fallback

### 2) short_term_risk_score가 score에 더해지는 코드

**검색 결과**: 없음

**결과**: ✅ **PASS**
- `short_term_risk_score`는 `risk_score`에만 가중 적용

### 3) cutoff 비교에서 risk_score 미반영된 코드

**검색 결과**: `backend/scanner_v2/core/scanner.py` (278, 282, 286줄)

```python
if effective_score >= regime_cutoffs['swing']:
```

**분석**: `effective_score = score - risk_score` 사용

**결과**: ✅ **PASS**
- `risk_score` 반영됨

### 4) midterm_regime 계산 누락

**검색 결과**: `backend/market_analyzer.py` (1328줄)

```python
midterm_regime = self.compute_mid_regime(date)
```

**결과**: ✅ **PASS**
- `midterm_regime` 계산 및 할당 확인

---

## 최종 검증 결과

| 검증 항목 | 상태 | 비고 |
|----------|------|------|
| [검증 1] market_analyzer.py | ✅ PASS | 모든 필드 및 함수 구현 확인 |
| [검증 2] scanner_v2/core/scanner.py | ✅ PASS | midterm_regime 우선, risk_score 가중 적용 |
| [검증 3] config_regime.py | ✅ PASS | crash longterm=6.0 확인 |
| [검증 4] scan_service.py | ✅ PASS | crash 차단 로직 제거 확인 |
| [검증 5] end-to-end 테스트 | ⚠️ 대기 | 테스트 스크립트 작성 완료 |
| [검증 6] fallback 로직 | ✅ PASS | gap/ext/ATR/min_signals 변경 없음 |
| [검증 7] 소스코드 일관성 | ✅ PASS | 모든 일관성 조건 만족 |

---

## 전체 PASS 여부

✅ **전체 PASS** (end-to-end 테스트 제외)

**주의사항**:
- end-to-end 테스트는 실제 스캔 실행이 필요하므로 로컬 환경에서 실행 필요
- 테스트 스크립트는 `backend/tests/test_regime_v4_final_verification.py`에 작성됨

