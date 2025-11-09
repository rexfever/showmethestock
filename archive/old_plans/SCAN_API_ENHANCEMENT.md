# 스캔 API 응답 필드 추가 작업

## 📋 목표

`/scan` API가 **거래일, 종목명, 거래량, 거래대금, 종목코드, 등락률, 종가**를 모두 반환하도록 개선

## 🔍 현재 상태 분석

### 현재 `/scan` API 응답 구조

```json
{
  "as_of": "2025-10-20",           // ✅ 거래일
  "items": [
    {
      "ticker": "005930",           // ✅ 종목코드
      "name": "삼성전자",            // ✅ 종목명
      "indicators": {
        "close": 54600.0,           // ✅ 종가
        "VOL": 2379791,             // ✅ 거래량
        "TEMA": 54555.95,
        "DEMA": 54503.48,
        // ❌ change_rate 없음 (등락률)
        // ❌ trading_value 없음 (거래대금)
      }
    }
  ]
}
```

### 누락된 필드

| 필드 | 설명 | 현재 상태 |
|------|------|----------|
| `거래일` | YYYY-MM-DD 형식 | ✅ `as_of` 필드로 제공 |
| `종목명` | 한글 종목명 | ✅ `name` 필드로 제공 |
| `거래량` | 일일 거래량 | ✅ `indicators.VOL`로 제공 |
| `종목코드` | 6자리 코드 | ✅ `ticker` 필드로 제공 |
| `종가` | 당일 종가 | ✅ `indicators.close`로 제공 |
| `등락률` | 전일 대비 등락률(%) | ❌ **없음** |
| `거래대금` | 종가 × 거래량 | ❌ **없음** |

## ✅ 구현 방안

### 방안 1: 모델에 필드 추가

**파일**: `backend/models.py` (라인 6-17)

**변경 전:**
```python
class IndicatorPayload(BaseModel):
    TEMA: float
    DEMA: float
    MACD_OSC: float
    MACD_LINE: float
    MACD_SIGNAL: float
    RSI_TEMA: float
    RSI_DEMA: float
    OBV: float
    VOL: int
    VOL_MA5: float
    close: float
```

**변경 후:**
```python
class IndicatorPayload(BaseModel):
    TEMA: float
    DEMA: float
    MACD_OSC: float
    MACD_LINE: float
    MACD_SIGNAL: float
    RSI_TEMA: float
    RSI_DEMA: float
    OBV: float
    VOL: int
    VOL_MA5: float
    close: float
    # ✅ 추가 필드
    change_rate: Optional[float] = 0.0      # 등락률 (%)
    trading_value: Optional[int] = 0        # 거래대금 (원)
```

**주의사항:**
- `Optional`로 설정하여 기존 데이터와 호환성 유지
- 기본값 설정으로 누락 시에도 에러 방지

---

### 방안 2: 스캔 시점에 계산

**파일**: `backend/scanner.py`
**함수**: `scan_one_symbol()` (라인 509-577)

#### 2-1. 등락률 계산

**추가 위치**: 라인 545 (return 문 바로 전)

```python
def scan_one_symbol(code: str, base_date: str = None, market_condition=None) -> dict:
    """단일 종목 스캔 함수 (기존 스캔 로직을 함수로 분리)"""
    try:
        from kiwoom_api import api
        df = api.get_ohlcv(code, config.ohlcv_count, base_date)
        if df.empty or len(df) < 21:
            return None
        
        # ... 기존 로직 (필터링, 지표 계산 등)
        
        cur = df.iloc[-1]  # 최근 데이터 (오늘)
        
        # ✅ 추가: 등락률 계산
        change_rate = 0.0
        if len(df) >= 2:
            prev_close = df.iloc[-2]["close"]  # 전일 종가
            current_close = cur["close"]        # 당일 종가
            if prev_close > 0:
                change_rate = round(((current_close - prev_close) / prev_close) * 100, 2)
        
        # ✅ 추가: 거래대금 계산 (OHLC 평균가 사용)
        avg_price = (cur["open"] + cur["high"] + cur["low"] + cur["close"]) / 4
        trading_value = int(avg_price * cur["volume"])
        
        return {
            "ticker": code,
            "name": api.get_stock_name(code),
            "match": matched,
            "score": score,
            "indicators": {
                "TEMA": cur.TEMA20,
                "DEMA": cur.DEMA10,
                "MACD_OSC": cur.MACD_OSC,
                "MACD_LINE": cur.MACD_LINE,
                "MACD_SIGNAL": cur.MACD_SIGNAL,
                "RSI_TEMA": cur.RSI_TEMA,
                "RSI_DEMA": cur.RSI_DEMA,
                "OBV": cur.OBV,
                "VOL": cur.volume,
                "VOL_MA5": cur.VOL_MA5,
                "close": cur.close,
                "change_rate": change_rate,        # ✅ 추가
                "trading_value": trading_value,    # ✅ 추가
            },
            "trend": {
                "TEMA20_SLOPE20": cur.TEMA20_SLOPE20,
                "OBV_SLOPE20": cur.OBV_SLOPE20,
                "ABOVE_CNT5": cur.ABOVE_CNT5,
                "DEMA10_SLOPE20": cur.DEMA10_SLOPE20,
            },
            "flags": flags,
            "score_label": score_label,
            "strategy": strategy,
        }
    except Exception:
        return None
```

**계산 로직:**
```python
# 등락률 = ((당일종가 - 전일종가) / 전일종가) × 100
change_rate = ((current_close - prev_close) / prev_close) * 100

# 거래대금 = 평균가 × 거래량 (OHLC 평균)
avg_price = (open + high + low + close) / 4
trading_value = avg_price * volume
```

**참고:**
- 종가 × 거래량은 부정확 (하루 중 특정 시점만 반영)
- OHLC 평균가를 사용하는 것이 실제 거래대금에 더 근사

---

### 방안 3: DB 저장 로직 개선

**파일**: `backend/main.py`
**함수**: `_save_snapshot_db()` (라인 179-233)

**변경 전:**
```python
def _save_snapshot_db(as_of: str, items: List[ScanItem]):
    for it in items:
        close_price = float(getattr(it.indicators, 'close', 0))
        volume = 0  # ❌
        change_rate = 0.0  # ❌
        
        # API 재조회
        try:
            quote = api.get_stock_quote(it.ticker)
            if "error" not in quote:
                close_price = quote.get("current_price", close_price)
                volume = quote.get("volume", volume)
                change_rate = quote.get("change_rate", change_rate)
        except Exception as e:
            pass
```

**변경 후:**
```python
def _save_snapshot_db(as_of: str, items: List[ScanItem]):
    for it in items:
        # ✅ 이미 계산된 값 사용
        close_price = float(it.indicators.close)
        volume = int(it.indicators.VOL)
        change_rate = float(getattr(it.indicators, 'change_rate', 0.0))
        
        # ❌ API 재조회 제거 (불필요)
        # quote = api.get_stock_quote(it.ticker)  # 삭제
        
        # ... 나머지 로직
```

**효과:**
- API 재조회 5회 제거
- 저장 시간 2~3초 단축
- 이미 계산된 정확한 값 사용

---

## 🔧 구현 순서

### 1단계: 모델 수정 (1분)

```python
# backend/models.py
class IndicatorPayload(BaseModel):
    # ... 기존 필드들
    close: float
    change_rate: Optional[float] = 0.0      # 추가
    trading_value: Optional[int] = 0        # 추가
```

### 2단계: 스캔 로직 수정 (5분)

```python
# backend/scanner.py - scan_one_symbol() 함수
cur = df.iloc[-1]

# 등락률 계산
change_rate = 0.0
if len(df) >= 2:
    prev_close = df.iloc[-2]["close"]
    if prev_close > 0:
        change_rate = round(((cur.close - prev_close) / prev_close) * 100, 2)

# 거래대금 계산 (OHLC 평균가)
avg_price = (cur.open + cur.high + cur.low + cur.close) / 4
trading_value = int(avg_price * cur.volume)

return {
    "indicators": {
        # ... 기존 필드들
        "change_rate": change_rate,
        "trading_value": trading_value,
    }
}
```

### 3단계: DB 저장 로직 수정 (3분)

```python
# backend/main.py - _save_snapshot_db() 함수
def _save_snapshot_db(as_of: str, items: List[ScanItem]):
    for it in items:
        close_price = float(it.indicators.close)
        volume = int(it.indicators.VOL)
        change_rate = float(getattr(it.indicators, 'change_rate', 0.0))
        
        # API 재조회 코드 삭제
```

### 4단계: 테스트 (5분)

```bash
# 1. 백엔드 재시작
cd backend
python main.py

# 2. 스캔 API 호출
curl "http://localhost:8010/scan?save_snapshot=true" | jq '.items[0].indicators'

# 3. 응답 확인
{
  "TEMA": 54555.95,
  "close": 54600.0,
  "VOL": 2379791,
  "change_rate": 2.35,           // ✅ 추가됨
  "trading_value": 129936000000  // ✅ 추가됨
}
```

---

## 📊 API 응답 예시

### 변경 후 `/scan` API 응답

```json
{
  "as_of": "2025-10-20",
  "universe_count": 50,
  "matched_count": 5,
  "items": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "score": 9,
      "score_label": "strong",
      "indicators": {
        "TEMA": 54555.95,
        "DEMA": 54503.48,
        "MACD_OSC": -41.65,
        "MACD_LINE": -167.65,
        "MACD_SIGNAL": -126.00,
        "RSI_TEMA": 49.93,
        "RSI_DEMA": 44.88,
        "OBV": -8353942.0,
        "VOL": 2379791,
        "VOL_MA5": 1077519.6,
        "close": 54600.0,
        "change_rate": 2.35,           // ✅ 추가
        "trading_value": 129936306600   // ✅ 추가
      },
      "trend": {
        "TEMA20_SLOPE20": 30.77,
        "OBV_SLOPE20": -245678.5,
        "ABOVE_CNT5": 3,
        "DEMA10_SLOPE20": 28.45
      }
    }
  ]
}
```

### 필드 매핑

| 요구사항 | API 응답 필드 | 데이터 타입 | 예시 |
|---------|--------------|------------|------|
| 거래일 | `as_of` | string | "2025-10-20" |
| 종목명 | `items[].name` | string | "삼성전자" |
| 거래량 | `items[].indicators.VOL` | integer | 2379791 |
| 거래대금 | `items[].indicators.trading_value` | integer | 129936306600 |
| 종목코드 | `items[].ticker` | string | "005930" |
| 등락률 | `items[].indicators.change_rate` | float | 2.35 |
| 종가 | `items[].indicators.close` | float | 54600.0 |

---

## 📝 테스트 체크리스트

### 기능 테스트
- [ ] `/scan` API 호출 시 `change_rate` 필드 포함
- [ ] `/scan` API 호출 시 `trading_value` 필드 포함
- [ ] 등락률 계산 정확성 검증 (수동 계산과 비교)
- [ ] 거래대금 계산 정확성 검증 (OHLC 평균가 × 거래량)

### 데이터 무결성 테스트
- [ ] `change_rate`가 null이 아닌지 확인
- [ ] `trading_value`가 0이 아닌지 확인
- [ ] 음수 등락률 테스트 (하락 종목)
- [ ] 전일 데이터 없을 때 `change_rate = 0.0` 확인

### 성능 테스트
- [ ] 스캔 실행 시간 측정 (개선 전/후)
- [ ] API 호출 횟수 확인 (57회 → 52회)
- [ ] DB 저장 시간 측정

### 호환성 테스트
- [ ] 기존 프론트엔드에서 정상 조회
- [ ] `/latest-scan` API 응답 확인
- [ ] DB 저장 후 조회 시 필드 포함 확인

---

## ⚠️ 주의사항

### 1. 기본값 설정
```python
# Optional 필드로 기존 데이터 호환성 유지
change_rate: Optional[float] = 0.0
trading_value: Optional[int] = 0
```

### 2. 전일 데이터 부재 처리
```python
# OHLCV 데이터가 1일만 있을 때 (드물지만 가능)
if len(df) >= 2:
    # 전일 데이터 있음 → 정상 계산
    change_rate = calculate_change_rate(...)
else:
    # 전일 데이터 없음 → 0 반환
    change_rate = 0.0
```

### 3. 거래대금 계산 정확성
```python
# OHLC 평균가 사용 (더 정확한 근사치)
avg_price = (open + high + low + close) / 4
trading_value = int(avg_price * volume)

# 종가만 사용하면 부정확
# bad: trading_value = close * volume  # 하루 중 특정 시점만 반영
```

**예시:**
```python
# 삼성전자
open = 54000, high = 55000, low = 53500, close = 54600, volume = 2,379,791

# 평균가 방식 (권장)
avg = (54000 + 55000 + 53500 + 54600) / 4 = 54,275
trading_value = 54,275 * 2,379,791 = 129,163,266,025원

# 종가 방식 (부정확)
trading_value = 54,600 * 2,379,791 = 129,936,306,600원
# 차이: 약 7억원
```

### 4. 백엔드 재시작 필요
모델 변경 시 백엔드를 재시작해야 반영됩니다.
```bash
# PID 확인
ps aux | grep "python.*main.py"

# 종료
kill <PID>

# 재시작
cd backend
python main.py &
```

---

## 🎯 기대 효과

### 기능 개선
- ✅ 모든 필수 필드 제공 (거래일, 종목명, 거래량, 거래대금, 종목코드, 등락률, 종가)
- ✅ 프론트엔드에서 추가 계산 불필요
- ✅ 일관된 데이터 제공

### 성능 개선
- ✅ API 호출 5회 절약 (57 → 52)
- ✅ 저장 시간 2~3초 단축
- ✅ 불필요한 중복 제거

### 코드 품질
- ✅ 간결한 코드
- ✅ 명확한 데이터 흐름
- ✅ 유지보수성 향상

---

## 📌 요약

| 항목 | 내용 |
|------|------|
| **추가 필드** | `change_rate` (등락률), `trading_value` (거래대금) |
| **수정 파일** | models.py, scanner.py, main.py |
| **소요 시간** | 약 10분 (코딩 5분 + 테스트 5분) |
| **API 호출 절약** | 5회 |
| **성능 향상** | 저장 시간 2~3초 단축 |
| **호환성** | 기존 코드 영향 없음 (Optional 필드) |

**최소 구현**: 모델 + 스캔 로직 수정 (5분)
**권장 구현**: 전체 수정 (10분)

