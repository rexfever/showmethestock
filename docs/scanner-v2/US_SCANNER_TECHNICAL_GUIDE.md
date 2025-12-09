# 미국 주식 스캐너 기술 가이드

**최종 업데이트**: 2025-12-06

## 개요

미국 주식 스캐너는 Scanner V2 아키텍처를 기반으로 Yahoo Finance API를 활용하여 S&P 500 및 NASDAQ 100 종목을 분석합니다.

## 시스템 구조

### 1. 데이터 수집 계층

#### USStocksUniverse
**위치**: `backend/services/us_stocks_universe.py`

**기능**:
- S&P 500, NASDAQ 100 종목 리스트 관리
- Wikipedia에서 종목 리스트 크롤링
- 캐시 TTL: 7일
- 통합 유니버스 제공

**주요 메서드**:
```python
get_sp500_list(use_cache=True) -> List[Dict]
get_nasdaq100_list(use_cache=True) -> List[Dict]
get_combined_universe(include_sp500=True, include_nasdaq100=True, limit=None) -> List[str]
get_stock_info(symbol: str) -> Optional[Dict]
```

**캐시 위치**: `cache/us_stocks/`

#### USStocksData
**위치**: `backend/services/us_stocks_data.py`

**기능**:
- Yahoo Finance Chart API 활용
- OHLCV 데이터 수집 (1년치)
- 디스크 캐시 관리
- Rate limiting (0.1초 딜레이)
- 실시간 주가 조회

**주요 메서드**:
```python
get_ohlcv(symbol: str, count: int = 220, base_dt: str = None) -> pd.DataFrame
get_stock_quote(symbol: str) -> Optional[Dict]
```

**캐시 위치**: `cache/us_stocks_ohlcv/`

**캐시 전략**:
- base_dt 기준 캐시 무효화
- 데이터 부족 시 자동 업데이트
- 중복 제거 및 정렬

### 2. 시장 분석 계층

#### Global Regime v4 (한국+미국 통합 분석)
**위치**: `backend/market_analyzer.py` - `analyze_market_condition_v4()`

**기능**:
- 한국과 미국 데이터를 모두 고려한 통합 레짐 분석
- Global Regime v4 사용

**데이터 소스**:
- **한국**: KOSPI, KOSDAQ
- **미국**: SPY, QQQ, VIX

**점수 계산**:
- Trend Score: 한국/미국 트렌드 분석
- Risk Score: 한국/미국 리스크 분석
- Global Regime 결정: bull/neutral/bear/crash

**레짐 분류**:
- `bull`: 강세장
- `neutral`: 중립장
- `bear`: 약세장
- `crash`: 급락장

**레짐 기반 Cutoff**:
```python
# 레짐별 전략별 점수 기준
bull: {
    'swing': 6.0,      # 강세장에서 단기 매매 점수 기준
    'position': 4.3,   # 강세장에서 중기 포지션 점수 기준 (완화)
    'longterm': 5.0    # 강세장에서 장기 투자 점수 기준
}
neutral: {
    'swing': 6.0,
    'position': 4.5,
    'longterm': 6.0
}
bear: {
    'swing': 999.0,    # 약세장에서 단기 매매 비활성화
    'position': 5.5,   # 약세장에서 중기 포지션 점수 기준 (강화)
    'longterm': 6.0
}
crash: {
    'swing': 999.0,    # 급락장에서 단기 매매 비활성화
    'position': 999.0, # 급락장에서 중기 포지션 비활성화
    'longterm': 6.0    # 급락장에서 장기 투자만 조건부 허용
}
```

**동적 필터 값**:
- 레짐별 RSI 임계값: 레짐 분석 결과에 따라 자동 조정
- 레짐별 최소 신호 개수: 레짐 분석 결과에 따라 자동 조정
- 레짐별 거래량 배수: 레짐 분석 결과에 따라 자동 조정
- 강세장 조건 완화: bull market에서 필터링 조건 완화

### 3. 스캐닝 계층

#### USScanner
**위치**: `backend/scanner_v2/us_scanner.py`

**기능**:
- Scanner V2 아키텍처 기반
- 한국 V1 지표 계산 재사용
- USD 기준 필터링
- 점수 계산 및 전략 분류

**주요 메서드**:
```python
scan_one(symbol: str, date: str = None, market_condition: Optional[MarketCondition] = None) -> Optional[ScanResult]
scan(universe: List[str], date: str = None, market_condition: Optional[MarketCondition] = None) -> List[ScanResult]
_apply_regime_cutoff(results: List[ScanResult], market_condition: MarketCondition) -> List[ScanResult]
```

**레짐 분석 적용**:
- `market_condition` 파라미터로 레짐 정보 전달
- 레짐 기반 cutoff 적용 (레짐별 전략별 점수 기준)
- 레짐 기반 필터링 조건 조정 (RSI 임계값, 최소 신호 개수, 거래량 배수)

**지표 계산**:
- 한국 V1의 `compute_indicators()` 재사용
- RSI, MACD, OBV, TEMA, DEMA 등

#### USFilterEngine
**위치**: `backend/scanner_v2/core/us_filter_engine.py`

**하드 필터 (통과/실패)**:
1. **ETF 제외**: inverse, short, bear, 2x, 3x, leveraged, bond, treasury
2. **유동성**: 평균 거래대금 $1M 이상
3. **가격**: $5 이상
4. **RSI 상한**: 동적 조정 (레짐별 + 25)
5. **과열**: RSI ≥ 70 AND 거래량 ≥ 3배
6. **갭/이격**: 동적 조정 (레짐별)
7. **ATR**: 선택적 (설정 시)

**소프트 필터 (신호 충족)**:
- **기본 신호 4개**: 골든크로스, MACD, RSI, 거래량
- **추가 신호 3개**: OBV 기울기, TEMA 기울기, 5일 상승 횟수
- **최소 신호**: 레짐별 동적 조정 (레짐 분석 결과 기반)
- **추세 조건**: 4개 중 2개 이상 (미국은 완화)
- **레짐 기반 조정**: 
  - RSI 임계값: 레짐별 동적 조정
  - 거래량 배수: 레짐별 동적 조정
  - 강세장 조건 완화: bull market에서 필터링 완화

**미국 특화 조정**:
- 추세 조건 완화: 4개 중 2개 (한국은 3개)
- 5일 상승: 2회 이상 (한국은 3회)
- 음수 갭 허용 (하락 후 반등 가능)

#### USScorer
**위치**: `backend/scanner_v2/core/us_scorer.py`

**점수 가중치**:
```python
골든크로스: 3점
거래량: 2점
MACD: 1점
RSI: 1점
TEMA 기울기: 2점
DEMA 기울기: 2점
OBV 기울기: 2점
5일 상승: 2점
```

**위험도 차감**:
```python
RSI 과매수 (>80): -2점
거래량 급증 (3배): -2점
모멘텀 약화 (<3일): -1점
가격 급등 (4일 이상 상승): -1점
```

**전략 분류**:
- 점수 기반으로 스윙/포지션/장기 결정
- 목표 수익률, 손절선, 보유 기간 제공

**레이블**:
```python
≥ 10점: "강한 매수"
≥ 8점: "매수 후보"
≥ 6점: "관심 종목"
< 6점: "후보 종목"
```

## 데이터 흐름

```
1. 레짐 분석 실행
   ↓ (Global Regime v4 - 한국+미국 통합 분석)
   ↓ (KOSPI, KOSDAQ, SPY, QQQ, VIX 데이터 사용)
2. 유니버스 조회
   ↓ (S&P 500 + NASDAQ 100)
3. OHLCV 수집
   ↓ (Yahoo Finance Chart API)
   ↓ (캐시 확인 → API 호출 → 캐시 저장)
4. 지표 계산
   ↓ (한국 V1 compute_indicators 재사용)
5. 하드 필터
   ↓ (USD 기준, 레짐 기반 RSI 임계값 조정)
6. 소프트 필터
   ↓ (신호 충족, 레짐 기반 조건 조정)
7. 점수 계산
   ↓ (가중치 + 위험도 차감)
8. 전략 분류
   ↓ (스윙/포지션/장기)
9. 레짐 기반 Cutoff 적용
   ↓ (레짐별 전략별 점수 기준)
10. DB 저장
    ↓ (us_scan_ranks 테이블)
```

## USD 기준 조정

### 필터 값 변환
```python
# 한국 → 미국 (환율 1300 기준)
거래대금: 10억원 → $1M
최소 가격: 2,000원 → $5
```

### 조건 완화 이유
- 미국 시장은 유동성이 높음
- 변동성이 상대적으로 낮음
- 추세 지속성이 강함

## API 엔드포인트

### 스캔 실행
```
GET /scan/us-stocks?universe_type=combined&limit=500&date=20251205&save_snapshot=true
```

**파라미터**:
- `universe_type`: 유니버스 타입 ('sp500', 'nasdaq100', 'combined', 기본값: 'sp500')
- `limit`: 최대 종목 수 (기본값: 500)
- `date`: 스캔 날짜 (YYYYMMDD 형식, 선택사항, 기본값: 오늘)
- `save_snapshot`: 스캔 결과를 DB에 저장할지 여부 (기본값: true)

**레짐 분석**:
- `market_analysis_enable` 설정이 활성화된 경우 자동으로 레짐 분석 실행
- Global Regime v4 사용 (한국+미국 통합 분석)
- 레짐 분석 결과는 필터링 조건 조정 및 cutoff 적용에 사용

**Response**:
```json
{
  "as_of": "20251205",
  "universe_count": 600,
  "matched_count": 15,
  "items": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "score": 8.5,
      "current_price": 150.0,
      "change_rate": 1.5,
      "strategy": "Swing",
      "indicators": {...},
      "trend": {...},
      "flags": {...}
    }
  ]
}
```

### 결과 조회
```
GET /scan/us-stocks/results?date=20251205&limit=50
```

## 데이터 구조

### ScanResult
```python
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "match": true,
  "score": 8.5,
  "indicators": {
    "TEMA": 150.0,
    "DEMA": 148.0,
    "MACD_OSC": 0.5,
    "MACD_LINE": 1.2,
    "MACD_SIGNAL": 0.7,
    "RSI_TEMA": 62.0,
    "RSI_DEMA": 60.0,
    "OBV": 1000000,
    "VOL": 50000000,
    "VOL_MA5": 45000000,
    "close": 150.0,
    "change_rate": 1.5
  },
  "trend": {
    "TEMA20_SLOPE20": 0.002,
    "OBV_SLOPE20": 0.001,
    "ABOVE_CNT5": 4,
    "DEMA10_SLOPE20": 0.0015
  },
  "strategy": "스윙",
  "flags": {
    "label": "매수 후보",
    "trading_strategy": "스윙",
    "target_profit": 5.0,
    "stop_loss": -5.0,
    "holding_period": "3~10일"
  }
}
```

## 최근 수정 사항

### 2025-12-06: 레짐 분석 적용

1. **Global Regime v4 적용**
   - 한국+미국 통합 레짐 분석 사용
   - 레짐 기반 cutoff 적용 (레짐별 전략별 점수 기준)
   - 레짐 기반 필터링 조건 조정

2. **레짐 기반 Cutoff**
   - bull: swing 6.0, position 4.3 (완화)
   - neutral: swing 6.0, position 4.5
   - bear: swing 999.0, position 5.5 (강화)
   - crash: swing 999.0, position 999.0 (비활성화)

3. **필터링 조건 동적 조정**
   - RSI 임계값: 레짐별 동적 조정
   - 최소 신호 개수: 레짐별 동적 조정
   - 거래량 배수: 레짐별 동적 조정
   - 강세장 조건 완화: bull market에서 필터링 완화

4. **안전성 강화**
   - `strategy`가 None인 경우 처리 추가
   - 레짐 분석 실패 시에도 스캔 계속 진행

### 2025-12-02

### 1. 데이터 구조 일치
- `indicators`와 `trend`를 Pydantic 모델과 일치
- `ValidationError` 해결

### 2. 에러 처리 강화
- 모든 외부 API 호출에 try-except 추가
- 명확한 에러 메시지

### 3. 데이터 검증
- 음수 가격 체크
- high < low 체크
- close가 high/low 범위 밖인지 체크

### 4. 캐시 개선
- base_dt 기준 캐시 무효화
- 오래된 캐시 자동 업데이트

### 5. 파일 핸들링
- ResourceWarning 해결
- `with open()` 사용

### 6. 테스트 코드
- 종합 테스트 작성 (`test_us_scanner_comprehensive.py`)

## 성능 최적화

### 캐시 전략
- 디스크 캐시로 API 호출 최소화
- 7일 TTL로 유니버스 캐시
- base_dt 기준 스마트 캐시 무효화

### Rate Limiting
- API 호출 간 0.1초 딜레이
- 과도한 호출 방지

### 병렬 처리
- 향후 개선 예정 (현재는 순차 처리)

## 문제 해결

### 캐시 관련
```bash
# 캐시 클리어
rm -rf backend/cache/us_stocks_ohlcv/*
rm -rf backend/cache/us_stocks/*
```

### API 오류
- Yahoo Finance API 장애 시 캐시 사용
- 타임아웃: 15초

### 데이터 품질
- 결측값 자동 제거
- 음수 가격 필터링
- OHLCV 일관성 검증

## 관련 문서

- [미국 주식 스캐너 코드 리뷰](../US_STOCK_SCANNER_CODE_REVIEW.md)
- [미국 주식 스캐너 수정 사항](../US_STOCK_SCANNER_FIXES.md)
- [미국 주식 스캐너 테스트 결과](../US_STOCK_SCANNER_TEST_RESULTS.md)
- [미국 주식 스캐너 최종 요약](../US_STOCK_SCANNER_FINAL_SUMMARY.md)
- [미국 주식 스캔 레짐 분석 적용](../US_STOCK_REGIME_ANALYSIS_FINAL_SUMMARY.md)
- [미국 주식 스캔 레짐 분석 테스트 보고서](../US_STOCK_REGIME_ANALYSIS_TEST_REPORT.md)
- [레짐 분석 및 스캔 프로세스](../REGIME_ANALYSIS_AND_SCAN_PROCESS.md)
- [Scanner V2 설계](./SCANNER_V2_DESIGN.md)

## 참고

- **Yahoo Finance Chart API**: https://query2.finance.yahoo.com/v8/finance/chart/
- **S&P 500 리스트**: https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
- **NASDAQ 100 리스트**: https://en.wikipedia.org/wiki/NASDAQ-100
