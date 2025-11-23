# 백필 실행 스크립트 가이드

## 📋 개요
백필(Backfill) 시스템을 쉽게 실행할 수 있는 스크립트 모음입니다.

## 🚀 스크립트 목록

### 1. `run_backfill.sh` - 기본 백필 실행
특정 기간의 백필을 실행합니다.

```bash
# 기본 사용법
./run_backfill.sh 2024-01-01 2024-01-31

# 워커 수 지정
./run_backfill.sh 2024-01-01 2024-01-31 8

# 실행 후 자동 검증 옵션 제공
```

### 2. `verify_backfill.sh` - 백필 검증
백필 결과의 품질을 검증합니다.

```bash
# 검증 실행
./verify_backfill.sh 2024-01-01 2024-01-31
```

### 3. `backfill_monthly.sh` - 월별 백필
특정 월 전체를 백필합니다.

```bash
# 2024년 1월 전체
./backfill_monthly.sh 2024 1

# 워커 수 지정
./backfill_monthly.sh 2024 1 8
```

### 4. `backfill_range.py` - 범위별 백필
여러 월/분기를 한 번에 처리합니다.

```bash
# 월별 범위 (2024년 1월~3월)
python backfill_range.py --mode monthly --start-year 2024 --start-month 1 --end-year 2024 --end-month 3

# 분기별 범위 (2024년 1분기~2분기)
python backfill_range.py --mode quarterly --start-year 2024 --start-quarter 1 --end-year 2024 --end-quarter 2

# 워커 수 지정
python backfill_range.py --mode monthly --start-year 2024 --start-month 1 --end-year 2024 --end-month 12 --workers 8
```

## 📁 실행 위치
모든 스크립트는 프로젝트 루트의 `scripts/` 디렉토리에서 실행하세요.

```bash
cd /path/to/stock-finder/scripts
./run_backfill.sh 2024-01-01 2024-01-31
```

## ⚙️ 사전 준비사항

### 1. 데이터 캐시 파일
백필 실행 전 다음 캐시 파일들이 준비되어 있어야 합니다:

```
backend/data_cache/
├── kospi200_ohlcv.pkl
├── spy_ohlcv.pkl
├── qqq_ohlcv.pkl
├── vix_ohlcv.pkl
└── universe_ohlcv.pkl
```

### 2. 데이터베이스 연결
PostgreSQL 데이터베이스가 실행 중이고 연결 설정이 올바른지 확인하세요.

### 3. Python 환경
필요한 패키지가 설치되어 있는지 확인하세요:

```bash
pip install pandas numpy psycopg[binary] pytz
```

## 🔧 고급 사용법

### 병렬 처리 최적화
- **CPU 코어 수**: 시스템 CPU 코어 수의 50-75% 권장
- **메모리**: 워커당 약 500MB 메모리 필요
- **I/O**: SSD 사용 시 더 높은 워커 수 가능

```bash
# 8코어 시스템에서 권장
./run_backfill.sh 2024-01-01 2024-01-31 6

# 16코어 시스템에서 권장  
./run_backfill.sh 2024-01-01 2024-01-31 12
```

### 대용량 데이터 처리
1년 이상의 데이터를 처리할 때는 월별로 나누어 실행하는 것을 권장합니다:

```bash
# 2024년 전체를 월별로 처리
python backfill_range.py --mode monthly --start-year 2024 --start-month 1 --end-year 2024 --end-month 12 --workers 6
```

### 실패 시 재시도
백필이 실패한 경우:

1. **로그 확인**: 실패 원인 파악
2. **부분 재실행**: 실패한 기간만 다시 실행
3. **워커 수 조정**: 메모리 부족 시 워커 수 감소

```bash
# 실패한 기간만 재실행
./run_backfill.sh 2024-01-15 2024-01-20 4

# 워커 수를 줄여서 재시도
./run_backfill.sh 2024-01-01 2024-01-31 2
```

## 📊 성능 가이드

### 예상 처리 시간
- **1개월 (약 22거래일)**: 2-5분 (4워커 기준)
- **1분기 (약 65거래일)**: 6-15분 (4워커 기준)
- **1년 (약 250거래일)**: 25-60분 (4워커 기준)

### 시스템 요구사항
- **CPU**: 4코어 이상 권장
- **메모리**: 4GB 이상 권장
- **디스크**: 10GB 이상 여유 공간
- **네트워크**: 안정적인 인터넷 연결

## 🚨 주의사항

### 1. 데이터 일관성
- 백필 실행 중에는 다른 스캔 작업을 중단하세요
- 데이터베이스 백업을 먼저 수행하세요

### 2. 시스템 리소스
- 백필 실행 중 시스템 부하가 높아질 수 있습니다
- 다른 중요한 작업과 동시 실행을 피하세요

### 3. 네트워크 안정성
- 미국 시장 데이터 수집을 위해 안정적인 인터넷 연결이 필요합니다
- VPN 사용 시 연결 안정성을 확인하세요

## 🔍 문제 해결

### 자주 발생하는 오류

#### 1. "백필 디렉토리를 찾을 수 없습니다"
```bash
# 해결방법: 올바른 디렉토리에서 실행
cd /path/to/stock-finder/scripts
./run_backfill.sh 2024-01-01 2024-01-31
```

#### 2. "DB 연결 실패"
```bash
# 해결방법: PostgreSQL 서비스 확인
sudo systemctl status postgresql
sudo systemctl start postgresql
```

#### 3. "캐시 파일이 없습니다"
```bash
# 해결방법: 캐시 파일 생성 (별도 스크립트 필요)
cd backend
python create_cache_files.py
```

#### 4. "메모리 부족"
```bash
# 해결방법: 워커 수 감소
./run_backfill.sh 2024-01-01 2024-01-31 2
```

### 로그 확인
백필 실행 중 문제가 발생하면 다음 로그를 확인하세요:

```bash
# Python 로그
tail -f backend/backfill.log

# 시스템 로그
journalctl -f -u stock-finder
```

## 📞 지원

문제가 지속되면 다음을 확인하세요:

1. **시스템 요구사항** 충족 여부
2. **데이터베이스 연결** 상태
3. **캐시 파일** 존재 여부
4. **Python 패키지** 설치 상태

추가 도움이 필요하면 개발팀에 문의하세요.