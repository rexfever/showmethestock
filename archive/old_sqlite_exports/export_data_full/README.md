# Stock Finder - Windows 개발환경 설정 가이드

## 📦 포함된 파일들

### 🗄️ 데이터베이스 (backend/)
- `snapshots.db` - 메인 데이터베이스 (사용자, 포지션, 스캔 데이터)
- `portfolio.db` - 포트폴리오 데이터베이스
- `email_verifications.db` - 이메일 인증 데이터베이스
- `news_data.db` - 뉴스 데이터베이스
- `snapshots/` - 과거 스캔 결과 JSON 파일들 (50+ 파일)

### ⚙️ 설정 파일
- `backend/config.py` - 백엔드 설정 파일
- `backend/requirements.txt` - Python 의존성
- `frontend/config.js` - 프론트엔드 환경 설정
- `frontend/package.json` - Node.js 의존성
- `frontend/next.config.js` - Next.js 설정

### 🚀 배포 스크립트
- `deploy-aws.sh` - AWS 배포 스크립트
- `server.sh` - 서버 관리 스크립트
- `local.sh` - 로컬 개발 스크립트
- `nginx_config` - Nginx 설정
- `ssh-config` - SSH 연결 설정
- `terraform.tfvars.example` - AWS 배포 설정 예시

## 🛠️ Windows에서 설치 가이드

### 1. 소스코드 다운로드
```bash
# Git으로 소스코드 클론
git clone https://github.com/rexfever/showmethestock.git
cd showmethestock
```

### 2. 설정 파일 복사
```bash
# 이 압축 파일의 내용을 프로젝트에 복사
# backend/ 폴더의 내용을 backend/에 복사
# frontend/ 폴더의 내용을 frontend/에 복사
```

### 3. 환경 변수 설정
```bash
# 프로젝트 루트에 .env 파일 생성
APP_KEY=your_kiwoom_app_key
APP_SECRET=your_kiwoom_app_secret
KAKAO_CLIENT_ID=your_kakao_client_id
KAKAO_CLIENT_SECRET=your_kakao_client_secret
NEXT_PUBLIC_KAKAO_CLIENT_ID=your_kakao_client_id
```

### 4. 의존성 설치
```bash
# 백엔드 (Python)
cd backend
pip install -r requirements.txt

# 프론트엔드 (Node.js)
cd frontend
npm install
```

### 5. 설정 파일 수정
- `frontend/config.js` - 도메인 URL을 환경에 맞게 수정
- `terraform.tfvars.example` - AWS 설정을 환경에 맞게 수정

### 6. 서버 시작
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

## 🎯 Windows 특별 주의사항
- Python 3.8+ 설치 필요
- Node.js 16+ 설치 필요
- SQLite3 설치 필요
- 관리자 권한으로 실행 권장

