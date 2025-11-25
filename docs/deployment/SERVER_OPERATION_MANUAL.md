# 서버 작업 메뉴얼 (2025-11-24)

이 문서는 `manuals/SERVER_DEPLOYMENT_MANUAL_20251109.md`의 최신화 버전입니다.

## 📋 목차

1. [서버 정보](#서버-정보)
2. [서버 접속](#서버-접속)
3. [PostgreSQL 관리](#postgresql-관리)
4. [백엔드 배포](#백엔드-배포)
5. [프론트엔드 배포](#프론트엔드-배포)
6. [환경 변수(.env) 관리](#환경-변수env-관리)
7. [데이터베이스 마이그레이션](#데이터베이스-마이그레이션)
8. [서비스 관리](#서비스-관리)
9. [데이터베이스 백업](#데이터베이스-백업)
10. [모니터링 및 로그](#모니터링-및-로그)
11. [문제 해결](#문제-해결)
12. [긴급 대응](#긴급-대응)

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

### 주요 디렉토리
```
/home/ubuntu/showmethestock/
├── backend/              # 백엔드 소스
│   ├── venv/            # Python 가상환경
│   ├── main.py          # FastAPI 앱
│   ├── .env             # 환경 변수 (Git 추적 안 됨)
│   ├── sql/             # SQL 마이그레이션 스크립트
│   └── logs/            # 로그 파일
├── frontend/            # 프론트엔드 소스
│   ├── .next/          # Next.js 빌드
│   └── .env.local      # 환경 변수 (Git 추적 안 됨)
└── backups/            # DB 백업
    └── postgres/       # PostgreSQL 백업
```

### 서비스 포트
- **백엔드 (FastAPI)**: 8010
- **프론트엔드 (Next.js)**: 3000
- **Nginx**: 80, 443
- **PostgreSQL**: 5432 (localhost only)

---

## 서버 접속

### SSH 접속

```bash
# SSH config 사용 (권장)
ssh stock-finder

# 직접 키 파일 지정
ssh -i ~/.ssh/id_rsa ubuntu@52.79.145.238
```

### 초기 설정 확인

```bash
# 서버 접속 후
cd /home/ubuntu/showmethestock

# Git 저장소 상태 확인
git status
git log --oneline -5

# 실행 중인 서비스 확인
sudo systemctl status stock-finder-backend
sudo systemctl status stock-finder-frontend
```

---

## PostgreSQL 관리

### 1. PostgreSQL 접속

```bash
# postgres 사용자로 접속
sudo -u postgres psql

# stockfinder 데이터베이스 접속
sudo -u postgres psql -d stockfinder
```

### 2. 데이터베이스 상태 확인

```bash
# PostgreSQL 서비스 상태
sudo systemctl status postgresql

# 데이터베이스 목록
sudo -u postgres psql -c "\l"

# 테이블 목록
sudo -u postgres psql -d stockfinder -c "\dt"

# 주요 테이블 확인
sudo -u postgres psql -d stockfinder -c "\d scan_rank"
sudo -u postgres psql -d stockfinder -c "\d scanner_settings"
```

### 3. 데이터베이스 작업

#### 데이터 조회

```bash
# 최근 스캔 결과 조회
sudo -u postgres psql -d stockfinder -c "
SELECT date, code, name, score, scanner_version 
FROM scan_rank 
ORDER BY date DESC, score DESC 
LIMIT 10;
"

# 특정 날짜 스캔 결과
sudo -u postgres psql -d stockfinder -c "
SELECT * FROM scan_rank 
WHERE date = '2025-11-24' 
ORDER BY score DESC;
"

# Scanner 설정 확인
sudo -u postgres psql -d stockfinder -c "SELECT * FROM scanner_settings;"

# 사용자 수 확인
sudo -u postgres psql -d stockfinder -c "SELECT COUNT(*) FROM users;"
```

#### 데이터 수정

```bash
# Scanner 버전 변경
sudo -u postgres psql -d stockfinder -c "
UPDATE scanner_settings 
SET setting_value = 'v2', updated_at = NOW() 
WHERE setting_key = 'scanner_version';
"

# Scanner V2 활성화
sudo -u postgres psql -d stockfinder -c "
UPDATE scanner_settings 
SET setting_value = 'true', updated_at = NOW() 
WHERE setting_key = 'scanner_v2_enabled';
"
```

#### 데이터 삭제

```bash
# 특정 날짜 스캔 결과 삭제
sudo -u postgres psql -d stockfinder -c "
DELETE FROM scan_rank WHERE date = '2025-11-24';
"

# 특정 종목 스캔 결과 삭제
sudo -u postgres psql -d stockfinder -c "
DELETE FROM scan_rank WHERE code = '005930';
"
```

#### 통계 조회

```bash
# 날짜별 스캔 결과 개수
sudo -u postgres psql -d stockfinder -c "
SELECT date, COUNT(*) as count, scanner_version
FROM scan_rank
GROUP BY date, scanner_version
ORDER BY date DESC
LIMIT 10;
"

# 테이블 크기 확인
sudo -u postgres psql -d stockfinder -c "
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC;
"
```

### 4. 대화형 psql 사용

```bash
# PostgreSQL 대화형 모드 접속
sudo -u postgres psql -d stockfinder

# 대화형 모드에서 사용 가능한 명령어:
# \dt          - 테이블 목록
# \d table     - 테이블 구조
# \l           - 데이터베이스 목록
# \q           - 종료
# \?           - 도움말
# \h SELECT    - SQL 명령어 도움말
```

---

## 백엔드 배포

### 1. 코드 업데이트

```bash
# 서버 접속
ssh stock-finder

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

**중요**: `.env` 파일은 Git에 추적되지 않으므로 배포 시 자동으로 변경되지 않습니다.

```bash
cd /home/ubuntu/showmethestock/backend

# .env 파일 확인
cat .env | grep -E "DB_ENGINE|DATABASE_URL|KIWOOM|SCANNER_VERSION"

# 필수 환경 변수:
# DB_ENGINE=postgres
# DATABASE_URL=postgresql://stockfinder:stockfinder_pass@localhost/stockfinder
# KIWOOM_APP_KEY=...
# KIWOOM_APP_SECRET=...
# JWT_SECRET_KEY=...
# SCANNER_VERSION=v1 (DB 우선, 없으면 .env 사용)
```

### 3. Python 패키지 업데이트

```bash
cd /home/ubuntu/showmethestock/backend

# 가상환경 활성화
source venv/bin/activate

# 패키지 업데이트
pip install -r requirements.txt --quiet

# PostgreSQL 관련 패키지 확인
pip list | grep psycopg
```

### 4. 백엔드 서비스 재시작

```bash
# 서비스 재시작
sudo systemctl restart stock-finder-backend

# 서비스 상태 확인
sudo systemctl status stock-finder-backend

# 로그 확인 (실시간)
sudo journalctl -u stock-finder-backend -f
```

### 5. 백엔드 동작 확인

```bash
# Health check
curl http://localhost:8010/health

# 스캐너 설정 확인 (관리자 토큰 필요)
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     http://localhost:8010/admin/scanner-settings | jq '.'

# 최신 스캔 데이터 확인
curl http://localhost:8010/latest-scan | jq '.ok'
```

---

## 프론트엔드 배포

### 1. 코드 업데이트

```bash
# 프로젝트 디렉토리 (이미 git pull 했다면 생략)
cd /home/ubuntu/showmethestock
git pull origin main
```

### 2. 환경 변수 확인

```bash
cd /home/ubuntu/showmethestock/frontend

# .env.local 파일 확인
cat .env.local

# 필수 환경 변수:
# NEXT_PUBLIC_BACKEND_URL=http://52.79.145.238:8010
```

### 3. 패키지 업데이트 및 빌드

```bash
cd /home/ubuntu/showmethestock/frontend

# 패키지 업데이트
npm install

# 프로덕션 빌드
npm run build

# 빌드 결과 확인
ls -la .next/
```

### 4. 프론트엔드 서비스 재시작

```bash
# 서비스 재시작
sudo systemctl restart stock-finder-frontend

# 서비스 상태 확인
sudo systemctl status stock-finder-frontend
```

---

## 환경 변수(.env) 관리

### 중요 사항

1. **Git 추적 안 됨**: `.env` 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다.
2. **배포 시 변경 안 됨**: `git pull` 시 `.env` 파일은 자동으로 변경되지 않습니다.
3. **로컬과 서버 독립**: 로컬 `.env`와 서버 `.env`는 서로 독립적으로 관리됩니다.
4. **변경 후 재시작 필수**: `.env` 변경 후 반드시 서비스 재시작이 필요합니다.

### .env 파일 확인

```bash
cd /home/ubuntu/showmethestock/backend

# 전체 확인
cat .env

# 특정 변수만 확인
cat .env | grep -E "GAP_MAX|MIN_SIGNALS|DATABASE_URL|SCANNER_VERSION"
```

### .env 파일 수정

```bash
# 백엔드 .env 편집
cd /home/ubuntu/showmethestock/backend
nano .env  # 또는 vi, vim

# 수정 후 서비스 재시작 필수
sudo systemctl restart stock-finder-backend
```

### .env 파일 백업

```bash
cd /home/ubuntu/showmethestock/backend

# 백업 생성 (타임스탬프 포함)
cp .env .env.backup_$(date +%Y%m%d_%H%M%S)

# 백업 파일 목록 확인
ls -lth .env.backup* | head -10
```

### 스캐너 버전 관리

**중요**: 스캐너 버전은 **DB에서 우선 관리**됩니다 (`scanner_settings` 테이블).

- DB에 설정이 있으면 DB 값 사용
- DB에 없으면 `.env`의 `SCANNER_VERSION` 사용
- 둘 다 없으면 기본값 `v1` 사용

```bash
# DB에서 스캐너 버전 확인
sudo -u postgres psql stockfinder -c "SELECT * FROM scanner_settings;"

# 관리자 API로 변경 (권장)
curl -X POST \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"scanner_version": "v2", "scanner_v2_enabled": true}' \
     http://localhost:8010/admin/scanner-settings
```

---

## 데이터베이스 마이그레이션

### 주요 테이블

1. **scanner_settings**: 스캐너 버전 및 설정 관리
2. **scan_rank**: 스캔 결과 저장 (scanner_version 컬럼 포함)

### 마이그레이션 실행

```bash
cd /home/ubuntu/showmethestock/backend

# 1. scanner_settings 테이블 생성
sudo -u postgres psql stockfinder -f sql/add_scanner_settings.sql

# 2. scan_rank 테이블에 scanner_version 컬럼 추가
sudo -u postgres psql stockfinder -f sql/add_scanner_version_to_scan_rank.sql

# 마이그레이션 확인
sudo -u postgres psql stockfinder -c "\dt scanner_settings"
sudo -u postgres psql stockfinder -c "\d scan_rank" | grep scanner_version
```

### 마이그레이션 롤백

```bash
# scanner_settings 테이블 삭제 (필요한 경우만)
sudo -u postgres psql stockfinder -c "DROP TABLE IF EXISTS scanner_settings;"

# scanner_version 컬럼 제거 (복잡하므로 주의)
# 기존 데이터 백업 필수
```

---

## 서비스 관리

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
```

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
ExecStart=/home/ubuntu/showmethestock/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8010
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**주의**: 포트는 8010입니다.

---

## 데이터베이스 백업

### 수동 백업

```bash
# 백업 디렉토리 생성
mkdir -p /home/ubuntu/showmethestock/backups/postgres

# 전체 데이터베이스 백업
sudo -u postgres pg_dump stockfinder > /home/ubuntu/showmethestock/backups/postgres/stockfinder_$(date +%Y%m%d_%H%M%S).sql

# 압축 백업
sudo -u postgres pg_dump stockfinder | gzip > /home/ubuntu/showmethestock/backups/postgres/stockfinder_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 백업 복원

```bash
# 압축된 백업 복원
gunzip < /home/ubuntu/showmethestock/backups/postgres/stockfinder_20251124_020000.sql.gz | sudo -u postgres psql stockfinder

# 일반 백업 복원
sudo -u postgres psql stockfinder < /home/ubuntu/showmethestock/backups/postgres/stockfinder_20251124_020000.sql
```

---

## 모니터링 및 로그

### 백엔드 로그

```bash
# systemd 로그 (실시간)
sudo journalctl -u stock-finder-backend -f

# systemd 로그 (최근 100줄)
sudo journalctl -u stock-finder-backend -n 100

# systemd 로그 (특정 날짜)
sudo journalctl -u stock-finder-backend --since "2025-11-24 00:00:00"
```

### 프론트엔드 로그

```bash
# systemd 로그
sudo journalctl -u stock-finder-frontend -f
```

### PostgreSQL 로그

```bash
# PostgreSQL 로그 위치
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# 에러 로그만 확인
sudo grep "ERROR" /var/log/postgresql/postgresql-16-main.log | tail -20
```

---

## 문제 해결

### 백엔드가 시작되지 않을 때

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
sudo lsof -i :8010

# 5. 환경 변수 확인
cat .env | grep -E "DB_ENGINE|DATABASE_URL"

# 6. PostgreSQL 연결 테스트
psql -U stockfinder -d stockfinder -c "SELECT 1;"

# 7. 스캐너 설정 테이블 확인
sudo -u postgres psql stockfinder -c "SELECT * FROM scanner_settings;"
```

### PostgreSQL 연결 오류

```bash
# 1. PostgreSQL 서비스 상태
sudo systemctl status postgresql

# 2. PostgreSQL 재시작
sudo systemctl restart postgresql

# 3. 연결 테스트
psql -U stockfinder -d stockfinder -c "SELECT version();"
```

---

## 긴급 대응

### 서비스 전체 재시작

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

### 롤백 (이전 버전으로 복구)

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
curl http://localhost:8010/health
curl http://localhost:3000
```

---

## 최신 변경사항 (2025-11-24)

### 주요 업데이트

1. **백엔드 포트**: 8000 → 8010
2. **Scanner V2**: DB 기반 설정 관리 추가
3. **scan_rank 테이블**: `scanner_version` 컬럼 추가 (V1/V2 결과 분리 저장)
4. **scanner_settings 테이블**: 스캐너 버전 DB 관리
5. **날짜 처리 개선**: DATE/TIMESTAMP 타입 통일
6. **OHLCV 캐싱**: 애프터마켓 시간대 고려한 동적 TTL

### 배포 시 주의사항

1. **DB 마이그레이션 필수**:
   - `scanner_settings` 테이블 생성
   - `scan_rank` 테이블에 `scanner_version` 컬럼 추가

2. **.env 파일 관리**:
   - 배포 시 `.env` 파일은 자동으로 변경되지 않음
   - 스캐너 버전은 DB에서 관리 (`.env`는 fallback)

3. **포트 확인**:
   - 백엔드: 8010 (8000 아님)
   - 프론트엔드: 3000

---

## 관련 문서

- **상세 배포 메뉴얼**: `manuals/SERVER_DEPLOYMENT_MANUAL_20251109.md`
- **Scanner V2 배포 체크리스트**: `docs/deployment/DEPLOYMENT_CHECKLIST_SCANNER_V2.md`
- **Scanner V2 사용 가이드**: `docs/scanner-v2/SCANNER_V2_USAGE.md`
- **데이터베이스 스키마**: `docs/database/`

---

**마지막 업데이트**: 2025년 11월 24일

