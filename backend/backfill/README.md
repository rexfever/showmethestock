# 백필 모듈 사용 가이드

## 📋 개요
백필 모듈은 과거 데이터를 고속으로 처리하여 스캔 결과를 생성하는 경량화된 시스템입니다.

## 🚀 빠른 시작

### 1. 독립 실행 (권장)
```bash
# 백필 실행
cd backend/backfill
python run_backfill_standalone.py --start 2024-01-01 --end 2024-01-31 --workers 4

# 검증 실행
python run_verifier_standalone.py --start 2024-01-01 --end 2024-01-31
```

### 2. 모듈로 사용
```python
# backend 디렉토리에서 실행
from backfill import BackfillRunner, BackfillVerifier

# 백필 실행
runner = BackfillRunner()
runner.run_backfill('2024-01-01', '2024-01-31', workers=4)

# 검증 실행
verifier = BackfillVerifier()
result = verifier.verify_backfill('2024-01-01', '2024-01-31')
```

## 📁 파일 구조
```
backfill/
├── __init__.py                          # 패키지 초기화
├── backfill_market_analyzer_light.py    # 경량 장세 분석기
├── backfill_fast_indicators.py          # 고속 지표 계산기
├── backfill_fast_scanner.py             # 고속 스캐너
├── backfill_runner.py                   # 백필 실행기
├── backfill_verifier.py                 # 품질 검증기
├── run_backfill_standalone.py           # 독립 실행 스크립트
├── run_verifier_standalone.py           # 독립 검증 스크립트
└── README.md                            # 이 파일
```

## ⚙️ 설정

### 환경 변수
```bash
export PYTHONPATH="/path/to/stock-finder/backend:$PYTHONPATH"
```

### 데이터 캐시
- 위치: `backend/data_cache/`
- 필요 파일:
  - `kospi200_ohlcv.pkl`
  - `spy_ohlcv.pkl`
  - `qqq_ohlcv.pkl`
  - `vix_ohlcv.pkl`
  - `universe_ohlcv.pkl`

## 🔧 주요 기능

### 1. 경량 장세 분석
- 한국 + 미국 시장 데이터 결합
- 4단계 레짐 분류 (bull/neutral/bear/crash)
- 로컬 캐시 기반 고속 처리

### 2. 고속 스캐너
- Stage1 필터링 (가격/거래량/ATR)
- 점수 계산 (RSI/MACD/EMA60 기반)
- Horizon 분류 (swing/position/longterm)

### 3. 병렬 처리
- multiprocessing Pool 사용
- 날짜별 독립 처리
- 멱등성 보장

### 4. 품질 검증
- 레짐별 후보 수 검증
- 데이터 품질 검사
- 누락 날짜 확인

## 📊 출력 데이터

### market_regime_daily 테이블
```sql
date, final_regime, us_metrics, kr_metrics, us_preopen_metrics, version
```

### scan_daily 테이블
```sql
date, horizon, code, score, price, volume, version
```

## 🚨 주의사항

1. **데이터 캐시**: 실행 전 필요한 캐시 파일들이 준비되어 있어야 함
2. **DB 연결**: PostgreSQL 연결 설정 필요
3. **메모리**: 병렬 처리 시 충분한 메모리 확보
4. **실행 시간**: 대용량 데이터 처리 시 시간 소요

## 🔍 문제 해결

### Import 오류
```bash
# PYTHONPATH 설정
export PYTHONPATH="/path/to/stock-finder/backend:$PYTHONPATH"

# 또는 독립 실행 스크립트 사용
python run_backfill_standalone.py --help
```

### 캐시 파일 없음
```python
# 캐시 파일 생성 (별도 스크립트 필요)
python create_cache_files.py
```

### DB 연결 실패
```python
# DB 설정 확인
from db_manager import db_manager
db_manager.test_connection()
```