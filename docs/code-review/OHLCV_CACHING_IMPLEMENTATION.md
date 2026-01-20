# OHLCV 캐싱 구현 완료

## 구현 일시
2025-11-24

## 구현 내용

### 1. KiwoomAPI 클래스에 캐싱 기능 추가

#### 캐시 설정
- **TTL**: 5분 (300초)
- **최대 크기**: 1000개 항목
- **캐시 키**: `(code, count, base_dt)` 튜플

#### 추가된 메서드

##### `_get_cache_key(code, count, base_dt)`
- 캐시 키 생성

##### `_get_cached_ohlcv(code, count, base_dt)`
- 캐시에서 데이터 조회
- TTL 확인 및 만료된 항목 자동 제거
- 복사본 반환 (원본 데이터 보호)

##### `_set_cached_ohlcv(code, count, base_dt, df)`
- 캐시에 데이터 저장
- 빈 DataFrame은 캐시하지 않음
- LRU 방식으로 오래된 항목 자동 제거

##### `clear_ohlcv_cache(code=None)`
- 캐시 클리어
- `code` 지정 시 특정 종목만 클리어
- `code=None` 시 전체 캐시 클리어

##### `get_ohlcv_cache_stats()`
- 캐시 통계 반환
- 총 항목 수, 유효 항목 수, 만료 항목 수, 최대 크기, TTL

##### `_fetch_ohlcv_from_api(code, count, base_dt)`
- 실제 API 호출 로직 (캐싱 없음)
- 기존 `get_ohlcv` 로직을 분리

#### 수정된 메서드

##### `get_ohlcv(code, count, base_dt)`
- 캐시 확인 → 캐시 히트 시 즉시 반환
- 캐시 미스 시 `_fetch_ohlcv_from_api` 호출
- 결과를 캐시에 저장 후 반환

---

## 적용 범위

### 자동 캐싱 적용
다음 모든 호출 경로에서 자동으로 캐싱이 적용됩니다:

1. ✅ `scanner.py` - `scan_one_symbol()`
2. ✅ `scanner_v2/core/scanner.py` - `ScannerV2.scan_one()`
3. ✅ `main.py` - `universe()`, `scan()`, `scan_historical()`
4. ✅ `services/scan_service.py` - `save_scan_snapshot()`
5. ✅ `services/returns_service.py` - `calculate_returns()` (기존 캐싱과 중복이지만 문제없음)

---

## 캐싱 동작 방식

### 1. 캐시 히트
```
사용자 호출: api.get_ohlcv("005930", 220, "20251124")
  ↓
캐시 확인: _get_cached_ohlcv()
  ↓
캐시 존재 & TTL 유효
  ↓
캐시에서 복사본 반환 (API 호출 없음)
```

### 2. 캐시 미스
```
사용자 호출: api.get_ohlcv("005930", 220, "20251124")
  ↓
캐시 확인: _get_cached_ohlcv()
  ↓
캐시 없음 또는 TTL 만료
  ↓
API 호출: _fetch_ohlcv_from_api()
  ↓
결과를 캐시에 저장: _set_cached_ohlcv()
  ↓
결과 반환
```

### 3. 캐시 만료
- TTL(5분) 경과 시 자동 만료
- 다음 호출 시 자동으로 제거되고 재조회

### 4. 캐시 크기 제한
- 최대 1000개 항목 초과 시
- 가장 오래된 항목(LRU) 자동 제거

---

## 테스트

### 테스트 파일
- `backend/tests/test_ohlcv_caching.py`

### 테스트 항목
1. ✅ 캐시 히트 테스트
2. ✅ 캐시 미스 테스트 (다른 파라미터)
3. ✅ TTL 만료 테스트
4. ✅ 최대 크기 제한 테스트
5. ✅ 캐시 클리어 테스트 (전체/특정 종목)
6. ✅ 캐시 통계 테스트
7. ✅ 빈 DataFrame 캐싱 안 함 테스트
8. ✅ 복사본 반환 테스트

---

## 성능 개선 효과

### Before (캐싱 없음)
```
스캔 1: api.get_ohlcv("005930", 220, "20251124")  # API 호출
스캔 2: api.get_ohlcv("005930", 220, "20251124")  # API 호출 (중복!)
수익률 계산: _get_cached_ohlcv("005930", 220, "20251124")  # 캐시 (returns_service만)
```

### After (캐싱 적용)
```
스캔 1: api.get_ohlcv("005930", 220, "20251124")  # API 호출 + 캐시 저장
스캔 2: api.get_ohlcv("005930", 220, "20251124")  # 캐시에서 반환 (API 호출 없음!)
수익률 계산: _get_cached_ohlcv("005930", 220, "20251124")  # 캐시 (returns_service)
```

### 예상 효과
- **API 호출 감소**: 같은 종목/날짜 조회 시 5분간 재호출 없음
- **응답 시간 단축**: 캐시 히트 시 즉시 반환
- **레이트 리밋 위험 감소**: 불필요한 API 호출 제거
- **비용 절감**: API 호출 횟수 감소

---

## 사용 예시

### 기본 사용 (자동 캐싱)
```python
from kiwoom_api import api

# 첫 번째 호출: API 호출 + 캐시 저장
df1 = api.get_ohlcv("005930", 220, "20251124")

# 두 번째 호출: 캐시에서 반환 (API 호출 없음)
df2 = api.get_ohlcv("005930", 220, "20251124")
```

### 캐시 관리
```python
# 캐시 통계 조회
stats = api.get_ohlcv_cache_stats()
print(f"캐시 항목: {stats['valid']}/{stats['total']}")

# 특정 종목 캐시 클리어
api.clear_ohlcv_cache("005930")

# 전체 캐시 클리어
api.clear_ohlcv_cache()
```

---

## 주의사항

### 1. DataFrame 복사본 반환
- 캐시에서 반환되는 DataFrame은 복사본
- 원본 데이터 수정 시 캐시에 영향 없음

### 2. TTL 기반 만료
- 5분 후 자동 만료
- 실시간 데이터가 필요한 경우 캐시 클리어 필요

### 3. 메모리 사용
- 최대 1000개 항목 캐싱
- 항목당 DataFrame 크기에 따라 메모리 사용량 변동

### 4. force_mock 모드
- 모의 모드에서도 캐싱 적용
- 테스트 시 일관된 동작 보장

---

## 다음 단계

1. ✅ 캐싱 기능 구현 완료
2. ✅ 테스트 코드 작성 완료
3. ⏳ 서버 배포 및 검증
4. ⏳ 성능 모니터링
5. ⏳ 필요 시 TTL/최대 크기 조정

