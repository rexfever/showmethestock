# OHLCV 캐시 24시간 후 동작 분석

## 현재 구현

### 시나리오: 장 마감 후 24시간 캐싱

```
16:00 (장 마감) → 캐시 저장 (TTL: 24시간)
  ↓
24시간 후 (다음날 16:00) → 캐시 만료
  ↓
재조회 → 새로운 데이터 조회
```

## 문제점

### 1. base_dt=None인 경우

**현재 로직**:
```python
def _calculate_ttl(self, base_dt: Optional[str]) -> int:
    if base_dt:
        # 과거 날짜 체크
        ...
    # base_dt=None: 현재 날짜로 간주
    if self._is_market_open():
        return 60  # 장중: 1분
    else:
        return 24 * 3600  # 장 마감 후: 24시간
```

**문제**:
- `base_dt=None`이면 항상 "현재 날짜"로 간주
- 24시간 후에도 여전히 "현재 날짜"로 인식
- 과거 날짜로 전환되지 않아 1년 캐싱이 적용되지 않음

**예시**:
```
2025-11-24 16:00: get_ohlcv("005930", 220, None)
  → 캐시 저장 (TTL: 24시간)
  → 2025-11-24 데이터

2025-11-25 16:01: get_ohlcv("005930", 220, None)
  → 캐시 만료 (24시간 경과)
  → 재조회 → 2025-11-25 데이터 (새로운 데이터)
  → 캐시 저장 (TTL: 24시간)
```

**결과**: 정상 동작하지만, 24시간 후에는 이미 다른 날짜 데이터가 필요함

### 2. base_dt가 명시된 경우

**현재 로직**:
```python
if base_dt:
    base_date = datetime.strptime(base_dt, "%Y%m%d").date()
    now_date = datetime.now().date()
    if base_date < now_date:
        return 365 * 24 * 3600  # 과거: 1년
```

**예시**:
```
2025-11-24 16:00: get_ohlcv("005930", 220, "20251124")
  → 캐시 저장 (TTL: 24시간, 장 마감 후)

2025-11-25 16:01: get_ohlcv("005930", 220, "20251124")
  → base_date (2025-11-24) < now_date (2025-11-25)
  → TTL: 1년 (과거 날짜로 인식)
  → 캐시에서 반환 (24시간이 지났지만 1년 TTL 적용)
```

**결과**: ✅ 정상 동작 - 과거 날짜로 전환되어 1년 캐싱 적용

## 개선 방안

### 옵션 1: 캐시 저장 시점의 날짜 기록 (권장)

**문제**: `base_dt=None`인 경우 실제 조회된 날짜를 알 수 없음

**해결**: 캐시에 조회된 날짜를 함께 저장

```python
# 캐시 구조 변경
self._ohlcv_cache: Dict[
    Tuple[str, int, Optional[str]], 
    Tuple[pd.DataFrame, float, str]  # (df, timestamp, actual_date)
] = {}

def _set_cached_ohlcv(self, code: str, count: int, base_dt: Optional[str], df: pd.DataFrame) -> None:
    """OHLCV 데이터를 캐시에 저장"""
    if df.empty:
        return
    
    # 실제 조회된 날짜 추출 (DataFrame의 마지막 날짜)
    actual_date = None
    if not df.empty and 'date' in df.columns:
        try:
            last_date_str = str(df.iloc[-1]['date'])
            if len(last_date_str) == 8 and last_date_str.isdigit():
                actual_date = last_date_str
        except:
            pass
    
    cache_key = self._get_cache_key(code, count, base_dt)
    
    # 캐시 저장 (actual_date 포함)
    self._ohlcv_cache[cache_key] = (df.copy(), time.time(), actual_date)

def _get_cached_ohlcv(self, code: str, count: int, base_dt: Optional[str]) -> Optional[pd.DataFrame]:
    """캐시에서 OHLCV 데이터 조회"""
    cache_key = self._get_cache_key(code, count, base_dt)
    
    if cache_key not in self._ohlcv_cache:
        return None
    
    cached_df, timestamp, actual_date = self._ohlcv_cache[cache_key]
    
    # actual_date를 사용하여 TTL 계산
    ttl = self._calculate_ttl(actual_date)  # base_dt 대신 actual_date 사용
    
    if time.time() - timestamp > ttl:
        del self._ohlcv_cache[cache_key]
        return None
    
    return cached_df.copy()
```

### 옵션 2: 캐시 조회 시 날짜 재확인

**간단한 방법**: 캐시 조회 시 DataFrame의 날짜를 확인하여 과거 날짜면 TTL 연장

```python
def _get_cached_ohlcv(self, code: str, count: int, base_dt: Optional[str]) -> Optional[pd.DataFrame]:
    """캐시에서 OHLCV 데이터 조회"""
    cache_key = self._get_cache_key(code, count, base_dt)
    
    if cache_key not in self._ohlcv_cache:
        return None
    
    cached_df, timestamp = self._ohlcv_cache[cache_key]
    
    # DataFrame의 실제 날짜 확인
    actual_date = None
    if not cached_df.empty and 'date' in cached_df.columns:
        try:
            last_date_str = str(cached_df.iloc[-1]['date'])
            if len(last_date_str) == 8 and last_date_str.isdigit():
                actual_date = last_date_str
        except:
            pass
    
    # actual_date를 사용하여 TTL 계산
    ttl = self._calculate_ttl(actual_date)
    
    if time.time() - timestamp > ttl:
        del self._ohlcv_cache[cache_key]
        return None
    
    return cached_df.copy()
```

## 권장 구현

### 옵션 2 선택 (더 간단하고 안전)

**이유**:
1. 캐시 구조 변경 최소화
2. DataFrame에 이미 날짜 정보가 있음
3. 조회 시점에 항상 최신 상태 확인

**구현**:
- `_get_cached_ohlcv()`에서 DataFrame의 마지막 날짜 확인
- 해당 날짜가 과거면 1년 TTL 적용
- 현재 날짜면 장중/장 마감 여부에 따라 TTL 적용

## 예상 동작

### 시나리오 1: base_dt=None, 24시간 후

```
2025-11-24 16:00: get_ohlcv("005930", 220, None)
  → 조회: 2025-11-24 데이터
  → 캐시 저장 (TTL: 24시간)

2025-11-25 16:01: get_ohlcv("005930", 220, None)
  → 캐시 확인: DataFrame의 마지막 날짜 = "20251124"
  → 2025-11-24 < 2025-11-25 (과거 날짜)
  → TTL: 1년 적용
  → 캐시에서 반환 (24시간이 지났지만 1년 TTL로 유효)
```

### 시나리오 2: base_dt="20251124", 24시간 후

```
2025-11-24 16:00: get_ohlcv("005930", 220, "20251124")
  → 캐시 저장 (TTL: 24시간)

2025-11-25 16:01: get_ohlcv("005930", 220, "20251124")
  → base_dt="20251124" < 현재 날짜
  → TTL: 1년 적용
  → 캐시에서 반환
```

## 결론

**현재 구현**:
- ✅ `base_dt`가 명시된 경우: 24시간 후 과거 날짜로 인식되어 1년 캐싱 적용
- ⚠️ `base_dt=None`인 경우: 24시간 후 재조회 (정상이지만 최적화 여지 있음)

**개선 필요**:
- `base_dt=None`인 경우에도 DataFrame의 실제 날짜를 확인하여 과거 날짜면 1년 캐싱 적용

