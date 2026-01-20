# Fallback 지표 분석

## 현재 Fallback 구조 (개선됨 ✅)

### 통합 Fallback: 점수와 지표를 동시에 Fallback

1. **Step 0**: 기본 조건 (10점 이상만, 지표 완화 없음)
2. **Step 1**: 지표 완화 Level 1 + 10점 이상
   - `min_signals: 3`, `vol_ma5_mult: 2.0`
3. **Step 2**: 지표 완화 Level 1 + 8점 이상 (점수 Fallback)
   - 동일 지표 완화 + 8점 이상 포함
4. **Step 3+**: 지표 추가 완화 + 8점 이상
   - `min_signals: 2`, `vol_ma5_mult: 1.8` 등 추가 완화

### 지표 Fallback 목록

- **min_signals**: 3 → 2 → 1 (신호 개수 완화)
- **vol_ma5_mult**: 2.5 → 2.0 → 1.8 → 1.5 → 1.3 (거래량 조건 완화)
- **vol_ma20_mult**: 1.2 → 1.1 (거래량 조건 완화)
- **gap_max**: 0.015 → 0.025 (갭 범위 완화)
- **ext_from_tema20_max**: 0.015 → 0.025 (이격 범위 완화)
- **require_dema_slope**: required → optional (DEMA 슬로프 완화)

## 개선 효과

### 기존 문제점
1. **Step 0-1**: 점수만 Fallback, 지표는 완화하지 않음
2. **Step 2+**: 지표 완화 시작, 하지만 이미 8-9점까지 포함한 상태
3. **비효율적**: 10점 이상이 없을 때 지표 완화 없이 8-9점만 찾음

### 개선된 구조
1. **Step 1**: 지표 완화로 더 많은 10점 이상 종목 발견 가능
2. **Step 2**: 지표 완화 후에도 10점 이상이 부족하면 8점 이상으로 Fallback
3. **Step 3+**: 지표 추가 완화로 목표 개수 달성 가능성 향상

## 구현 상세

### Fallback Preset
```python
fallback_presets = [
    # step 0: current strict (현 설정 그대로 사용)
    {},
    # step 1: 신호 및 거래량 약간 완화 (현재 강화된 파라미터 고려)
    {"min_signals": 3, "vol_ma5_mult": 2.0},  # 완화 (현재 5/2.2 → 3/2.0)
    # step 2: 추가 완화
    {"min_signals": 2, "vol_ma5_mult": 1.8},  # 더 완화
    # step 3: 거래량 현실적 완화
    {"min_signals": 2, "vol_ma5_mult": 1.5, "vol_ma20_mult": 1.1},  # 거래량 현실적 완화
    # step 4: 갭/이격 범위 완화
    {"min_signals": 2, "vol_ma5_mult": 1.5, "gap_max": 0.025, "ext_from_tema20_max": 0.025},  # 갭/이격 완화
    # step 5: 최종 현실적 완화 (DEMA 슬로프도 완화)
    {"min_signals": 1, "vol_ma5_mult": 1.3, "require_dema_slope": "optional"},  # 최종 완화
]
```

### Fallback 로직
```python
# Step 0: 기본 조건 (10점 이상만, 지표 완화 없음)
items = scan_with_preset(universe, {}, date, market_condition)
items_10_plus = [item for item in items if item.get("score", 0) >= 10]

# Step 1: 지표 완화 Level 1 + 10점 이상
if len(items_10_plus) < target_min:
    items = scan_with_preset(universe, config.fallback_presets[1], date, market_condition)
    items_10_plus = [item for item in items if item.get("score", 0) >= 10]

# Step 2: 지표 완화 Level 1 + 8점 이상 (점수 Fallback)
if len(items_10_plus) < target_min:
    items_8_plus = [item for item in items if item.get("score", 0) >= 8]

# Step 3+: 지표 추가 완화 + 8점 이상
if len(items_8_plus) < target_min:
    for overrides in config.fallback_presets[2:]:
        items = scan_with_preset(universe, overrides, date, market_condition)
        items_8_plus = [item for item in items if item.get("score", 0) >= 8]
        if len(items_8_plus) >= target_min:
            break
```

## 결론

### 개선 완료 ✅
- **점수와 지표를 동시에 Fallback**하는 통합 구조 구현
- **지표 완화로 더 많은 10점 이상 종목 발견 가능**
- **지표 완화 후에도 10점 이상이 부족하면 8점 이상으로 Fallback**
- **더 효율적인 Fallback 순서로 목표 개수 달성 가능성 향상**

### 효과
1. **10점 이상이 없을 때 지표를 완화하여 더 많은 10점 이상 종목 발견 가능**
2. **지표 완화 후에도 10점 이상이 부족하면 8점 이상으로 Fallback**
3. **지표 추가 완화로 목표 개수 달성 가능성 향상**
