# Step 7까지 진행되는 이유 분석

## 🔍 Step 7이 나타나는 메커니즘

### Fallback Preset 구조

`config.fallback_presets`는 총 **6개** 요소를 가집니다 (인덱스 0~5):

| 인덱스 | Step | 설정 | 설명 |
|--------|------|------|------|
| 0 | Step 0 | `{}` | 기본 조건 (10점 이상만) |
| 1 | Step 1 | `{"min_signals": 3, "vol_ma5_mult": 2.0}` | 신호 및 거래량 약간 완화 |
| 2 | Step 3 | `{"min_signals": 2, "vol_ma5_mult": 1.8}` | 추가 완화 |
| 3 | Step 4 | `{"min_signals": 2, "vol_ma5_mult": 1.5, "vol_ma20_mult": 1.1}` | 거래량 현실적 완화 |
| 4 | Step 5 | `{"min_signals": 2, "vol_ma5_mult": 1.5, "gap_max": 0.025, ...}` | 갭/이격 범위 완화 |
| 5 | Step 6 | `{"min_signals": 1, "vol_ma5_mult": 1.3, "require_dema_slope": "optional"}` | 최종 완화 |

### Fallback 로직 흐름

```python
# Step 0: 기본 조건 (10점 이상만)
if len(items_10_plus) >= target_min:
    chosen_step = 0  # ✅ 목표 달성
else:
    # Step 1: 지표 완화 Level 1 + 10점 이상
    if len(items_10_plus) >= target_min:
        chosen_step = 1  # ✅ 목표 달성
    else:
        # Step 2: 지표 완화 Level 1 + 8점 이상
        if len(items_8_plus) >= target_min:
            chosen_step = 2  # ✅ 목표 달성
        else:
            # Step 3~6: 지표 추가 완화 + 8점 이상
            for step_idx, overrides in enumerate(config.fallback_presets[2:], start=3):
                # Step 3, 4, 5, 6 순차 실행
                if len(items_8_plus) >= target_min:
                    chosen_step = step_idx  # ✅ 목표 달성
                    break
                else:
                    continue
            
            # ⚠️ 모든 단계에서 목표 미달
            if not final_items:
                if items_8_plus:  # 마지막 단계에서 결과가 있다면
                    final_items = items_8_plus[:min(config.top_k, target_max)]
                    chosen_step = len(config.fallback_presets) + 1  # 👈 여기서 Step 7 생성!
                    # len(fallback_presets) = 6이므로 chosen_step = 7
```

## 🎯 Step 7이 나타나는 조건

**Step 7은 다음 조건에서 나타납니다:**

1. ✅ Step 0~6까지 **모든 단계에서 목표 개수 미달**
2. ✅ 하지만 **마지막 단계(Step 6)에서 결과가 1개 이상 있음**
3. ✅ 목표 미달이지만 **빈 리스트를 반환하지 않고 마지막 결과를 사용**

### 실제 사례 (2025-10-27)

```
📅 스캔 날짜: 20251027
📈 시장 상황: bull (+0.02%)
목표: 3~5개

Step 0: 0개 (목표 미달)
Step 1: 0개 (목표 미달)
Step 2: 0개 (목표 미달)
Step 3: 0개 (목표 미달)
Step 4: 0개 (목표 미달)
Step 5: 0개 (목표 미달)
Step 6: 2개 (목표 미달: 2 < 3)

⚠️ 모든 단계에서 목표 미달 - 마지막 단계 결과 사용
📊 최종 결과: 2개 종목 (마지막 단계)
🎯 최종 선택: Step 7, 2개 종목
```

## ⚠️ 문제점

### 1. Step 7은 "실패한 Fallback"의 표시

- Step 7은 **정상적인 Fallback 단계가 아님**
- 모든 단계에서 목표를 달성하지 못했지만, **마지막 결과를 강제로 사용**하는 것
- `chosen_step = len(config.fallback_presets) + 1`로 **임의로 생성된 값**

### 2. 품질 저하

검증 결과:
- **Step 0**: 평균 수익률 +3.26% ✅
- **Step 7**: 평균 수익률 +0.80% ⚠️
- **Step 7이 Step 0보다 4배 낮은 성과**

### 3. 목표 개수 미달을 무시

- 목표: 3~5개
- 실제: 2개
- 하지만 Step 7로 강제 사용하여 **품질 저하된 종목 추천**

## 🔧 개선 방안

### 방안 1: Step 7 제거 (권장) ⭐

**모든 단계에서 목표 미달 시 빈 리스트 반환**

```python
# 만약 모든 단계에서도 목표 미달이라면
if not final_items:
    print(f"⚠️ 모든 단계에서 목표 미달 - 추천 종목 없음")
    print(f"🔍 디버깅: universe={len(universe)}개, market_condition={market_condition}")
    final_items = []  # 빈 리스트 반환
    chosen_step = None  # Step 7 대신 None
```

**장점**:
- 품질 저하된 종목 추천 방지
- 명확한 실패 신호
- 사용자가 상황을 정확히 파악 가능

**단점**:
- 일부 날짜에 추천 종목이 없을 수 있음

### 방안 2: Step 7 품질 기준 강화

**Step 7에서도 최소 품질 기준 적용**

```python
if not final_items:
    if items_8_plus:
        # 최소 품질 기준 적용
        high_quality = [item for item in items_8_plus if item.get("score", 0) >= 9]
        if high_quality:
            final_items = high_quality[:min(config.top_k, target_max)]
            chosen_step = 7
        else:
            # 품질 기준 미달 시 빈 리스트
            final_items = []
            chosen_step = None
```

**장점**:
- Step 7에서도 최소 품질 유지
- 완전히 빈 리스트보다는 나음

**단점**:
- 여전히 목표 개수 미달

### 방안 3: Fallback 단계 제한

**Step 5 이상으로는 진행하지 않음**

```python
# Step 3~5까지만 시도
for step_idx, overrides in enumerate(config.fallback_presets[2:5], start=3):
    # Step 3, 4, 5만 실행
    if len(items_8_plus) >= target_min:
        chosen_step = step_idx
        break

# Step 5에서도 목표 미달이면 빈 리스트
if not final_items:
    final_items = []
    chosen_step = None
```

**장점**:
- 과도한 완화 방지
- 품질 유지

**단점**:
- 일부 날짜에 추천 종목이 없을 수 있음

## 📊 권장 조치

### 즉시 적용 (High Priority)

1. **Step 7 제거**: 모든 단계에서 목표 미달 시 빈 리스트 반환
2. **로깅 개선**: Step 7 대신 "목표 미달로 추천 없음" 명확히 표시

### 중기 개선 (Medium Priority)

1. **Fallback 단계 제한**: Step 5 이상으로는 진행하지 않음
2. **목표 개수 조정**: 장세별 목표를 현실적으로 조정 (예: 2~3개)

## 🎯 결론

**Step 7은 정상적인 Fallback 단계가 아니라 "실패한 Fallback"의 표시입니다.**

- 모든 단계에서 목표를 달성하지 못했지만
- 마지막 결과를 강제로 사용하기 위해
- `len(fallback_presets) + 1 = 7`로 임의 생성된 값

**권장**: Step 7을 제거하고, 목표 미달 시 빈 리스트를 반환하여 품질 저하를 방지해야 합니다.

