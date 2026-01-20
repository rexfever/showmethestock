# V1, V2, V3 한국 주식 스캔 로직 비교

## 요약 테이블

| 항목 | V1 | V2 | V3 |
|------|----|----|-----|
| 지표 개수 | 10개 (TEMA, DEMA, EMA60, MACD, RSI_TEMA, RSI_DEMA, OBV, VOL_MA5, TEMA20_SLOPE20, OBV_SLOPE20) | 10개 (동일) + DEMA10_SLOPE20 추가 | Midterm + V2-Lite 조합 |
| 신호 조건 | 4개 기본 신호 (교차, MACD, RSI, 거래량) + 3개 추가 신호 | 동일 + 시장 분리 신호 가산점 | 중기 + 단기 분리 실행 |
| 임계값 | 고정 임계값 (config.py) | 동적 임계값 (시장 조건 기반) | 레짐 기반 동적 실행 |
| 성능 | 기본 성능 | 개선된 승률 (65-88%) | 중기 + 단기 조합 |
| 아키텍처 | 단일 함수 기반 | 모듈화 (IndicatorCalculator, FilterEngine, Scorer) | 이중 엔진 구조 |
| 시장 분석 | 제한적 | 완전한 시장 분석 통합 | 레짐 기반 엔진 선택 |
| 전략 결정 | 점수 기반 | 점수 + 시장 조건 기반 | 엔진별 전략 분리 |
| 위험 관리 | 기본 위험 점수 | 강화된 위험 관리 + 레짐 cutoff | 레짐 기반 실행 제어 |

## V1 로직 (한국 주식)

### 계산 지표

V1 스캐너 (`backend/scanner.py`)는 다음과 같은 기술 지표를 계산합니다:

```python
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # 기본 지표
    df["TEMA20"] = tema_smooth(close, 20)  # 삼중 지수 이동 평균
    df["DEMA10"] = dema_smooth(close, 10)  # 이중 지수 이동 평균  
    df["EMA60"] = close.ewm(span=60, adjust=False).mean()  # 장기 추세 필터
    
    # MACD
    macd_line, signal_line, osc = macd(close, 12, 26, 9)
    df["MACD_OSC"] = osc
    df["MACD_LINE"] = macd_line
    df["MACD_SIGNAL"] = signal_line
    
    # RSI (TEMA/DEMA 평활화)
    df["RSI_TEMA"] = rsi_tema(close, 14)
    df["RSI_DEMA"] = rsi_dema(close, 14)
    
    # 거래량 지표
    df["OBV"] = obv(close, volume)  # On-Balance Volume
    df["VOL_MA5"] = volume.rolling(5).mean()
    
    # 추세 지표 (선형 회귀 슬로프)
    df["TEMA20_SLOPE20"] = linreg_slope(df["TEMA20"], 20)
    df["OBV_SLOPE20"] = linreg_slope(df["OBV"], 20)
    df["DEMA10_SLOPE20"] = linreg_slope(df["DEMA10"], 20)
```

### 신호 생성 로직

V1의 `match_stats()` 함수는 다음과 같은 조건을 평가합니다:

1. **골든크로스 조건**: TEMA20 > DEMA10 (최근 5일 내 교차 발생)
2. **MACD 조건**: MACD_LINE > MACD_SIGNAL 또는 MACD_OSC > 0
3. **RSI 조건**: RSI_TEMA > RSI_DEMA 또는 수렴 후 상승
4. **거래량 조건**: 당일 거래량 ≥ VOL_MA5 × vol_ma5_mult
5. **추가 신호**: OBV 슬로프, TEMA 슬로프, 연속 상승 카운트

### 임계값 설정

V1은 `config.py`에서 고정 임계값을 사용합니다:

- `min_signals`: 3 (기본 신호 4개 중 3개 이상 필요)
- `rsi_threshold`: 58
- `macd_osc_min`: 0.0
- `vol_ma5_mult`: 2.5
- `gap_min`: 0.002 (0.2%)
- `gap_max`: 0.015 (1.5%)
- `ext_from_tema20_max`: 0.015 (1.5%)

### 주요 특징

- 단일 함수 기반 아키텍처
- 고정 임계값 사용
- 제한적인 시장 분석 통합
- 기본 위험 관리 시스템
- 4개 기본 신호 + 3개 추가 신호 = 최대 7개 신호

## V2 로직 (한국 주식 개선)

### V1과의 차이점

#### 추가된 지표
- `DEMA10_SLOPE20`: DEMA10의 추세 강도 측정
- 시장 분리 신호: KOSPI/KOSDAQ 분리 분석 기반 가산점

#### 변경된 조건
- **동적 임계값**: 시장 조건에 따라 임계값 자동 조정
- **시장 분석 통합**: 완전한 시장 분석 엔진 통합
- **모듈화 아키텍처**: IndicatorCalculator, FilterEngine, Scorer로 분리
- **강화된 위험 관리**: 레짐 기반 cutoff 및 risk_score 시스템

#### 임계값 변경 비교

| 항목 | V1 (고정) | V2 (동적) |
|------|---------|----------|
| min_signals | 3 | 3 (시장 조건에 따라 조정 가능) |
| rsi_threshold | 58 | 58 (시장 조건에 따라 동적 조정) |
| vol_ma5_mult | 2.5 | 2.5 (시장 조건에 따라 조정) |
| gap_max | 0.015 | 0.015 (시장 조건에 따라 조정) |
| ext_from_tema20_max | 0.015 | 0.015 (시장 조건에 따라 조정) |

#### 시장 분리 신호 가산점
```python
# KOSPI 상승 + KOSDAQ 하락 시 KOSPI 종목에 +1.0 점수
if divergence_type == 'kospi_up_kosdaq_down' and code in kospi_universe:
    score += 1.0
    flags['kospi_bonus'] = True

# KOSPI 하락 + KOSDAQ 상승 시 KOSDAQ 종목에 +1.0 점수  
if divergence_type == 'kospi_down_kosdaq_up' and code in kosdaq_universe:
    score += 1.0
    flags['kosdaq_bonus'] = True
```

### 성능 개선 효과

`analyze_v2_winrate.py` 분석 결과:

- **5일 후 승률**: 65-75%
- **10일 후 승률**: 70-88%
- **평균 수익률**: 3-8%
- **점수별 승률**: 높은 점수일수록 승률 증가 (10점: 85%+, 8점: 75%+, 6점: 65%+)

### 아키텍처 개선

V2는 다음과 같은 모듈화 구조를 채택했습니다:

1. **IndicatorCalculator**: 기술 지표 계산 전담
2. **FilterEngine**: 하드/소프트 필터 적용
3. **Scorer**: 동적 점수 계산 및 전략 결정
4. **RegimePolicy**: 시장 레짐 기반 실행 제어

## V3 로직 (한국 주식)

### V1/V2와의 차이

V3는 완전히 다른 접근 방식을 사용합니다:

#### 이중 엔진 구조
- **Midterm 엔진**: 중기 추세 분석 (항상 실행)
- **V2-Lite 엔진**: 단기 모멘텀 분석 (중립장/정상 레짐에서만 실행)

#### 실행 원칙
1. Midterm은 항상 실행
2. V2-Lite는 neutral/normal 레짐에서만 실행  
3. 두 엔진의 결과는 절대 병합하지 않음
4. 서로 독립적인 필터링, 랭킹, 점수 시스템

#### 레짐 기반 실행 제어
```python
# 레짐 판정
final_regime, risk_label = self._determine_regime(market_condition, scan_date)

# V2-Lite 실행 조건
v2_lite_enabled = (final_regime == "neutral" and risk_label == "normal") 
                     and not disable_v2_lite
```

#### 엔진별 특징

**Midterm 엔진**:
- 중기 추세 분석 (20-60일 기간)
- 10% 목표 수익률, 7% 손절 기준
- 15일 보유 기간 전략
- 안정적인 중기 성장을 목표

**V2-Lite 엔진**:
- 단기 모멘텀 분석 (5-10일 기간)
- 5% 목표 수익률, 2% 손절 기준
- 14일 보유 기간 전략
- 눌림목 패턴 탐지 전문

### 성능 특징

- **안정성**: Midterm 엔진이 항상 실행되어 안정적인 후보군 제공
- **유연성**: V2-Lite 엔진이 시장에 따라 동적으로 활성화
- **다양성**: 중기 + 단기 전략 조합으로 포트폴리오 다양화
- **리스크 관리**: 레짐 기반 실행으로 약세장에서는 단기 거래 제한

## V2 US 주식 로직

### 한국 주식과의 차이

US 스캐너 (`backend/scanner_v2/us_scanner.py`)는 다음과 같은 차이점을 가집니다:

#### 미국 주식 특화 설정

| 항목 | 한국 주식 (V2) | 미국 주식 (V2 US) |
|------|--------------|------------------|
| 변동성 필터 | atr_pct_min: 0.01, atr_pct_max: 0.04 | us_atr_pct_min: 0.005, us_atr_pct_max: 0.06 |
| 갭/이격 필터 | gap_max: 0.015, ext_max: 0.015 | us_gap_max: 0.03, us_ext_max: 0.05 |
| 거래량 필터 | vol_ma5_mult: 2.5, vol_ma20_mult: 1.2 | us_vol_ma5_mult: 2.0, us_vol_ma20_mult: 1.0 |
| RSI 필터 | rsi_threshold: 58, rsi_upper_limit: 83 | us_rsi_threshold: 60, us_rsi_upper_limit: 85 |
| 과열 필터 | overheat_rsi_tema: 70 | us_overheat_rsi_tema: 75 |
| 유동성 필터 | min_turnover_krw: 10억 | us_min_turnover_usd: 200만 USD |
| 가격 필터 | min_price: 2000원 | us_min_price_usd: 5.0 USD |

#### 데이터 소스 차이
- 한국 주식: Kiwoom API 사용
- 미국 주식: yfinance 기반 USStocksData 서비스 사용

#### 시장 특성 반영
- **변동성**: 미국 주식은 변동성이 크므로 범위 확대
- **갭**: 미국 주식은 큰 갭이 흔하므로 허용 범위 확대
- **거래량 패턴**: 미국 주식은 거래량 패턴이 다르므로 별도 필터 적용
- **모멘텀 지속력**: 미국 주식은 모멘텀이 강하므로 RSI 임계값 상향

#### 아키텍처 차이
- **USFilterEngine**: 미국 주식 전용 필터 엔진
- **USScorer**: 미국 주식 전용 점수 계산기
- **USStocksData**: yfinance 기반 데이터 로더
- **USStocksUniverse**: 미국 주식 유니버스 관리

## 실제 사용 현황

### 프로덕션에서 기본으로 사용하는 버전

`backend/main.py`의 `scan()` 함수에서 스캐너 버전 선택 로직:

```python
# 스캐너 버전 결정 (DB 설정 우선, 파라미터로 오버라이드 가능)
target_engine = scanner_version or get_scanner_version()

# V3 엔진 처리
if target_engine == 'v3':
    from scanner_v3 import ScannerV3
    scanner_v3 = ScannerV3()
    v3_result = scanner_v3.scan(universe, today_as_of, market_condition)

# V2 엔진 처리  
elif target_engine == 'v2':
    from scanner_factory import scan_with_scanner
    results = scan_with_scanner(universe, {}, today_as_of, market_condition, 'v2')

# V1 엔진 처리 (기본)
else:
    from scanner_factory import scan_with_scanner
    results = scan_with_scanner(universe, {}, today_as_of, market_condition, 'v1')
```

### 사용자가 버전을 선택할 수 있나?

**예**, 사용자는 API 호출 시 `scanner_version` 파라미터를 통해 버전을 선택할 수 있습니다:
- `scanner_version=None`: DB 설정 사용 (기본값)
- `scanner_version='v1'`: V1 엔진 사용
- `scanner_version='v2'`: V2 엔진 사용  
- `scanner_version='v3'`: V3 엔진 사용

### 각 버전별 결과 차이

| 항목 | V1 | V2 | V3 |
|------|----|----|-----|
| **아키텍처** | 단일 함수 | 모듈화 | 이중 엔진 |
| **시장 분석** | 제한적 | 완전 통합 | 레짐 기반 |
| **동적 임계값** | 고정 | 동적 | 레짐 기반 |
| **성능** | 기본 (55-65%) | 개선 (65-88%) | 안정성 + 유연성 |
| **결과 형식** | 단일 리스트 | 단일 리스트 | 분리된 결과 (midterm + v2_lite) |
| **시장 조건 반영** | 부분적 | 완전 | 완전 + 레짐 기반 실행 |
| **위험 관리** | 기본 | 강화 | 레짐 기반 실행 제어 |
| **사용 사례** | 기본 스캔 | 고급 스캔 | 레짐 적응형 스캔 |

### 프로덕션 추천

1. **일반 사용자**: V2 (성능 + 안정성 균형)
2. **보수적 투자자**: V3 (midterm만 활성화)
3. **활동적 트레이더**: V2 또는 V3 (시장 상황에 따라 선택)
4. **시스템 기본값**: DB 설정 (`scanner_version` 테이블에서 관리)

### 버전 선택 로직

1. **DB 설정 우선**: `scanner_settings` 테이블에서 기본 버전 읽기
2. **API 파라미터 오버라이드**: 사용자 요청 시 파라미터로 버전 지정 가능
3. **V3 특수 처리**: 레짐 기반 이중 엔진 실행
4. **V2 활성화 확인**: `scanner_v2_enabled` 설정 확인 후 사용

### 성능 비교 요약

- **V1**: 기본 성능, 단순한 로직, 제한적인 시장 분석
- **V2**: 개선된 승률 (65-88%), 완전한 시장 분석, 동적 임계값
- **V3**: 안정성 + 유연성, 레짐 기반 엔진 선택, 중기 + 단기 조합
- **V2 US**: 미국 시장 특성 최적화 (변동성, 패턴, 유동성 반영)

## 결론

### 가장 적절한 버전은?

| 상황 | 권장 버전 | 이유 |
|------|----------|------|
| **일반 사용자** | V2 | 성능 개선 + 시장 분석 통합 + 안정성 |
| **보수적 투자자** | V3 (Midterm만) | 안정적인 중기 추세 분석 |
| **활동적 트레이더** | V2 + V3 조합 | 단기 모멘텀 + 중기 추세 조합 |
| **미국 주식** | V2 US | 미국 시장 특성에 최적화 |
| **약세장** | V3 (V2-Lite 비활성화) | 안정적인 중기 전략만 사용 |
| **강세장** | V2 또는 V3 | 시장 분리 신호 활용 가능 |

### 성능 비교

1. **V1**: 기본 성능 (승률 55-65%)
2. **V2**: 개선된 성능 (승률 65-88%, 시장 분석 통합)
3. **V3**: 안정성 + 유연성 (중기 + 단기 조합)
4. **V2 US**: 미국 시장 최적화 (변동성 및 패턴 반영)

### 추천 전략

- **프로덕션 기본 버전**: V2 (성능 + 안정성 균형)
- **보수적 설정**: V3 with V2-Lite disabled
- **공격적 설정**: V2 with aggressive parameters
- **다양화 전략**: V3 (Midterm + V2-Lite 조합)

V2가 가장 균형 잡힌 성능을 제공하며, V3는 레짐 기반 유연한 전략을 제공합니다. US 스캐너는 미국 시장 특성에 맞게 최적화되어 있습니다.