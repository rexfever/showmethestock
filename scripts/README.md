# Scripts Directory

이 디렉토리는 서버 운영, 데이터베이스 백업, 백필 작업을 위한 스크립트들을 포함합니다.

## 📁 파일 목록

### 백필 스크립트 ✨ **NEW**
- `run_backfill.sh` - 특정 기간 백필 실행
- `verify_backfill.sh` - 백필 데이터 품질 검증
- `backfill_monthly.sh` - 월별 백필 실행
- `backfill_range.py` - 여러 월/분기 백필 실행
- `README_BACKFILL.md` - 백필 사용 가이드

### 데이터베이스 백업 스크립트

### `backup-database.sh`
- **용도**: 데이터베이스 파일들을 일단위로 백업
- **백업 대상**:
  - `portfolio.db` - 사용자 포트폴리오 데이터
  - `snapshots.db` - 스캔 결과 데이터
  - `email_verifications.db` - 이메일 인증 데이터
  - `news_data.db` - 뉴스 데이터
  - `snapshots/` - 스캔 결과 JSON 파일들
- **백업 위치**: `/home/ubuntu/backups/`
- **자동 정리**: 30일 이상 된 백업 파일 자동 삭제

### `setup-backup-cron.sh`
- **용도**: 자동 백업을 위한 cron 작업 설정
- **실행 시간**: 매일 새벽 2시
- **로그**: `/home/ubuntu/backups/backup.log`

### `manual-backup.sh`
- **용도**: 수동 백업 실행
- **사용법**: `./manual-backup.sh`

## 🚀 사용법

### 백필 작업
```bash
# 기본 백필
./run_backfill.sh 2024-01-01 2024-01-31

# 월별 백필
./backfill_monthly.sh 2024 1

# 범위 백필
python backfill_range.py --mode monthly --start-year 2024 --start-month 1 --end-year 2024 --end-month 3

# 검증
./verify_backfill.sh 2024-01-01 2024-01-31
```

자세한 백필 사용법은 `README_BACKFILL.md`를 참조하세요.

### 데이터베이스 백업

### 1. 자동 백업 설정 (서버에서)
```bash
cd /home/ubuntu/showmethestock
./scripts/setup-backup-cron.sh
```

### 2. 수동 백업 실행 (서버에서)
```bash
cd /home/ubuntu/showmethestock
./scripts/manual-backup.sh
```

### 3. 백업 상태 확인
```bash
# 백업 파일 목록 확인
ls -la /home/ubuntu/backups/

# 백업 로그 확인
tail -f /home/ubuntu/backups/backup.log

# cron 작업 확인
crontab -l
```

## 📋 백업 파일 형식

```
/home/ubuntu/backups/
├── portfolio_20251012_020000.db
├── snapshots_20251012_020000.db
├── email_verifications_20251012_020000.db
├── news_data_20251012_020000.db
├── snapshots_20251012_020000.tar.gz
└── backup.log
```

## 🔧 백업 복원

### 데이터베이스 복원
```bash
# 백업 파일을 현재 데이터베이스로 복사
cp /home/ubuntu/backups/portfolio_20251012_020000.db /home/ubuntu/showmethestock/backend/portfolio.db
cp /home/ubuntu/backups/snapshots_20251012_020000.db /home/ubuntu/showmethestock/backend/snapshots.db

# 서비스 재시작
sudo systemctl restart stock-finder-backend
```

### 스캔 결과 복원
```bash
# 백업 파일 압축 해제
cd /home/ubuntu/showmethestock/backend
tar -xzf /home/ubuntu/backups/snapshots_20251012_020000.tar.gz
```

## ⚠️ 주의사항

1. **백업 파일 크기**: 스캔 결과가 많아질수록 백업 파일 크기가 증가합니다
2. **디스크 공간**: 30일간의 백업 파일을 저장할 충분한 디스크 공간이 필요합니다
3. **권한**: 백업 스크립트는 `ubuntu` 사용자 권한으로 실행됩니다
4. **서비스 중단**: 백업 중에는 서비스가 중단되지 않습니다 (읽기 전용)

## 🔍 문제 해결

### 백업이 실행되지 않는 경우
```bash
# cron 서비스 상태 확인
sudo systemctl status cron

# cron 로그 확인
sudo tail -f /var/log/cron

# 수동 실행으로 테스트
./scripts/manual-backup.sh
```

### 백업 파일이 생성되지 않는 경우
```bash
# 백업 디렉토리 권한 확인
ls -la /home/ubuntu/backups/

# 스크립트 실행 권한 확인
ls -la scripts/backup-database.sh
```
