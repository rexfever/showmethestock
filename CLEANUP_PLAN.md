# showmethestock 불필요 파일 정리 계획

> 마지막 업데이트: 2025-01-21

## 📊 요약

- **삭제 대상**: 약 50개 파일/폴더
- **정리 예상 효과**: ~5.7MB 절감 (로그, 백업, 아카이브 제외)
- **캐시 최적화**: 334MB (backend/cache/ohlcv - 67,597개 .pkl 파일)
- **예상 시간**: 1-2시간

## 🎯 정리 전략

### 정리 원칙
1. ✅ VCS(git)로 버전 관리 중이므로 백업 파일 불필요
2. ✅ 로그 파일은 .gitignore에 추가하고 삭제
3. ✅ 보안 위험 파일 즉시 삭제
4. ✅ 일회성 분석 스크립트는 archive로 이동 또는 삭제
5. ⚠️ 실제 서비스에서 사용 중인 파일은 보존

---

## 🔴 1순위: 즉시 삭제 (보안/백업/로그 파일)

### A. 백업 파일 (2.5KB)
```bash
backend/.env.backup                       # 608B
backend/.env.backup.20251023_004613       # 1.7KB
backend/.env.example.backup               # 207B
```
**삭제 이유**: git으로 버전 관리 중이므로 불필요

### B. 보안 위험 파일 (2.2KB)
```bash
aws_console_copy_paste.txt                # 2.2KB - AWS 정책 JSON 포함
notification_recipients.txt               # 28B - 개인 전화번호 포함
```
**삭제 이유**: 
- AWS 정책은 terraform 또는 docs에 문서화되어야 함
- 전화번호는 데이터베이스 또는 환경변수로 관리

### C. 로그 파일 (~260KB)
```bash
# Root level
update_regime_v4.log                      # 211B

# Backend logs
backend/backend.log                       # 31KB
backend/update_regime_v4.log              # 84KB
backend/optimal_conditions.log            # 273B
backend/optimal_conditions_full.log       # 3.3KB
backend/optimal_conditions_full_v2.log    # 3.3KB
backend/optimal_conditions_jul_sep.log    # 389B
backend/rescan_november_full.log          # 9.7KB
backend/server_scan_validation.log        # 0B
backend/server_scan_validation_oct27.log  # 25KB

# Frontend logs
frontend/frontend.log                     # 4KB
```
**삭제 이유**: 
- 실행 시마다 생성되는 파일
- .gitignore에 추가하여 git에서 추적 제외

### D. 기타 임시 파일
```bash
backend/.coverage                         # 53KB - pytest 커버리지 결과
```
**삭제 이유**: 테스트 실행 시마다 재생성

### 1순위 삭제 스크립트
```bash
#!/bin/bash
# Priority 1: Remove backup, security, log files

echo "🗑️  Removing backup files..."
rm -f backend/.env.backup
rm -f backend/.env.backup.20251023_004613
rm -f backend/.env.example.backup

echo "🗑️  Removing security risk files..."
rm -f aws_console_copy_paste.txt
rm -f notification_recipients.txt

echo "🗑️  Removing log files..."
rm -f update_regime_v4.log
rm -f backend/backend.log
rm -f backend/update_regime_v4.log
rm -f backend/optimal_conditions*.log
rm -f backend/rescan_november_full.log
rm -f backend/server_scan_validation*.log
rm -f frontend/frontend.log

echo "🗑️  Removing coverage files..."
rm -f backend/.coverage

echo "✅ Priority 1 cleanup completed!"
```

---

## 🟡 2순위: 일회성 분석 스크립트 삭제 (~70KB)

### A. 분석 스크립트 (사용 안함)
```bash
backend/analyze_v2_winrate.py                    # 10KB
backend/analyze_v2_winrate_by_horizon.py         # 8KB
backend/analyze_november_regime_cached.py        # 3.5KB
backend/analyze_november_regime_with_csv.py      # 11KB
backend/analyze_optimal_conditions.py            # 18KB
backend/analyze_regime_v4_july_nov.py            # 6.5KB
```
**확인 결과**: 
- `main.py`에서 import 안함
- 서비스 파일에서 사용 안함
- 일회성 분석용 스크립트로 판단

**조치**: `backend/archive/non-essential-files/analysis/`로 이동 또는 삭제

### B. 일회성 유틸리티 스크립트
```bash
backend/check_aws_v2_data.py                     # 2.4KB
backend/check_v2_scan_data.py                    # 1.4KB
backend/create_admin_user.py                     # 2.8KB
backend/create_cache_data.py                     # 5KB
backend/create_regime_table_sqlite.py            # 1.7KB
```
**확인 결과**:
- SQLite는 현재 사용 안함 (PostgreSQL 사용 중)
- create_admin_user.py는 일회성 실행 스크립트
- check_*는 디버깅용 스크립트

**조치**: `backend/scripts/one_time_scripts/` 로 이동

### 2순위 삭제 스크립트
```bash
#!/bin/bash
# Priority 2: Archive or remove one-time analysis scripts

echo "📦 Moving analysis scripts to archive..."
mkdir -p backend/archive/analysis_scripts_2025

mv backend/analyze_v2_winrate.py backend/archive/analysis_scripts_2025/
mv backend/analyze_v2_winrate_by_horizon.py backend/archive/analysis_scripts_2025/
mv backend/analyze_november_regime_cached.py backend/archive/analysis_scripts_2025/
mv backend/analyze_november_regime_with_csv.py backend/archive/analysis_scripts_2025/
mv backend/analyze_optimal_conditions.py backend/archive/analysis_scripts_2025/
mv backend/analyze_regime_v4_july_nov.py backend/archive/analysis_scripts_2025/

echo "📦 Moving one-time utility scripts..."
mkdir -p backend/scripts/one_time_scripts

mv backend/check_aws_v2_data.py backend/scripts/one_time_scripts/
mv backend/check_v2_scan_data.py backend/scripts/one_time_scripts/
mv backend/create_admin_user.py backend/scripts/one_time_scripts/
mv backend/create_cache_data.py backend/scripts/one_time_scripts/
mv backend/create_regime_table_sqlite.py backend/scripts/one_time_scripts/

echo "✅ Priority 2 cleanup completed!"
```

---

## 🟢 3순위: 폴더 정리 및 통합

### A. archive/ 폴더 (4.4MB)
```
archive/
├── deprecated/
├── old_analysis/
├── old_db_backups/
├── old_logs/
├── old_logs_runtime/
├── old_manuals/
├── old_plans/
├── old_sqlite_backups/
├── old_sqlite_dbs/
├── old_sqlite_exports/
├── old_tests/
└── temp_cleanup_20251123/
```

**분석 결과**:
- README.md에 의하면 "더 이상 활발히 사용되지 않는 문서들"
- SQLite 관련 파일들은 PostgreSQL로 전환 후 불필요
- temp_cleanup_20251123은 이전 정리 작업의 임시 폴더

**권장 조치**:
```bash
# Option 1: 완전 삭제 (git 히스토리에 남아있음)
rm -rf archive/

# Option 2: 중요 파일만 남기고 정리
rm -rf archive/old_sqlite_backups/
rm -rf archive/old_sqlite_dbs/
rm -rf archive/old_sqlite_exports/
rm -rf archive/temp_cleanup_20251123/
rm -rf archive/old_logs_runtime/
```

### B. backend/archive/ 폴더 (956KB)
```bash
du -sh backend/archive/
# 956KB
```

**조치**: 
- 실제 사용 여부 재확인
- 불필요시 root의 archive/로 통합

### C. backend/admin_scanner/ 폴더 (5KB)
```
backend/admin_scanner/
└── index.html  # 5KB
```

**확인 결과**:
- `main.py`에서 import 안함
- admin_service.py와 별개로 사용 안됨
- 정적 HTML 파일만 존재

**조치**: 
```bash
# admin_service.py가 제공하는 기능과 중복되면 삭제
rm -rf backend/admin_scanner/
```

### D. nginx 설정 파일 통합 (9KB)
```bash
nginx_config                    # 1.5KB
nginx_config_fixed              # 1.9KB
nginx_config_simple             # 1.5KB
nginx_config_updated            # 1.9KB
nginx_https_config              # 3.2KB
```

**확인 결과**:
- deploy-aws.sh에서 사용 안함
- 어느 것이 현재 production인지 불명확

**권장 조치**:
1. 현재 AWS 서버의 nginx 설정 확인
2. 사용 중인 설정 1개만 `nginx.conf` 또는 `nginx_production.conf`로 rename
3. 나머지는 `archive/old_nginx_configs/`로 이동

```bash
# 예시
mkdir -p archive/old_nginx_configs/
mv nginx_config* archive/old_nginx_configs/
mv nginx_https_config archive/old_nginx_configs/
# 실제 사용 중인 파일만 남기기
# cp /etc/nginx/sites-available/showmethestock ./nginx_production.conf
```

### E. docs.zip (147KB)
```bash
docs.zip  # 147KB
```

**분석 결과**:
- docs/ 폴더가 이미 존재 (최신 문서)
- 중복 가능성

**조치**:
```bash
# docs.zip 내용 확인
unzip -l docs.zip

# docs/ 폴더와 비교 후 불필요시 삭제
rm -f docs.zip
```

### 3순위 정리 스크립트
```bash
#!/bin/bash
# Priority 3: Archive consolidation and config cleanup

echo "📦 Consolidating archive folders..."
mkdir -p archive/old_archives_consolidated

# Move old sqlite files (no longer needed)
mv archive/old_sqlite_backups archive/old_archives_consolidated/ 2>/dev/null
mv archive/old_sqlite_dbs archive/old_archives_consolidated/ 2>/dev/null
mv archive/old_sqlite_exports archive/old_archives_consolidated/ 2>/dev/null

# Remove temporary cleanup folder
rm -rf archive/temp_cleanup_20251123/

echo "📦 Consolidating nginx configs..."
mkdir -p archive/old_nginx_configs
mv nginx_config archive/old_nginx_configs/ 2>/dev/null
mv nginx_config_fixed archive/old_nginx_configs/ 2>/dev/null
mv nginx_config_simple archive/old_nginx_configs/ 2>/dev/null
mv nginx_config_updated archive/old_nginx_configs/ 2>/dev/null
mv nginx_https_config archive/old_nginx_configs/ 2>/dev/null

echo "🗑️  Removing unnecessary admin_scanner..."
rm -rf backend/admin_scanner/

echo "🗑️  Removing docs.zip (docs/ folder exists)..."
rm -f docs.zip

echo "✅ Priority 3 cleanup completed!"
```

---

## 🔵 특별 고려 사항

### 1. backend/cache/ 폴더 (334MB, 67,597개 파일)
```
backend/cache/
├── ohlcv/           # 334MB, 67,597 .pkl files
└── us_futures/
```

**분석 결과**:
- OHLCV 데이터 캐시 (kiwoom_api.py에서 사용)
- 성능 최적화를 위한 필수 캐시
- 실제 서비스에서 사용 중

**권장 조치**:
```bash
# .gitignore에 추가 (이미 추가되어 있는지 확인)
echo "backend/cache/ohlcv/*.pkl" >> .gitignore

# 오래된 캐시 파일 정리 (90일 이상)
find backend/cache/ohlcv -name "*.pkl" -mtime +90 -delete

# 또는 특정 날짜 이전 파일 삭제
find backend/cache/ohlcv -name "*_2024*.pkl" -delete  # 2024년 데이터만 삭제
```

**주의**: 삭제 시 캐시 재생성으로 API 호출량 증가 가능

### 2. backfill/, backtest/, backtester/ 폴더 (168KB)
```
backend/backfill/     # 84KB
backend/backtest/     # 68KB
backend/backtester/   # 16KB
```

**분석 결과**:
- ✅ **실제 사용 중** - services/backtest_service.py에서 참조
- ✅ main.py, tests에서 import됨
- ✅ 백테스트 기능에 필수

**조치**: **삭제하지 않음**

### 3. cache/ 폴더 (root level, 500KB)
```bash
cache/  # 500KB (root)
```

**확인 필요**:
- backend/cache/와 다른 용도?
- 사용 여부 확인

---

## 📝 .gitignore 업데이트

기존 .gitignore에 추가할 항목:

```gitignore
# Logs (추가)
*.log
backend/*.log
frontend/*.log
update_regime_v4.log

# Backup files (이미 있음)
*.backup
*.bak

# Coverage reports
.coverage
htmlcov/
.pytest_cache/

# Cache files
backend/cache/ohlcv/*.pkl

# Temporary files
*.tmp
*.temp
notification_recipients.txt
aws_console_copy_paste.txt
```

---

## ⚠️ 충돌 가능성 체크리스트

### 배포 스크립트 확인
```bash
# deploy-aws.sh에서 참조하는 파일 확인
grep -n "\.env\|nginx\|cache\|log" deploy-aws.sh

# server.sh에서 참조하는 파일 확인
grep -n "\.env\|nginx\|cache\|log" server.sh
```

### Cron Job 확인
```bash
# 서버에서 실행 중인 cron job 확인
crontab -l

# analyze_* 스크립트가 cron에서 실행 중인지 확인
crontab -l | grep -E "analyze_|check_|create_"
```

### 환경변수 파일 확인
```bash
# .env 파일에서 참조하는 경로 확인
grep -E "cache|log|archive" backend/.env
```

---

## 🎯 실행 순서

### 1단계: 백업 (선택사항)
```bash
# 전체 프로젝트 백업 (git commit으로 충분하지만 안전을 위해)
cd /home/engine/project
tar -czf ../showmethestock_backup_$(date +%Y%m%d).tar.gz .

# 또는 git commit
git add -A
git commit -m "chore: backup before cleanup"
```

### 2단계: 안전한 순서로 정리
```bash
# 1. 1순위 실행 (로그, 백업, 보안 파일)
bash cleanup_priority_1.sh

# 2. git status 확인
git status

# 3. .gitignore 업데이트
cat >> .gitignore << 'EOF'

# Cleanup additions
*.log
backend/*.log
frontend/*.log
.coverage
notification_recipients.txt
aws_console_copy_paste.txt
backend/cache/ohlcv/*.pkl
EOF

# 4. 2순위 실행 (분석 스크립트)
bash cleanup_priority_2.sh

# 5. 3순위 실행 (폴더 정리)
bash cleanup_priority_3.sh

# 6. git commit
git add -A
git commit -m "chore: cleanup unnecessary files and update .gitignore"
```

### 3단계: 검증
```bash
# 백엔드 테스트 실행
cd backend
pytest

# 서비스 시작 테스트
cd /home/engine/project
bash local.sh  # 로컬 테스트

# 문제 없으면 배포
bash deploy-aws.sh
```

---

## 📊 예상 효과

### 즉시 효과
- **저장소 크기**: ~5.7MB 감소 (로그, 백업, 아카이브 제외)
- **파일 개수**: ~50개 감소
- **보안 위험**: 제거됨 (aws_console_copy_paste.txt, notification_recipients.txt)
- **코드베이스 명확성**: 향상

### 장기 효과
- **신입 온보딩 시간**: 20-30% 단축 (혼란스러운 파일 제거)
- **배포 속도**: 소폭 향상 (불필요한 파일 제외)
- **유지보수성**: 향상 (명확한 파일 구조)
- **보안 수준**: 향상 (민감 정보 제거)

### 선택적 효과 (cache 정리 시)
- **backend/cache/ohlcv/**: 최대 334MB 절감 가능
  - 위험: 캐시 재생성으로 API 호출량 증가
  - 권장: 90일 이상 된 파일만 선택 삭제

---

## 🔍 남겨야 할 파일 (확인됨)

### 실제 사용 중인 폴더
```
✅ backend/backfill/      # backfill_past_scans.py 등
✅ backend/backtest/      # services/backtest_service.py에서 사용
✅ backend/backtester/    # 테스트에서 참조
✅ backend/cache/         # OHLCV 캐시 (성능 최적화)
✅ backend/services/      # 핵심 비즈니스 로직
✅ backend/tests/         # 테스트 코드
✅ docs/                  # 최신 문서
```

### 실제 사용 중인 설정 파일
```
✅ .env.example           # 환경변수 예제
✅ .gitignore             # Git 설정
✅ deploy-aws.sh          # 배포 스크립트
✅ server.sh              # 서버 관리 스크립트
```

---

## 📋 체크리스트

실행 전 확인:

- [ ] git 상태 clean (`git status`)
- [ ] 백업 완료 (git commit 또는 tar.gz)
- [ ] 현재 nginx 설정 확인 (`cat /etc/nginx/sites-available/showmethestock`)
- [ ] cron job 확인 (`crontab -l`)
- [ ] .env 파일 확인
- [ ] 서버에서 실행 중인 프로세스 확인

실행 후 확인:

- [ ] pytest 통과
- [ ] 로컬 서버 시작 성공 (`bash local.sh`)
- [ ] git status 확인
- [ ] .gitignore 업데이트 적용 확인
- [ ] 배포 테스트 성공

---

## 💡 추가 권장 사항

### 1. 문서 업데이트
- `aws_console_copy_paste.txt` 내용을 `docs/infrastructure/aws-setup.md`로 이동
- `notification_recipients.txt` 내용을 환경변수 또는 DB로 이전

### 2. 캐시 관리 자동화
```bash
# cron job으로 오래된 캐시 자동 삭제
# 매주 일요일 오전 3시
0 3 * * 0 find /home/engine/project/backend/cache/ohlcv -name "*.pkl" -mtime +90 -delete
```

### 3. 로그 로테이션 설정
```bash
# logrotate 설정 추가
cat > /etc/logrotate.d/showmethestock << 'EOF'
/home/engine/project/backend/*.log
/home/engine/project/frontend/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
EOF
```

### 4. pre-commit hook 추가
```bash
# .git/hooks/pre-commit
#!/bin/bash
# Prevent committing sensitive files

if git diff --cached --name-only | grep -qE "\.backup$|\.log$|notification_recipients\.txt|aws_console_copy_paste\.txt"; then
    echo "❌ Error: Attempting to commit sensitive or backup files"
    echo "Please check your commit and update .gitignore"
    exit 1
fi
```

---

## 🚨 주의사항

### 절대 삭제하지 말 것
1. ❌ `backend/backfill/` - 실제 사용 중
2. ❌ `backend/backtest/` - 실제 사용 중
3. ❌ `backend/backtester/` - 실제 사용 중
4. ❌ `backend/cache/` - 성능 최적화에 필수
5. ❌ `backend/services/` - 핵심 비즈니스 로직
6. ❌ `backend/tests/` - 테스트 코드
7. ❌ `.env` - 실제 환경변수 (백업만 삭제)

### 신중히 삭제할 것
1. ⚠️ `archive/` - git 히스토리 확인 후
2. ⚠️ nginx 설정 파일 - 현재 production 설정 확인 후
3. ⚠️ cache 파일 - 오래된 것만 선택 삭제

---

**작성자**: AI Assistant  
**검토자**: (검토 필요)  
**승인 필요**: ✅  
**위험도**: 🟢 Low (신중한 순서 준수 시)
