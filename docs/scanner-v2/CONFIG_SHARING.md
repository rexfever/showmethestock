# 스캐너 V1/V2 설정 공유 정책

## 개요

스캐너 V2는 V1과 **대부분의 설정을 공유**합니다. V2 전용 설정(`SCANNER_V2_` 접두사)이 없으면 V1 설정을 자동으로 사용합니다.

## 설정 우선순위

1. **V2 전용 설정** (`SCANNER_V2_*`) - 최우선
2. **V1 설정** (`*` 접두사 없음) - Fallback
3. **기본값** - 최종 Fallback

## 예시

### 시나리오 1: V2 전용 설정 없음

```bash
# .env
MIN_SIGNALS=3
GAP_MAX=0.015
VOL_MA5_MULT=2.5
```

**결과:**
- V1: `MIN_SIGNALS=3` 사용
- V2: `MIN_SIGNALS=3` 사용 (V1 설정 공유)

### 시나리오 2: V2 전용 설정 있음

```bash
# .env
MIN_SIGNALS=3          # V1용
SCANNER_V2_MIN_SIGNALS=4  # V2 전용 (우선)
GAP_MAX=0.015          # V1/V2 공통 (V2 전용 없음)
```

**결과:**
- V1: `MIN_SIGNALS=3` 사용
- V2: `MIN_SIGNALS=4` 사용 (V2 전용 설정 우선)
- V1/V2 모두: `GAP_MAX=0.015` 사용 (공통)

## 공유되는 설정 목록

다음 설정들은 V1과 V2가 공유합니다 (V2 전용 설정이 없으면):

- `MIN_SIGNALS` → `SCANNER_V2_MIN_SIGNALS`
- `MACD_OSC_MIN` → `SCANNER_V2_MACD_OSC_MIN`
- `RSI_THRESHOLD` → `SCANNER_V2_RSI_THRESHOLD`
- `GAP_MIN` → `SCANNER_V2_GAP_MIN`
- `GAP_MAX` → `SCANNER_V2_GAP_MAX`
- `EXT_FROM_TEMA20_MAX` → `SCANNER_V2_EXT_FROM_TEMA20_MAX`
- `VOL_MA5_MULT` → `SCANNER_V2_VOL_MA5_MULT`
- `VOL_MA20_MULT` → `SCANNER_V2_VOL_MA20_MULT`
- `MIN_TURNOVER_KRW` → `SCANNER_V2_MIN_TURNOVER_KRW`
- `USE_ATR_FILTER` → `SCANNER_V2_USE_ATR_FILTER`
- `ATR_PCT_MAX` → `SCANNER_V2_ATR_PCT_MAX`
- `ATR_PCT_MIN` → `SCANNER_V2_ATR_PCT_MIN`
- `MIN_PRICE` → `SCANNER_V2_MIN_PRICE`
- `OVERHEAT_RSI_TEMA` → `SCANNER_V2_OVERHEAT_RSI_TEMA`
- `OVERHEAT_VOL_MULT` → `SCANNER_V2_OVERHEAT_VOL_MULT`
- `RISK_SCORE_THRESHOLD` → `SCANNER_V2_RISK_SCORE_THRESHOLD`
- `SCORE_W_*` (모든 점수 가중치) → `SCANNER_V2_SCORE_W_*`
- `TREND_SLOPE_LOOKBACK` → `SCANNER_V2_TREND_SLOPE_LOOKBACK`
- `TREND_ABOVE_LOOKBACK` → `SCANNER_V2_TREND_ABOVE_LOOKBACK`
- `REQUIRE_DEMA_SLOPE` → `SCANNER_V2_REQUIRE_DEMA_SLOPE`

## V2 전용 설정

다음 설정은 V2에서만 사용되며, V1 설정이 없습니다:

- `SCANNER_V2_RSI_UPPER_LIMIT_OFFSET` (기본값: 25.0)

## 장점

1. **중복 제거**: 같은 설정을 두 번 정의할 필요 없음
2. **일관성**: V1과 V2가 기본적으로 같은 설정 사용
3. **유연성**: 필요한 경우에만 V2 전용 설정 추가
4. **간편함**: 대부분의 경우 .env 파일 수정 불필요

## 사용 예시

### 기본 사용 (V1 설정 공유)

```bash
# .env
SCANNER_VERSION=v2
SCANNER_V2_ENABLED=true

# V1 설정 그대로 사용 (추가 설정 불필요)
MIN_SIGNALS=3
GAP_MAX=0.015
```

### V2 전용 설정 추가

```bash
# .env
SCANNER_VERSION=v2
SCANNER_V2_ENABLED=true

# V1 설정
MIN_SIGNALS=3
GAP_MAX=0.015

# V2 전용 설정 (V1과 다르게 설정)
SCANNER_V2_MIN_SIGNALS=4  # V2만 4개 필요
# GAP_MAX는 V1 설정(0.015) 그대로 사용
```

## 구현

`scanner_v2/config_v2.py`의 `_get_env_with_fallback()` 함수가 이 로직을 처리합니다:

```python
def _get_env_with_fallback(v2_key: str, v1_key: str, default: str):
    """V2 전용 설정이 있으면 사용, 없으면 V1 설정을 fallback으로 사용"""
    v2_value = os.getenv(v2_key)
    if v2_value is not None:
        return v2_value
    return os.getenv(v1_key, default)
```

