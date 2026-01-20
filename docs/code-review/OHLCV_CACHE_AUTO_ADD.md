# OHLCV 캐시 자동 추가 동작

## 질문

**"추가되는 데이터는 캐시에 추가 되는가?"**

## 답변

### ✅ 네, 자동으로 추가됩니다

새로운 데이터를 조회하면 **자동으로 메모리 캐시와 디스크 캐시에 추가**됩니다.

---

## 자동 캐시 추가 동작

### get_ohlcv() 메서드 동작

```python
def get_ohlcv(self, code: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
    # 1. 메모리 캐시 확인
    cached_df = self._get_cached_ohlcv(code, count, base_dt)
    if cached_df is not None:
        return cached_df  # 캐시 히트
    
    # 2. 디스크 캐시 확인
    if base_dt and self._disk_cache_enabled:
        cached_df = self._load_from_disk_cache(code, count, base_dt)
        if cached_df is not None:
            self._set_cached_ohlcv(code, count, base_dt, cached_df)  # 메모리에도 저장
            return cached_df
    
    # 3. API 호출
    df = self._fetch_ohlcv_from_api(code, count, base_dt)
    
    # 4. 캐시 저장 (자동)
    if not df.empty:
        self._set_cached_ohlcv(code, count, base_dt, df)  # 메모리 캐시 저장
        if base_dt and self._disk_cache_enabled:
            self._save_to_disk_cache(code, count, base_dt, df)  # 디스크 캐시 저장
    
    return df
```

**핵심**: API 호출 후 자동으로 메모리 + 디스크 캐시에 저장됩니다.

---

## 시나리오별 동작

### 시나리오 1: 새로운 종목 조회

```python
# 첫 번째 종목
df1 = api.get_ohlcv("005930", 220, "20251001")
# → API 호출
# → 메모리 캐시 저장 ✅
# → 디스크 캐시 저장 ✅ (과거 날짜)

# 두 번째 종목 (새로운 종목)
df2 = api.get_ohlcv("000660", 220, "20251001")
# → API 호출
# → 메모리 캐시 저장 ✅ (새 항목 추가)
# → 디스크 캐시 저장 ✅ (새 파일 생성)
```

**결과**:
- 메모리 캐시: 2개 항목
- 디스크 캐시: 2개 파일

### 시나리오 2: 새로운 날짜 조회

```python
# 첫 번째 날짜
df1 = api.get_ohlcv("005930", 220, "20251001")
# → API 호출
# → 메모리 캐시 저장 ✅
# → 디스크 캐시 저장 ✅

# 두 번째 날짜 (새로운 날짜)
df2 = api.get_ohlcv("005930", 220, "20251002")
# → API 호출
# → 메모리 캐시 저장 ✅ (새 항목 추가)
# → 디스크 캐시 저장 ✅ (새 파일 생성)
```

**결과**:
- 메모리 캐시: 2개 항목
- 디스크 캐시: 2개 파일

### 시나리오 3: 다른 count 조회

```python
# count 220
df1 = api.get_ohlcv("005930", 220, "20251001")
# → 메모리 캐시: ("005930", 220, "20251001", None)

# count 100 (다른 count)
df2 = api.get_ohlcv("005930", 100, "20251001")
# → API 호출 (다른 캐시 키)
# → 메모리 캐시 저장 ✅ (새 항목 추가)
# → 디스크 캐시 저장 ✅ (새 파일 생성)
```

**결과**:
- 메모리 캐시: 2개 항목 (다른 캐시 키)
- 디스크 캐시: 2개 파일

---

## 캐시 저장 조건

### 메모리 캐시 저장 조건

```python
if not df.empty:
    self._set_cached_ohlcv(code, count, base_dt, df)
```

**조건**:
- ✅ DataFrame이 비어있지 않으면 저장
- ✅ 모든 조회 결과 자동 저장

### 디스크 캐시 저장 조건

```python
if base_dt and self._disk_cache_enabled:
    # base_dt가 과거 날짜인 경우만 저장
    if base_date < now_date:
        self._save_to_disk_cache(code, count, base_dt, df)
```

**조건**:
- ✅ `base_dt`가 있어야 함
- ✅ 디스크 캐시가 활성화되어 있어야 함
- ✅ 과거 날짜여야 함 (현재 날짜/미래 날짜는 저장 안 함)

---

## 실제 테스트 결과

```
=== 초기 상태 ===
메모리 캐시: 0개
디스크 캐시: 0개 파일

=== 새로운 데이터 조회 (과거 날짜) ===
데이터 조회 완료: 220개 행
메모리 캐시: 1개 (추가됨: 1)
디스크 캐시: 1개 파일 (추가됨: 1) ✅

=== 다른 종목 조회 ===
데이터 조회 완료: 220개 행
메모리 캐시: 2개 (추가됨: 1)
디스크 캐시: 2개 파일 (추가됨: 1) ✅

=== 다른 날짜 조회 ===
데이터 조회 완료: 220개 행
메모리 캐시: 3개 (추가됨: 1)
디스크 캐시: 3개 파일 (추가됨: 1) ✅
```

---

## 결론

### ✅ 자동 캐시 추가

1. **메모리 캐시**: 모든 조회 결과 자동 저장
2. **디스크 캐시**: 과거 날짜만 자동 저장
3. **별도 작업 불필요**: API 호출 후 자동으로 캐시에 추가

### 캐시 누적

- 새로운 종목 조회 → 캐시 추가
- 새로운 날짜 조회 → 캐시 추가
- 다른 count 조회 → 캐시 추가

**결과**: 백테스트를 실행하면 자동으로 캐시가 누적되어, 다음 실행 시 API 호출 없이 실행 가능합니다.

---

## 참고

- **메모리 캐시**: 최대 1000개 항목 (LRU 방식으로 오래된 항목 자동 제거)
- **디스크 캐시**: 제한 없음 (디스크 공간만큼 저장 가능)
- **TTL**: 과거 날짜는 1년, 현재 날짜는 시간대별 동적 계산

