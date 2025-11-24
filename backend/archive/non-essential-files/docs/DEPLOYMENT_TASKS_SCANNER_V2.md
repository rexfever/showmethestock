# 스캐너 V2 서버 배포 작업 목록

## 📋 배포 전 준비사항

### 1. 로컬 변경사항 커밋 및 푸시
```bash
# 현재 상태 확인
git status

# 변경사항 커밋 (필요시)
git add .
git commit -m "feat: 스캐너 V2 배포 준비"

# GitHub에 푸시
git push origin main
```

### 2. 배포 대상 파일 확인
- ✅ `scanner_settings_manager.py` (신규)
- ✅ `scanner_factory.py` (수정)
- ✅ `config.py` (수정)
- ✅ `main.py` (수정)
- ✅ `scanner_v2/` 디렉토리 전체 (신규)
- ✅ `scan_service.py` (수정)
- ✅ `frontend/pages/admin.js` (수정)
- ✅ `backend/sql/add_scanner_settings.sql` (마이그레이션)

---

## 🚀 서버 배포 작업 순서

### Step 1: 서버 접속 및 상태 확인
```bash
ssh stock-finder
cd /home/ubuntu/showmethestock

# 현재 커밋 확인
git log --oneline -1

# 서비스 상태 확인
sudo systemctl status stock-finder-backend
sudo systemctl status stock-finder-frontend
```

### Step 2: 데이터베이스 백업
```bash
# PostgreSQL 백업
sudo -u postgres pg_dump stockfinder > ~/backups/postgres/backup_before_scanner_v2_$(date +%Y%m%d_%H%M%S).sql

# 백업 확인
ls -lh ~/backups/postgres/backup_before_scanner_v2_*.sql
```

### Step 3: DB 스키마 마이그레이션
```bash
cd /home/ubuntu/showmethestock/backend

# PostgreSQL 접속하여 마이그레이션 실행
sudo -u postgres psql stockfinder -f sql/add_scanner_settings.sql

# 또는 직접 실행
sudo -u postgres psql stockfinder << EOF
\i sql/add_scanner_settings.sql
\dt scanner_settings
SELECT * FROM scanner_settings;
\q
EOF
```

### Step 4: 코드 업데이트
```bash
cd /home/ubuntu/showmethestock

# 로컬 변경사항 확인
git status

# 최신 코드 가져오기
git fetch origin
git pull origin main

# 업데이트 확인
git log --oneline -5
```

### Step 5: 백엔드 의존성 확인
```bash
cd /home/ubuntu/showmethestock/backend

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt --quiet

# 모듈 import 테스트
python3 -c "from scanner_settings_manager import get_scanner_version; print('✅ OK')"
python3 -c "from scanner_factory import get_scanner; print('✅ OK')"
python3 -c "from scanner_v2 import ScannerV2; print('✅ OK')"
```

### Step 6: 백엔드 서비스 재시작
```bash
# 서비스 재시작
sudo systemctl restart stock-finder-backend

# 상태 확인
sleep 5
sudo systemctl status stock-finder-backend

# 로그 확인
sudo journalctl -u stock-finder-backend -n 50 --no-pager
```

### Step 7: 프론트엔드 빌드 및 재시작
```bash
cd /home/ubuntu/showmethestock/frontend

# 의존성 설치
npm ci --production=false

# 빌드
npm run build

# 서비스 재시작
sudo systemctl restart stock-finder-frontend

# 상태 확인
sleep 5
sudo systemctl status stock-finder-frontend
```

### Step 8: 기능 테스트
```bash
# 헬스 체크
curl http://localhost:8010/health

# 스캔 기능 테스트
curl "http://localhost:8010/scan?date=20251121" | jq '.ok'
```

---

## ✅ 배포 후 확인사항

- [ ] 백엔드 서비스 정상 실행
- [ ] 프론트엔드 서비스 정상 실행
- [ ] 헬스 체크 통과
- [ ] DB 테이블 생성 확인 (`scanner_settings`)
- [ ] 관리자 UI에서 스캐너 설정 표시
- [ ] 스캔 기능 정상 동작

---

## 🐛 문제 발생 시 롤백

```bash
cd /home/ubuntu/showmethestock

# 이전 커밋으로 롤백
git log --oneline -10  # 이전 커밋 해시 확인
git reset --hard <이전_커밋_해시>

# DB 롤백 (필요시)
sudo -u postgres psql stockfinder -c "DROP TABLE IF EXISTS scanner_settings;"

# 서비스 재시작
sudo systemctl restart stock-finder-backend
sudo systemctl restart stock-finder-frontend
```

