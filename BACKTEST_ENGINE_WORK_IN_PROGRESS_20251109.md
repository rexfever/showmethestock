# 백테스트 엔진 구축 작업 진행 상황

## 📌 작업 개요

`scanner_v2` 기반의 완전한 백테스트 엔진을 구축하는 작업입니다.

**목표:**
- 스캔 결과 기반으로 트레이드 자동 생성
- 각 Horizon(Swing/Position/Long-term)별 매매 로직 분리
- 장세(bull/neutral/bear/crash)에 따라 전략 강도 반영
- 개별 트레이드 리포트 + 일자별 equity curve 생성
- 성과 지표(CAGR, MDD, Sharpe, 승률, 평균 P/L) 계산
- CSV 및 JSON 리포트 출력

---

## ✅ 완료한 작업

### 1. 파일 구조 생성

다음 파일들이 생성되었습니다:

```
backend/backtest/
    __init__.py
    backtest_runner.py      # 백테스트 통합 러너
    trade_logic.py          # 트레이드 생성 및 시뮬레이션
    metrics.py              # 성과 지표 계산 (CAGR, MDD, Sharpe 등)
    report.py               # 리포트 생성 및 CSV 저장

scanner_v2/
    backtest_entry.py       # CLI 엔트리포인트
```

### 2. 구현된 주요 기능

#### `backend/backtest/trade_logic.py`
- ✅ `Trade` dataclass 정의
- ✅ `HOLD_DAYS` 상수 정의 (swing: 5일, position: 10일, longterm: 20일)
- ✅ `simulate_trade()`: 단일 트레이드 시뮬레이션
  - signal_date 다음 거래일 시가에 진입
  - Horizon별 고정 보유일수 후 종가에 청산
- ✅ `generate_trades()`: 스캔 결과 기반 트레이드 리스트 생성

#### `backend/backtest/metrics.py`
- ✅ `calculate_cagr()`: CAGR 계산
- ✅ `calculate_mdd()`: 최대 낙폭 계산
- ✅ `calculate_sharpe()`: Sharpe Ratio 계산
- ✅ `calculate_winrate()`: 승률 계산
- ✅ `aggregate_metrics()`: 종합 지표 집계

#### `backend/backtest/report.py`
- ✅ `print_summary()`: 텍스트 요약 출력
- ✅ `save_trades_csv()`: 트레이드 리스트 CSV 저장
- ✅ `save_equity_curve_csv()`: Equity curve CSV 저장

#### `backend/backtest/backtest_runner.py`
- ✅ `_iter_dates()`: 날짜 범위 순회
- ✅ `_load_price_panel_for_symbols()`: OHLCV 패널 로드
- ✅ `_build_equity_curve()`: Equity curve 생성
- ✅ `run_backtest()`: 전체 백테스트 실행 함수

#### `scanner_v2/backtest_entry.py`
- ✅ CLI 인자 파싱 (--start, --end, --horizon, --max-trades-per-day)
- ✅ `main()`: 백테스트 실행 및 리포트 생성

---

## ⚠️ 발생한 문제점 및 해결 상태

### 1. Syntax 오류 (해결됨)
- **문제**: f-string 내부의 이스케이프 문자 처리 문제
- **원인**: patch 생성 시 따옴표 이스케이프가 잘못됨
- **해결**: 모든 f-string의 따옴표를 일반 따옴표로 수정

### 2. Import 오류 (부분 해결)
- **문제**: `from backend.backtest.trade_logic import HOLD_DAYS` 모듈을 찾을 수 없음
- **원인**: 절대 import 경로 문제 (backend 폴더에서 실행할 때)
- **해결**: 상대 import로 변경 (`from .trade_logic import HOLD_DAYS`)

### 3. Trade 객체 생성 문제 (확인 필요)
- **상태**: `raw_trades`는 dict 리스트인데 `Trade` 객체로 변환 필요
- **위치**: `backtest_runner.py:149`

---

## 🔧 남은 할 일

### 1. 즉시 해결 필요 (Critical)

#### 1-1. Trade 객체 생성 로직 수정
- **파일**: `backend/backtest/backtest_runner.py`
- **위치**: 약 149번 라인
- **문제**: `raw_trades`가 dict 리스트인데 `Trade` 객체로 변환하는 부분 확인
- **수정 방안**:
  ```python
  # 현재 (확인 필요)
  trades = [Trade(**t) for t in raw_trades]
  
  # 또는 generate_trades가 이미 Trade 객체를 반환하는지 확인
  ```

#### 1-2. 백테스트 실행 검증
- **명령어**:
  ```bash
  cd backend
  python -m scanner_v2.backtest_entry --start 20250723 --end 20251105 --horizon position --max-trades-per-day 5
  ```
- **검증 항목**:
  - [ ] 트레이드 생성 여부 확인
  - [ ] Equity curve 생성 확인
  - [ ] Metrics 계산 확인
  - [ ] CSV 파일 생성 확인

#### 1-3. 거래일 필터링
- **문제**: `_iter_dates()`가 모든 날짜(토/일 포함)를 순회
- **해결**: 거래일만 필터링하도록 수정
  - 방법 1: `scanner_v2.scan_v2`를 호출할 때 거래일만 스캔
  - 방법 2: `run_scan_v2()`가 주말/공휴일을 자동 스킵하는지 확인

### 2. 기능 개선 (Important)

#### 2-1. 에러 처리 강화
- 종목 delist 처리
- 데이터 부족 시 skip 로직
- 가격 데이터 없는 경우 처리

#### 2-2. 성능 최적화
- 날짜별 스캔 결과 캐싱
- OHLCV 패널 로드 최적화
- 병렬 처리 고려

#### 2-3. 리포트 개선
- JSON 리포트 추가
- 상세 트레이드 리포트 (종목별, 날짜별 통계)
- Equity curve 시각화 데이터 생성

### 3. 테스트 및 검증

#### 3-1. 샘플 백테스트 실행
다음 날짜들로 테스트:
- 2025-07-23 (neutral)
- 2025-09-17 (neutral)
- 2025-10-22 (neutral)
- 2025-08-20 (bear)
- 2025-11-05 (crash)

#### 3-2. 결과 검증
- [ ] 트레이드 수가 합리적인지 확인
- [ ] Equity curve가 정상적으로 생성되는지 확인
- [ ] Metrics 값이 합리적인 범위인지 확인
- [ ] CSV 파일이 올바르게 생성되는지 확인

---

## 📁 파일 구조

```
backend/
├── backtest/
│   ├── __init__.py
│   ├── backtest_runner.py      # ✅ 완료
│   ├── trade_logic.py          # ✅ 완료
│   ├── metrics.py              # ✅ 완료
│   └── report.py               # ✅ 완료
│
├── scanner_v2/
│   ├── backtest_entry.py       # ✅ 완료
│   └── scan_v2.py             # (기존 파일, 백테스트에서 사용)
│
└── data_loader.py              # (기존 파일, OHLCV 로드용)
```

---

## 🚀 실행 방법

### 환경 설정
```bash
cd /Users/rexsmac/workspace/stock-finder/backend
source venv/bin/activate  # 또는 실제 venv 경로
```

### 백테스트 실행
```bash
# 기본 실행
python -m scanner_v2.backtest_entry \
    --start 20250723 \
    --end 20251105 \
    --horizon position

# 하루 최대 트레이드 수 제한
python -m scanner_v2.backtest_entry \
    --start 20250723 \
    --end 20251105 \
    --horizon position \
    --max-trades-per-day 5

# Swing Horizon 백테스트
python -m scanner_v2.backtest_entry \
    --start 20250723 \
    --end 20251105 \
    --horizon swing

# Long-term Horizon 백테스트
python -m scanner_v2.backtest_entry \
    --start 20250723 \
    --end 20251105 \
    --horizon longterm
```

### 출력 파일
- `trades_{horizon}.csv`: 개별 트레이드 리스트
- `equity_{horizon}.csv`: 일자별 equity curve

---

## 🔍 디버깅 체크리스트

백테스트 실행 시 다음을 확인하세요:

1. **Import 오류**
   - `ModuleNotFoundError: No module named 'backend'`
   - → 상대 import로 수정 필요

2. **데이터 로드 오류**
   - `KeyError` 또는 `AttributeError` 발생
   - → `scanner_v2.scan_v2.run_scan_v2()` 반환 구조 확인

3. **Trade 생성 오류**
   - `TypeError` 또는 `ValueError` 발생
   - → `generate_trades()` 반환 형식과 `Trade` dataclass 필드 일치 확인

4. **Metrics 계산 오류**
   - `ZeroDivisionError` 또는 `ValueError`
   - → 빈 트레이드 리스트 처리 확인

---

## 📝 참고 사항

### 기존 코드와의 관계
- **기존 백테스터**: `backend/backtester/engine.py` (v1 스캐너용)
- **새 백테스터**: `backend/backtest/` (v2 스캐너용)
- 두 엔진은 독립적으로 동작하며, v1 코드는 수정하지 않음

### 의존성
- `scanner_v2.scan_v2.run_scan_v2()`: 스캔 결과 생성
- `data_loader.load_price_data()`: OHLCV 데이터 로드
- `pandas`, `numpy`: 데이터 처리

### Trade 시뮬레이션 로직
- **진입**: signal_date 다음 거래일 시가
- **청산**: 진입 후 고정 보유일수 경과 후 종가
  - Swing: 5일
  - Position: 10일
  - Long-term: 20일

---

## 📅 작업 일정 (예상)

1. **즉시 해결** (1시간 내)
   - Trade 객체 생성 로직 수정
   - 기본 백테스트 실행 검증

2. **단기 개선** (2-3시간)
   - 거래일 필터링
   - 에러 처리 강화
   - 리포트 개선

3. **최종 검증** (1-2시간)
   - 다양한 날짜 범위 테스트
   - 결과 검증 및 문서화

---

## 🔗 관련 파일

- 요구사항: 사용자 프롬프트 (백테스트 엔진 구축)
- 기존 백테스터: `backend/backtester/engine.py`
- 스캐너 v2: `backend/scanner_v2/scan_v2.py`
- 데이터 로더: `backend/data_loader.py`

---

**작성일**: 2025-11-09  
**작성자**: AI Assistant  
**상태**: 진행 중 (90% 완료, 실행 검증 필요)

