# 서버 작업 메뉴얼

## 1. 서버 정보

### 기본 정보
- **호스트명**: ip-172-31-12-241
- **IP 주소**: 52.79.145.238
- **사용자**: ubuntu
- **홈 디렉토리**: /home/ubuntu

### SSH 접속
```bash
# SSH 설정 사용
ssh stock-finder

# 직접 접속
ssh -i ~/.ssh/id_rsa ubuntu@52.79.145.238
```

### 주요 디렉토리
```bash
/home/ubuntu/showmethestock/backend/    # 백엔드 코드
/home/ubuntu/showmethestock/frontend/   # 프론트엔드 코드
/home/ubuntu/showmethestock/backend/snapshots.db    # 메인 DB
/home/ubuntu/showmethestock/backend/portfolio.db    # 포트폴리오 DB
/home/ubuntu/showmethestock/backend/email_verifications.db  # 이메일 인증 DB
```

## 2. 작업 순서 (로컬 → 서버)

### 기본 원칙
**⚠️ 항상 로컬에서 먼저 작업하고 테스트한 후 서버에 반영**

### 작업 절차
1. **로컬 개발**
   ```bash
   # 로컬에서 코드 수정
   cd /Users/a201808029/sandbox/showmethestock
   # 코드 수정 및 테스트
   ```

2. **로컬 테스트**
   ```bash
   # 백엔드 테스트
   cd backend
   python main.py
   
   # 프론트엔드 테스트
   cd frontend
   npm run dev
   ```

3. **서버 반영**
   ```bash
   # 파일 업로드 (scp 사용)
   scp -r backend/ stock-finder:/home/ubuntu/showmethestock/
   scp -r frontend/ stock-finder:/home/ubuntu/showmethestock/
   
   # 또는 git 사용
   ssh stock-finder "cd /home/ubuntu/showmethestock && git pull"
   ```

4. **서버 재시작 (프로세스 완전 종료 후)**
   ```bash
   # 기존 프로세스 완전 종료
   ssh stock-finder "sudo pkill -f 'python.*main.py' && sudo pkill -f 'next'"
   
   # 포트 사용 프로세스 강제 종료
   ssh stock-finder "sudo lsof -ti :8010 | xargs -r sudo kill -9"
   ssh stock-finder "sudo lsof -ti :3000 | xargs -r sudo kill -9"
   
   # 서비스 재시작
   ssh stock-finder "sudo systemctl restart backend"
   ssh stock-finder "sudo systemctl restart frontend"
   
   # 상태 확인
   ssh stock-finder "systemctl is-active backend frontend"
   ```

## 3. DB 백업 (작업 전 필수)

### 자동 백업 스크립트
```bash
# 서버에서 실행
ssh stock-finder "cd /home/ubuntu/showmethestock && ./scripts/backup-database.sh"
```

### 수동 백업
```bash
# 서버 접속
ssh stock-finder

# 백업 디렉토리 생성
mkdir -p /home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)

# DB 파일 백업
cd /home/ubuntu/showmethestock/backend
cp snapshots.db /home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)/
cp portfolio.db /home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)/
cp email_verifications.db /home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)/

# 백업 확인
ls -la /home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)/
```

### 로컬로 백업 다운로드
```bash
# 로컬에서 실행
scp stock-finder:/home/ubuntu/showmethestock/backend/*.db ./backup/
```

## 4. 주요 명령어

### 서버 상태 확인
```bash
ssh stock-finder "systemctl status backend"
ssh stock-finder "systemctl status frontend"
ssh stock-finder "ps aux | grep python"
ssh stock-finder "lsof -i :8010"  # 백엔드 포트
ssh stock-finder "lsof -i :3000"  # 프론트엔드 포트
```

### 로그 확인
```bash
ssh stock-finder "tail -f /home/ubuntu/showmethestock/backend/backend.log"
ssh stock-finder "journalctl -u backend -f"
```

### DB 데이터 현황 확인
```bash
# 전체 데이터 수
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'SELECT COUNT(*) FROM scan_rank;'"

# 날짜별 데이터 수
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'SELECT date, COUNT(*) FROM scan_rank GROUP BY date ORDER BY date DESC LIMIT 10;'"

# 최신 스캔 데이터
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'SELECT date, code, name, score FROM scan_rank WHERE date = (SELECT MAX(date) FROM scan_rank) ORDER BY score DESC LIMIT 5;'"

# 사용자 수
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'SELECT COUNT(*) FROM users;'"

# 포트폴리오 수
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 portfolio.db 'SELECT COUNT(*) FROM portfolio;'"
```

### 스캔 실행
```bash
# API를 통한 스캔
curl "https://sohntech.ai.kr/api/scan?save_snapshot=true"

# 서버에서 직접 실행
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && python -c 'import requests; print(requests.get(\"http://localhost:8010/scan?save_snapshot=true\").json())'"
```

## 5. 비상 복구

### DB 복구
```bash
# 백업에서 복구
ssh stock-finder "cd /home/ubuntu/showmethestock/backend"
ssh stock-finder "cp /home/ubuntu/backups/YYYYMMDD_HHMMSS/snapshots.db ."
```

### 서비스 재시작 (완전 종료 후)
```bash
# 1단계: 기존 프로세스 완전 종료
ssh stock-finder "sudo pkill -f 'python.*main.py'"
ssh stock-finder "sudo pkill -f 'next'"

# 2단계: 포트 점유 프로세스 강제 종료
ssh stock-finder "sudo lsof -ti :8010 | xargs -r sudo kill -9"
ssh stock-finder "sudo lsof -ti :3000 | xargs -r sudo kill -9"

# 3단계: 서비스 재시작
ssh stock-finder "sudo systemctl restart backend frontend"

# 4단계: 상태 확인
ssh stock-finder "systemctl is-active backend frontend"
ssh stock-finder "curl -I http://localhost:8010"
ssh stock-finder "curl -I http://localhost:3000"
```

### 롤백
```bash
ssh stock-finder "cd /home/ubuntu/showmethestock && git reset --hard HEAD~1"
```

## 6. 주의사항

- ⚠️ **DB 작업 전 반드시 백업**
- ⚠️ **로컬 테스트 후 서버 반영**
- ⚠️ **서버 직접 수정 금지**
- ⚠️ **스케줄러 실행 시간 고려 (15:36 KST)**
- ⚠️ **백업 파일 정기 정리**

## 7. 연락처 및 문서

- **서버 관리**: AWS EC2 콘솔
- **도메인**: sohntech.ai.kr
- **SSL**: Let's Encrypt (자동 갱신)
- **모니터링**: 서버 로그 및 API 응답 확인