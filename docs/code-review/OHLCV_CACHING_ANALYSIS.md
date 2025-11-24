# OHLCV 데이터 캐싱 분석

## 분석 일시
2025-11-24

## 현재 상태

### 캐싱이 있는 곳

#### 1. `returns_service.py` ✅

```python
@lru_cache(maxsize=1000)
def _get_cached_ohlcv(ticker: str, count: int, base_dt: str = None) -> str:
    """캐시된 OHLCV 데이터 조회"""
    try:
        df = api.get_ohlcv(ticker, count, base_dt)
        if df.empty:
            return ""
        return df.to_json(orient='records')
    except Exception:
        return ""
```

**특징**:
- `@lru_cache(maxsize=1000)` 사용
- 최대 1000개 항목 캐싱
- JSON 문자열로 캐싱
- `calculate_returns()` 함수에서만 사용

**사용 위치**:
- `calculate_returns()`: 수익률 계산 시
- `calculate_returns_batch()`: 배치 수익률 계산 시

### 캐싱이 없는 곳

#### 1. `kiwoom_api.py` ❌

```python
def get_ohlcv(self, code: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
    """일봉 OHLCV DataFrame 반환"""
    # 캐싱 없음 - 매번 API 호출
    def _request(bdt: str) -> list:
        payload = {"stk_cd": code, "base_dt": bdt or "", "upd_stkpc_tp": "1"}
        d = self._post(api_id, path, payload)
        # ...
```

**문제점**:
- 캐싱 메커니즘 없음
- 매번 API 호출
- 같은 종목, 같은 날짜를 여러 번 조회해도 재호출

#### 2. `scanner.py` ❌

```python
def scan_one_symbol(code: str, base_date: str = None, market_condition=None) -> dict:
    # ...
    df = api.get_ohlcv(code, config.ohlcv_count, base_date)  # 직접 호출, 캐싱 없음
```

**문제점**:
- `api.get_ohlcv()` 직접 호출
- 캐싱 없음
- 스캔 시마다 API 호출

#### 3. `scanner_v2/core/scanner.py` ❌

```python
def scan_one(self, code: str, date: str = None, market_condition: Optional[MarketCondition] = None):
    # ...
    df = api.get_ohlcv(code, self.config.ohlcv_count, date)  # 직접 호출, 캐싱 없음
```

**문제점**:
- `api.get_ohlcv()` 직접 호출
- 캐싱 없음
- 스캔 시마다 API 호출

#### 4. `main.py` ❌

```python
@app.get('/universe')
def universe(apply_scan: bool = False, ...):
    # ...
    df = api.get_ohlcv(code, config.ohlcv_count)  # 직접 호출, 캐싱 없음
```

**문제점**:
- `api.get_ohlcv()` 직접 호출
- 캐싱 없음

---

## 문제점 분석

### 1. 중복 API 호출

**시나리오**: 같은 종목을 여러 번 스캔하는 경우

```
스캔 1: api.get_ohlcv("005930", 220, "20251124")  # API 호출
스캔 2: api.get_ohlcv("005930", 220, "20251124")  # 동일한 API 호출 (중복!)
수익률 계산: _get_cached_ohlcv("005930", 220, "20251124")  # 캐시 사용 ✅
```

**영향**:
- 불필요한 API 호출 증가
- 레이트 리밋 위험
- 응답 시간 증가
- 비용 증가

### 2. 캐싱 불일치

**현재 상황**:
- `returns_service.py`: 캐싱 있음 ✅
- `scanner.py`, `scanner_v2`: 캐싱 없음 ❌
- `main.py`: 캐싱 없음 ❌

**문제점**:
- 같은 데이터를 다른 방식으로 조회
- 일관성 부족
- 캐시 활용도 낮음

### 3. 캐시 크기 제한

**현재**:
- `@lru_cache(maxsize=1000)`: 최대 1000개 항목
- 캐시 키: `(ticker, count, base_dt)`

**문제점**:
- 종목 수가 많으면 캐시 미스 증가
- 같은 종목, 다른 count/base_dt 조합이 많으면 캐시 효율 낮음

---

## 개선 방안

### 옵션 1: KiwoomAPI에 캐싱 추가 (권장)

**장점**:
- 모든 호출 경로에서 자동 캐싱
- 중앙화된 캐싱 관리
- 일관성 확보

**구현**:
```python
class KiwoomAPI:
    def __init__(self):
        # ...
        self._ohlcv_cache = {}
        self._cache_ttl = 300  # 5분
    
    def get_ohlcv(self, code: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
        # 캐시 키 생성
        cache_key = (code, count, base_dt)
        
        # 캐시 확인
        if cache_key in self._ohlcv_cache:
            cached_df, timestamp = self._ohlcv_cache[cache_key]
            if (time.time() - timestamp) < self._cache_ttl:
                return cached_df.copy()  # 복사본 반환
        
        # API 호출
        df = self._fetch_ohlcv_from_api(code, count, base_dt)
        
        # 캐시 저장
        if not df.empty:
            self._ohlcv_cache[cache_key] = (df.copy(), time.time())
        
        return df
```

### 옵션 2: 전역 캐시 매니저 추가

**장점**:
- 캐시 정책 중앙 관리
- TTL, 크기 제한 등 세밀한 제어
- 통계 및 모니터링 가능

**구현**:
```python
class OHLCVCache:
    def __init__(self, maxsize=1000, ttl=300):
        self._cache = {}
        self.maxsize = maxsize
        self.ttl = ttl
    
    def get(self, code: str, count: int, base_dt: str = None):
        key = (code, count, base_dt)
        if key in self._cache:
            df, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return df.copy()
            del self._cache[key]
        return None
    
    def set(self, code: str, count: int, base_dt: str, df: pd.DataFrame):
        key = (code, count, base_dt)
        if len(self._cache) >= self.maxsize:
            # LRU: 가장 오래된 항목 제거
            oldest_key = min(self._cache.items(), key=lambda x: x[1][1])[0]
            del self._cache[oldest_key]
        self._cache[key] = (df.copy(), time.time())
```

### 옵션 3: functools.lru_cache 사용 (간단)

**장점**:
- 구현 간단
- 자동 LRU 관리
- 메모리 효율적

**구현**:
```python
from functools import lru_cache

class KiwoomAPI:
    @lru_cache(maxsize=1000)
    def get_ohlcv_cached(self, code: str, count: int, base_dt: str = None) -> pd.DataFrame:
        """캐시된 OHLCV 조회"""
        return self._fetch_ohlcv_from_api(code, count, base_dt)
    
    def get_ohlcv(self, code: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
        """기존 메서드를 캐시 버전으로 리다이렉트"""
        return self.get_ohlcv_cached(code, count, base_dt)
```

**주의사항**:
- `base_dt`가 `None`일 수 있어서 캐시 키 처리 필요
- DataFrame은 mutable이므로 복사본 반환 필요

---

## 권장 개선 사항

### 1. KiwoomAPI에 캐싱 추가

**우선순위**: 높음

**이유**:
- 모든 호출 경로에서 자동 적용
- 중복 API 호출 방지
- 성능 개선

### 2. 캐시 정책 설정

**권장 설정**:
- **TTL**: 5분 (300초)
- **최대 크기**: 1000개 항목
- **캐시 키**: `(code, count, base_dt)`

### 3. 캐시 무효화 메커니즘

**필요한 경우**:
- 특정 종목 캐시 클리어
- 전체 캐시 클리어
- 시간 기반 자동 만료

---

## 현재 사용 패턴 분석

### 캐싱 사용
- ✅ `calculate_returns()`: `_get_cached_ohlcv()` 사용

### 캐싱 미사용
- ❌ `scan_one_symbol()`: 직접 `api.get_ohlcv()` 호출
- ❌ `ScannerV2.scan_one()`: 직접 `api.get_ohlcv()` 호출
- ❌ `universe()`: 직접 `api.get_ohlcv()` 호출
- ❌ `save_scan_snapshot()`: 직접 `api.get_ohlcv()` 호출

---

## 결론

### 현재 상태
- **부분적 캐싱**: `returns_service.py`에서만 캐싱 사용
- **대부분 미사용**: 스캔 로직에서는 캐싱 없음

### 문제점
- 중복 API 호출
- 레이트 리밋 위험
- 성능 저하
- 비용 증가

### 개선 필요성
- **높음**: 스캔 시마다 API 호출로 인한 성능 및 비용 문제
- **권장**: `KiwoomAPI.get_ohlcv()`에 캐싱 추가

