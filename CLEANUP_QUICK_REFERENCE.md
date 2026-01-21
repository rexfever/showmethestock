# 🗑️ Cleanup Quick Reference

> 빠른 참조용 - 자세한 내용은 [CLEANUP_PLAN.md](./CLEANUP_PLAN.md) 참조

## ⚡ 빠른 실행

```bash
# 3단계로 안전하게 정리
bash cleanup_priority_1.sh  # 로그, 백업, 보안 파일
bash cleanup_priority_2.sh  # 분석 스크립트 아카이브
bash cleanup_priority_3.sh  # 폴더 정리

# 테스트
cd backend && pytest

# 커밋
git add -A
git commit -m "chore: cleanup unnecessary files"
```

## 📊 한눈에 보기

| 우선순위 | 대상 | 크기 | 위험도 | 시간 |
|---------|------|------|--------|------|
| 1 | 로그/백업/보안 파일 | ~260KB | 🟢 Low | < 1분 |
| 2 | 분석 스크립트 | ~70KB | 🟢 Low | < 1분 |
| 3 | 아카이브/설정 통합 | ~5MB | 🟡 Medium | < 2분 |

## 🎯 삭제 대상 요약

### 🔴 즉시 삭제 (Priority 1)
```
✗ backend/.env.backup*                    (백업 파일)
✗ aws_console_copy_paste.txt              (보안 위험)
✗ notification_recipients.txt             (개인정보)
✗ *.log                                   (로그 파일)
✗ backend/.coverage                       (커버리지)
```

### 📦 아카이브 이동 (Priority 2)
```
→ analyze_*.py                            → backend/archive/analysis_scripts_2025/
→ check_*.py, create_*.py                 → backend/scripts/one_time_scripts/
```

### 🗂️ 통합/정리 (Priority 3)
```
→ archive/old_sqlite_*                    → archive/old_archives_consolidated/
→ nginx_config*                           → archive/old_nginx_configs/
✗ backend/admin_scanner/                  (사용 안함)
✗ docs.zip                                (docs/ 폴더 존재)
```

## ✅ 보존 (절대 삭제 금지)

```
✓ backend/backfill/          # 실제 사용 중
✓ backend/backtest/          # 실제 사용 중
✓ backend/backtester/        # 실제 사용 중
✓ backend/cache/             # 필수 캐시
✓ backend/services/          # 핵심 로직
✓ backend/tests/             # 테스트
✓ .env                       # 환경변수
```

## 🔍 검증 명령어

```bash
# 테스트
cd backend && pytest

# Import 체크
python -m py_compile *.py

# 로컬 서버
bash local.sh

# Git 상태
git status
```

## 🚨 롤백 (문제 발생 시)

```bash
# 전체 롤백
git reset --hard HEAD

# 특정 파일 복원
git checkout HEAD -- backend/analyze_v2_winrate.py
```

## 📈 예상 효과

- 파일 수: **-50개**
- 크기: **-5.7MB**
- 보안: **✅ 개선** (민감 정보 제거)
- 명확성: **✅ 향상** (혼란 파일 제거)

## 🔗 관련 문서

- 📋 [CLEANUP_PLAN.md](./CLEANUP_PLAN.md) - 상세 계획
- 📖 [CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md) - 실행 가이드
- 🛠️ `cleanup_priority_1.sh` - 스크립트 1
- 🛠️ `cleanup_priority_2.sh` - 스크립트 2
- 🛠️ `cleanup_priority_3.sh` - 스크립트 3

---

**마지막 업데이트**: 2025-01-21
