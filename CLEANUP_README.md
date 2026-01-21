# 🧹 showmethestock 정리 프로젝트

> showmethestock 레포지토리의 불필요한 파일과 폴더를 식별하고 정리하는 프로젝트입니다.

## 📚 문서 구조

이 정리 프로젝트는 다음 4개의 문서로 구성되어 있습니다:

### 1. 📋 [CLEANUP_PLAN.md](./CLEANUP_PLAN.md) ⭐ 메인 문서
**상세 정리 계획서** - 가장 포괄적인 문서

**포함 내용**:
- 삭제 대상 파일 상세 분석 (크기, 용도, 위험도)
- 3단계 우선순위별 정리 전략
- 폴더별 상세 분석 (archive, cache, backfill 등)
- 충돌 가능성 및 주의사항
- .gitignore 업데이트 제안
- 예상 효과 및 장기 효과

**대상 독자**: 프로젝트 리더, 검토자, 정리 작업 담당자

---

### 2. 📖 [CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md) ⭐ 실행 가이드
**단계별 실행 매뉴얼** - 실제 작업 시 참조

**포함 내용**:
- 빠른 시작 가이드
- 각 스크립트 상세 설명
- 검증 절차 (테스트, 배포)
- 문제 해결 (Q&A)
- 체크리스트

**대상 독자**: 실제 정리 작업을 수행하는 개발자

---

### 3. ⚡ [CLEANUP_QUICK_REFERENCE.md](./CLEANUP_QUICK_REFERENCE.md) 
**빠른 참조 카드** - 1페이지 요약

**포함 내용**:
- 빠른 실행 명령어
- 한눈에 보는 요약 표
- 삭제/보존 대상 리스트
- 검증 및 롤백 명령어

**대상 독자**: 빠른 참조가 필요한 모든 사용자

---

### 4. 🛠️ 실행 스크립트 (3개)
- `cleanup_priority_1.sh` - 로그, 백업, 보안 파일 제거
- `cleanup_priority_2.sh` - 분석 스크립트 아카이브
- `cleanup_priority_3.sh` - 폴더 정리 및 통합

**실행 가능**, README 자동 생성 포함

---

## 🚀 시작하기

### 처음 사용하는 경우
1. **[CLEANUP_PLAN.md](./CLEANUP_PLAN.md)** 먼저 읽기
2. **[CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md)** 참조하며 실행
3. **[CLEANUP_QUICK_REFERENCE.md](./CLEANUP_QUICK_REFERENCE.md)** 필요시 빠른 참조

### 빠르게 시작하려면
1. **[CLEANUP_QUICK_REFERENCE.md](./CLEANUP_QUICK_REFERENCE.md)** 읽기
2. 스크립트 실행:
   ```bash
   bash cleanup_priority_1.sh
   bash cleanup_priority_2.sh
   bash cleanup_priority_3.sh
   ```

---

## 📊 정리 요약

### 목표
- **파일 감소**: ~50개 파일 제거/이동
- **크기 절감**: ~5.7MB (로그, 백업, 아카이브)
- **보안 개선**: 민감 정보 파일 제거
- **명확성 향상**: 불필요한 파일로 인한 혼란 제거

### 대상
| 카테고리 | 파일 수 | 크기 | 조치 |
|---------|--------|------|------|
| 로그 파일 | 20개 | ~260KB | 삭제 |
| 백업 파일 | 3개 | ~2.5KB | 삭제 |
| 보안 위험 | 2개 | ~2.2KB | 삭제 |
| 분석 스크립트 | 11개 | ~70KB | 아카이브 |
| 폴더 통합 | 5개 | ~5MB | 통합/정리 |

### 위험도
🟢 **Low** - 신중한 순서로 진행하면 안전함

---

## ⚡ 빠른 실행

```bash
# 1단계: 로그, 백업, 보안 파일 제거
bash cleanup_priority_1.sh

# 2단계: 분석 스크립트 아카이브
bash cleanup_priority_2.sh

# 3단계: 폴더 정리 및 통합
bash cleanup_priority_3.sh

# 검증
cd backend && pytest

# 커밋
git add -A
git commit -m "chore: cleanup unnecessary files and update .gitignore"
```

---

## 🎯 주요 특징

### ✅ 안전성
- 3단계 우선순위로 위험 최소화
- 삭제가 아닌 **아카이브 이동** 우선
- Git으로 언제든 복원 가능
- 실제 사용 중인 폴더는 보존 (backfill, backtest 등)

### ✅ 자동화
- 실행 가능한 쉘 스크립트 제공
- 자동 README 생성
- .gitignore 자동 업데이트

### ✅ 문서화
- 4개의 체계적인 문서
- 각 파일의 용도 및 위험도 명시
- 롤백 및 문제 해결 가이드

---

## 🔍 상세 정보

### 삭제 대상 (Priority 1)
```
✗ backend/.env.backup*                    # 백업 파일 (git으로 충분)
✗ aws_console_copy_paste.txt              # AWS 정책 JSON (보안 위험)
✗ notification_recipients.txt             # 전화번호 (개인정보)
✗ *.log (20개 파일)                       # 실행 시마다 재생성
✗ backend/.coverage                       # 테스트 커버리지 (재생성 가능)
```

### 아카이브 이동 (Priority 2)
```
analyze_v2_winrate.py                     → backend/archive/analysis_scripts_2025/
analyze_v2_winrate_by_horizon.py          → backend/archive/analysis_scripts_2025/
analyze_november_regime_cached.py         → backend/archive/analysis_scripts_2025/
analyze_november_regime_with_csv.py       → backend/archive/analysis_scripts_2025/
analyze_optimal_conditions.py             → backend/archive/analysis_scripts_2025/
analyze_regime_v4_july_nov.py             → backend/archive/analysis_scripts_2025/

check_aws_v2_data.py                      → backend/scripts/one_time_scripts/
check_v2_scan_data.py                     → backend/scripts/one_time_scripts/
create_admin_user.py                      → backend/scripts/one_time_scripts/
create_cache_data.py                      → backend/scripts/one_time_scripts/
create_regime_table_sqlite.py             → backend/scripts/one_time_scripts/
```

### 폴더 통합 (Priority 3)
```
archive/old_sqlite_*                      → archive/old_archives_consolidated/
archive/temp_cleanup_20251123/            → 삭제
nginx_config*                             → archive/old_nginx_configs/
backend/admin_scanner/                    → 삭제 (사용 안함)
docs.zip                                  → 삭제 (docs/ 폴더 존재)
```

### 보존 (절대 삭제 금지)
```
✓ backend/backfill/          # backfill_past_scans.py 등 실제 사용
✓ backend/backtest/          # services/backtest_service.py에서 참조
✓ backend/backtester/        # 테스트에서 참조
✓ backend/cache/             # 334MB, 67K 파일 - 성능 최적화 필수
✓ backend/services/          # 핵심 비즈니스 로직
✓ backend/tests/             # 테스트 코드
```

---

## ⚠️ 중요 주의사항

### 실행 전 확인
- [ ] Git 상태가 clean인지 확인: `git status`
- [ ] Cron job에서 사용 안하는지 확인: `crontab -l`
- [ ] Deploy 스크립트에서 참조 안하는지 확인

### 실행 후 확인
- [ ] 테스트 통과: `cd backend && pytest`
- [ ] Import 에러 없음: `python -m py_compile *.py`
- [ ] 로컬 서버 시작: `bash local.sh`

### 절대 하지 말 것
```bash
# ❌ 위험! 전체 캐시 삭제 (API 호출량 폭증)
rm -rf backend/cache/

# ❌ 위험! 실제 .env 삭제
rm backend/.env

# ❌ 위험! 실제 사용 중인 폴더 삭제
rm -rf backend/backfill/
rm -rf backend/backtest/
rm -rf backend/backtester/
```

---

## 🔄 롤백 (문제 발생 시)

```bash
# 전체 롤백
git reset --hard HEAD

# 특정 파일만 복원
git checkout HEAD -- backend/analyze_v2_winrate.py

# 특정 폴더 복원
git checkout HEAD -- backend/admin_scanner/
```

---

## 📈 예상 효과

### 즉시 효과
- **저장소 크기**: ~5.7MB 감소
- **파일 개수**: ~50개 감소
- **보안 위험**: 제거 (민감 정보 파일 삭제)
- **코드베이스 명확성**: 향상

### 장기 효과
- **신입 온보딩 시간**: 20-30% 단축
- **배포 속도**: 소폭 향상
- **유지보수성**: 향상
- **보안 수준**: 향상

---

## 📞 문의 및 문제 해결

### 문서 참조 순서
1. **[CLEANUP_QUICK_REFERENCE.md](./CLEANUP_QUICK_REFERENCE.md)** - 빠른 참조
2. **[CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md)** - 문제 해결 섹션
3. **[CLEANUP_PLAN.md](./CLEANUP_PLAN.md)** - 충돌 가능성 섹션

### 문제 발생 시
1. 먼저 **롤백**: `git reset --hard HEAD`
2. 문서의 "문제 해결" 섹션 참조
3. 필요시 프로젝트 리더에게 문의

---

## ✅ 체크리스트

- [ ] 모든 문서를 읽었음
- [ ] Git 상태 확인 완료
- [ ] 백업 완료 (git commit)
- [ ] Cron job 확인 완료
- [ ] 실행 순서 이해함
- [ ] 롤백 방법 숙지함
- [ ] Priority 1 실행 완료
- [ ] Priority 2 실행 완료
- [ ] Priority 3 실행 완료
- [ ] 테스트 통과 확인
- [ ] Git commit 완료

---

**프로젝트 시작일**: 2025-01-21  
**마지막 업데이트**: 2025-01-21  
**상태**: ✅ Ready for execution  
**위험도**: 🟢 Low (순서 준수 시)

---

## 📝 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-01-21 | 1.0 | 초기 계획 및 문서 작성 |

---

**작성자**: AI Assistant  
**검토자**: (검토 필요)  
**승인자**: (승인 필요)
