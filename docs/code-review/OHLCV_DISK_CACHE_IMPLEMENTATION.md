# OHLCV 디스크 캐시 구현

## 구현 일시
2025-11-24

## 구현 목적

백테스트를 자주 실행할 예정이므로, 프로세스 재시작 후에도 캐시를 유지하기 위해 디스크 캐시를 추가했습니다.

---

## 구현 내용

### 1. 디스크 캐시 설정

```python
# KiwoomAPI.__init__()
self._disk_cache_dir = Path("cache/ohlcv")
self._disk_cache_dir.mkdir(parents=True, exist_ok=True)
self._disk_cache_enabled = True
```

- **캐시 디렉토리**: `cache/ohlcv/`
- **파일 형식**: `{code}_{count}_{base_dt}.pkl`
- **저장 형식**: `(DataFrame, timestamp)` pickle

### 2. 디스크 캐시 저장

```python
def _save_to_disk_cache(self, code: str, count: int, base_dt: str, df: pd.DataFrame):
    # 과거 날짜만 디스크 캐시 저장
    if base_date < now_date:
        cache_file = self._get_disk_cache_file_path(code, count, base_dt)
        with open(cache_file, 'wb') as f:
            pickle.dump((df.copy(), time.time()), f)
```

**특징**:
- 과거 날짜만 디스크 캐시 저장
- 현재 날짜/미래 날짜는 저장 안 함 (메모리 캐시만 사용)
- pickle 형식으로 저장

### 3. 디스크 캐시 로드

```python
def _load_from_disk_cache(self, code: str, count: int, base_dt: str) -> Optional[pd.DataFrame]:
    cache_file = self._get_disk_cache_file_path(code, count, base_dt)
    
    if not cache_file.exists():
        return None
    
    with open(cache_file, 'rb') as f:
        cached_data = pickle.load(f)
        df, timestamp = cached_data
    
    # TTL 확인
    ttl = self._calculate_ttl(base_dt)
    if time.time() - timestamp > ttl:
        cache_file.unlink()  # 만료된 캐시 삭제
        return None
    
    return df.copy()
```

**특징**:
- TTL 확인 후 만료된 캐시 자동 삭제
- 로드 실패 시 파일 삭제
- 메모리 캐시에도 저장 (다음 요청 시 빠른 접근)

### 4. get_ohlcv() 수정

```python
def get_ohlcv(self, code: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
    # 1. 메모리 캐시 확인
    cached_df = self._get_cached_ohlcv(code, count, base_dt)
    if cached_df is not None:
        return cached_df
    
    # 2. 디스크 캐시 확인 (base_dt가 있는 경우만)
    if base_dt and self._disk_cache_enabled:
        cached_df = self._load_from_disk_cache(code, count, base_dt)
        if cached_df is not None:
            # 메모리 캐시에도 저장
            self._set_cached_ohlcv(code, count, base_dt, cached_df)
            return cached_df
    
    # 3. API 호출
    df = self._fetch_ohlcv_from_api(code, count, base_dt)
    
    # 4. 캐시 저장 (메모리 + 디스크)
    if not df.empty:
        self._set_cached_ohlcv(code, count, base_dt, df)
        if base_dt and self._disk_cache_enabled:
            self._save_to_disk_cache(code, count, base_dt, df)
    
    return df
```

**우선순위**:
1. 메모리 캐시 (가장 빠름)
2. 디스크 캐시 (base_dt가 있는 경우)
3. API 호출

---

## 동작 시나리오

### 시나리오 1: 첫 번째 호출 (과거 날짜)

```python
# 프로세스 1
api = KiwoomAPI()
df = api.get_ohlcv("005930", 220, "20251001")
# → API 호출
# → 메모리 캐시 저장
# → 디스크 캐시 저장 (과거 날짜)
```

**결과**:
- 메모리 캐시: 저장됨
- 디스크 캐시: `cache/ohlcv/005930_220_20251001.pkl` 생성

### 시나리오 2: 프로세스 재시작 후

```python
# 프로세스 2 (재시작)
api = KiwoomAPI()  # _ohlcv_cache = {} (비어있음)
df = api.get_ohlcv("005930", 220, "20251001")
# → 메모리 캐시 확인: 없음
# → 디스크 캐시 확인: 있음 ✅
# → 디스크에서 로드
# → 메모리 캐시에도 저장
```

**결과**:
- API 호출 없음 ✅
- 디스크 캐시에서 로드
- 메모리 캐시에도 저장 (다음 요청 시 빠름)

### 시나리오 3: 백테스트 실행

```python
# 백테스트 스크립트 (새 프로세스)
api = KiwoomAPI()

# 여러 날짜 스캔
for date in ["20251001", "20251002", "20251003"]:
    df = api.get_ohlcv("005930", 220, date)
    # 첫 실행: API 호출, 디스크 저장
    # 이후 실행: 디스크에서 로드 ✅
```

**결과**:
- 첫 실행: API 호출 (디스크 저장)
- 이후 실행: 디스크에서 로드 (API 호출 없음) ✅

---

## 캐시 통계

```python
stats = api.get_ohlcv_cache_stats()
# {
#     "total": 10,  # 메모리 캐시 항목 수
#     "valid": 10,
#     "expired": 0,
#     "maxsize": 1000,
#     "ttl": 300,
#     "disk": {
#         "enabled": True,
#         "total_files": 50,
#         "total_size_bytes": 5242880,
#         "total_size_mb": 5.0,
#         "cache_dir": "cache/ohlcv"
#     }
# }
```

---

## 디스크 캐시 관리

### 캐시 클리어

```python
# 전체 캐시 클리어
api.clear_ohlcv_cache()

# 특정 종목만 클리어
api.clear_ohlcv_cache(code="005930")
```

### 캐시 비활성화

```python
api._disk_cache_enabled = False
```

---

## 파일 구조

```
cache/
└── ohlcv/
    ├── 005930_220_20251001.pkl
    ├── 005930_220_20251002.pkl
    ├── 000660_220_20251001.pkl
    └── ...
```

**파일명 형식**: `{code}_{count}_{base_dt}.pkl`

---

## 성능 고려사항

### 장점

1. **프로세스 재시작 후에도 캐시 유지**: 백테스트 시 API 호출 없음
2. **과거 날짜만 저장**: 현재 날짜는 메모리만 사용 (디스크 I/O 최소화)
3. **자동 만료 처리**: TTL 확인 후 만료된 캐시 자동 삭제

### 주의사항

1. **디스크 공간**: 많은 종목/날짜 조합 시 디스크 공간 필요
2. **I/O 오버헤드**: 디스크 읽기/쓰기 오버헤드 (하지만 과거 날짜만 사용)
3. **파일 관리**: 오래된 캐시 파일 정리 필요 (선택사항)

---

## 테스트

### 단위 테스트

```python
# backend/tests/test_ohlcv_disk_cache.py
- 디스크 캐시 저장 및 로드
- 과거 날짜만 저장 확인
- 캐시 클리어
- 통계 확인
```

### 통합 테스트

```python
# 프로세스 재시작 시나리오
api1 = KiwoomAPI()
df1 = api1.get_ohlcv("005930", 220, "20251001")  # API 호출, 디스크 저장

# 프로세스 재시작 (새 인스턴스)
api2 = KiwoomAPI()
df2 = api2.get_ohlcv("005930", 220, "20251001")  # 디스크에서 로드 ✅
```

---

## 사용 예시

### 백테스트 스크립트

```python
from kiwoom_api import api

# 여러 날짜 백테스트
for date in date_range("20251001", "20251031"):
    for code in ["005930", "000660", "051910"]:
        df = api.get_ohlcv(code, 220, date)
        # 첫 실행: API 호출, 디스크 저장
        # 이후 실행: 디스크에서 로드 (API 호출 없음) ✅
```

### 캐시 통계 확인

```python
stats = api.get_ohlcv_cache_stats()
print(f"메모리 캐시: {stats['total']}개")
print(f"디스크 캐시: {stats['disk']['total_files']}개 파일, {stats['disk']['total_size_mb']}MB")
```

---

## 결론

✅ **디스크 캐시 구현 완료**

**효과**:
- 백테스트 시 API 호출 없이 실행 가능
- 프로세스 재시작 후에도 캐시 유지
- 과거 날짜만 디스크 저장 (I/O 최소화)

**다음 단계**:
- 백테스트 스크립트에서 활용
- 캐시 파일 정리 스크립트 (선택사항)

