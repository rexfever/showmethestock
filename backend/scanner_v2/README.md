# Scanner V2 - 실시간 스캔 엔진

## 개요

Scanner V2는 모듈화된 구조의 실시간 주식 스캔 엔진입니다. 기존 scanner.py의 함수형 구조를 개선하여 객체지향적이고 확장 가능한 아키텍처로 재설계되었습니다.

## 아키텍처

```
scanner_v2/
├── __init__.py
├── config_v2.py           # V2 전용 설정
└── core/
    ├── scanner.py          # 메인 스캐너 클래스
    ├── filter_engine.py    # 필터링 엔진
    ├── scorer.py           # 점수 계산기
    ├── strategy.py         # 전략 분류기
    └── indicator_calculator.py  # 지표 계산기
```

## 핵심 클래스

### ScannerV2
메인 스캐너 클래스로 전체 스캔 프로세스를 관리합니다.

```python
from scanner_factory import get_scanner

# 스캐너 인스턴스 생성 (팩토리 사용)
scanner = get_scanner(version='v2')

# 단일 종목 스캔
result = scanner.scan_one("005930")  # 삼성전자

# 유니버스 스캔
results = scanner.scan(["005930", "000660", "035420"])
```

### FilterEngine
하드 필터와 소프트 필터를 담당합니다.

**하드 필터 (즉시 제외)**:
- 데이터 검증 (21일 이상)
- 인버스 ETF 제외
- 채권 ETF 제외
- RSI 상한선 (동적 조정)
- 유동성 필터 (10억원 이상)
- 가격 하한 (2,000원 이상)
- 과열 필터
- 갭/이격 필터

**소프트 필터 (신호 기반)**:
- 기본 신호 4개: 골든크로스, MACD, RSI, 거래량
- 추가 신호 3개: OBV 슬로프, TEMA 슬로프, 연속상승
- 총 7개 신호 중 min_signals 개 이상 충족 필요

### Scorer
점수 계산을 담당합니다.

```python
# 점수 계산
score, flags = scorer.calculate_score(df, market_condition)

# flags 구조
{
    "cross": bool,           # 골든크로스
    "vol_expand": bool,      # 거래량 급증
    "macd_ok": bool,         # MACD 신호
    "rsi_ok": bool,          # RSI 신호
    "tema_slope_ok": bool,   # TEMA 슬로프
    "obv_slope_ok": bool,    # OBV 슬로프
    "above_cnt5_ok": bool,   # 연속상승
    "match": bool,           # 최종 매칭 여부
    "label": str,            # 전략 라벨
    "score": float           # 총점
}
```

## 스캔 프로세스

```
1. 하드 필터 적용 → 즉시 제외 여부 판단
2. 지표 계산 → 모든 기술적 지표 계산
3. 소프트 필터 적용 → 신호 충족 여부 판단
4. 점수 계산 → 순위 결정용 점수 산출
5. 전략 결정 → 매매 전략 분류
```

## 설정 관리

### ScannerV2Config
V2 전용 설정 클래스입니다.

```python
from scanner_v2.config_v2 import ScannerV2Config

config = ScannerV2Config()

# 주요 설정값
config.min_signals = 3              # 최소 신호 개수
config.rsi_threshold = 58           # RSI 임계값
config.vol_ma5_mult = 2.5          # 거래량 배수
config.min_turnover_krw = 1e9      # 최소 거래대금 (10억원)
config.gap_max = 0.025             # 최대 갭 (2.5%)
config.ext_from_tema20_max = 0.025 # 최대 이격 (2.5%)
```

### 동적 조정
시장 상황에 따라 임계값이 동적으로 조정됩니다.

```python
# 시장 상황별 조정
if market_condition and config.market_analysis_enable:
    rsi_threshold = market_condition.rsi_threshold
    rsi_upper_limit = rsi_threshold + config.rsi_upper_limit_offset  # 동적 계산
    min_signals = market_condition.min_signals
    vol_ma5_mult = market_condition.vol_ma5_mult
    gap_max = market_condition.gap_max
```

## 사용 예제

### 기본 사용법

```python
from scanner_factory import get_scanner

# 1. 스캐너 생성 (설정 자동 로드)
scanner = get_scanner(version='v2')

# 3. 단일 종목 스캔
result = scanner.scan_one("005930")
if result:
    print(f"종목: {result.name}")
    print(f"점수: {result.score}")
    print(f"전략: {result.strategy}")
    print(f"신호: {result.flags}")

# 4. 유니버스 스캔
universe = ["005930", "000660", "035420", "207940", "006400"]
results = scanner.scan(universe)

for result in results:
    print(f"{result.ticker} {result.name}: {result.score}점 ({result.strategy})")
```

### 시장 조건과 함께 사용

```python
from market_analyzer import market_analyzer

# 1. 시장 조건 분석
market_condition = market_analyzer.analyze_market_condition("20251121")

# 2. 시장 조건을 반영한 스캔
scanner = ScannerV2(config, market_analyzer)
result = scanner.scan_one("005930", market_condition=market_condition)
```

### 커스텀 설정

```python
# 커스텀 설정으로 스캔
config = ScannerV2Config()
config.min_signals = 2              # 신호 개수 완화
config.rsi_threshold = 55           # RSI 임계값 하향
config.vol_ma5_mult = 2.0          # 거래량 조건 완화

scanner = ScannerV2(config)
results = scanner.scan(universe)
```

## V1과의 차이점

| 항목 | V1 (scanner.py) | V2 (scanner_v2/) |
|------|----------------|------------------|
| **구조** | 함수형 | 객체지향 |
| **모듈화** | 단일 파일 | 기능별 분리 |
| **신호 처리** | 점수 우선 | 신호 우선 |
| **설정 관리** | .env만 | DB + .env |
| **확장성** | 제한적 | 높음 |
| **테스트** | 어려움 | 용이 |

## 성능 특징

- **메모리 효율**: 필요한 데이터만 로드
- **속도 최적화**: 하드 필터로 조기 제외
- **확장성**: 모듈별 독립적 개발 가능
- **안정성**: 에러 처리 및 검증 로직 내장

## 마이그레이션 가이드

### 기존 코드에서 V2로 전환

```python
# 기존 V1 코드
from scanner import scan_one_symbol
result = scan_one_symbol("005930")

# V2 코드
from scanner_factory import get_scanner

scanner = get_scanner(version='v2')
result = scanner.scan_one("005930")
```

### 설정 전환

```python
# V1: config.py 사용
from config import config
min_signals = config.min_signals

# V2: scanner_v2_config 사용
from scanner_v2.config_v2 import scanner_v2_config
min_signals = scanner_v2_config.min_signals
```

## 주의사항

1. **호환성**: V1과 V2는 다른 결과를 낼 수 있습니다.
2. **설정**: V2 전용 설정을 사용해야 합니다.
3. **의존성**: scanner_v2/ 모듈 전체가 필요합니다.
4. **성능**: 초기 로딩 시간이 V1보다 길 수 있습니다.

## 문제 해결

### 일반적인 오류

```python
# ImportError 해결
# scanner_v2/ 디렉토리가 PYTHONPATH에 있는지 확인
import sys
sys.path.append('/path/to/backend')

# 설정 오류 해결
# scanner_v2_config 사용 확인
from scanner_v2.config_v2 import scanner_v2_config
config = scanner_v2_config  # config.py 대신 사용

# 결과 없음 해결
# 필터 조건이 너무 엄격한지 확인
config.min_signals = 2  # 3에서 2로 완화
config.rsi_threshold = 55  # 58에서 55로 완화
```

## 개발 가이드

### 새로운 필터 추가

```python
# filter_engine.py에 추가
def apply_custom_filter(self, df, condition):
    # 커스텀 필터 로직
    return filter_result

# scanner.py에서 사용
if not self.filter_engine.apply_custom_filter(df, condition):
    return None
```

### 새로운 지표 추가

```python
# indicator_calculator.py에 추가
def compute_custom_indicator(self, df):
    # 커스텀 지표 계산
    df["CUSTOM_INDICATOR"] = custom_calculation(df)
    return df
```

## 라이선스

이 코드는 Stock Finder 프로젝트의 일부입니다.