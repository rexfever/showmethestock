# 로컬 개발 환경 구성 메뉴얼

**최종 업데이트**: 2025-11-24

## 📋 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [PostgreSQL 설치](#postgresql-설치)
3. [Python 환경 설정](#python-환경-설정)
4. [프로젝트 클론 및 설정](#프로젝트-클론-및-설정)
5. [데이터베이스 초기화](#데이터베이스-초기화)
6. [환경 변수 설정](#환경-변수-설정)
7. [백엔드 실행](#백엔드-실행)
8. [프론트엔드 실행](#프론트엔드-실행)
9. [테스트 실행](#테스트-실행)
10. [문제 해결](#문제-해결)

---

## 시스템 요구사항

### 필수 소프트웨어

- **OS**: macOS 10.14+, Ubuntu 20.04+, Windows 10+ (WSL2)
- **Python**: 3.8 이상 (권장: 3.11)
- **Node.js**: 14.x 이상 (권장: 18.x)
- **PostgreSQL**: 14 이상 (권장: 16)
- **Git**: 2.x 이상

### 권장 사양

- **RAM**: 8GB 이상
- **디스크 여유 공간**: 10GB 이상
- **인터넷 연결**: 필수 (키움 API 호출)

---

## PostgreSQL 설치

### macOS (Homebrew 사용)

```bash
# 1. Homebrew가 없다면 설치
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. PostgreSQL 16 설치
brew install postgresql@16

# 3. PostgreSQL 서비스 시작
brew services start postgresql@16

# 4. PATH 설정 (선택사항)
echo 'export PATH="/usr/local/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 5. 설치 확인
/usr/local/opt/postgresql@16/bin/psql --version
```

### Ubuntu/Debian

```bash
# 1. PostgreSQL 공식 저장소 추가
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# 2. 패키지 목록 업데이트 및 설치
sudo apt update
sudo apt install -y postgresql-16 postgresql-contrib-16

# 3. PostgreSQL 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 4. 설치 확인
psql --version
```

### Windows (WSL2 권장)

WSL2에서 Ubuntu 설치 후 위의 Ubuntu 가이드를 따르세요.

---

## Python 환경 설정

### 1. Python 버전 확인

```bash
python3 --version
# Python 3.8.0 이상이어야 함 (권장: 3.11)
```

### 2. pyenv 설치 (선택사항, 권장)

```bash
# macOS
brew install pyenv

# Ubuntu
curl https://pyenv.run | bash

# pyenv 초기화 (.zshrc 또는 .bashrc에 추가)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# Python 3.11 설치
pyenv install 3.11.0
pyenv global 3.11.0
```

### 3. pip 업그레이드

```bash
pip install --upgrade pip
```

---

## 프로젝트 클론 및 설정

### 1. Git 저장소 클론

```bash
# 작업 디렉토리로 이동
cd ~/workspace  # 또는 원하는 디렉토리

# 프로젝트 클론
git clone https://github.com/rexfever/showmethestock.git
cd showmethestock
```

### 2. 브랜치 확인

```bash
# 현재 브랜치 확인
git branch

# 최신 코드 가져오기
git pull origin main
```

---

## 데이터베이스 초기화

### 1. PostgreSQL 데이터베이스 생성

```bash
# PostgreSQL 접속 (macOS)
/usr/local/opt/postgresql@16/bin/psql postgres

# PostgreSQL 접속 (Ubuntu)
sudo -u postgres psql

# 데이터베이스 생성
CREATE DATABASE stockfinder;

# 사용자 생성 (선택사항, 기본 사용자 사용 가능)
-- CREATE USER stockfinder_user WITH PASSWORD 'your_password';
-- GRANT ALL PRIVILEGES ON DATABASE stockfinder TO stockfinder_user;

# 종료
\q
```

### 2. 스키마 생성

```bash
cd ~/workspace/showmethestock/backend

# PostgreSQL 스키마 적용 (macOS)
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -f sql/postgres_schema.sql

# PostgreSQL 스키마 적용 (Ubuntu)
psql -d stockfinder -f sql/postgres_schema.sql

# Scanner Settings 테이블 생성 (최신 기능)
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -f sql/add_scanner_settings.sql
```

### 3. 테이블 확인

```bash
# PostgreSQL 접속
/usr/local/opt/postgresql@16/bin/psql -d stockfinder

# 테이블 목록 확인
\dt

# 예상 테이블:
# - users
# - scan_rank
# - portfolio
# - subscriptions
# - payments
# - email_verifications
# - news_data
# - search_trends
# - market_conditions
# - send_logs
# - positions
# - trading_history
# - maintenance_settings
# - popup_notice
# - daily_reports
# - scanner_settings (최신 추가)

# 종료
\q
```

---

## 환경 변수 설정

### 1. 백엔드 .env 파일 생성

```bash
cd ~/workspace/showmethestock/backend

# .env 파일 생성
cat > .env << 'EOF'
# 데이터베이스 설정
DB_ENGINE=postgres
DATABASE_URL=postgresql://your_username@localhost/stockfinder

# 키움 API 설정
APP_KEY=your_kiwoom_app_key
APP_SECRET=your_kiwoom_app_secret
API_BASE=https://api.kiwoom.com
TOKEN_PATH=/oauth2/token

# JWT 설정
JWT_SECRET_KEY=your_jwt_secret_key_here_change_this_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# 스캔 파라미터 (기본값)
UNIVERSE_KOSPI=25
UNIVERSE_KOSDAQ=25
OHLCV_COUNT=220
MIN_SIGNALS=3
RSI_THRESHOLD=58
RSI_MODE=tema
MACD_OSC_MIN=0.0
GAP_MIN=0.002
GAP_MAX=0.015
EXT_FROM_TEMA20_MAX=0.015
VOL_MA5_MULT=2.5
VOL_MA20_MULT=1.2
MIN_TURNOVER_KRW=1000000000
RSI_UPPER_LIMIT=70.0
MIN_PRICE=2000
TOP_K=5

# 장세 분석 설정
MARKET_ANALYSIS_ENABLE=true
KOSPI_BULL_THRESHOLD=0.015
KOSPI_BEAR_THRESHOLD=-0.015

# Fallback 설정
FALLBACK_ENABLE=true
FALLBACK_TARGET_MIN=3
FALLBACK_TARGET_MAX=5
FALLBACK_TARGET_MIN_BULL=3
FALLBACK_TARGET_MAX_BULL=5
FALLBACK_TARGET_MIN_BEAR=2
FALLBACK_TARGET_MAX_BEAR=3

# 스캐너 버전 설정 (선택사항, DB에서 관리 가능)
SCANNER_VERSION=v1
SCANNER_V2_ENABLED=false

# 이메일 설정 (선택사항)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# AWS S3 설정 (선택사항)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-northeast-2
S3_BUCKET_NAME=your_bucket_name
EOF

# 중요: DATABASE_URL의 your_username을 실제 사용자명으로 변경
# macOS: 일반적으로 현재 로그인 사용자명
# Ubuntu: postgres 또는 생성한 사용자명
```

### 2. 프론트엔드 .env 파일 생성

```bash
cd ~/workspace/showmethestock/frontend

# .env.local 파일 생성
cat > .env.local << 'EOF'
NEXT_PUBLIC_BACKEND_URL=http://localhost:8010
EOF
```

**참고**: 백엔드 포트는 **8010**입니다 (기존 8000에서 변경됨).

---

## 백엔드 실행

### 1. Python 패키지 설치

```bash
cd ~/workspace/showmethestock/backend

# 가상환경 생성 (권장)
python3 -m venv venv

# 가상환경 활성화
# macOS/Linux:
source venv/bin/activate
# Windows (WSL):
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# PostgreSQL 관련 패키지 추가 설치 (필수)
pip install psycopg psycopg-binary psycopg-pool python-dotenv
```

### 2. requirements.txt 확인

현재 `requirements.txt`에 포함된 주요 패키지:
- `fastapi==0.104.1`
- `uvicorn==0.24.0`
- `pandas==2.1.3`
- `numpy==1.25.2`
- `requests==2.31.0`
- `python-jose[cryptography]==3.3.0`
- `passlib[bcrypt]==1.7.4`
- `python-multipart==0.0.6`
- `pydantic==2.5.0`
- `schedule==1.2.0`
- `pytz==2023.3`
- `holidays==0.34`
- `boto3==1.34.0`

**추가 설치 필요**:
```bash
pip install psycopg psycopg-binary psycopg-pool python-dotenv
```

### 3. 백엔드 서버 실행

```bash
cd ~/workspace/showmethestock/backend

# 가상환경 활성화 (아직 안했다면)
source venv/bin/activate

# uvicorn으로 실행 (개발 모드)
uvicorn main:app --reload --host 0.0.0.0 --port 8010

# 또는 백그라운드 실행
nohup uvicorn main:app --host 0.0.0.0 --port 8010 > backend.log 2>&1 &
```

**중요**: 백엔드 포트는 **8010**입니다.

### 4. 백엔드 동작 확인

```bash
# 새 터미널에서
curl http://localhost:8010/health

# 예상 응답:
# {"status":"ok","timestamp":"2025-11-24T..."}

# API 문서 확인
# 브라우저에서: http://localhost:8010/docs
```

---

## 프론트엔드 실행

### 1. Node.js 및 npm 설치 확인

```bash
node --version  # v14.x 이상 (권장: v18.x)
npm --version   # 6.x 이상
```

### 2. 패키지 설치

```bash
cd ~/workspace/showmethestock/frontend

# 패키지 설치
npm install

# 또는 yarn 사용
# yarn install
```

### 3. 개발 서버 실행

```bash
cd ~/workspace/showmethestock/frontend

# 개발 모드 실행
npm run dev

# 또는 yarn 사용
# yarn dev
```

### 4. 프론트엔드 접속

```bash
# 브라우저에서 접속
# http://localhost:3000

# 스캐너 페이지: http://localhost:3000/customer-scanner
# 관리자 페이지: http://localhost:3000/admin
```

---

## 테스트 실행

### 1. 백엔드 테스트

```bash
cd ~/workspace/showmethestock/backend

# 가상환경 활성화
source venv/bin/activate

# 전체 테스트 실행
python -m pytest tests/ -v

# 특정 테스트 실행
python -m pytest tests/test_scanner_settings.py -v
python -m pytest tests/test_ohlcv_caching.py -v
```

### 2. OHLCV 캐시 테스트

```bash
cd ~/workspace/showmethestock/backend

# 가상환경 활성화
source venv/bin/activate

# 디스크 캐시 테스트
python -m pytest tests/test_ohlcv_disk_cache.py -v
```

---

## 문제 해결

### 1. PostgreSQL 연결 오류

**증상**: `psycopg.OperationalError: connection failed`

**해결**:
```bash
# PostgreSQL 서비스 상태 확인
# macOS:
brew services list | grep postgresql

# Ubuntu:
sudo systemctl status postgresql

# 서비스 재시작
# macOS:
brew services restart postgresql@16

# Ubuntu:
sudo systemctl restart postgresql

# 연결 테스트
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -c "SELECT 1;"
```

### 2. 모듈 import 오류

**증상**: `ModuleNotFoundError: No module named 'psycopg'`

**해결**:
```bash
cd ~/workspace/showmethestock/backend
source venv/bin/activate
pip install psycopg psycopg-binary psycopg-pool python-dotenv
```

### 3. 포트 충돌 오류

**증상**: `ERROR: [Errno 48] Address already in use`

**해결**:
```bash
# 8010 포트 사용 프로세스 확인 및 종료
lsof -ti:8010 | xargs kill -9

# 3000 포트 사용 프로세스 확인 및 종료
lsof -ti:3000 | xargs kill -9
```

### 4. 키움 API 오류

**증상**: `키움 API 연결 실패`

**해결**:
- `.env` 파일의 `APP_KEY`, `APP_SECRET` 확인
- 키움증권 개발자 센터에서 API 키 발급 상태 확인
- 주말/공휴일에는 데이터 조회 불가 (정상)

### 5. 데이터베이스 스키마 오류

**증상**: `relation "table_name" does not exist`

**해결**:
```bash
cd ~/workspace/showmethestock/backend

# 스키마 재적용
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -f sql/postgres_schema.sql
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -f sql/add_scanner_settings.sql

# 테이블 확인
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -c "\dt"
```

### 6. 프론트엔드 빌드 오류

**증상**: `npm run dev` 실패

**해결**:
```bash
cd ~/workspace/showmethestock/frontend

# node_modules 삭제 및 재설치
rm -rf node_modules package-lock.json
npm install

# 캐시 정리
npm cache clean --force
npm install
```

### 7. 환경 변수 미설정

**증상**: `DATABASE_URL is not configured`

**해결**:
```bash
# .env 파일 존재 확인
ls -la ~/workspace/showmethestock/backend/.env

# 없다면 생성 (위의 "환경 변수 설정" 섹션 참조)

# .env 파일 내용 확인
cat ~/workspace/showmethestock/backend/.env | grep DATABASE_URL
```

### 8. OHLCV 캐시 디렉토리 오류

**증상**: `PermissionError: [Errno 13] Permission denied`

**해결**:
```bash
# 캐시 디렉토리 생성 및 권한 설정
cd ~/workspace/showmethestock/backend
mkdir -p cache/ohlcv
chmod 755 cache/ohlcv
```

---

## 데이터베이스 접속 및 작업

### 1. 로컬 DB 접속

#### macOS

```bash
# PostgreSQL 접속
/usr/local/opt/postgresql@16/bin/psql -d stockfinder

# 또는 postgres 사용자로 접속
/usr/local/opt/postgresql@16/bin/psql -U postgres -d stockfinder
```

#### Ubuntu/Linux

```bash
# PostgreSQL 접속
sudo -u postgres psql -d stockfinder

# 또는 직접 접속
psql -U postgres -d stockfinder
```

### 2. 기본 작업 명령어

#### 테이블 목록 확인

```sql
-- 모든 테이블 목록
\dt

-- 특정 테이블 상세 정보
\d scan_rank
\d scanner_settings
\d users
```

#### 데이터 조회

```sql
-- 사용자 수 확인
SELECT COUNT(*) FROM users;

-- 최근 스캔 결과 조회
SELECT date, code, name, score, scanner_version 
FROM scan_rank 
ORDER BY date DESC, score DESC 
LIMIT 10;

-- 특정 날짜 스캔 결과
SELECT * FROM scan_rank 
WHERE date = '2025-11-24' 
ORDER BY score DESC;

-- Scanner 설정 확인
SELECT * FROM scanner_settings;
```

#### 데이터 수정

```sql
-- Scanner 버전 변경
UPDATE scanner_settings 
SET setting_value = 'v2', updated_at = NOW() 
WHERE setting_key = 'scanner_version';

-- Scanner V2 활성화
UPDATE scanner_settings 
SET setting_value = 'true', updated_at = NOW() 
WHERE setting_key = 'scanner_v2_enabled';
```

#### 데이터 삭제

```sql
-- 특정 날짜 스캔 결과 삭제
DELETE FROM scan_rank WHERE date = '2025-11-24';

-- 특정 종목 스캔 결과 삭제
DELETE FROM scan_rank WHERE code = '005930';
```

### 3. 유용한 쿼리 예시

#### 스캔 결과 통계

```sql
-- 날짜별 스캔 결과 개수
SELECT date, COUNT(*) as count, scanner_version
FROM scan_rank
GROUP BY date, scanner_version
ORDER BY date DESC;

-- 종목별 등장 횟수
SELECT code, name, COUNT(*) as appearance_count
FROM scan_rank
GROUP BY code, name
ORDER BY appearance_count DESC
LIMIT 20;

-- 평균 점수 확인
SELECT 
    date,
    AVG(score) as avg_score,
    MAX(score) as max_score,
    MIN(score) as min_score,
    COUNT(*) as count
FROM scan_rank
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY date
ORDER BY date DESC;
```

#### 테이블 크기 확인

```sql
-- 테이블별 데이터 개수
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### 인덱스 확인

```sql
-- 테이블의 인덱스 목록
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

### 4. psql 유용한 명령어

```sql
-- 도움말
\?

-- SQL 명령어 도움말
\h SELECT
\h UPDATE
\h DELETE

-- 테이블 목록
\dt

-- 테이블 구조
\d+ scan_rank

-- 데이터베이스 목록
\l

-- 현재 데이터베이스
SELECT current_database();

-- 현재 사용자
SELECT current_user;

-- 쿼리 결과를 파일로 저장
\o /tmp/scan_results.txt
SELECT * FROM scan_rank WHERE date = '2025-11-24';
\o

-- 파일에서 SQL 실행
\i /path/to/script.sql

-- 종료
\q
```

### 5. 백업 및 복원

#### 로컬 DB 백업

```bash
# 전체 데이터베이스 백업
/usr/local/opt/postgresql@16/bin/pg_dump -d stockfinder > backup_$(date +%Y%m%d).sql

# 특정 테이블만 백업
/usr/local/opt/postgresql@16/bin/pg_dump -d stockfinder -t scan_rank > scan_rank_backup.sql

# 압축 백업
/usr/local/opt/postgresql@16/bin/pg_dump -d stockfinder | gzip > backup_$(date +%Y%m%d).sql.gz
```

#### 로컬 DB 복원

```bash
# SQL 파일로 복원
/usr/local/opt/postgresql@16/bin/psql -d stockfinder < backup_20251124.sql

# 압축 파일 복원
gunzip < backup_20251124.sql.gz | /usr/local/opt/postgresql@16/bin/psql -d stockfinder
```

---

## 추가 도구 및 팁

### 1. PostgreSQL GUI 도구

- **pgAdmin 4**: https://www.pgadmin.org/
- **DBeaver**: https://dbeaver.io/
- **Postico** (macOS): https://eggerapps.at/postico/

### 2. API 테스트 도구

- **Postman**: https://www.postman.com/
- **Insomnia**: https://insomnia.rest/
- **HTTPie**: `brew install httpie` (CLI)

### 3. 유용한 명령어

```bash
# 백엔드 로그 실시간 확인
tail -f ~/workspace/showmethestock/backend/backend.log

# PostgreSQL 쿼리 실행
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -c "SELECT COUNT(*) FROM users;"

# Git 상태 확인
cd ~/workspace/showmethestock
git status
git log --oneline -10

# 디스크 사용량 확인
du -sh ~/workspace/showmethestock

# OHLCV 캐시 크기 확인
du -sh ~/workspace/showmethestock/backend/cache/ohlcv
```

### 4. 개발 워크플로우

1. **코드 수정 전**: `git pull origin main`
2. **코드 수정**: 원하는 에디터 사용 (VS Code, PyCharm 등)
3. **테스트 실행**: `python -m pytest tests/`
4. **로컬 확인**: 백엔드/프론트엔드 실행 후 브라우저 테스트
5. **커밋**: `git add .` → `git commit -m "메시지"`
6. **푸시**: `git push origin main`

---

## 최신 기능

### 1. Scanner V2

- DB 기반 설정 관리
- 관리자 화면에서 버전 선택 가능
- V1/V2 스캔 결과 분리 저장

### 2. OHLCV 디스크 캐시

- 과거 날짜 데이터 디스크 캐싱
- 프로세스 재시작 후에도 캐시 유지
- 백테스트 시 API 호출 없이 실행 가능

### 3. 날짜 처리 개선

- PostgreSQL DATE/TIMESTAMP 타입 직접 사용
- 불필요한 문자열 변환 제거
- 타입 안정성 향상

---

## 참고 문서

- **프로젝트 README**: `README.md`
- **서버 배포 메뉴얼**: `docs/deployment/SERVER_OPERATION_MANUAL.md`
- **Scanner V2 가이드**: `docs/scanner-v2/SCANNER_V2_USAGE.md`
- **OHLCV 캐시 문서**: `docs/code-review/OHLCV_DISK_CACHE_IMPLEMENTATION.md`
- **API 문서**: `docs/API_ENDPOINTS.md`

---

## 문의 및 지원

- **이슈 등록**: GitHub Issues
- **문서 업데이트**: 2025-11-24
- **작성자**: AI Assistant
- **검토자**: 개발팀

---

**마지막 업데이트**: 2025년 11월 24일

