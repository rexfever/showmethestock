# showmethestock 정리 실행 가이드

> 📅 작성일: 2025-01-21  
> 📋 관련 문서: [CLEANUP_PLAN.md](./CLEANUP_PLAN.md)

## 🎯 빠른 시작

### 전제 조건
- ✅ Git 저장소가 clean 상태여야 함
- ✅ 백업이 필요하면 먼저 git commit
- ✅ 실행 권한이 있어야 함

### 실행 순서 (권장)

```bash
# 1. 현재 상태 확인
git status

# 2. 백업 (선택사항 - git commit으로 충분)
git add -A
git commit -m "chore: backup before cleanup"

# 3. 1순위: 로그, 백업, 보안 파일 제거 (안전)
bash cleanup_priority_1.sh

# 4. 상태 확인
git status

# 5. 2순위: 분석 스크립트 아카이브 이동 (안전)
bash cleanup_priority_2.sh

# 6. 상태 확인
git status

# 7. 3순위: 아카이브 정리 및 통합 (안전)
bash cleanup_priority_3.sh

# 8. 최종 확인
git status
git diff

# 9. 테스트 (중요!)
cd backend
pytest

# 10. 로컬 서버 테스트
cd ..
bash local.sh

# 11. 문제 없으면 commit
git add -A
git commit -m "chore: cleanup unnecessary files and update .gitignore

- Remove backup files (.env.backup*)
- Remove security risk files (aws_console_copy_paste.txt, notification_recipients.txt)
- Remove log files (*.log)
- Archive analysis scripts to backend/archive/analysis_scripts_2025/
- Move one-time scripts to backend/scripts/one_time_scripts/
- Consolidate SQLite archives (PostgreSQL now in use)
- Archive old nginx configs
- Remove admin_scanner/ (unused static HTML)
- Remove docs.zip (docs/ folder is current)
- Update .gitignore to prevent future commits of these file types"
```

---

## 📦 각 스크립트 설명

### cleanup_priority_1.sh
**목적**: 임시 파일, 백업 파일, 로그 파일, 보안 위험 파일 제거

**제거 대상**:
- `.env.backup*` (3개)
- `aws_console_copy_paste.txt` 🔴 보안 위험
- `notification_recipients.txt` 🔴 개인정보
- `*.log` 파일들 (~260KB)
- `.coverage` 파일

**위험도**: 🟢 Low - 안전함 (모두 재생성 가능한 파일)

**예상 시간**: < 1분

---

### cleanup_priority_2.sh
**목적**: 일회성 분석 스크립트를 아카이브로 이동

**이동 대상**:
- `analyze_*.py` 스크립트들 → `backend/archive/analysis_scripts_2025/`
- `check_*.py`, `create_*.py` 유틸리티 → `backend/scripts/one_time_scripts/`

**위험도**: 🟢 Low - 이동만 함 (삭제 아님)

**예상 시간**: < 1분

---

### cleanup_priority_3.sh
**목적**: 아카이브 정리 및 중복 파일 제거

**처리 대상**:
- SQLite 관련 아카이브 통합
- 중복 nginx 설정 파일 아카이브
- `admin_scanner/` 폴더 제거
- `docs.zip` 제거

**위험도**: 🟡 Medium - nginx 설정 파일 이동 포함

**예상 시간**: < 2분

---

## ⚠️ 주의사항

### 실행 전 필수 확인
1. **Cron Job 확인**
   ```bash
   crontab -l | grep -E "analyze_|check_|create_"
   ```
   → 결과 없어야 함 (이 스크립트들이 cron에서 실행 중이면 안됨)

2. **Deploy 스크립트 확인**
   ```bash
   grep -r "analyze_\|nginx_config" deploy-aws.sh server.sh
   ```
   → 결과 없어야 함

3. **현재 Nginx 설정 확인**
   ```bash
   # 서버에서
   ssh your-server "cat /etc/nginx/sites-available/showmethestock"
   ```
   → 어떤 nginx_config 파일을 사용하는지 확인

### 실행 중 문제 발생 시
```bash
# 롤백 (마지막 commit으로 복원)
git reset --hard HEAD

# 또는 특정 파일만 복원
git checkout HEAD -- backend/analyze_v2_winrate.py
```

---

## 🧪 검증 절차

### 1. 코드 정상 작동 확인
```bash
# 백엔드 테스트
cd backend
pytest

# 특정 테스트만 실행
pytest tests/test_scanner_v2.py -v
```

### 2. Import 에러 확인
```bash
# 모든 Python 파일에서 import 에러 체크
cd backend
python -m py_compile *.py
python -m py_compile services/*.py
```

### 3. 로컬 서버 시작
```bash
cd /home/engine/project
bash local.sh
```

브라우저에서 확인:
- http://localhost:3000 (프론트엔드)
- http://localhost:8000/health (백엔드 헬스체크)

### 4. 배포 테스트 (선택사항)
```bash
# Staging 환경이 있다면 먼저 배포
bash deploy-aws.sh --env staging

# Production 배포
bash deploy-aws.sh
```

---

## 📊 예상 결과

### 파일 변경 통계
```
Priority 1: ~20개 파일 삭제 (~260KB)
Priority 2: ~11개 파일 이동
Priority 3: ~10개 파일 이동/삭제, ~3개 폴더 제거
```

### Git 상태
```bash
$ git status
On branch cleanup-showmethestock-unused-files-plan

Changes to be committed:
  modified:   .gitignore
  deleted:    aws_console_copy_paste.txt
  deleted:    notification_recipients.txt
  deleted:    backend/.env.backup
  deleted:    backend/.env.backup.20251023_004613
  deleted:    backend/.env.example.backup
  renamed:    backend/analyze_v2_winrate.py -> backend/archive/analysis_scripts_2025/analyze_v2_winrate.py
  ... (more changes)
  new file:   CLEANUP_PLAN.md
  new file:   CLEANUP_EXECUTION_GUIDE.md
  new file:   cleanup_priority_1.sh
  new file:   cleanup_priority_2.sh
  new file:   cleanup_priority_3.sh
```

---

## 🚫 절대 하지 말 것

### ❌ 삭제하면 안 되는 폴더/파일
```
backend/backfill/          # 실제 사용 중 - backfill_past_scans.py
backend/backtest/          # 실제 사용 중 - services/backtest_service.py
backend/backtester/        # 실제 사용 중 - tests에서 참조
backend/cache/             # 필수 캐시 (성능 최적화)
backend/services/          # 핵심 비즈니스 로직
backend/tests/             # 테스트 코드
backend/scripts/           # 활성 스크립트들
docs/                      # 최신 문서
.env                       # 실제 환경변수 (백업만 삭제)
```

### ❌ 실행하면 안 되는 명령어
```bash
# 위험! 전체 캐시 삭제 (API 호출량 폭증)
rm -rf backend/cache/

# 위험! 실제 .env 삭제
rm backend/.env

# 위험! 테스트 폴더 삭제
rm -rf backend/tests/
```

---

## 🔄 선택적 추가 정리

### Cache 최적화 (선택사항)
**90일 이상 된 캐시 파일 삭제**:
```bash
# 예상 절감: 수십~수백 MB
# 위험: 캐시 재생성으로 Kiwoom API 호출량 증가

find backend/cache/ohlcv -name "*.pkl" -mtime +90 -ls
# 확인 후:
find backend/cache/ohlcv -name "*.pkl" -mtime +90 -delete
```

### Archive 완전 삭제 (선택사항)
**Git 히스토리가 충분하다면**:
```bash
# 예상 절감: ~5MB
# 주의: 복원 불가 (git 히스토리에는 남음)

rm -rf archive/
```

---

## 📝 정리 후 할 일

### 1. 문서 업데이트
- [ ] `aws_console_copy_paste.txt` 내용을 `docs/infrastructure/aws-setup.md`로 이동
- [ ] `notification_recipients.txt` 내용을 환경변수 또는 DB로 마이그레이션

### 2. 자동화 설정
```bash
# Cron job으로 캐시 자동 정리 (선택사항)
# 매주 일요일 오전 3시
0 3 * * 0 find /path/to/backend/cache/ohlcv -name "*.pkl" -mtime +90 -delete

# 또는 systemd timer 사용
```

### 3. Pre-commit Hook 추가 (선택사항)
```bash
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Prevent committing sensitive files

if git diff --cached --name-only | grep -qE "\.backup$|\.log$|notification_recipients\.txt|aws_console_copy_paste\.txt"; then
    echo "❌ Error: Attempting to commit sensitive or backup files"
    echo "Files:"
    git diff --cached --name-only | grep -E "\.backup$|\.log$|notification_recipients\.txt|aws_console_copy_paste\.txt"
    echo ""
    echo "Please remove these files from your commit or update .gitignore"
    exit 1
fi
EOF

chmod +x .git/hooks/pre-commit
```

### 4. 정기 리뷰 일정
- [ ] 매월: 로그 파일 확인 및 정리
- [ ] 매 분기: 캐시 파일 정리
- [ ] 매 반기: archive/ 폴더 리뷰

---

## 🆘 문제 해결

### Q: cleanup_priority_2.sh 실행 후 import 에러 발생
**A**: 
```bash
# 파일을 원래 위치로 복원
git checkout HEAD -- backend/analyze_v2_winrate.py

# 또는 전체 롤백
git reset --hard HEAD
```

### Q: 로그 파일이 계속 생성됨
**A**: .gitignore가 제대로 업데이트되었는지 확인
```bash
git check-ignore backend/backend.log
# → backend/backend.log 출력되어야 함
```

### Q: Nginx 설정 파일을 잘못 삭제함
**A**: 
```bash
# Git에서 복원
git checkout HEAD -- nginx_https_config

# 서버의 실제 설정 복사
scp user@server:/etc/nginx/sites-available/showmethestock ./nginx_production.conf
```

### Q: 캐시 삭제 후 성능 저하
**A**: 
```bash
# 캐시 재생성 (시간 소요)
# 백엔드 서비스 재시작하면 자동으로 재생성됨
cd backend
python create_cache_data.py  # 또는 서비스 재시작
```

---

## ✅ 체크리스트

### 실행 전
- [ ] `git status`로 clean 상태 확인
- [ ] 백업 완료 (git commit 또는 tar.gz)
- [ ] Cron job 확인 (`crontab -l`)
- [ ] Deploy 스크립트에서 참조 여부 확인
- [ ] Nginx 설정 확인 (서버에서)

### 실행 중
- [ ] Priority 1 실행 완료
- [ ] `git status` 확인
- [ ] Priority 2 실행 완료
- [ ] `git status` 확인
- [ ] Priority 3 실행 완료
- [ ] `git status` 확인

### 실행 후
- [ ] `pytest` 통과
- [ ] Import 에러 없음
- [ ] 로컬 서버 시작 성공
- [ ] .gitignore 업데이트 확인
- [ ] Git commit 완료
- [ ] 배포 테스트 성공 (선택사항)

---

## 📞 문의

문제 발생 시:
1. 먼저 git으로 롤백: `git reset --hard HEAD`
2. CLEANUP_PLAN.md의 "주의사항" 섹션 참조
3. 이 가이드의 "문제 해결" 섹션 참조

---

**최종 검토**: 필요  
**승인자**: (승인 필요)  
**위험도**: 🟢 Low (순서 준수 시)
