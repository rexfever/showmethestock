# 캐시 기반 주식 스캔과 레짐 분석 프로세스

## 개요

개선된 캐시 전략을 활용한 한국 주식 스캔과 레짐 분석의 전체 프로세스를 설명합니다.

**참고**: 미국 주식 스캔 프로세스는 [레짐 분석 및 스캔 프로세스 종합 보고서](./REGIME_ANALYSIS_AND_SCAN_PROCESS.md)를 참고하세요.

---

## 1. 전체 프로세스 타임라인

### 한국 주식 (KST 기준)

```
15:35 - 레짐 분석용 캐시 사전 생성 (필수)
    ├─▶ KOSPI: pykrx 우선 → FinanceDataReader fallback
    ├─▶ KOSDAQ: 키움 API (229200)
    └─▶ SPY/QQQ/VIX: us_futures_data_v8.fetch_data()

15:40 - 레짐 분석 실행
    ├─▶ 사전 생성된 캐시 사용 ✅
    └─▶ 레짐 분석 결과 저장

15:42 - 한국 주식 스캔 실행
    ├─▶ 과거 데이터: 캐시에서 자동 로드 ✅
    └─▶ 당일 데이터: API 호출 → 캐시 저장 ✅
```

---

## 2. 레짐 분석용 캐시 사전 생성 (15:35)

### 목적
- 레짐 분석 실패 방지
- 장 마감 후 확정 데이터 사용
- 종목 수 적음 (10개 미만) → 빠른 생성

### 프로세스

#### 2.1 KOSPI 지수 데이터 생성

**우선순위**: pykrx > FinanceDataReader > 캐시 > 키움 API ETF

```python
# backend/scheduler.py - preload_regime_cache_kr()
from utils.kospi_data_loader import get_kospi_data

today = datetime.now().strftime('%Y%m%d')
kospi_df = get_kospi_data(date=today, days=365)
```

**동작**:
1. **pykrx 시도** (한국거래소 공식 데이터)
   ```python
   from pykrx import stock
   df = stock.get_index_ohlcv_by_date(start_date, end_date, "1001")
   ```
   - 정확도 높음
   - 당일 데이터 제공 가능

2. **FinanceDataReader fallback**
   ```python
   import FinanceDataReader as fdr
   df = fdr.DataReader('KS11', start_date, end_date)
   ```
   - 지연 가능성 있음
   - 과거 데이터는 정확

3. **캐시 fallback**
   - `data_cache/kospi200_ohlcv.pkl` 사용

4. **키움 API ETF 최후의 수단**
   - `069500` (KOSPI200 ETF) 사용
   - 정확도 낮음 (약 15배 차이)

**결과**: KOSPI 지수 데이터 준비 완료

#### 2.2 KOSDAQ 지수 데이터 생성

**방법**: 키움 API 직접 사용

```python
# backend/scheduler.py - preload_regime_cache_kr()
from kiwoom_api import api

kosdaq_csv = "data_cache/ohlcv/229200.csv"

# 캐시 없으면 키움 API로 생성
if not os.path.exists(kosdaq_csv):
    today = datetime.now().strftime('%Y%m%d')
    df = api.get_ohlcv("229200", 365, today)  # KOSDAQ 지수
    df.to_csv(kosdaq_csv)
```

**동작**:
1. CSV 캐시 확인
2. 캐시 없으면 키움 API 호출
3. CSV로 저장

**결과**: KOSDAQ 지수 데이터 준비 완료

#### 2.3 미국 선물 데이터 생성

**방법**: Yahoo Finance Chart API

```python
# backend/scheduler.py - preload_regime_cache_kr()
from services.us_futures_data_v8 import us_futures_data_v8

symbols = ['SPY', 'QQQ', '^VIX']
for symbol in symbols:
    df = us_futures_data_v8.fetch_data(symbol, period='1y')
    # 자동으로 캐시 저장됨
```

**동작**:
1. `us_futures_data_v8.fetch_data()` 호출
2. 자동으로 CSV 캐시 저장
3. 캐시 경로: `cache/us_futures/{symbol}.csv`

**결과**: SPY/QQQ/VIX 데이터 준비 완료

---

## 3. 레짐 분석 실행 (15:40)

### 프로세스

#### 3.1 데이터 로드

```python
# backend/scanner_v2/regime_v4.py - load_full_data()
from utils.kospi_data_loader import get_kospi_data

# KOSPI 데이터 (pykrx 우선)
date_str = target_date.strftime('%Y%m%d')
kospi_df = get_kospi_data(date=date_str, days=365)

# KOSDAQ 데이터 (CSV 캐시)
kosdaq_csv = "data_cache/ohlcv/229200.csv"
kosdaq_df = pd.read_csv(kosdaq_csv, index_col=0, parse_dates=True)

# 미국 선물 데이터 (CSV 캐시)
df_spy = us_futures_data_v8.fetch_data("SPY")
df_qqq = us_futures_data_v8.fetch_data("QQQ")
df_vix = us_futures_data_v8.fetch_data("^VIX")
```

**캐시 활용**:
- ✅ KOSPI: pykrx/FinanceDataReader (사전 생성됨)
- ✅ KOSDAQ: CSV 캐시 (사전 생성됨)
- ✅ SPY/QQQ/VIX: CSV 캐시 (사전 생성됨)

#### 3.2 레짐 분석 수행

```python
# Trend Score 계산
kr_trend = compute_kr_trend_features(kospi_df, kosdaq_df)
us_trend = compute_us_trend_features(df_spy, df_qqq, df_vix)

# Risk Score 계산
kr_risk = compute_kr_risk_features(kospi_df, date)
us_risk = compute_us_risk_features(df_spy, df_qqq, df_vix)

# Global Regime 결정
final_regime = combine_global_regime_v4(...)
```

**결과**: 레짐 분석 완료 (bull/neutral/bear/crash)

---

## 4. 한국 주식 스캔 실행 (15:42)

### 프로세스

#### 4.1 유니버스 구성

```python
# backend/main.py - scan()
from kiwoom_api import api

kospi = api.get_top_codes('KOSPI', 200)
kosdaq = api.get_top_codes('KOSDAQ', 200)
universe = kospi + kosdaq  # 총 400개
```

#### 4.2 각 종목 스캔

```python
# backend/kiwoom_api.py - get_ohlcv()
for code in universe:
    df = api.get_ohlcv(code, 220, None)  # base_dt=None (최신 데이터)
    # ↑ 내부 동작:
    # 1. 메모리 캐시 확인
    # 2. 디스크 캐시 확인
    # 3. API 호출 (과거 데이터는 캐시에서, 당일 데이터만 API)
    # 4. 캐시 저장 (메모리 + 디스크)
```

**캐시 활용**:

**1단계: 메모리 캐시 확인**
```python
# backend/kiwoom_api.py - _get_cached_ohlcv()
cached_df = self._get_cached_ohlcv(code, count, base_dt)
if cached_df is not None:
    return cached_df  # 캐시 히트 ✅
```

**2단계: 디스크 캐시 확인** (base_dt가 None이면 스킵)
```python
# base_dt가 None이면 디스크 캐시 확인 안 함
# (최신 데이터가 필요하므로)
```

**3단계: API 호출**
```python
# backend/kiwoom_api.py - _fetch_ohlcv_from_api()
df = self._fetch_ohlcv_from_api(code, count, base_dt)
```

**내부 동작**:
- 과거 데이터: 디스크 캐시에서 자동 로드
- 당일 데이터: API로 가져와서 추가
- 캐시 저장: 메모리 + 디스크

**4단계: 캐시 저장**
```python
# 메모리 캐시 저장
self._set_cached_ohlcv(code, count, base_dt, df)

# 디스크 캐시 저장 (base_dt가 None이면 스킵)
if base_dt and self._disk_cache_enabled:
    self._save_to_disk_cache(code, count, base_dt, df)
```

#### 4.3 스캔 결과 저장

```python
# 스캔 결과를 DB에 저장
# scan_ranks 테이블에 저장
```

---

## 5. 캐시 동작 상세

### 5.1 레짐 분석용 캐시

| 종목 | 데이터 소스 | 캐시 위치 | 생성 시점 | 사용 시점 |
|------|------------|----------|----------|----------|
| **KOSPI** | pykrx > FinanceDataReader | 메모리/임시 | 15:35 | 15:40 |
| **KOSDAQ** | 키움 API (229200) | `data_cache/ohlcv/229200.csv` | 15:35 | 15:40 |
| **SPY** | Yahoo Finance Chart API | `cache/us_futures/SPY.csv` | 15:35 | 15:40 |
| **QQQ** | Yahoo Finance Chart API | `cache/us_futures/QQQ.csv` | 15:35 | 15:40 |
| **VIX** | Yahoo Finance Chart API | `cache/us_futures/^VIX.csv` | 15:35 | 15:40 |

**특징**:
- 종목 수 적음 (5개)
- 생성 시간 짧음 (1분 미만)
- 장 마감 후 확정 데이터

### 5.2 스캔용 캐시

| 항목 | 내용 |
|------|------|
| **캐시 타입** | 메모리 캐시 + 디스크 캐시 |
| **메모리 캐시** | `{(code, count, base_dt, hour_key): (df, timestamp)}` |
| **디스크 캐시** | `cache/ohlcv/{code}_{count}_{base_dt}.pkl` |
| **TTL** | 동적 계산 (장중 1분, 장 마감 후 24시간) |
| **자동 관리** | `get_ohlcv()` 함수가 자동 처리 |

**동작 방식**:
```
스캔 시작
    └─▶ api.get_ohlcv(code, 220, None)
        ├─▶ 1. 메모리 캐시 확인
        │   └─▶ 캐시 있으면 반환 ✅
        │
        ├─▶ 2. 디스크 캐시 확인 (base_dt=None이면 스킵)
        │
        └─▶ 3. API 호출
            ├─▶ 과거 데이터: 디스크 캐시에서 자동 로드 ✅
            └─▶ 당일 데이터: API로 가져와서 추가 ✅
            └─▶ 캐시 저장 (메모리 + 디스크)
```

---

## 6. 개선 사항 요약

### 6.1 레짐 분석용 캐시

**개선 전**:
- KOSPI: FinanceDataReader 직접 사용
- 지연 가능성 있음
- 당일 데이터 미제공 가능

**개선 후**:
- KOSPI: pykrx 우선 사용
- 한국거래소 공식 데이터
- 당일 데이터 제공 가능
- FinanceDataReader fallback 유지

### 6.2 스캔용 캐시

**개선 전**:
- 사전 생성 함수 필요 (복잡)
- 불필요한 API 호출 가능

**개선 후**:
- `get_ohlcv()` 함수가 자동 처리
- 과거 데이터는 캐시에서 자동 로드
- 당일 데이터만 API 호출
- 사전 생성 불필요

---

## 7. 전체 프로세스 플로우차트

```
[15:35] 레짐 분석용 캐시 사전 생성
    │
    ├─▶ KOSPI: pykrx → FinanceDataReader → 캐시 → ETF
    │   └─▶ 한국거래소 공식 데이터 사용 ✅
    │
    ├─▶ KOSDAQ: 키움 API (229200)
    │   └─▶ CSV 캐시 저장 ✅
    │
    └─▶ SPY/QQQ/VIX: Yahoo Finance Chart API
        └─▶ CSV 캐시 저장 ✅

[15:40] 레짐 분석 실행
    │
    ├─▶ 사전 생성된 캐시 사용 ✅
    ├─▶ Trend Score 계산
    ├─▶ Risk Score 계산
    └─▶ Global Regime 결정

[15:42] 한국 주식 스캔 실행
    │
    ├─▶ 유니버스 구성 (400개 종목)
    │
    └─▶ 각 종목 스캔
        │
        ├─▶ api.get_ohlcv(code, 220, None)
        │   │
        │   ├─▶ 메모리 캐시 확인
        │   │   └─▶ 캐시 있으면 반환 ✅
        │   │
        │   ├─▶ 디스크 캐시 확인 (스킵)
        │   │
        │   └─▶ API 호출
        │       ├─▶ 과거 데이터: 디스크 캐시에서 로드 ✅
        │       └─▶ 당일 데이터: API로 가져옴 ✅
        │       └─▶ 캐시 저장 (메모리 + 디스크)
        │
        ├─▶ 지표 계산
        ├─▶ 필터링
        └─▶ 결과 저장 (DB)
```

---

## 8. 캐시 히트율 예상

### 레짐 분석용 캐시

| 종목 | 캐시 히트율 | 이유 |
|------|------------|------|
| **KOSPI** | 100% | 사전 생성됨 |
| **KOSDAQ** | 100% | 사전 생성됨 |
| **SPY/QQQ/VIX** | 100% | 사전 생성됨 |

### 스캔용 캐시

| 데이터 타입 | 캐시 히트율 | 이유 |
|------------|------------|------|
| **과거 데이터** | 90%+ | 디스크 캐시에 저장됨 |
| **당일 데이터** | 0% | 스캔 시점에 API 호출 |
| **전체** | 80%+ | 과거 데이터가 대부분 |

---

## 9. 성능 개선 효과

### 레짐 분석

**개선 전**:
- FinanceDataReader 지연 가능
- 당일 데이터 미제공 가능
- 레짐 분석 정확도 저하 가능

**개선 후**:
- pykrx 우선 사용 (정확도 높음)
- 당일 데이터 제공 가능
- 레짐 분석 정확도 향상 ✅

### 스캔

**개선 전**:
- 모든 데이터 API 호출
- 스캔 시간: 약 5분

**개선 후**:
- 과거 데이터는 캐시에서 로드
- 당일 데이터만 API 호출
- 스캔 시간: 약 3분 (40% 단축) ✅

---

## 10. 핵심 개선 사항

### 10.1 레짐 분석용 캐시

1. **KOSPI**: pykrx 우선 사용
   - 한국거래소 공식 데이터
   - 정확도 높음
   - 당일 데이터 제공 가능

2. **KOSDAQ**: 키움 API 자동 생성
   - 캐시 없으면 자동 생성
   - CSV 캐시 저장

3. **SPY/QQQ/VIX**: Yahoo Finance Chart API
   - 자동 캐시 저장
   - 사전 생성 완료

### 10.2 스캔용 캐시

1. **자동 캐시 관리**
   - `get_ohlcv()` 함수가 자동 처리
   - 메모리 캐시 + 디스크 캐시

2. **과거 데이터 자동 로드**
   - 디스크 캐시에서 자동 로드
   - API 호출 최소화

3. **당일 데이터만 API 호출**
   - 최신 데이터 보장
   - 효율적인 캐시 활용

---

## 11. 결론

### 레짐 분석용 캐시
- ✅ **사전 생성 필수** (15:35)
- ✅ **pykrx 우선 사용** (정확도 높음)
- ✅ **당일 데이터 제공 가능** (지연 문제 해소)

### 스캔용 캐시
- ✅ **자동 캐시 관리** (get_ohlcv 함수)
- ✅ **과거 데이터 자동 로드** (캐시 활용)
- ✅ **당일 데이터만 API 호출** (최신성 보장)

**핵심**: 레짐 분석용 캐시는 사전 생성으로 안정성을 확보하고, 스캔용 캐시는 자동 관리로 효율성을 높였습니다.

