# Stock Finder - 개발환경 이전 가이드

## 📦 Export된 파일들

### 🗄️ 데이터베이스
- `snapshots.db` - 메인 데이터베이스 (사용자, 포지션, 스캔 데이터)
- `portfolio.db` - 포트폴리오 데이터베이스
- `email_verifications.db` - 이메일 인증 데이터베이스
- `news_data.db` - 뉴스 데이터베이스
- `*_dump.sql` - SQL 덤프 파일들

### 📁 스캔 데이터
- `snapshots/` - 과거 스캔 결과 JSON 파일들

### ⚙️ 설정 파일
- `frontend_config.js` - 프론트엔드 환경 설정
- `backend_config.py` - 백엔드 설정 파일
- `ssh-config` - SSH 연결 설정
- `terraform.tfvars.example` - AWS 배포 설정 예시

### 🚀 배포 스크립트
- `deploy-aws.sh` - AWS 배포 스크립트
- `server.sh` - 서버 관리 스크립트
- `local.sh` - 로컬 개발 스크립트
- `nginx_config` - Nginx 설정

### 📋 의존성 파일
- `requirements.txt` - Python 의존성
- `package.json` - Node.js 의존성
- `next.config.js` - Next.js 설정

## 🛠️ 설치 가이드

### 1. 환경 변수 설정
```bash
# .env 파일 생성 (민감한 정보 포함)
APP_KEY=your_kiwoom_app_key
APP_SECRET=your_kiwoom_app_secret
KAKAO_CLIENT_ID=your_kakao_client_id
KAKAO_CLIENT_SECRET=your_kakao_client_secret
NEXT_PUBLIC_KAKAO_CLIENT_ID=your_kakao_client_id
```

### 2. 데이터베이스 복원
```bash
# SQLite 데이터베이스 복원
sqlite3 backend/snapshots.db < snapshots_dump.sql
sqlite3 backend/portfolio.db < portfolio_dump.sql
sqlite3 backend/email_verifications.db < email_verifications_dump.sql
sqlite3 backend/news_data.db < news_data_dump.sql
```

### 3. 의존성 설치
```bash
# 백엔드
cd backend
pip install -r requirements.txt

# 프론트엔드
cd frontend
npm install
```

### 4. 설정 파일 수정
- `frontend_config.js` - 도메인 URL 수정
- `terraform.tfvars.example` - AWS 설정 수정
- `ssh-config` - SSH 키 경로 수정

### 5. 서버 시작
```bash
# 백엔드
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8010 --reload

# 프론트엔드
cd frontend
npm run dev
```

## 📊 데이터 현황
- **사용자**: 5명
- **포지션**: 19개
- **스캔 랭킹**: 94개
- **스캔 파일**: 50+ 개

## 🔐 보안 주의사항
- `.env` 파일은 Git에 커밋하지 마세요
- API 키는 환경에 맞게 새로 발급받으세요
- 데이터베이스 파일은 안전하게 보관하세요

