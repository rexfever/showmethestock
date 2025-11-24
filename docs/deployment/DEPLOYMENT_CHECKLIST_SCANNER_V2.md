# 스캐너 V2 배포 체크리스트

## 📋 배포 전 확인사항

### 1. 코드 상태 확인
- [x] 로컬 테스트 통과
- [x] GitHub에 최신 코드 푸시 완료
- [x] DB 스키마 변경사항 확인 (`scanner_settings` 테이블)

### 2. 배포 대상 파일 목록

#### 백엔드 파일
- `scanner_settings_manager.py` (신규)
- `scanner_factory.py` (수정)
- `config.py` (수정 - DB 우선 읽기)
- `main.py` (수정 - API 엔드포인트 추가)
- `scanner_v2/` 디렉토리 전체 (신규)
- `scan_service.py` (수정 - scanner_factory 사용)

#### 프론트엔드 파일
- `frontend/pages/admin.js` (수정 - 스캐너 설정 UI 추가)

#### DB 스키마
- `backend/sql/add_scanner_settings.sql` (마이그레이션 스크립트)

---

## 🚀 배포 절차

### Step 1: 서버 접속 및 현재 상태 확인

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

# PostgreSQL 접속
sudo -u postgres psql stockfinder

# 마이그레이션 스크립트 실행
\i sql/add_scanner_settings.sql

# 테이블 생성 확인
\dt scanner_settings
SELECT * FROM scanner_settings;

# 종료
\q
```

### Step 4: 코드 업데이트

```bash
cd /home/ubuntu/showmethestock

# 로컬 변경사항 확인 (있으면 백업)
git status

# 최신 코드 가져오기
git fetch origin
git pull origin main

# 업데이트된 파일 확인
git log --oneline -5
git diff HEAD~3 HEAD --name-only
```

### Step 5: 백엔드 의존성 확인

```bash
cd /home/ubuntu/showmethestock/backend

# 가상환경 활성화
source venv/bin/activate

# 의존성 확인 (필요시 설치)
pip install -r requirements.txt --quiet

# 새로 추가된 모듈 import 테스트
python3 -c "from scanner_settings_manager import get_scanner_version; print('✅ scanner_settings_manager OK')"
python3 -c "from scanner_factory import get_scanner; print('✅ scanner_factory OK')"
python3 -c "from scanner_v2 import ScannerV2; print('✅ scanner_v2 OK')"
```

### Step 6: 백엔드 서비스 재시작

```bash
# 서비스 재시작
sudo systemctl restart stock-finder-backend

# 서비스 상태 확인
sleep 5
sudo systemctl status stock-finder-backend

# 로그 확인
sudo journalctl -u stock-finder-backend -n 50 --no-pager
```

### Step 7: 프론트엔드 빌드 및 재시작

```bash
cd /home/ubuntu/showmethestock/frontend

# 의존성 확인
npm ci --production=false

# 빌드
npm run build

# 서비스 재시작
sudo systemctl restart stock-finder-frontend

# 서비스 상태 확인
sleep 5
sudo systemctl status stock-finder-frontend
```

### Step 8: 기능 테스트

#### 8.1 백엔드 API 테스트

```bash
# 헬스 체크
curl http://localhost:8010/health

# 스캐너 설정 조회 (관리자 토큰 필요)
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     http://localhost:8010/admin/scanner-settings

# 스캐너 설정 업데이트 테스트
curl -X POST \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"scanner_version": "v1", "scanner_v2_enabled": false}' \
     http://localhost:8010/admin/scanner-settings
```

#### 8.2 프론트엔드 UI 테스트

1. 관리자 페이지 접속: `https://your-domain.com/admin`
2. "스캐너 설정" 섹션 확인
3. 스캐너 버전 선택 (V1/V2) 테스트
4. V2 활성화 토글 테스트
5. 설정 저장 후 반영 확인

#### 8.3 스캔 기능 테스트

```bash
# V1 스캔 테스트
curl "http://localhost:8010/scan?date=20251121"

# V2 스캔 테스트 (DB에서 V2 활성화 후)
# 관리자 UI에서 V2 활성화 후
curl "http://localhost:8010/scan?date=20251121"
```

### Step 9: 롤백 준비 (문제 발생 시)

```bash
# 이전 커밋으로 롤백
cd /home/ubuntu/showmethestock
git log --oneline -10  # 이전 커밋 해시 확인
git reset --hard <이전_커밋_해시>

# DB 롤백 (필요시)
sudo -u postgres psql stockfinder << EOF
DROP TABLE IF EXISTS scanner_settings;
EOF

# 서비스 재시작
sudo systemctl restart stock-finder-backend
sudo systemctl restart stock-finder-frontend
```

---

## ✅ 배포 후 확인사항

### 필수 확인
- [ ] 백엔드 서비스 정상 실행 (`systemctl status stock-finder-backend`)
- [ ] 프론트엔드 서비스 정상 실행 (`systemctl status stock-finder-frontend`)
- [ ] 헬스 체크 통과 (`/health` 엔드포인트)
- [ ] DB 테이블 생성 확인 (`scanner_settings` 테이블)
- [ ] 관리자 UI에서 스캐너 설정 표시 확인
- [ ] 스캔 기능 정상 동작 (V1 기본값)

### 선택 확인
- [ ] V2 스캐너 활성화 후 정상 동작
- [ ] 스캐너 설정 변경 후 즉시 반영 확인
- [ ] 로그에 에러 없음 (`journalctl -u stock-finder-backend`)

---

## 🐛 문제 해결

### 문제 1: DB 연결 실패
```bash
# PostgreSQL 서비스 확인
sudo systemctl status postgresql

# DB 연결 테스트
sudo -u postgres psql stockfinder -c "SELECT 1;"
```

### 문제 2: Import 에러
```bash
# Python 경로 확인
cd /home/ubuntu/showmethestock/backend
python3 -c "import sys; print(sys.path)"

# 모듈 직접 테스트
python3 -c "from scanner_settings_manager import get_scanner_version; print(get_scanner_version())"
```

### 문제 3: 서비스 시작 실패
```bash
# 상세 로그 확인
sudo journalctl -u stock-finder-backend -n 100 --no-pager

# 수동 실행으로 에러 확인
cd /home/ubuntu/showmethestock/backend
source venv/bin/activate
python3 main.py
```

### 문제 4: 프론트엔드 빌드 실패
```bash
# 빌드 캐시 제거
cd /home/ubuntu/showmethestock/frontend
rm -rf .next
rm -rf node_modules/.cache

# 재빌드
npm run build
```

---

## 📝 배포 완료 체크리스트

- [ ] 모든 단계 완료
- [ ] 기능 테스트 통과
- [ ] 로그에 에러 없음
- [ ] 서비스 정상 동작 확인
- [ ] 관리자 UI에서 설정 변경 가능 확인
- [ ] 스캔 기능 정상 동작 확인

---

## 📅 배포 일자
- 배포 예정일: 
- 배포 완료일: 
- 배포 담당자: 

---

## 📌 참고사항

1. **DB 우선순위**: 설정은 DB에서 우선 조회하고, 없으면 `.env`에서 읽습니다.
2. **기본값**: 배포 직후는 V1이 기본값입니다. 관리자 UI에서 V2로 변경 가능합니다.
3. **롤백**: 문제 발생 시 이전 커밋으로 롤백하고 DB 테이블만 제거하면 됩니다.
4. **모니터링**: 배포 후 24시간 동안 로그를 모니터링하세요.

