# KOSPI 지수 데이터 소스 분석 및 해결 방법

**작성일**: 2025-11-29  
**문제**: 키움 API로는 KOSPI 지수를 직접 조회할 수 없음

---

## 🔍 문제 상황

### 키움 API의 한계

키움 API (KIS OpenAPI)는:
- ✅ **개별 종목 데이터**: 조회 가능 (예: `005930` = 삼성전자)
- ✅ **ETF 데이터**: 조회 가능 (예: `069500` = KOSPI200 ETF)
- ❌ **지수 데이터**: 조회 불가능 (지수는 종목 코드가 아님)

**결론**: KOSPI 지수는 "종목"이 아니라 "지수"이므로 API로 직접 조회할 수 없습니다.

---

## 📊 현재 코드의 해결 방법

### 1. `market_analyzer.py` - `_get_kospi_data()`

**우선순위**:
1. **FinanceDataReader** (`KS11`) ← 실제 지수 ✅
2. 키움 API ETF(`069500`) ← fallback ⚠️

**코드**:
```python
try:
    import FinanceDataReader as fdr
    df_fdr = fdr.DataReader('KS11', start_date, end_date_str)
    # 실제 KOSPI 지수 데이터 사용
except (ImportError, Exception) as e:
    logger.warning(f"FinanceDataReader 사용 실패: {e}, 키움 API ETF 사용")
    # Fallback: 기존 방법 (069500 ETF)
    df = api.get_ohlcv("069500", lookback_days, date)
```

**문제점**:
- FinanceDataReader 실패 시 ETF 사용
- ETF는 지수가 아니므로 부정확

### 2. `scanner_v2/regime_v4.py` - `load_full_data()`

**우선순위**:
1. **FinanceDataReader** (`KS11`) ← 실제 지수 ✅
2. **캐시** (`kospi200_ohlcv.pkl`) ← 이미 실제 지수로 교체됨 ✅

**코드**:
```python
try:
    import FinanceDataReader as fdr
    kospi_df = fdr.DataReader('KS11', start_date, end_date)
    # 실제 KOSPI 지수 데이터 사용
except ImportError:
    # Fallback: 캐시 사용
    cache_path = "data_cache/kospi200_ohlcv.pkl"
    kospi_df = pd.read_pickle(cache_path)
```

**상태**:
- ✅ 캐시가 실제 지수 데이터로 교체됨
- ✅ 정확한 데이터 사용

### 3. `services/regime_analyzer_cached.py` - `get_kospi_data()`

**현재**:
```python
df = api.get_ohlcv("069500", 30, date)  # KOSPI200 ETF (30일)
```

**문제점**:
- ❌ ETF 데이터 직접 사용
- ❌ 실제 지수 데이터 아님

---

## 📈 실제 데이터 비교

| 데이터 소스 | 값 | 타입 | 정확도 |
|------------|-----|------|--------|
| 키움 API ETF(069500) | 55,650원 | ETF 가격 | ❌ 부정확 |
| FinanceDataReader (KS11) | 3,926.59 포인트 | 실제 지수 | ✅ 정확 |
| pykrx (1001) | 3,926.59 포인트 | 실제 지수 | ✅ 정확 |

**차이**:
- ETF와 실제 지수: 약 **15배** 차이
- R20 계산 시: 약 **5%p** 차이 발생

---

## ✅ 해결 방법

### 이미 완료된 작업

1. ✅ **캐시 교체**: `kospi200_ohlcv.pkl`을 실제 지수 데이터로 교체
2. ✅ **regime_v4.py**: FinanceDataReader 사용 (캐시 fallback)
3. ✅ **market_analyzer.py**: FinanceDataReader 우선 사용

### 수정이 필요한 코드

#### 1. `services/regime_analyzer_cached.py`

**현재**:
```python
def get_kospi_data(self, date: str = None) -> pd.DataFrame:
    df = api.get_ohlcv("069500", 30, date)  # ❌ ETF 사용
    return df
```

**수정 필요**:
```python
def get_kospi_data(self, date: str = None) -> pd.DataFrame:
    """KOSPI 지수 데이터 조회"""
    try:
        # 1. pykrx 시도 (한국거래소 공식 데이터)
        from pykrx import stock
        end_date = pd.to_datetime(date, format='%Y%m%d') if date else pd.to_datetime(datetime.now())
        start_date = (end_date - pd.Timedelta(days=30)).strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        df = stock.get_index_ohlcv_by_date(start_date, end_date_str, "1001")
        # 컬럼명 변환
        column_mapping = {'시가': 'open', '고가': 'high', '저가': 'low', '종가': 'close', '거래량': 'volume'}
        df = df.rename(columns=column_mapping)[['open', 'high', 'low', 'close', 'volume']]
        return df
    except ImportError:
        # 2. FinanceDataReader 시도
        try:
            import FinanceDataReader as fdr
            end_date = pd.to_datetime(date, format='%Y%m%d') if date else datetime.now()
            start_date = (end_date - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            df = fdr.DataReader('KS11', start_date, end_date_str)
            df.columns = df.columns.str.lower()
            return df
        except ImportError:
            # 3. 캐시 사용 (이미 실제 지수 데이터로 교체됨)
            cache_path = os.path.join(os.path.dirname(__file__), '..', 'data_cache', 'kospi200_ohlcv.pkl')
            if os.path.exists(cache_path):
                df = pd.read_pickle(cache_path)
                if date:
                    target_date = pd.to_datetime(date, format='%Y%m%d')
                    df = df[df.index <= target_date].tail(30)
                return df
            return pd.DataFrame()
```

#### 2. `fill_november_regime_cache.py`

**현재**:
```python
df_new = api.get_ohlcv("069500", count=220, base_dt=end_date)  # ❌ ETF 사용
```

**수정 필요**: pykrx 또는 FinanceDataReader 사용

#### 3. `regenerate_kospi_cache.py`

**현재**:
```python
df_batch = api.get_ohlcv("069500", count=count, base_dt=batch_end_str)  # ❌ ETF 사용
```

**수정 필요**: pykrx 또는 FinanceDataReader 사용

#### 4. `market_analyzer.py` - ETF fallback 경고 추가

**현재**:
```python
except (ImportError, Exception) as e:
    logger.warning(f"FinanceDataReader 사용 실패: {e}, 키움 API ETF 사용")
    df = api.get_ohlcv("069500", lookback_days, date)  # ⚠️ ETF fallback
```

**개선**:
```python
except (ImportError, Exception) as e:
    logger.error(f"FinanceDataReader 사용 실패: {e}")
    logger.error("⚠️ 경고: ETF(069500) 데이터 사용 - 실제 지수가 아님!")
    # 캐시 시도 (이미 실제 지수 데이터로 교체됨)
    cache_path = Path("data_cache/kospi200_ohlcv.pkl")
    if cache_path.exists():
        df = pd.read_pickle(cache_path)
        # 날짜 필터링
        if date:
            target_date = pd.to_datetime(date, format='%Y%m%d')
            df = df[df.index <= target_date].tail(lookback_days)
    else:
        # 최후의 수단: ETF 사용 (부정확)
        df = api.get_ohlcv("069500", lookback_days, date)
```

---

## 🎯 권장 해결 순서

### 우선순위 1: 즉시 수정 (높음)

1. **`services/regime_analyzer_cached.py`**
   - ETF 대신 pykrx/FinanceDataReader 사용
   - 캐시 fallback 추가

### 우선순위 2: 개선 (중간)

2. **`fill_november_regime_cache.py`**
   - ETF 대신 실제 지수 데이터 사용

3. **`regenerate_kospi_cache.py`**
   - ETF 대신 실제 지수 데이터 사용

### 우선순위 3: 경고 추가 (낮음)

4. **`market_analyzer.py`**
   - ETF fallback 시 명확한 경고 추가
   - 캐시 우선 사용

---

## 📝 결론

**현재 상황**:
- ✅ 캐시는 이미 실제 지수 데이터로 교체됨
- ✅ `regime_v4.py`는 FinanceDataReader 사용
- ⚠️ 일부 코드는 여전히 ETF 사용

**해결 방법**:
1. 모든 코드에서 pykrx/FinanceDataReader 우선 사용
2. 캐시를 실제 지수 데이터로 유지
3. ETF fallback 제거 또는 명확한 경고 추가

**핵심**: 키움 API만으로는 KOSPI 지수를 알 수 없으므로, **외부 라이브러리(pykrx/FinanceDataReader) 또는 캐시된 실제 지수 데이터**를 사용해야 합니다.

