# 로컬 개발 환경 구성 메뉴얼 (2025-11-09)

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
- **Python**: 3.8 이상
- **Node.js**: 14.x 이상
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
python --version  # 또는 python3 --version
# Python 3.8.0 이상이어야 함
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

# Python 3.8 설치
pyenv install 3.8.0
pyenv global 3.8.0
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
git clone <repository-url> stock-finder
cd stock-finder
```

### 2. 브랜치 확인

```bash
# 현재 브랜치 확인
git branch

# 최신 코드 가져오기
git pull origin main  # 또는 master
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
cd ~/workspace/stock-finder/backend

# PostgreSQL 스키마 적용 (macOS)
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -f sql/postgres_schema.sql

# PostgreSQL 스키마 적용 (Ubuntu)
psql -d stockfinder -f sql/postgres_schema.sql

# 검증 테이블 생성
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -f sql/create_market_analysis_validation.sql
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
# - market_analysis_validation
# - send_logs
# - positions
# - trading_history
# - maintenance_settings
# - popup_notice
# - daily_reports

# 종료
\q
```

---

## 환경 변수 설정

### 1. 백엔드 .env 파일 생성

```bash
cd ~/workspace/stock-finder/backend

# .env 파일 생성
cat > .env << 'EOF'
# 데이터베이스 설정
DB_ENGINE=postgres
DATABASE_URL=postgresql://your_username@localhost/stockfinder

# 키움 API 설정
KIWOOM_APP_KEY=your_kiwoom_app_key
KIWOOM_APP_SECRET=your_kiwoom_app_secret

# JWT 설정
JWT_SECRET_KEY=your_jwt_secret_key_here_change_this_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

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

# 스캔 파라미터
MIN_SIGNALS=3
RSI_UPPER_LIMIT=58.0
VOL_MA5_MULT=1.5
GAP_MAX=0.03
EXT_FROM_TEMA20_MAX=0.05
MIN_SCORE=10.0

# 장세 분석 설정
KOSPI_BULL_THRESHOLD=0.015
KOSPI_BEAR_THRESHOLD=-0.015
MARKET_ANALYSIS_ENABLE=true

# Fallback 설정
FALLBACK_ENABLE=true
FALLBACK_TARGET_MIN=5
FALLBACK_TARGET_MAX=10

# 기타
TOP_K=10
EOF

# 중요: DATABASE_URL의 your_username을 실제 사용자명으로 변경
# macOS: 일반적으로 현재 로그인 사용자명
# Ubuntu: postgres 또는 생성한 사용자명
```

### 2. 프론트엔드 .env 파일 생성

```bash
cd ~/workspace/stock-finder/frontend

# .env.local 파일 생성
cat > .env.local << 'EOF'
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
EOF
```

---

## 백엔드 실행

### 1. Python 패키지 설치

```bash
cd ~/workspace/stock-finder/backend

# 가상환경 생성 (권장)
python -m venv venv

# 가상환경 활성화
# macOS/Linux:
source venv/bin/activate
# Windows (WSL):
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# 추가 패키지 설치 (PostgreSQL 관련)
pip install psycopg psycopg-binary psycopg-pool
```

### 2. requirements.txt 확인

```bash
# requirements.txt에 다음 패키지들이 포함되어 있어야 함:
# fastapi
# uvicorn[standard]
# python-dotenv
# python-jose[cryptography]
# passlib[bcrypt]
# python-multipart
# pydantic
# pandas
# numpy
# requests
# schedule
# psycopg
# psycopg-binary
# psycopg-pool
# boto3
# openpyxl
```

### 3. 백엔드 서버 실행

```bash
cd ~/workspace/stock-finder/backend

# 가상환경 활성화 (아직 안했다면)
source venv/bin/activate

# uvicorn으로 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 또는 백그라운드 실행
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

### 4. 백엔드 동작 확인

```bash
# 새 터미널에서
curl http://localhost:8000/health

# 예상 응답:
# {"status":"ok","timestamp":"2025-11-09T..."}

# API 문서 확인
# 브라우저에서: http://localhost:8000/docs
```

---

## 프론트엔드 실행

### 1. Node.js 및 npm 설치 확인

```bash
node --version  # v14.x 이상
npm --version   # 6.x 이상
```

### 2. 패키지 설치

```bash
cd ~/workspace/stock-finder/frontend

# 패키지 설치
npm install

# 또는 yarn 사용
# yarn install
```

### 3. 개발 서버 실행

```bash
cd ~/workspace/stock-finder/frontend

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
cd ~/workspace/stock-finder/backend

# 가상환경 활성화
source venv/bin/activate

# 전체 테스트 실행
python -m pytest tests/ -v

# 특정 테스트 실행
python tests/test_market_validation_system.py
python tests/test_validation_api.py
python tests/test_scheduler_integration.py
```

### 2. 검증 스크립트 테스트

```bash
cd ~/workspace/stock-finder/backend

# 검증 스크립트 실행
python validate_market_data_timing.py

# 예상 출력:
# INFO:__main__:📊 장세 데이터 검증 시작: 2025-11-09 ...
# INFO:__main__:✅ 검증 데이터 저장 완료
```

### 3. 스케줄러 테스트

```bash
cd ~/workspace/stock-finder/backend

# 스케줄러 통합 테스트
python tests/test_scheduler_integration.py

# 예상 출력:
# ✅ run_validation 실행 성공
# ✅ run_market_analysis 실행 성공
# ✅ setup_scheduler 실행 성공
# 📋 등록된 작업 수: 12
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
cd ~/workspace/stock-finder/backend
source venv/bin/activate
pip install psycopg psycopg-binary psycopg-pool
```

### 3. 포트 충돌 오류

**증상**: `ERROR: [Errno 48] Address already in use`

**해결**:
```bash
# 8000 포트 사용 프로세스 확인 및 종료
lsof -ti:8000 | xargs kill -9

# 3000 포트 사용 프로세스 확인 및 종료
lsof -ti:3000 | xargs kill -9
```

### 4. 키움 API 오류

**증상**: `키움 API 연결 실패`

**해결**:
- `.env` 파일의 `KIWOOM_APP_KEY`, `KIWOOM_APP_SECRET` 확인
- 키움증권 개발자 센터에서 API 키 발급 상태 확인
- 주말/공휴일에는 데이터 조회 불가 (정상)

### 5. 데이터베이스 스키마 오류

**증상**: `relation "table_name" does not exist`

**해결**:
```bash
cd ~/workspace/stock-finder/backend

# 스키마 재적용
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -f sql/postgres_schema.sql
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -f sql/create_market_analysis_validation.sql

# 테이블 확인
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -c "\dt"
```

### 6. 프론트엔드 빌드 오류

**증상**: `npm run dev` 실패

**해결**:
```bash
cd ~/workspace/stock-finder/frontend

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
ls -la ~/workspace/stock-finder/backend/.env

# 없다면 생성 (위의 "환경 변수 설정" 섹션 참조)

# .env 파일 내용 확인
cat ~/workspace/stock-finder/backend/.env | grep DATABASE_URL
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
tail -f ~/workspace/stock-finder/backend/backend.log

# PostgreSQL 쿼리 실행
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -c "SELECT COUNT(*) FROM users;"

# Git 상태 확인
cd ~/workspace/stock-finder
git status
git log --oneline -10

# 디스크 사용량 확인
du -sh ~/workspace/stock-finder
```

### 4. 개발 워크플로우

1. **코드 수정 전**: `git pull origin main`
2. **코드 수정**: 원하는 에디터 사용 (VS Code, PyCharm 등)
3. **테스트 실행**: `python -m pytest tests/`
4. **로컬 확인**: 백엔드/프론트엔드 실행 후 브라우저 테스트
5. **커밋**: `git add .` → `git commit -m "메시지"`
6. **푸시**: `git push origin main`

---

## 참고 문서

- **프로젝트 README**: `README.md`
- **서버 배포 메뉴얼**: `SERVER_DEPLOYMENT_MANUAL_20251109.md`
- **테스트 리포트**: `backend/tests/TEST_REPORT.md`
- **코드 리뷰 이슈**: `CODE_REVIEW_ISSUES.md`
- **DB 관리 가이드**: `DB_MANAGEMENT.md`

---

## 문의 및 지원

- **이슈 등록**: GitHub Issues
- **문서 업데이트**: 2025-11-09
- **작성자**: AI Assistant
- **검토자**: 개발팀

---

**마지막 업데이트**: 2025년 11월 9일

