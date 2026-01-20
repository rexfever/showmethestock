# OHLCV 캐시와 프로세스 구조

## 현재 프로세스 구조

### 단일 프로세스 구조

**서버 설정**:
```ini
# /etc/systemd/system/stock-finder-backend.service
ExecStart=/home/ubuntu/showmethestock/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8010 --workers 1
```

- **워커 수**: 1개 (`--workers 1`)
- **프로세스**: 단일 프로세스
- **KiwoomAPI 인스턴스**: 전역 단일 인스턴스

### KiwoomAPI 인스턴스 생성

```python
# backend/kiwoom_api.py
# 전역 API 인스턴스
api = KiwoomAPI()
```

```python
# backend/main.py
from kiwoom_api import api  # 전역 인스턴스 사용
```

---

## 프로세스 구조 분석

### 현재 구조 (단일 프로세스)

```
프로세스 1 (stock-finder-backend)
  ↓
uvicorn (워커 1개)
  ↓
FastAPI 앱
  ↓
전역 KiwoomAPI 인스턴스 (api)
  ↓
_ohlcv_cache = {} (프로세스 메모리)
```

### 특징

1. **단일 프로세스**: `--workers 1`로 단일 워커
2. **전역 인스턴스**: `api = KiwoomAPI()` 전역 변수
3. **캐시 공유**: 모든 요청이 같은 `_ohlcv_cache` 사용

---

## 캐시 동작

### 같은 프로세스 내

```python
# 요청 1
GET /scan?date=20251001
  → api.get_ohlcv("005930", 220, "20251001")
  → API 호출
  → _ohlcv_cache[("005930", 220, "20251001", None)] = (df, timestamp)

# 요청 2 (같은 프로세스)
GET /scan?date=20251001
  → api.get_ohlcv("005930", 220, "20251001")
  → 캐시 히트 ✅ (API 호출 없음)
```

**장점**:
- 같은 프로세스 내에서 캐시 공유
- 여러 요청이 같은 캐시 활용

### 프로세스 재시작 후

```python
# 프로세스 종료
sudo systemctl restart stock-finder-backend

# 새 프로세스 시작
프로세스 2 (stock-finder-backend)
  ↓
새 KiwoomAPI 인스턴스 생성
  ↓
_ohlcv_cache = {} (비어있음)

# 요청
GET /scan?date=20251001
  → api.get_ohlcv("005930", 220, "20251001")
  → 캐시 미스 ❌ (API 호출 필요)
```

---

## 멀티 프로세스 구조로 변경 시

### 만약 `--workers 4`로 변경한다면?

```
프로세스 1 (stock-finder-backend)
  ├─ 워커 1
  │   └─ KiwoomAPI 인스턴스 1
  │       └─ _ohlcv_cache_1 = {}
  ├─ 워커 2
  │   └─ KiwoomAPI 인스턴스 2
  │       └─ _ohlcv_cache_2 = {}
  ├─ 워커 3
  │   └─ KiwoomAPI 인스턴스 3
  │       └─ _ohlcv_cache_3 = {}
  └─ 워커 4
      └─ KiwoomAPI 인스턴스 4
          └─ _ohlcv_cache_4 = {}
```

**문제점**:
- 각 워커가 독립적인 KiwoomAPI 인스턴스 생성
- 캐시가 워커별로 분리됨
- 워커 1의 캐시를 워커 2가 사용할 수 없음

**예시**:
```python
# 워커 1에서
api1.get_ohlcv("005930", 220, "20251001")  # API 호출, 캐시 저장

# 워커 2에서 (다른 인스턴스)
api2.get_ohlcv("005930", 220, "20251001")  # API 호출 (캐시 없음)
```

---

## 현재 구조의 장단점

### 장점

1. **캐시 공유**: 모든 요청이 같은 캐시 사용
2. **단순함**: 단일 프로세스로 관리 용이
3. **메모리 효율**: 캐시 중복 없음

### 단점

1. **프로세스 재시작 시 캐시 소실**: 서비스 재시작 시 모든 캐시 사라짐
2. **확장성 제한**: 단일 워커로 부하 분산 불가
3. **백테스트 제한**: 프로세스 재시작 후 API 호출 필요

---

## 결론

### 현재 구조

- ✅ **단일 프로세스**: `--workers 1`
- ✅ **전역 인스턴스**: `api = KiwoomAPI()`
- ✅ **캐시 공유**: 같은 프로세스 내 모든 요청이 같은 캐시 사용

### 캐시 동작

- ✅ **같은 프로세스 내**: 캐시 공유 가능
- ❌ **프로세스 재시작 후**: 캐시 소실 (TTL과 무관)

### 개선 필요

**디스크 캐시 추가**가 필요합니다:
- 프로세스 재시작 후에도 캐시 유지
- 멀티 워커 환경에서도 캐시 공유 가능

---

## 참고

- **현재 워커 수**: 1개 (`--workers 1`)
- **KiwoomAPI 인스턴스**: 전역 단일 인스턴스
- **캐시 위치**: 프로세스 메모리 (RAM)
- **캐시 공유**: 같은 프로세스 내에서만 가능

