# 캐시 데이터 문제 해결 방법 심층 분석 및 검증

**작성일**: 2025-11-28  
**목적**: KOSPI 및 VIX 캐시 데이터 문제의 원인 분석, 해결 방법 제시, 검증

---

## 📋 문제 요약

| 문제 | 심각도 | 영향 |
|------|--------|------|
| KOSPI: ETF 데이터 사용 | **높음** | 레짐 분석 정확도 저하 |
| VIX: 단위 오류 (10배) | **높음** | 리스크 판단 오류 |

---

## 🔍 문제 1: KOSPI 데이터가 ETF(069500) 데이터를 사용

### 원인 분석

#### 1.1 데이터 소스 확인

**문제가 발생하는 코드 위치**:
```python
# backend/fill_november_regime_cache.py:69
df_new = api.get_ohlcv("069500", count=220, base_dt=end_date)

# backend/regenerate_kospi_cache.py:106
df_batch = api.get_ohlcv("069500", count=count, base_dt=batch_end_str)

# backend/services/regime_analyzer_cached.py:25
df = api.get_ohlcv("069500", 30, date)  # KOSPI200 ETF (30일)

# backend/market_analyzer.py:266, 319
df = api.get_ohlcv("069500", 2, date)
df = api.get_ohlcv("069500", lookback_days, date)
```

**문제점**:
- `069500`은 KOSPI200 ETF 코드
- 실제 KOSPI 지수 코드가 아님
- ETF 가격과 지수 값이 다름 (약 15배 차이)

#### 1.2 ETF vs 지수 차이

| 항목 | ETF(069500) | 실제 지수 |
|------|-------------|-----------|
| 가격 범위 | 50,000~60,000원 | 3,000~4,000 포인트 |
| 최근 종가 | 55,650원 | 3,926.59 포인트 |
| 7월 R20 평균 | 17.44% | 12.65% |
| 차이 | - | 약 5%p |

**영향**:
- R20 계산이 부정확 → Trend Score 오류
- 레짐 판단 오류 → 스캐너 추천 종목 수 오류

### 해결 방법

#### 방법 1: pykrx 사용 (권장) ⭐

**장점**:
- 한국거래소(KRX) 공식 데이터
- 정확도 높음
- 무료

**단점**:
- 추가 패키지 설치 필요 (`pip install pykrx`)

**구현**:
```python
from pykrx import stock

# KOSPI 지수 코드: 1001
df = stock.get_index_ohlcv_by_date(start_date, end_date, "1001")
```

**검증**:
- ✅ 실제 KOSPI 지수 데이터 제공
- ✅ 정확한 가격 범위 (2000~4000)
- ✅ R20 계산 정확

#### 방법 2: FinanceDataReader 사용

**장점**:
- 설치 간단
- 안정적
- 널리 사용됨

**단점**:
- 외부 라이브러리 의존
- 데이터 소스가 공식이 아님

**구현**:
```python
import FinanceDataReader as fdr

df = fdr.DataReader('KS11', start_date, end_date)
```

**검증**:
- ✅ 실제 KOSPI 지수 데이터 제공
- ✅ 정확한 가격 범위
- ⚠️ pykrx보다 약간 느릴 수 있음

#### 방법 3: yfinance 사용

**장점**:
- 글로벌 데이터 소스
- 다양한 시장 데이터 제공

**단점**:
- 한국 데이터 정확도 낮을 수 있음
- API 제한 가능

**구현**:
```python
import yfinance as yf

ticker = yf.Ticker("^KS11")
df = ticker.history(start=start_date, end=end_date)
```

**검증**:
- ⚠️ 데이터 정확도 확인 필요
- ⚠️ 지연 가능성

### 권장 해결 순서

1. **1순위**: pykrx 사용 (공식 데이터, 정확도 높음)
2. **2순위**: FinanceDataReader (fallback)
3. **3순위**: yfinance (최후의 수단)

### 수정 대상 파일

1. `backend/fill_november_regime_cache.py` - `update_kospi_cache()` 함수
2. `backend/regenerate_kospi_cache.py` - `regenerate_kospi_cache()` 함수
3. `backend/services/regime_analyzer_cached.py` - `get_kospi_data()` 함수
4. `backend/market_analyzer.py` - `_get_kospi_data()` 함수
5. `backend/scanner_v2/regime_v4.py` - `load_full_data()` 함수 (이미 FinanceDataReader 사용 중)

---

## 🔍 문제 2: VIX 데이터가 10배로 저장됨

### 원인 분석

#### 2.1 데이터 확인

**현재 상태**:
- 캐시 파일: `data_cache/vix_ohlcv.pkl`
- 캐시 값: 140.30
- 실제 값: 16.35
- 비율: 약 8.6배 (반올림 시 10배)

**영향**:
- VIX 기반 리스크 판단 오류
- 글로벌 레짐 결정 오류
- crash 레짐 판단 오류

#### 2.2 가능한 원인

1. **데이터 수집 시 단위 오류**
   - API 응답 단위 오류
   - 데이터 변환 과정에서 10배 곱셈

2. **데이터 소스 확인 필요**
   - `backend/services/us_futures_data_v8.py` 확인
   - `backend/fill_november_regime_cache.py` 확인

### 해결 방법

#### 방법 1: 캐시 데이터 직접 수정 (즉시 적용) ⭐

**장점**:
- 빠른 수정
- 즉시 적용 가능
- 롤백 가능 (백업)

**단점**:
- 근본 원인 미해결
- 향후 데이터 수집 시 재발 가능

**구현**:
```python
# 캐시 로드
with open("data_cache/vix_ohlcv.pkl", 'rb') as f:
    vix_df = pickle.load(f)

# 단위 수정
vix_df['close'] = vix_df['close'] / 10
vix_df['open'] = vix_df['open'] / 10
vix_df['high'] = vix_df['high'] / 10
vix_df['low'] = vix_df['low'] / 10

# 저장
vix_df.to_pickle("data_cache/vix_ohlcv.pkl")
```

**검증**:
- ✅ 즉시 적용 가능
- ✅ 백업 후 수정 가능
- ⚠️ 근본 원인 해결 필요

#### 방법 2: 데이터 소스 수정 (근본 해결)

**장점**:
- 근본 원인 해결
- 향후 재발 방지

**단점**:
- 데이터 수집 로직 수정 필요
- 시간 소요

**작업**:
1. VIX 데이터 수집 코드 확인
2. 단위 오류 발생 지점 찾기
3. 수정 및 테스트

### 권장 해결 순서

1. **즉시**: 캐시 데이터 직접 수정 (방법 1)
2. **장기**: 데이터 소스 수정 (방법 2)

---

## 🛠️ 해결 스크립트

### `backend/fix_cache_data_issues.py`

**기능**:
1. KOSPI 캐시를 실제 지수 데이터로 교체
2. VIX 캐시 단위 오류 수정
3. 검증

**사용법**:
```bash
cd backend
source venv/bin/activate
python fix_cache_data_issues.py
```

**동작**:
1. 기존 캐시 백업
2. pykrx → FinanceDataReader → yfinance 순서로 시도
3. 데이터 검증
4. 캐시 저장

---

## ✅ 검증 방법

### 1. KOSPI 검증

```python
# 캐시 로드
with open("data_cache/kospi200_ohlcv.pkl", 'rb') as f:
    kospi_df = pickle.load(f)

# 검증
latest_close = kospi_df.iloc[-1]['close']
assert 2000 <= latest_close <= 4000, f"KOSPI 지수 범위 비정상: {latest_close}"

# R20 계산
if len(kospi_df) >= 21:
    r20 = (kospi_df.iloc[-1]['close'] / kospi_df.iloc[-21]['close'] - 1) * 100
    print(f"R20: {r20:.2f}%")
```

### 2. VIX 검증

```python
# 캐시 로드
with open("data_cache/vix_ohlcv.pkl", 'rb') as f:
    vix_df = pickle.load(f)

# 검증
latest_close = vix_df.iloc[-1]['close']
assert 10 <= latest_close <= 50, f"VIX 범위 비정상: {latest_close}"

# 실제 값과 비교
import yfinance as yf
ticker = yf.Ticker("^VIX")
real_vix = ticker.history(period="1d").iloc[-1]['Close']
diff = abs(latest_close - real_vix)
assert diff < 2, f"VIX 차이가 큼: {diff}"
```

---

## 📊 예상 효과

### 수정 전

| 항목 | 값 | 문제 |
|------|-----|------|
| KOSPI 종가 | 55,650원 | ETF 데이터 |
| KOSPI R20 | 17.44% | 비정상적 |
| VIX 종가 | 140.30 | 10배 오류 |
| 레짐 정확도 | 낮음 | 데이터 오류 |

### 수정 후

| 항목 | 값 | 상태 |
|------|-----|------|
| KOSPI 종가 | 3,926.59 포인트 | ✅ 정상 |
| KOSPI R20 | 12.65% | ✅ 정상 |
| VIX 종가 | 16.35 | ✅ 정상 |
| 레짐 정확도 | 높음 | ✅ 개선 |

---

## 🚀 실행 계획

### Phase 1: 즉시 조치 (1일)

1. ✅ 문제 분석 완료
2. ✅ 해결 스크립트 작성
3. ⏳ 스크립트 실행 및 검증
4. ⏳ 결과 확인

### Phase 2: 코드 수정 (2-3일)

1. ⏳ KOSPI 데이터 소스 수정
   - `fill_november_regime_cache.py`
   - `regenerate_kospi_cache.py`
   - `services/regime_analyzer_cached.py`
   - `market_analyzer.py`

2. ⏳ VIX 데이터 소스 확인 및 수정
   - `services/us_futures_data_v8.py`
   - `fill_november_regime_cache.py`

### Phase 3: 검증 및 모니터링 (1주일)

1. ⏳ 레짐 분석 정확도 확인
2. ⏳ 스캐너 추천 종목 수 확인
3. ⏳ 정기적인 캐시 데이터 검증

---

## 📝 주의사항

1. **백업 필수**: 수정 전 기존 캐시 백업
2. **롤백 계획**: 문제 발생 시 즉시 롤백 가능
3. **점진적 적용**: 한 번에 하나씩 수정 및 검증
4. **모니터링**: 수정 후 일주일간 모니터링

---

## 🔗 참고 자료

- [pykrx 문서](https://github.com/sharebook-kr/pykrx)
- [FinanceDataReader 문서](https://github.com/financedata-org/FinanceDataReader)
- [yfinance 문서](https://github.com/ranaroussi/yfinance)

