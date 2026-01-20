# 스캐닝 프로세스 확인

## 사용자 제시 프로세스

1. 키움 API 이용하여 유니버스 실시간 조회
2. 조회된 종목의 오늘자 OHLCV를 실시간 조회하여 캐시에 추가
3. 캐시 데이터를 이용하여 필터링 계산

---

## 실제 코드 동작 확인

### 1. 유니버스 실시간 조회

**위치**: `backend/main.py` - `scan()` 함수

```python
@app.get('/scan')
def scan(...):
    # 유니버스 조회
    kospi = api.get_top_codes('KOSPI', kp)
    kosdaq = api.get_top_codes('KOSDAQ', kd)
    universe: List[str] = [*kospi, *kosdaq]
    
    # 스캔 실행
    result = execute_scan_with_fallback(universe, today_as_of, market_condition)
```

**확인**: ✅ **맞습니다**
- `get_top_codes()`로 KOSPI/KOSDAQ 상위 종목 조회
- 유니버스 구성

---

### 2. OHLCV 실시간 조회 및 캐시 추가

**위치**: `backend/scanner.py` - `scan_one_symbol()` 또는 `backend/scanner_v2/core/scanner.py` - `scan_one()`

#### V1 스캐너

```python
def scan_one_symbol(code: str, base_date: str = None, market_condition: MarketCondition = None):
    # OHLCV 조회
    df = api.get_ohlcv(code, config.ohlcv_count, base_date)
    
    # get_ohlcv() 내부 동작:
    # 1. 메모리 캐시 확인
    # 2. 디스크 캐시 확인 (base_dt가 있는 경우)
    # 3. 캐시 미스 시 API 호출
    # 4. 자동으로 메모리 + 디스크 캐시에 저장 ✅
```

#### V2 스캐너

```python
def scan_one(self, code: str, date: str = None, ...):
    # OHLCV 조회
    df = api.get_ohlcv(code, self.config.ohlcv_count, date)
    
    # get_ohlcv() 내부 동작:
    # 1. 메모리 캐시 확인
    # 2. 디스크 캐시 확인 (base_dt가 있는 경우)
    # 3. 캐시 미스 시 API 호출
    # 4. 자동으로 메모리 + 디스크 캐시에 저장 ✅
```

**확인**: ✅ **맞습니다**
- `get_ohlcv()` 호출 시 자동으로 캐시 확인/저장
- 캐시에 있으면 API 호출 없이 반환
- 캐시에 없으면 API 호출 후 자동 저장

---

### 3. 캐시 데이터를 이용하여 필터링 계산

**위치**: `backend/scanner.py` 또는 `backend/scanner_v2/core/scanner.py`

#### V1 스캐너

```python
def scan_one_symbol(code: str, base_date: str = None, ...):
    # 1. OHLCV 조회 (캐시에서 가져옴)
    df = api.get_ohlcv(code, config.ohlcv_count, base_date)
    
    # 2. 지표 계산 (캐시된 데이터 사용)
    df = compute_indicators(df)
    
    # 3. 필터링
    matched, signals_count, signals_total = match_stats(df, market_condition, stock_name)
    
    # 4. 점수 계산
    score, flags = calculate_score(df, market_condition)
```

#### V2 스캐너

```python
def scan_one(self, code: str, date: str = None, ...):
    # 1. OHLCV 조회 (캐시에서 가져옴)
    df = api.get_ohlcv(code, self.config.ohlcv_count, date)
    
    # 2. 지표 계산 (캐시된 데이터 사용)
    df = self.indicator_calculator.compute_all(df)
    
    # 3. 필터링
    matched, signals_count, signals_total = self.filter_engine.apply_soft_filters(...)
    
    # 4. 점수 계산
    score, flags = self.scorer.calculate_score(df, market_condition)
```

**확인**: ✅ **맞습니다**
- 캐시에서 가져온 OHLCV 데이터로 지표 계산
- 필터링 및 점수 계산

---

## 실제 실행 순서

```
1. 유니버스 조회
   ↓
   api.get_top_codes('KOSPI', kp)
   api.get_top_codes('KOSDAQ', kd)
   ↓
   universe = [code1, code2, code3, ...]

2. 각 종목별 스캔 (병렬 처리)
   ↓
   for code in universe:
       ↓
       df = api.get_ohlcv(code, count, date)
       ↓
       [캐시 확인]
       ├─ 메모리 캐시 있음 → 반환 ✅
       ├─ 디스크 캐시 있음 → 로드 후 메모리 저장 → 반환 ✅
       └─ 캐시 없음 → API 호출 → 메모리+디스크 저장 → 반환 ✅
       ↓
       [필터링 계산]
       ├─ 지표 계산 (RSI, MACD, OBV 등)
       ├─ 하드 필터 적용 (ETF 등)
       ├─ 소프트 필터 적용 (신호 충족 여부)
       └─ 점수 계산
```

---

## 확인 결과

### ✅ 사용자 제시 프로세스가 정확합니다

1. **유니버스 실시간 조회**: ✅ `get_top_codes()` 사용
2. **OHLCV 실시간 조회 및 캐시 추가**: ✅ `get_ohlcv()` 호출 시 자동 처리
3. **캐시 데이터로 필터링 계산**: ✅ 캐시된 데이터로 지표/필터링/점수 계산

---

## 추가 확인 사항

### 캐시 동작

- **메모리 캐시**: 모든 조회 결과 자동 저장
- **디스크 캐시**: 과거 날짜만 자동 저장
- **TTL**: 과거 날짜는 1년, 현재 날짜는 시간대별 동적 계산

### 스캔 시나리오

#### 시나리오 1: 첫 번째 스캔 (캐시 없음)

```
1. 유니버스 조회
2. 각 종목 OHLCV 조회
   → API 호출
   → 메모리 캐시 저장 ✅
   → 디스크 캐시 저장 ✅ (과거 날짜만)
3. 필터링 계산
```

#### 시나리오 2: 두 번째 스캔 (캐시 있음)

```
1. 유니버스 조회
2. 각 종목 OHLCV 조회
   → 메모리 캐시 확인 → 있음 ✅
   → API 호출 없음 ✅
3. 필터링 계산
```

#### 시나리오 3: 프로세스 재시작 후 스캔

```
1. 유니버스 조회
2. 각 종목 OHLCV 조회
   → 메모리 캐시 확인 → 없음 (재시작)
   → 디스크 캐시 확인 → 있음 ✅
   → 디스크에서 로드
   → 메모리 캐시 저장 ✅
   → API 호출 없음 ✅
3. 필터링 계산
```

---

## 결론

**사용자가 제시한 스캐닝 프로세스가 정확합니다.**

1. ✅ 유니버스 실시간 조회
2. ✅ OHLCV 실시간 조회 및 캐시 자동 추가
3. ✅ 캐시 데이터로 필터링 계산

**추가 확인**:
- 캐시는 자동으로 추가됨 (별도 작업 불필요)
- 메모리 캐시 우선, 디스크 캐시 보조
- 프로세스 재시작 후에도 디스크 캐시 활용 가능

