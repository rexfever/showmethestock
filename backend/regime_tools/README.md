# Regime Tools

Regime v4 + Scanner v2 품질 검증 및 백테스트 도구

## 파일 구조

```
backend/
├── regime_tools/
│   ├── __init__.py
│   ├── regime_quality_validator.py  # 레짐 품질 검증
│   ├── run_regime_and_backtest.py   # 통합 실행 스크립트
│   └── README.md
└── backtest/
    ├── __init__.py
    └── simple_backtester_v2.py      # 간단한 백테스터
```

## 사용법

### 1. 레짐 품질 검증만 실행

```python
from regime_tools.regime_quality_validator import analyze_regime_quality

result = analyze_regime_quality('20250701', '20250930')
```

### 2. 백테스트만 실행

```python
from backtest.simple_backtester_v2 import run_simple_backtest

result = run_simple_backtest('20250701', '20250930')
```

### 3. 통합 실행 (CLI)

```bash
cd backend
python regime_tools/run_regime_and_backtest.py --start 20250701 --end 20250930
```

## 기능

### Regime Quality Validator

- midterm_regime과 실제 시장의 5~20일 수익률 상관관계 검증
- 각 날짜별 KOSPI 5/10/20일 수익률과 midterm_regime의 매칭률 분석
- crash/bear/bull/neutral별 성과 분포 출력

### Simple Backtester v2

- Scanner v2 + Regime v4 기반 스캔 결과 백테스트
- 종가 매수 → 다음날 시초가 매도
- 동일 비중
- 거래비용 0.05% 반영
- horizon별 성과 계산 (swing/position/longterm)
- crash 구간에서는 longterm만 테스트

## 출력 예시

### 레짐 품질 검증

```
📊 BULL:
   - 일수: 45일
   - R20: 평균 5.23%, 표준편차 2.15%, 중앙값 5.10%

매칭률 분석:
   - BULL: 85.0% (38/45)
```

### 백테스트

```
📊 SWING:
   - 총 트레이드: 120건
   - 승률: 58.3%
   - CAGR: 12.5%
   - MDD: 5.2%
```

## 주의사항

- 기존 코드를 수정하지 않음
- 독립적으로 동작 가능
- DB 스키마 변경 불필요
- 실패한 날짜는 skip하고 계속 진행

