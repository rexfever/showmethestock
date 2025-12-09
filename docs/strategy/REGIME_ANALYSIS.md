# 레짐 분석 (Regime Analysis)

**최종 업데이트**: 2025-12-06

## 버전 관리

레짐 분석 버전은 **Scanner 버전과 독립적으로** 관리됩니다:
- **Scanner 버전**: v1, v2 (스캔 로직)
- **레짐 분석 버전**: v1, v3, v4 (시장 상황 분석)

두 버전은 독립적으로 선택 가능하며, 다양한 조합으로 사용할 수 있습니다 (예: Scanner V1 + Regime V4).

## 개요

레짐 분석은 시장의 중기 추세와 리스크를 종합적으로 평가하여 현재 시장 상황을 **bull(강세)**, **neutral(중립)**, **bear(약세)**, **crash(급락)** 중 하나로 분류하는 시스템입니다.

Global Regime Analyzer v4를 사용하여 한국과 미국 시장을 동시에 분석하고, 두 시장의 추세와 리스크를 결합하여 최종 레짐을 결정합니다.

## 레짐 분석 프로세스

### 1. 데이터 수집

레짐 분석은 다음 데이터를 사용합니다:

- **한국 시장**: KOSPI200 OHLCV 데이터
- **미국 시장**: SPY, QQQ, VIX 데이터

### 2. Feature 계산

#### 한국 Trend Features

- **R5, R20, R60**: 5일, 20일, 60일 수익률
- **DD20, DD60**: 20일, 60일 최고점 대비 드로우다운
- **MA20_SLOPE, MA60_SLOPE**: 20일, 60일 이동평균 기울기

#### 한국 Risk Features

- **intraday_drop**: 일중 최저가 대비 시가 하락률
- **r3**: 3일 수익률
- **day_range**: 일중 변동폭 (고가/저가 비율)

#### 미국 Trend Features

- **SPY_R20, SPY_R60**: SPY 20일, 60일 수익률
- **QQQ_R20, QQQ_R60**: QQQ 20일, 60일 수익률
- **SPY_MA50_ABOVE_200**: SPY 50일선이 200일선 위에 있는지 여부
- **QQQ_MA50_ABOVE_200**: QQQ 50일선이 200일선 위에 있는지 여부

#### 미국 Risk Features

- **VIX_LEVEL**: VIX 현재 수준
- **VIX_MA5, VIX_MA20**: VIX 5일, 20일 이동평균
- **VIX_CHG_3D**: VIX 3일 변화율

### 3. Score 계산

#### 한국 Trend Score

다음 기준으로 점수를 계산합니다:

- **R20 > 4%**: +1.0점
- **R20 < -4%**: -1.0점
- **R60 > 8%**: +1.0점
- **R60 < -8%**: -1.0점
- **DD20 < -5%**: -1.0점
- **DD20 < -10%**: -1.0점 (추가)
- **DD60 < -15%**: -1.0점
- **MA20_SLOPE > 0**: +1.0점
- **MA60_SLOPE > 0**: +1.0점
- **MA60_SLOPE < 0**: -0.5점

**레짐 결정**:
- `score >= 2`: **bull**
- `score <= -2`: **bear**
- 그 외: **neutral**

#### 미국 Trend Score

- **SPY_R60 > 8%**: +1.0점
- **SPY_R60 < -8%**: -1.0점
- **QQQ_R60 > 10%**: +1.0점
- **QQQ_R60 < -10%**: -1.0점
- **SPY_MA50_ABOVE_200**: +0.5점
- **QQQ_MA50_ABOVE_200**: +0.5점

**레짐 결정**:
- `score >= 2`: **bull**
- `score <= -2`: **bear**
- 그 외: **neutral**

#### 한국 Risk Score

- **intraday_drop < -3%**: -2.0점
- **day_range > 4%**: -1.0점
- **r3 < -4%**: -1.0점

**레이블 결정**:
- `score <= -3`: **stressed**
- `score <= -1`: **elevated**
- 그 외: **normal**

#### 미국 Risk Score

- **VIX_CHG_3D > 20%**: -2.0점
- **VIX_LEVEL > 25**: -1.0점
- **VIX_LEVEL > 35 또는 VIX_CHG_3D > 30%**: -3.0점 (극단적 상황)

**레이블 결정**:
- `score <= -3`: **stressed**
- `score <= -1`: **elevated**
- 그 외: **normal**

### 4. Global Regime 결합

한국과 미국의 Trend/Risk 점수를 가중 평균하여 글로벌 점수를 계산합니다:

```
global_trend_score = 0.4 * kr_trend_score + 0.6 * us_trend_score
global_risk_score = 0.4 * kr_risk_score + 0.6 * us_risk_score
```

**글로벌 추세 결정**:
- `global_trend_score >= 2`: **bull**
- `global_trend_score <= -2`: **bear**
- 그 외: **neutral**

**글로벌 리스크 결정**:
- `global_risk_score <= -3`: **stressed**
- `global_risk_score <= -1`: **elevated**
- 그 외: **normal**

### 5. 최종 레짐 결정

글로벌 추세와 리스크를 결합하여 최종 레짐을 결정합니다:

| 글로벌 추세 | 글로벌 리스크 | 최종 레짐 |
|------------|--------------|----------|
| bull | normal | **bull** |
| bear | stressed | **crash** |
| neutral | stressed | **crash** |
| bull | elevated | **neutral** |
| 그 외 | - | 글로벌 추세와 동일 |

## 레짐 분석 결과 구조

레짐 분석 결과는 `MarketCondition` 객체에 저장되며, 다음 필드를 포함합니다:

```python
@dataclass
class MarketCondition:
    # 기본 시장 분석 필드
    market_sentiment: str  # 'bull', 'neutral', 'bear', 'crash'
    sentiment_score: float
    
    # Global Regime v4 필드
    final_regime: Optional[str]  # 최종 레짐: 'bull', 'neutral', 'bear', 'crash'
    final_score: float  # 최종 점수
    global_trend_score: float  # 글로벌 추세 점수
    global_risk_score: float  # 글로벌 리스크 점수
    kr_trend_score: float  # 한국 추세 점수
    us_trend_score: float  # 미국 추세 점수
    kr_risk_score: float  # 한국 리스크 점수
    us_risk_score: float  # 미국 리스크 점수
    kr_regime: str  # 한국 레짐
    us_prev_regime: str  # 미국 레짐
    version: str  # 'regime_v1', 'regime_v3', 'regime_v4'
```

## 레짐 분석 버전 선택

레짐 분석은 3가지 버전을 지원하며, **DB에서 선택**할 수 있습니다:

- **V1 (기본 장세 분석)**: KOSPI 수익률 기반 시장 상황 판단
- **V3 (Global Regime v3)**: 한국/미국 시장 분석
- **V4 (Global Regime v4)**: 한국/미국 시장 + 리스크 분석 (권장)

### 관리자 UI에서 선택

1. 관리자 페이지 접속: `/admin`
2. "스캐너 설정" 섹션으로 이동
3. "레짐 분석 버전" 드롭다운에서 선택
4. "설정 저장" 클릭

다음 스캔부터 선택한 레짐 버전이 적용됩니다.

### API를 통한 선택

**설정 조회:**
```bash
GET /admin/scanner-settings
Authorization: Bearer <admin_token>
```

**설정 업데이트:**
```bash
POST /admin/scanner-settings
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "regime_version": "v4"
}
```

### 환경 변수 설정 (Fallback)

DB 설정이 없거나 DB 연결 실패 시 `.env` 파일의 설정을 사용합니다:

```env
REGIME_VERSION=v4
```

### 설정 우선순위

1. **DB 우선**: `scanner_settings` 테이블에서 조회
2. **.env Fallback**: DB에 없으면 환경 변수에서 읽기
3. **기본값**: 둘 다 없으면 `v1` 사용

## 레짐 분석 사용

### 코드에서 사용

레짐 분석은 `scanner_v2/regime_v4.py`의 `analyze_regime_v4()` 함수를 통해 실행됩니다:

```python
from scanner_v2.regime_v4 import analyze_regime_v4

# 특정 날짜의 레짐 분석
result = analyze_regime_v4('20251124')

print(f"최종 레짐: {result['final_regime']}")
print(f"글로벌 추세 점수: {result['global_trend_score']:.2f}")
print(f"글로벌 리스크 점수: {result['global_risk_score']:.2f}")
```

### Market Analyzer 통합

레짐 분석 결과는 `MarketAnalyzer`를 통해 `MarketCondition` 객체에 통합됩니다. 스캐너는 이 정보를 사용하여 시장 상황에 맞는 필터 조건을 동적으로 조정합니다.

`MarketAnalyzer.analyze_market_condition()` 메서드는 설정된 레짐 버전에 따라 자동으로 적절한 분석 메서드를 호출합니다:

- `regime_version='v1'`: `_analyze_market_condition_v1()` 호출
- `regime_version='v3'`: `analyze_market_condition_v3()` 호출
- `regime_version='v4'`: `analyze_market_condition_v4()` 호출

## 레짐별 스캔 전략

### Bull (강세)

- **특징**: 상승 추세가 명확하고 리스크가 낮음
- **스캔 전략**: 
  - RSI 임계값 상향 조정 (과매수 구간 허용)
  - 최소 신호 수 완화
  - 갭/이격 필터 완화

### Neutral (중립)

- **특징**: 추세가 불명확하거나 리스크가 중간 수준
- **스캔 전략**:
  - 기본 조건 사용
  - 보수적 필터 적용

### Bear (약세)

- **특징**: 하락 추세가 명확
- **스캔 전략**:
  - RSI 임계값 하향 조정
  - 최소 신호 수 강화
  - 갭/이격 필터 강화

### Crash (급락)

- **특징**: 극단적 하락 또는 높은 리스크
- **스캔 전략**:
  - 매우 보수적 필터 적용
  - 스캔 건수 최소화
  - 안전 자산 선호

## 데이터 요구사항

레짐 분석을 위해서는 다음 데이터가 필요합니다:

1. **한국 데이터**: KOSPI200 OHLCV (최소 65일)
2. **미국 데이터**: 
   - SPY OHLCV (최소 61일, MA50/200 계산을 위해 200일 권장)
   - QQQ OHLCV (최소 61일, MA50/200 계산을 위해 200일 권장)
   - VIX OHLCV (최소 20일)

데이터가 부족한 경우 기본값(neutral, normal)을 사용합니다.

## 캐싱

레짐 분석 결과는 `MarketAnalyzer`의 캐시에 저장되어 5분간 유지됩니다. 같은 날짜에 대한 반복 분석 요청 시 캐시된 결과를 반환합니다.

## 참고

- **구현 위치**: `backend/scanner_v2/regime_v4.py`
- **통합 위치**: `backend/market_analyzer.py`
- **데이터 저장**: `market_conditions` 테이블 (PostgreSQL)

## 적용 범위

### 한국 주식 스캔
- ✅ 레짐 분석 적용 (Global Regime v4)
- ✅ 레짐 기반 cutoff 적용
- ✅ 레짐 기반 필터링 조건 조정

### 미국 주식 스캔
- ✅ 레짐 분석 적용 (Global Regime v4) - 2025-12-06 적용
- ✅ 레짐 기반 cutoff 적용
- ✅ 레짐 기반 필터링 조건 조정
- ✅ 강세장 조건 완화

**참고**: 미국 주식 스캔도 한국 주식과 동일하게 Global Regime v4를 사용하여 레짐 분석을 수행합니다.

## 관련 문서

- [레짐 분석 버전 선택 가이드](./REGIME_VERSION_SELECTION.md)
- [시장 분석기 계획](../plans/MARKET_ANALYZER_PLAN.md)
- [프로젝트 개요](../PROJECT_OVERVIEW.md)
- [Scanner V2 사용 가이드](../scanner-v2/SCANNER_V2_USAGE.md)
- [스캐너 설정 테이블](../database/SCANNER_SETTINGS_TABLE.md)
- [레짐 분석 및 스캔 프로세스](../REGIME_ANALYSIS_AND_SCAN_PROCESS.md)
- [미국 주식 스캔 레짐 분석 적용](../US_STOCK_REGIME_ANALYSIS_FINAL_SUMMARY.md)

