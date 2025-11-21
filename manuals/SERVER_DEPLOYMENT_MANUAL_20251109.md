# 서버 배포 및 운영 메뉴얼 (2025-11-09)

## 📋 목차
1. [서버 정보](#서버-정보)
2. [서버 접속](#서버-접속)
3. [PostgreSQL 관리](#postgresql-관리)
4. [백엔드 배포](#백엔드-배포)
5. [프론트엔드 배포](#프론트엔드-배포)
6. [환경 변수(.env) 관리](#환경-변수env-관리)
7. [서비스 관리](#서비스-관리)
8. [데이터베이스 백업](#데이터베이스-백업)
9. [모니터링 및 로그](#모니터링-및-로그)
10. [문제 해결](#문제-해결)
11. [긴급 대응](#긴급-대응)

---

## 서버 정보

### 기본 정보
- **서버 IP**: `52.79.145.238`
- **OS**: Ubuntu 22.04 LTS
- **RAM**: 1GB
- **CPU**: 1 vCPU
- **디스크**: 30GB
- **리전**: AWS ap-northeast-2 (Seoul)

### 설치된 소프트웨어
- **Python**: 3.10
- **Node.js**: 18.x
- **PostgreSQL**: 16
- **Nginx**: 1.18.0
- **PM2**: 5.x (프론트엔드 프로세스 관리)

### 주요 디렉토리
```
/home/ubuntu/showmethestock/
├── backend/              # 백엔드 소스
│   ├── venv/            # Python 가상환경
│   ├── main.py          # FastAPI 앱
│   ├── .env             # 환경 변수
│   └── logs/            # 로그 파일
├── frontend/            # 프론트엔드 소스
│   ├── .next/          # Next.js 빌드
│   └── .env.local      # 환경 변수
└── backups/            # DB 백업
    └── postgres/       # PostgreSQL 백업
```

### 서비스 포트
- **백엔드 (FastAPI)**: 8000
- **프론트엔드 (Next.js)**: 3000
- **Nginx**: 80, 443
- **PostgreSQL**: 5432 (localhost only)

---

## 서버 접속

### SSH 접속

**사용 키 파일**: `~/.ssh/id_rsa`

```bash
# SSH config 사용 (권장)
ssh stock-finder

# 직접 키 파일 지정
ssh -i ~/.ssh/id_rsa ubuntu@52.79.145.238

# 기본 접속 (키 없이)
ssh ubuntu@52.79.145.238
```

### 초기 설정 확인

```bash
# 서버 접속 후
cd /home/ubuntu/showmethestock

# Git 저장소 상태 확인
git status
git log --oneline -5

# 실행 중인 서비스 확인
systemctl status stock-finder-backend
systemctl status stock-finder-frontend
```

---

## PostgreSQL 관리

### 1. PostgreSQL 접속

```bash
# postgres 사용자로 접속
sudo -u postgres psql

# stockfinder 데이터베이스 접속
sudo -u postgres psql -d stockfinder

# stockfinder 사용자로 접속
psql -U stockfinder -d stockfinder
# 비밀번호: stockfinder_pass
```

### 2. 데이터베이스 상태 확인

```bash
# PostgreSQL 서비스 상태
sudo systemctl status postgresql

# 데이터베이스 목록
sudo -u postgres psql -c "\l"

# 테이블 목록
sudo -u postgres psql -d stockfinder -c "\dt"

# 테이블 크기 확인
sudo -u postgres psql -d stockfinder -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### 3. 사용자 및 권한 관리

```bash
# 사용자 목록
sudo -u postgres psql -c "\du"

# stockfinder 사용자 권한 확인
sudo -u postgres psql -d stockfinder -c "
SELECT grantee, privilege_type 
FROM information_schema.role_table_grants 
WHERE grantee='stockfinder';
"

# 테이블 소유권 변경 (필요시)
sudo -u postgres psql -d stockfinder -c "
ALTER TABLE users OWNER TO stockfinder;
ALTER TABLE scan_rank OWNER TO stockfinder;
-- 모든 테이블에 대해 반복
"
```

### 4. PostgreSQL 설정 최적화

```bash
# 설정 파일 편집
sudo nano /etc/postgresql/16/main/postgresql.conf

# 1GB RAM 서버 권장 설정:
# shared_buffers = 256MB
# work_mem = 4MB
# maintenance_work_mem = 64MB
# effective_cache_size = 768MB
# max_connections = 50
# wal_buffers = 8MB
# checkpoint_completion_target = 0.9
# random_page_cost = 1.1
# seq_page_cost = 1.0

# 설정 적용
sudo systemctl restart postgresql
```

---

## 백엔드 배포

### 1. 코드 업데이트

```bash
# 서버 접속
ssh ubuntu@52.79.145.238

# 프로젝트 디렉토리로 이동
cd /home/ubuntu/showmethestock

# 현재 변경사항 확인
git status

# 변경사항 stash (있다면)
git stash

# 최신 코드 가져오기
git pull origin main

# stash 적용 (필요시)
git stash pop
```

### 2. 환경 변수 확인

```bash
cd /home/ubuntu/showmethestock/backend

# .env 파일 확인
cat .env | grep -E "DB_ENGINE|DATABASE_URL|KIWOOM"

# 필수 환경 변수:
# DB_ENGINE=postgres
# DATABASE_URL=postgresql://stockfinder:stockfinder_pass@localhost/stockfinder
# KIWOOM_APP_KEY=...
# KIWOOM_APP_SECRET=...
# JWT_SECRET_KEY=...
```

### 3. Python 패키지 업데이트

```bash
cd /home/ubuntu/showmethestock/backend

# 가상환경 활성화
source venv/bin/activate

# 패키지 업데이트
pip install -r requirements.txt

# PostgreSQL 관련 패키지 확인
pip list | grep psycopg

# 예상 출력:
# psycopg                3.2.12
# psycopg-binary         3.2.12
# psycopg-pool           3.2.7
```

### 4. 데이터베이스 마이그레이션

```bash
cd /home/ubuntu/showmethestock/backend

# 새로운 SQL 파일이 있다면 적용
psql -U stockfinder -d stockfinder -f sql/create_market_analysis_validation.sql

# 또는 특정 마이그레이션 스크립트 실행
python migrations/extend_market_conditions.py
```

### 5. 백엔드 서비스 재시작

```bash
# 서비스 중지
sudo systemctl stop stock-finder-backend

# 서비스 시작
sudo systemctl start stock-finder-backend

# 서비스 재시작 (중지 + 시작)
sudo systemctl restart stock-finder-backend

# 서비스 상태 확인
sudo systemctl status stock-finder-backend

# 로그 확인 (실시간)
sudo journalctl -u stock-finder-backend -f
```

### 6. 백엔드 동작 확인

```bash
# Health check
curl http://localhost:8000/health

# 예상 응답:
# {"status":"ok","timestamp":"2025-11-09T..."}

# 최신 스캔 데이터 확인
curl http://localhost:8000/latest-scan | jq '.ok'

# 장세 분석 검증 데이터 확인
curl "http://localhost:8000/admin/market-validation?date=20251109" | jq '.'
```

---

## 프론트엔드 배포

### 1. 코드 업데이트

```bash
# 프로젝트 디렉토리 (이미 git pull 했다면 생략)
cd /home/ubuntu/showmethestock

# 최신 코드 가져오기 (아직 안했다면)
git pull origin main
```

### 2. 환경 변수 확인

```bash
cd /home/ubuntu/showmethestock/frontend

# .env.local 파일 확인
cat .env.local

# 필수 환경 변수:
# NEXT_PUBLIC_BACKEND_URL=http://52.79.145.238:8000
```

### 3. 패키지 업데이트 및 빌드

```bash
cd /home/ubuntu/showmethestock/frontend

# 패키지 업데이트 (package.json이 변경된 경우)
npm install

# 프로덕션 빌드
npm run build

# 빌드 결과 확인
ls -la .next/
```

### 4. 프론트엔드 서비스 재시작

```bash
# 서비스 중지
sudo systemctl stop stock-finder-frontend

# 서비스 시작
sudo systemctl start stock-finder-frontend

# 서비스 재시작
sudo systemctl restart stock-finder-frontend

# 서비스 상태 확인
sudo systemctl status stock-finder-frontend

# PM2로 관리하는 경우
pm2 restart stock-finder-frontend
pm2 status
pm2 logs stock-finder-frontend
```

### 5. 프론트엔드 동작 확인

```bash
# 로컬 접속 확인
curl http://localhost:3000

# 외부 접속 확인 (브라우저에서)
# http://52.79.145.238:3000
# 또는 도메인 (설정된 경우)
```

---

## 환경 변수(.env) 관리

### 1. .env 파일 개요

**중요**: `.env` 파일은 Git에 추적되지 않습니다 (`.gitignore`에 포함됨). 따라서 서버 배포 시 `.env` 파일은 자동으로 변경되지 않으며, 서버에서 직접 관리해야 합니다.

**위치**:
- 백엔드: `/home/ubuntu/showmethestock/backend/.env`
- 프론트엔드: `/home/ubuntu/showmethestock/frontend/.env.local`

### 2. .env 파일 확인

```bash
# 백엔드 .env 확인
cd /home/ubuntu/showmethestock/backend
cat .env

# 특정 변수만 확인
cat .env | grep -E "GAP_MAX|MIN_SIGNALS|DATABASE_URL"

# 프론트엔드 .env 확인
cd /home/ubuntu/showmethestock/frontend
cat .env.local
```

### 3. .env 파일 수정

#### 3.1 수동 수정

```bash
# 백엔드 .env 편집
cd /home/ubuntu/showmethestock/backend
nano .env  # 또는 vi, vim

# 수정 후 서비스 재시작 필수
sudo systemctl restart stock-finder-backend
```

#### 3.2 관리자 API를 통한 수정 (일부 변수만)

일부 스캔 관련 파라미터는 관리자 API를 통해 수정할 수 있습니다:

```bash
# 관리자 API 엔드포인트: /admin/trend-apply
# 수정 가능한 변수:
# - MIN_SIGNALS
# - RSI_UPPER_LIMIT
# - VOL_MA5_MULT
# - GAP_MAX
# - EXT_FROM_TEMA20_MAX
```

### 4. .env 파일 백업

#### 4.1 수동 백업

```bash
cd /home/ubuntu/showmethestock/backend

# 백업 생성 (타임스탬프 포함)
cp .env .env.backup_$(date +%Y%m%d_%H%M%S)

# 백업 파일 목록 확인
ls -lth .env.backup* | head -10
```

#### 4.2 자동 백업

관리자 API(`/admin/trend-apply`)를 통해 변경 시 자동으로 백업이 생성됩니다:
- 형식: `.env.backup.YYYYMMDD_HHMMSS`
- 위치: `/home/ubuntu/showmethestock/backend/`

### 5. .env 파일 복원

```bash
cd /home/ubuntu/showmethestock/backend

# 백업 파일 목록 확인
ls -lth .env.backup* | head -10

# 특정 백업으로 복원
cp .env.backup_20251119_115145 .env

# 서비스 재시작
sudo systemctl restart stock-finder-backend
```

### 6. .env 변경 이력 확인

```bash
cd /home/ubuntu/showmethestock/backend

# 백업 파일 목록 (시간순)
ls -lth .env* | head -10

# 특정 변수의 변경 이력 확인
for f in .env.backup*; do
    echo "=== $f ==="
    grep "^GAP_MAX" "$f" 2>/dev/null || echo "없음"
done

# 파일 수정 시간 확인
stat .env | grep -E "Modify|Change"
```

### 7. .env 파일 검증

#### 7.1 중복 변수 확인

```bash
cd /home/ubuntu/showmethestock/backend

# 중복된 변수 찾기
cat .env | grep -v "^#" | grep -v "^$" | cut -d'=' -f1 | sort | uniq -d

# 특정 변수의 중복 확인
grep -n "^GAP_MAX" .env
```

#### 7.2 필수 변수 확인

```bash
cd /home/ubuntu/showmethestock/backend

# 필수 변수 목록
REQUIRED_VARS=(
    "DATABASE_URL"
    "DB_ENGINE"
    "KIWOOM_APP_KEY"
    "KIWOOM_APP_SECRET"
    "JWT_SECRET_KEY"
)

# 필수 변수 존재 여부 확인
for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${var}=" .env; then
        echo "✅ $var 존재"
    else
        echo "❌ $var 없음"
    fi
done
```

### 8. .env 파일 관리 규칙

#### 8.1 변경 전 필수 사항

1. **항상 백업 생성**
   ```bash
   cp .env .env.backup_$(date +%Y%m%d_%H%M%S)
   ```

2. **변경 사유 주석 추가**
   ```bash
   # .env 파일에 주석 추가
   # 2025-11-19: GAP_MAX 테스트 설정 제거
   GAP_MAX=0.015
   ```

3. **변경 후 서비스 재시작**
   ```bash
   sudo systemctl restart stock-finder-backend
   ```

#### 8.2 테스트 설정 관리

- 테스트용 설정은 사용 후 즉시 제거
- 테스트 설정에는 명확한 주석 추가
- 예: `# 9월 4일자 테스트를 위한 갭/이격 조건 완화` (사용 후 제거)

#### 8.3 중복 변수 방지

- 동일한 변수가 여러 번 정의되면 마지막 값이 적용됨
- 변경 전 중복 확인 필수
- 예: `GAP_MAX=0.015`와 `GAP_MAX=0.0500`이 동시에 있으면 `0.0500`이 적용됨

### 9. .env 파일 문제 해결

#### 9.1 서비스 시작 실패

```bash
# .env 파일 문법 오류 확인
cd /home/ubuntu/showmethestock/backend

# 빈 줄이나 특수문자 확인
cat -A .env | grep -E "^[^#].*[^=]$"

# systemd 로그에서 .env 관련 오류 확인
sudo journalctl -u stock-finder-backend | grep -i "env\|invalid"
```

#### 9.2 변수 값이 적용되지 않을 때

```bash
# 1. .env 파일 확인
cat .env | grep "GAP_MAX"

# 2. 중복 변수 확인
grep -n "^GAP_MAX" .env

# 3. 서비스 재시작
sudo systemctl restart stock-finder-backend

# 4. 환경 변수 로드 확인
cd /home/ubuntu/showmethestock/backend
source venv/bin/activate
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GAP_MAX'))"
```

#### 9.3 백업 파일 정리

```bash
cd /home/ubuntu/showmethestock/backend

# 30일 이상 된 백업 파일 삭제
find . -name ".env.backup*" -mtime +30 -delete

# 또는 특정 개수만 유지
ls -t .env.backup* | tail -n +11 | xargs rm -f
```

### 10. .env 파일 예시

#### 10.1 백엔드 .env 주요 변수

```bash
# 데이터베이스
DB_ENGINE=postgres
DATABASE_URL=postgresql://stockfinder:stockfinder_pass@localhost/stockfinder

# 키움 API
KIWOOM_APP_KEY=your_app_key
KIWOOM_APP_SECRET=your_app_secret

# JWT
JWT_SECRET_KEY=your_jwt_secret

# 스캔 설정
MIN_SIGNALS=3
GAP_MAX=0.015
RSI_THRESHOLD=58
VOL_MA5_MULT=2.5

# 스캐너 버전 선택
SCANNER_VERSION=v1
SCANNER_V2_ENABLED=false
```

#### 10.2 프론트엔드 .env.local 주요 변수

```bash
NEXT_PUBLIC_BACKEND_URL=http://52.79.145.238:8010
NEXT_PUBLIC_KAKAO_CLIENT_ID=your_kakao_client_id
```

### 11. 주의사항

1. **Git에 커밋하지 않기**: `.env`는 `.gitignore`에 포함되어 있지만, 실수로 커밋하지 않도록 주의
2. **민감한 정보 보호**: API 키, 비밀번호 등은 절대 공개하지 않기
3. **로컬과 서버 독립 관리**: 로컬 `.env`와 서버 `.env`는 서로 독립적으로 관리됨
4. **배포 시 변경 안 됨**: `git pull` 시 `.env` 파일은 자동으로 변경되지 않음
5. **변경 후 재시작**: `.env` 변경 후 반드시 서비스 재시작 필요

---

## 서비스 관리

### 백엔드 서비스 파일

**위치**: `/etc/systemd/system/stock-finder-backend.service`

```ini
[Unit]
Description=Stock Finder Backend (FastAPI)
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/showmethestock/backend
Environment="PATH=/home/ubuntu/showmethestock/backend/venv/bin"
EnvironmentFile=/home/ubuntu/showmethestock/backend/.env
ExecStart=/home/ubuntu/showmethestock/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 프론트엔드 서비스 파일

**위치**: `/etc/systemd/system/stock-finder-frontend.service`

```ini
[Unit]
Description=Stock Finder Frontend (Next.js)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/showmethestock/frontend
Environment="PATH=/usr/bin:/usr/local/bin"
Environment="NODE_ENV=production"
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 서비스 명령어

```bash
# 서비스 시작
sudo systemctl start stock-finder-backend
sudo systemctl start stock-finder-frontend

# 서비스 중지
sudo systemctl stop stock-finder-backend
sudo systemctl stop stock-finder-frontend

# 서비스 재시작
sudo systemctl restart stock-finder-backend
sudo systemctl restart stock-finder-frontend

# 서비스 상태 확인
sudo systemctl status stock-finder-backend
sudo systemctl status stock-finder-frontend

# 서비스 자동 시작 설정
sudo systemctl enable stock-finder-backend
sudo systemctl enable stock-finder-frontend

# 서비스 자동 시작 해제
sudo systemctl disable stock-finder-backend
sudo systemctl disable stock-finder-frontend

# 서비스 설정 파일 수정 후 reload
sudo systemctl daemon-reload
```

---

## 데이터베이스 백업

### 1. 수동 백업

```bash
# 백업 디렉토리 생성
mkdir -p /home/ubuntu/showmethestock/backups/postgres

# 전체 데이터베이스 백업
sudo -u postgres pg_dump stockfinder > /home/ubuntu/showmethestock/backups/postgres/stockfinder_$(date +%Y%m%d_%H%M%S).sql

# 압축 백업
sudo -u postgres pg_dump stockfinder | gzip > /home/ubuntu/showmethestock/backups/postgres/stockfinder_$(date +%Y%m%d_%H%M%S).sql.gz

# 특정 테이블만 백업
sudo -u postgres pg_dump stockfinder -t users -t scan_rank > /home/ubuntu/showmethestock/backups/postgres/critical_tables_$(date +%Y%m%d_%H%M%S).sql
```

### 2. 자동 백업 스크립트

**파일**: `/home/ubuntu/showmethestock/scripts/backup_db.sh`

```bash
#!/bin/bash

# 백업 설정
BACKUP_DIR="/home/ubuntu/showmethestock/backups/postgres"
DB_NAME="stockfinder"
RETENTION_DAYS=7

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# 백업 파일명 (날짜 포함)
BACKUP_FILE="$BACKUP_DIR/stockfinder_$(date +%Y%m%d_%H%M%S).sql.gz"

# 백업 실행
echo "$(date): 백업 시작..."
sudo -u postgres pg_dump $DB_NAME | gzip > $BACKUP_FILE

# 백업 성공 확인
if [ $? -eq 0 ]; then
    echo "$(date): 백업 완료 - $BACKUP_FILE"
    
    # 오래된 백업 삭제 (7일 이상)
    find $BACKUP_DIR -name "stockfinder_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo "$(date): 오래된 백업 정리 완료"
else
    echo "$(date): 백업 실패!"
    exit 1
fi
```

### 3. Cron 설정 (자동 백업)

```bash
# crontab 편집
crontab -e

# 매일 새벽 2시에 백업 실행
0 2 * * * /home/ubuntu/showmethestock/scripts/backup_db.sh >> /home/ubuntu/showmethestock/backups/backup.log 2>&1

# 매주 일요일 새벽 3시에 백업 실행
0 3 * * 0 /home/ubuntu/showmethestock/scripts/backup_db.sh >> /home/ubuntu/showmethestock/backups/backup.log 2>&1
```

### 4. 백업 복원

```bash
# 압축된 백업 복원
gunzip < /home/ubuntu/showmethestock/backups/postgres/stockfinder_20251109_020000.sql.gz | sudo -u postgres psql stockfinder

# 일반 백업 복원
sudo -u postgres psql stockfinder < /home/ubuntu/showmethestock/backups/postgres/stockfinder_20251109_020000.sql

# 데이터베이스 재생성 후 복원
sudo -u postgres psql -c "DROP DATABASE IF EXISTS stockfinder;"
sudo -u postgres psql -c "CREATE DATABASE stockfinder;"
gunzip < backup.sql.gz | sudo -u postgres psql stockfinder
```

---

## 모니터링 및 로그

### 1. 시스템 리소스 모니터링

```bash
# CPU 및 메모리 사용량
top
htop  # 설치: sudo apt install htop

# 디스크 사용량
df -h

# 특정 디렉토리 크기
du -sh /home/ubuntu/showmethestock/*

# 네트워크 연결 상태
netstat -tulpn | grep -E '8000|3000|5432'

# 프로세스 확인
ps aux | grep -E 'uvicorn|node|postgres'
```

### 2. 백엔드 로그

```bash
# systemd 로그 (실시간)
sudo journalctl -u stock-finder-backend -f

# systemd 로그 (최근 100줄)
sudo journalctl -u stock-finder-backend -n 100

# systemd 로그 (특정 날짜)
sudo journalctl -u stock-finder-backend --since "2025-11-09 00:00:00"

# 애플리케이션 로그 (있다면)
tail -f /home/ubuntu/showmethestock/backend/logs/app.log
```

### 3. 프론트엔드 로그

```bash
# systemd 로그
sudo journalctl -u stock-finder-frontend -f

# PM2 로그 (PM2 사용 시)
pm2 logs stock-finder-frontend

# Next.js 빌드 로그
cat /home/ubuntu/showmethestock/frontend/.next/build.log
```

### 4. PostgreSQL 로그

```bash
# PostgreSQL 로그 위치
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# 느린 쿼리 확인
sudo grep "duration:" /var/log/postgresql/postgresql-16-main.log | tail -20

# 에러 로그만 확인
sudo grep "ERROR" /var/log/postgresql/postgresql-16-main.log | tail -20
```

### 5. Nginx 로그 (Nginx 사용 시)

```bash
# 액세스 로그
sudo tail -f /var/log/nginx/access.log

# 에러 로그
sudo tail -f /var/log/nginx/error.log

# 특정 IP 필터링
sudo grep "52.79.145.238" /var/log/nginx/access.log
```

---

## 문제 해결

### 1. 백엔드가 시작되지 않을 때

```bash
# 1. 서비스 상태 확인
sudo systemctl status stock-finder-backend

# 2. 로그 확인
sudo journalctl -u stock-finder-backend -n 50

# 3. 수동 실행으로 에러 확인
cd /home/ubuntu/showmethestock/backend
source venv/bin/activate
python main.py

# 4. 포트 충돌 확인
sudo lsof -i :8000

# 5. 환경 변수 확인
cat .env | grep -E "DB_ENGINE|DATABASE_URL"

# 6. PostgreSQL 연결 테스트
psql -U stockfinder -d stockfinder -c "SELECT 1;"
```

### 2. 프론트엔드가 시작되지 않을 때

```bash
# 1. 서비스 상태 확인
sudo systemctl status stock-finder-frontend

# 2. 로그 확인
sudo journalctl -u stock-finder-frontend -n 50

# 3. 수동 실행으로 에러 확인
cd /home/ubuntu/showmethestock/frontend
npm run build
npm start

# 4. 포트 충돌 확인
sudo lsof -i :3000

# 5. 빌드 파일 확인
ls -la .next/

# 6. 재빌드
rm -rf .next
npm run build
```

### 3. PostgreSQL 연결 오류

```bash
# 1. PostgreSQL 서비스 상태
sudo systemctl status postgresql

# 2. PostgreSQL 재시작
sudo systemctl restart postgresql

# 3. 연결 테스트
psql -U stockfinder -d stockfinder -c "SELECT version();"

# 4. pg_hba.conf 확인 (인증 설정)
sudo cat /etc/postgresql/16/main/pg_hba.conf | grep -v "^#"

# 5. postgresql.conf 확인 (연결 설정)
sudo grep "listen_addresses" /etc/postgresql/16/main/postgresql.conf
sudo grep "port" /etc/postgresql/16/main/postgresql.conf

# 6. 로그 확인
sudo tail -50 /var/log/postgresql/postgresql-16-main.log
```

### 4. 디스크 공간 부족

```bash
# 1. 디스크 사용량 확인
df -h

# 2. 큰 파일/디렉토리 찾기
sudo du -sh /home/ubuntu/showmethestock/* | sort -h
sudo du -sh /var/log/* | sort -h

# 3. 오래된 로그 삭제
sudo journalctl --vacuum-time=7d

# 4. 오래된 백업 삭제
find /home/ubuntu/showmethestock/backups -mtime +30 -delete

# 5. 패키지 캐시 정리
sudo apt clean
sudo apt autoremove

# 6. Docker 정리 (사용 시)
docker system prune -a
```

### 5. 메모리 부족

```bash
# 1. 메모리 사용량 확인
free -h

# 2. 프로세스별 메모리 사용량
ps aux --sort=-%mem | head -10

# 3. 스왑 설정 확인
swapon --show

# 4. 스왑 생성 (없다면)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 5. PostgreSQL 메모리 설정 조정
sudo nano /etc/postgresql/16/main/postgresql.conf
# shared_buffers를 줄이기 (예: 256MB → 128MB)

# 6. 서비스 재시작
sudo systemctl restart postgresql
sudo systemctl restart stock-finder-backend
```

### 6. 스케줄러 작동 확인

```bash
# 1. 백엔드 로그에서 스케줄러 확인
sudo journalctl -u stock-finder-backend | grep "스케줄러"

# 2. 검증 데이터 확인
psql -U stockfinder -d stockfinder -c "
SELECT analysis_date, analysis_time, data_available, data_complete 
FROM market_analysis_validation 
ORDER BY analysis_date DESC, analysis_time DESC 
LIMIT 10;
"

# 3. 장세 분석 데이터 확인
psql -U stockfinder -d stockfinder -c "
SELECT date, market_sentiment, kospi_return 
FROM market_conditions 
ORDER BY date DESC 
LIMIT 5;
"

# 4. 스캔 데이터 확인
psql -U stockfinder -d stockfinder -c "
SELECT DISTINCT date 
FROM scan_rank 
ORDER BY date DESC 
LIMIT 5;
"
```

---

## 긴급 대응

### 1. 서비스 전체 재시작

```bash
# 순서대로 재시작
sudo systemctl restart postgresql
sleep 5
sudo systemctl restart stock-finder-backend
sleep 5
sudo systemctl restart stock-finder-frontend

# 상태 확인
sudo systemctl status postgresql
sudo systemctl status stock-finder-backend
sudo systemctl status stock-finder-frontend
```

### 2. 데이터베이스 긴급 복구

```bash
# 1. 최신 백업 확인
ls -lht /home/ubuntu/showmethestock/backups/postgres/ | head -5

# 2. 현재 DB 백업 (안전장치)
sudo -u postgres pg_dump stockfinder > /tmp/stockfinder_emergency_$(date +%Y%m%d_%H%M%S).sql

# 3. 데이터베이스 재생성
sudo -u postgres psql -c "DROP DATABASE stockfinder;"
sudo -u postgres psql -c "CREATE DATABASE stockfinder OWNER stockfinder;"

# 4. 최신 백업 복원
gunzip < /home/ubuntu/showmethestock/backups/postgres/stockfinder_YYYYMMDD_HHMMSS.sql.gz | sudo -u postgres psql stockfinder

# 5. 권한 재설정
sudo -u postgres psql -d stockfinder -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stockfinder;"
sudo -u postgres psql -d stockfinder -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stockfinder;"

# 6. 서비스 재시작
sudo systemctl restart stock-finder-backend
```

### 3. 롤백 (이전 버전으로 복구)

```bash
# 1. 현재 상태 백업
cd /home/ubuntu/showmethestock
git stash
sudo -u postgres pg_dump stockfinder > /tmp/stockfinder_before_rollback_$(date +%Y%m%d_%H%M%S).sql

# 2. 이전 커밋으로 롤백
git log --oneline -10  # 롤백할 커밋 확인
git reset --hard <commit-hash>

# 3. 백엔드 재배포
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart stock-finder-backend

# 4. 프론트엔드 재배포
cd ../frontend
npm install
npm run build
sudo systemctl restart stock-finder-frontend

# 5. 동작 확인
curl http://localhost:8000/health
curl http://localhost:3000
```

### 4. 긴급 연락처 및 체크리스트

**긴급 상황 발생 시 체크리스트**:
1. [ ] 서비스 상태 확인 (`systemctl status`)
2. [ ] 로그 확인 (`journalctl -u`)
3. [ ] 리소스 확인 (`top`, `df -h`)
4. [ ] 데이터베이스 연결 확인 (`psql`)
5. [ ] 백업 존재 확인 (`ls backups/`)
6. [ ] 서비스 재시작 시도
7. [ ] 롤백 고려
8. [ ] 관리자에게 보고

---

## 정기 점검 항목

### 일일 점검
- [ ] 서비스 상태 확인
- [ ] 디스크 사용량 확인
- [ ] 에러 로그 확인
- [ ] 스캔 데이터 생성 확인

### 주간 점검
- [ ] 백업 파일 확인
- [ ] 데이터베이스 크기 확인
- [ ] 시스템 업데이트 확인
- [ ] 로그 파일 정리

### 월간 점검
- [ ] 보안 패치 적용
- [ ] 데이터베이스 최적화 (VACUUM)
- [ ] 백업 복원 테스트
- [ ] 성능 모니터링 리뷰

---

## 유용한 스크립트

### 1. 서비스 상태 확인 스크립트

**파일**: `/home/ubuntu/showmethestock/scripts/check_services.sh`

```bash
#!/bin/bash

echo "========================================="
echo "Stock Finder 서비스 상태 확인"
echo "========================================="
echo ""

echo "1. PostgreSQL 상태:"
sudo systemctl is-active postgresql && echo "✅ 실행 중" || echo "❌ 중지됨"
echo ""

echo "2. 백엔드 상태:"
sudo systemctl is-active stock-finder-backend && echo "✅ 실행 중" || echo "❌ 중지됨"
curl -s http://localhost:8000/health > /dev/null && echo "✅ API 응답 정상" || echo "❌ API 응답 없음"
echo ""

echo "3. 프론트엔드 상태:"
sudo systemctl is-active stock-finder-frontend && echo "✅ 실행 중" || echo "❌ 중지됨"
curl -s http://localhost:3000 > /dev/null && echo "✅ 웹 응답 정상" || echo "❌ 웹 응답 없음"
echo ""

echo "4. 디스크 사용량:"
df -h / | tail -1
echo ""

echo "5. 메모리 사용량:"
free -h | grep Mem
echo ""

echo "========================================="
```

### 2. 빠른 배포 스크립트

**파일**: `/home/ubuntu/showmethestock/scripts/quick_deploy.sh`

```bash
#!/bin/bash

set -e  # 에러 발생 시 중단

echo "========================================="
echo "Stock Finder 빠른 배포"
echo "========================================="

# 1. 코드 업데이트
echo "1. 코드 업데이트 중..."
cd /home/ubuntu/showmethestock
git pull origin main

# 2. 백엔드 배포
echo "2. 백엔드 배포 중..."
cd backend
source venv/bin/activate
pip install -r requirements.txt --quiet
sudo systemctl restart stock-finder-backend
echo "✅ 백엔드 재시작 완료"

# 3. 프론트엔드 배포
echo "3. 프론트엔드 배포 중..."
cd ../frontend
npm install --silent
npm run build
sudo systemctl restart stock-finder-frontend
echo "✅ 프론트엔드 재시작 완료"

# 4. 동작 확인
echo "4. 동작 확인 중..."
sleep 5
curl -s http://localhost:8000/health > /dev/null && echo "✅ 백엔드 정상" || echo "❌ 백엔드 오류"
curl -s http://localhost:3000 > /dev/null && echo "✅ 프론트엔드 정상" || echo "❌ 프론트엔드 오류"

echo "========================================="
echo "배포 완료!"
echo "========================================="
```

---

## 참고 문서

- **로컬 환경 구성**: `LOCAL_SETUP_MANUAL_20251109.md`
- **테스트 리포트**: `backend/tests/TEST_REPORT.md`
- **코드 리뷰 이슈**: `CODE_REVIEW_ISSUES.md`
- **DB 관리 가이드**: `DB_MANAGEMENT.md`

---

## 문의 및 지원

- **긴급 연락**: [관리자 연락처]
- **이슈 등록**: GitHub Issues
- **문서 업데이트**: 2025-11-09
- **작성자**: AI Assistant
- **검토자**: 운영팀

---

**마지막 업데이트**: 2025년 11월 19일

