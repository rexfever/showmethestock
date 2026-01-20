# 코드 리뷰 - 문제점 분석

## 🔍 발견된 문제점

### 1. ⚠️ **변수 스코프 혼란** (중요도: 중간)

**위치**: `execute_scan_with_fallback` 함수 전체

**문제**:
- `items` 변수가 여러 단계에서 재사용되어 혼란스러움
- Step 0, Step 1, Step 3에서 각각 다른 의미로 사용됨

**현재 코드**:
```python
# Step 0
items = scan_with_preset(universe, {}, date, market_condition)
items_10_plus = [item for item in items if item.get("score", 0) >= 10]

# Step 1
items = scan_with_preset(universe, config.fallback_presets[1], date, market_condition)
items_10_plus = [item for item in items if item.get("score", 0) >= 10]

# Step 2 (Step 1의 items 재사용)
items_8_plus = [item for item in items if item.get("score", 0) >= 8]

# Step 3
items = scan_with_preset(universe, overrides, date, market_condition)
items_8_plus = [item for item in items if item.get("score", 0) >= 8]
```

**문제점**:
- Step 2에서 Step 1의 `items`를 재사용하는 것은 의도된 동작이지만, 변수명이 혼란스러움
- Step 3에서 `items`를 다시 할당하면 Step 2의 로직과 연결이 끊김

**권장 수정**:
```python
# Step별로 명확한 변수명 사용
step0_items = scan_with_preset(universe, {}, date, market_condition)
step0_items_10_plus = [item for item in step0_items if item.get("score", 0) >= 10]

step1_items = scan_with_preset(universe, config.fallback_presets[1], date, market_condition)
step1_items_10_plus = [item for item in step1_items if item.get("score", 0) >= 10]
step1_items_8_plus = [item for item in step1_items if item.get("score", 0) >= 8]  # Step 2용
```

### 2. ⚠️ **Fallback 비활성화 시 chosen_step 미설정** (중요도: 낮음)

**위치**: Line 179-186

**문제**:
- `use_fallback = False`일 때 `chosen_step`이 설정되지 않아 `None` 반환
- 일관성 문제

**현재 코드**:
```python
if not use_fallback:
    items = scan_with_preset(universe, {}, date, market_condition)
    items_10_plus = [item for item in items if item.get("score", 0) >= 10]
    items = items_10_plus[:config.top_k]
    print(f"📊 스캔 결과: {len(items)}개 종목 (10점 이상만, 조건 강화)")
    # chosen_step이 설정되지 않음!
```

**권장 수정**:
```python
if not use_fallback:
    items = scan_with_preset(universe, {}, date, market_condition)
    items_10_plus = [item for item in items if item.get("score", 0) >= 10]
    items = items_10_plus[:config.top_k]
    chosen_step = 0  # 기본 조건 사용
    print(f"📊 스캔 결과: {len(items)}개 종목 (10점 이상만, 조건 강화)")
```

### 3. ⚠️ **chosen_step 초기화 값** (중요도: 낮음)

**위치**: Line 192

**문제**:
- `chosen_step = 0`으로 초기화하지만, 실제로는 Step 0이 선택되지 않을 수 있음
- 초기값과 실제 선택값의 불일치

**현재 코드**:
```python
final_items = []
chosen_step = 0  # 초기값이지만 실제로는 None일 수도 있음
```

**권장 수정**:
```python
final_items = []
chosen_step = None  # 명확한 초기값
```

### 4. ✅ **Step 2의 items 재사용** (의도된 동작, 하지만 주석 필요)

**위치**: Line 216-219

**현재 코드**:
```python
# Step 2: 지표 완화 Level 1 + 8점 이상 (점수 Fallback)
print(f"🔄 Step 2: 지표 완화 Level 1 + 8점 이상")
items_8_plus = [item for item in items if item.get("score", 0) >= 8]  # Step 1의 items 재사용
```

**설명**:
- Step 2는 Step 1의 결과를 재사용하여 8점 이상으로 필터링
- 이는 의도된 동작이지만, 주석으로 명확히 표시 필요

**권장 수정**:
```python
# Step 2: 지표 완화 Level 1 + 8점 이상 (점수 Fallback)
# Step 1의 결과를 재사용하여 8점 이상으로 필터링
print(f"🔄 Step 2: 지표 완화 Level 1 + 8점 이상")
items_8_plus = [item for item in items if item.get("score", 0) >= 8]  # Step 1의 items 재사용
```

### 5. ⚠️ **Step 3의 for 루프 불필요** (중요도: 낮음)

**위치**: Line 230

**문제**:
- `fallback_presets[2:3]`는 단일 요소만 포함하므로 for 루프가 불필요
- 가독성 저하

**현재 코드**:
```python
# Step 3까지만 시도 (fallback_presets[2:3] = Step 3만)
for step_idx, overrides in enumerate(config.fallback_presets[2:3], start=3):
    # 단일 요소만 처리
```

**권장 수정**:
```python
# Step 3: 지표 추가 완화 + 8점 이상
print(f"🔄 Step 3: 지표 완화 Level 2 + 8점 이상")
overrides = config.fallback_presets[2]
print(f"   설정: {overrides}")
items = scan_with_preset(universe, overrides, date, market_condition)
items_8_plus = [item for item in items if item.get("score", 0) >= 8]
print(f"📊 Step 3 결과: {len(items_8_plus)}개 종목 (지표 완화 Level 2 + 8점 이상)")

if len(items_8_plus) >= target_min:
    chosen_step = 3
    final_items = items_8_plus[:min(config.top_k, target_max)]
    print(f"✅ Step 3에서 목표 달성: {len(final_items)}개 종목 선택")
else:
    print(f"❌ Step 3 목표 미달: {len(items_8_plus)} < {target_min}")
```

### 6. ⚠️ **에러 처리 부재** (중요도: 높음)

**위치**: 전체 함수

**문제**:
- `scan_with_preset` 호출 시 예외 처리 없음
- `config.fallback_presets` 인덱스 접근 시 예외 처리 없음

**권장 수정**:
```python
try:
    items = scan_with_preset(universe, {}, date, market_condition)
except Exception as e:
    print(f"❌ Step 0 스캔 오류: {e}")
    return [], None
```

### 7. ⚠️ **target_min/target_max 검증 부재** (중요도: 중간)

**위치**: Line 167-175

**문제**:
- `target_min`, `target_max` 값이 유효한지 검증하지 않음
- 음수나 비정상적인 값에 대한 처리 없음

**권장 수정**:
```python
# 장세별 MIN/MAX 설정
if market_condition and market_condition.market_sentiment == 'bear':
    target_min = max(1, config.fallback_target_min_bear)  # 최소 1개
    target_max = max(target_min, config.fallback_target_max_bear)  # 최소 target_min 이상
else:
    target_min = max(1, config.fallback_target_min_bull)
    target_max = max(target_min, config.fallback_target_max_bull)
```

### 8. ✅ **Step 3 이후 빈 리스트 반환** (정상 동작)

**위치**: Line 245-250

**설명**:
- Step 0~3 모두 목표 미달 시 빈 리스트 반환하는 것은 의도된 동작
- Step 7 제거가 올바르게 구현됨

## 📊 우선순위별 정리

### 높은 우선순위
1. **에러 처리 추가**: `scan_with_preset` 호출 시 try-except 추가
2. **target_min/target_max 검증**: 유효성 검사 추가

### 중간 우선순위
3. **변수 스코프 개선**: 명확한 변수명 사용
4. **Step 3 for 루프 제거**: 단일 요소이므로 직접 처리

### 낮은 우선순위
5. **Fallback 비활성화 시 chosen_step 설정**: 일관성 개선
6. **chosen_step 초기화**: None으로 변경
7. **주석 추가**: Step 2의 items 재사용 명확화

## 🎯 권장 수정 사항 요약

1. ✅ **에러 처리 추가** (필수)
2. ✅ **target_min/target_max 검증** (필수)
3. ⚠️ **변수명 개선** (권장)
4. ⚠️ **Step 3 for 루프 제거** (권장)
5. ⚠️ **일관성 개선** (선택)

