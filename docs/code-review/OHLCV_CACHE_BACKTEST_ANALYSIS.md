# OHLCV 캐시를 활용한 백테스트 가능성 분석

## 현재 구현 상태

### 캐시 구조

```python
# KiwoomAPI 클래스
self._ohlcv_cache: Dict[Tuple[str, int, Optional[str], Optional[str]], Tuple[pd.DataFrame, float]] = {}
```

- **저장 위치**: 메모리 (프로세스 내부)
- **캐시 키**: `(code, count, base_dt, hour_key)`
- **캐시 값**: `(DataFrame, timestamp)`
- **TTL**: 과거 날짜는 1년, 현재 날짜는 시간대별 동적 계산

### 캐시 동작 방식

```python
def get_ohlcv(self, code: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
    # 1. 캐시 확인
    cached_df = self._get_cached_ohlcv(code, count, base_dt)
    if cached_df is not None:
        return cached_df  # 캐시 히트
    
    # 2. 캐시 미스: API 호출
    df = self._fetch_ohlcv_from_api(code, count, base_dt)
    
    # 3. 캐시 저장
    self._set_cached_ohlcv(code, count, base_dt, df)
    
    return df
```

---

## 백테스트 가능성 분석

### ✅ 부분적으로 가능

**시나리오 1: 같은 프로세스 내 재실행**

```python
# 첫 번째 실행: API 호출 발생
api = KiwoomAPI()
df1 = api.get_ohlcv("005930", 220, "20251001")  # API 호출

# 두 번째 실행: 캐시 활용
df2 = api.get_ohlcv("005930", 220, "20251001")  # 캐시 히트 (API 호출 없음)
```

**장점**:
- 같은 프로세스 내에서 반복 실행 시 API 호출 없이 캐시 활용 가능
- 과거 날짜는 TTL이 1년이므로 캐시가 오래 유지됨

**단점**:
- 프로세스가 종료되면 캐시가 사라짐
- 첫 번째 실행 시에는 여전히 API 호출 필요

### ❌ 완전히 불가능한 경우

**시나리오 2: 프로세스 재시작 후**

```python
# 프로세스 1
api1 = KiwoomAPI()
df1 = api1.get_ohlcv("005930", 220, "20251001")  # API 호출
# 프로세스 종료 → 캐시 소실

# 프로세스 2 (새로 시작)
api2 = KiwoomAPI()
df2 = api2.get_ohlcv("005930", 220, "20251001")  # API 호출 (캐시 없음)
```

**문제점**:
- 프로세스가 종료되면 메모리 캐시가 사라짐
- 새 프로세스에서는 캐시가 비어있어 API 호출 필요

---

## 개선 방안

### 방안 1: 디스크 캐시 추가 (권장)

**구현 예시**:

```python
import pickle
import os
from pathlib import Path

class KiwoomAPI:
    def __init__(self):
        # ... 기존 코드 ...
        self._cache_dir = Path("cache/ohlcv")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_file_path(self, code: str, count: int, base_dt: str) -> Path:
        """디스크 캐시 파일 경로"""
        cache_key = f"{code}_{count}_{base_dt or 'latest'}.pkl"
        return self._cache_dir / cache_key
    
    def _load_from_disk_cache(self, code: str, count: int, base_dt: str) -> Optional[pd.DataFrame]:
        """디스크 캐시에서 로드"""
        cache_file = self._get_cache_file_path(code, count, base_dt)
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
                df, timestamp = cached_data
                
                # TTL 확인
                if time.time() - timestamp > self._calculate_ttl(base_dt):
                    cache_file.unlink()  # 만료된 캐시 삭제
                    return None
                
                return df.copy()
        except Exception:
            return None
    
    def _save_to_disk_cache(self, code: str, count: int, base_dt: str, df: pd.DataFrame):
        """디스크 캐시에 저장"""
        cache_file = self._get_cache_file_path(code, count, base_dt)
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump((df.copy(), time.time()), f)
        except Exception:
            pass  # 저장 실패해도 계속 진행
    
    def get_ohlcv(self, code: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
        # 1. 메모리 캐시 확인
        cached_df = self._get_cached_ohlcv(code, count, base_dt)
        if cached_df is not None:
            return cached_df
        
        # 2. 디스크 캐시 확인 (base_dt가 있는 경우만)
        if base_dt:
            cached_df = self._load_from_disk_cache(code, count, base_dt)
            if cached_df is not None:
                # 메모리 캐시에도 저장
                self._set_cached_ohlcv(code, count, base_dt, cached_df)
                return cached_df
        
        # 3. API 호출
        df = self._fetch_ohlcv_from_api(code, count, base_dt)
        
        # 4. 캐시 저장 (메모리 + 디스크)
        self._set_cached_ohlcv(code, count, base_dt, df)
        if base_dt:  # 과거 날짜만 디스크 캐시
            self._save_to_disk_cache(code, count, base_dt, df)
        
        return df
```

**장점**:
- 프로세스 재시작 후에도 캐시 유지
- 과거 날짜 데이터는 디스크에 영구 저장
- 백테스트 시 API 호출 없이 실행 가능

**단점**:
- 디스크 I/O 오버헤드 (하지만 과거 날짜만 사용하므로 문제 없음)
- 디스크 공간 필요

### 방안 2: 백테스트 전 데이터 프리로드

**구현 예시**:

```python
def preload_ohlcv_for_backtest(
    codes: List[str],
    start_date: str,
    end_date: str,
    count: int = 220
):
    """백테스트를 위한 OHLCV 데이터 미리 로드"""
    from kiwoom_api import api
    from datetime import datetime, timedelta
    
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    
    current = start
    while current <= end:
        date_str = current.strftime("%Y%m%d")
        
        for code in codes:
            # API 호출하여 캐시에 저장
            api.get_ohlcv(code, count, date_str)
        
        current += timedelta(days=1)
    
    print(f"✅ {len(codes)}개 종목, {start_date}~{end_date} 데이터 프리로드 완료")

# 사용 예시
preload_ohlcv_for_backtest(
    codes=["005930", "000660", "051910"],
    start_date="20251001",
    end_date="20251031"
)

# 이후 백테스트 실행 (API 호출 없음)
run_backtest("20251001", "20251031")
```

**장점**:
- 간단한 구현
- 기존 캐시 구조 활용

**단점**:
- 첫 실행 시 여전히 API 호출 필요
- 프로세스 재시작 시 다시 프리로드 필요

### 방안 3: 데이터베이스 캐시

**구현 예시**:

```sql
CREATE TABLE IF NOT EXISTS ohlcv_cache (
    code TEXT NOT NULL,
    count INTEGER NOT NULL,
    base_dt TEXT,
    data JSONB NOT NULL,
    cached_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (code, count, base_dt)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_cache_date ON ohlcv_cache(base_dt);
```

```python
def _load_from_db_cache(self, code: str, count: int, base_dt: str) -> Optional[pd.DataFrame]:
    """DB 캐시에서 로드"""
    try:
        from db_manager import get_cursor
        with get_cursor() as cur:
            cur.execute("""
                SELECT data, cached_at
                FROM ohlcv_cache
                WHERE code = %s AND count = %s AND base_dt = %s
            """, (code, count, base_dt))
            
            row = cur.fetchone()
            if not row:
                return None
            
            data_json, cached_at = row
            
            # TTL 확인 (과거 날짜는 1년)
            ttl = 365 * 24 * 3600
            if (datetime.now() - cached_at).total_seconds() > ttl:
                return None
            
            # JSON을 DataFrame으로 변환
            df = pd.read_json(data_json, orient='records')
            return df
    except Exception:
        return None
```

**장점**:
- 영구 저장
- 여러 프로세스에서 공유 가능
- 쿼리로 관리 가능

**단점**:
- DB 부하 증가
- 구현 복잡도 증가

---

## 권장 방안

### 단기: 방안 2 (프리로드)

백테스트 전에 필요한 데이터를 미리 로드:

```python
# 백테스트 스크립트
from kiwoom_api import api

# 1. 데이터 프리로드
print("데이터 프리로드 중...")
for date in date_range("20251001", "20251031"):
    for code in target_codes:
        api.get_ohlcv(code, 220, date)  # 캐시에 저장

# 2. 백테스트 실행 (API 호출 없음)
print("백테스트 실행 중...")
run_backtest("20251001", "20251031")
```

### 장기: 방안 1 (디스크 캐시)

과거 날짜 데이터는 디스크에 영구 저장:

```python
# 첫 실행: API 호출 + 디스크 저장
df = api.get_ohlcv("005930", 220, "20251001")

# 이후 실행: 디스크에서 로드 (API 호출 없음)
df = api.get_ohlcv("005930", 220, "20251001")
```

---

## 결론

### 현재 상태
- ✅ **같은 프로세스 내**: 부분적으로 가능 (첫 실행 후 재실행 시)
- ❌ **프로세스 재시작 후**: 불가능 (캐시 소실)

### 개선 후
- ✅ **디스크 캐시 추가**: 완전히 가능 (프로세스 재시작 후에도)
- ✅ **프리로드 방식**: 부분적으로 가능 (프리로드 후)

### 권장사항
1. **단기**: 백테스트 전 데이터 프리로드 (간단한 구현)
2. **장기**: 디스크 캐시 추가 (영구 저장)

---

## 구현 우선순위

1. **높음**: 디스크 캐시 추가 (과거 날짜만)
2. **중간**: 프리로드 유틸리티 함수
3. **낮음**: DB 캐시 (필요 시)

