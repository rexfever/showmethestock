# 🚀 시작하기 - showmethestock 정리 프로젝트

> **이 문서부터 읽으세요!** 가장 빠르게 시작하는 방법을 안내합니다.

---

## ⚡ 30초 요약

```bash
# 1. 요약 읽기 (5분)
cat CLEANUP_SUMMARY.md

# 2. 실행 (3가지 방법 중 선택)

# 방법 1: 한 번에 실행 (권장하지 않음)
bash cleanup_all.sh

# 방법 2: 단계별 실행 (권장 ⭐)
bash cleanup_priority_1.sh  # 로그/백업 제거
bash cleanup_priority_2.sh  # 스크립트 정리
bash cleanup_priority_3.sh  # 폴더 통합

# 방법 3: 안전 모드 (가장 안전 ⭐⭐)
bash cleanup_priority_1.sh && git status && cd backend && pytest && cd ..
# 문제 없으면 다음 단계 진행
```

---

## 📚 문서 선택 가이드

### "빠르게 시작하고 싶어요" ⚡
1. **읽기**: [CLEANUP_QUICK_REFERENCE.md](./CLEANUP_QUICK_REFERENCE.md) (2분)
2. **실행**: `bash cleanup_priority_1.sh` (1분)
3. **검증**: `git status && cd backend && pytest`

### "전체 계획을 이해하고 싶어요" 📋
1. **읽기**: [CLEANUP_SUMMARY.md](./CLEANUP_SUMMARY.md) (10분)
2. **읽기**: [CLEANUP_PLAN.md](./CLEANUP_PLAN.md) (30분)
3. **실행**: [CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md) 참조

### "안전하게 하나씩 실행하고 싶어요" 🛡️
1. **읽기**: [CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md) (15분)
2. **실행**: Priority 1 → 검증 → Priority 2 → 검증 → Priority 3
3. **커밋**: 모든 검증 통과 후

### "전체 구조를 파악하고 싶어요" 🗂️
1. **읽기**: [CLEANUP_INDEX.md](./CLEANUP_INDEX.md) (5분)
2. **네비게이션**: 인덱스에서 필요한 문서로 이동

---

## 📊 한눈에 보기

| 문서 | 용도 | 읽는 시간 | 대상 |
|------|------|----------|------|
| [CLEANUP_START_HERE.md](./CLEANUP_START_HERE.md) | 👈 **시작점** | 2분 | 모두 |
| [CLEANUP_QUICK_REFERENCE.md](./CLEANUP_QUICK_REFERENCE.md) | ⚡ 빠른 참조 | 2분 | 빠른 실행 |
| [CLEANUP_SUMMARY.md](./CLEANUP_SUMMARY.md) | 📊 전체 요약 | 10분 | 리더 |
| [CLEANUP_README.md](./CLEANUP_README.md) | 📖 프로젝트 소개 | 15분 | 검토자 |
| [CLEANUP_PLAN.md](./CLEANUP_PLAN.md) | 📋 상세 계획 | 30분 | 분석 필요 시 |
| [CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md) | 🔧 실행 가이드 | 20분 | 실행 담당자 |
| [CLEANUP_INDEX.md](./CLEANUP_INDEX.md) | 🗂️ 문서 인덱스 | 5분 | 네비게이션 |

---

## 🎯 무엇을 정리하나요?

### 삭제 대상 (총 ~5.7MB)
- ❌ **로그 파일** (20개, ~260KB) - 실행 시마다 재생성
- ❌ **백업 파일** (3개, ~2.5KB) - Git으로 관리됨
- ❌ **보안 위험 파일** (2개, ~2.2KB) 🔴 - AWS 정책, 전화번호
- ❌ **Coverage 파일** (1개, 53KB) - pytest 실행 시 재생성
- 📦 **분석 스크립트** (11개, ~70KB) - 아카이브로 이동
- 📦 **아카이브 통합** (여러 폴더, ~5MB) - 정리 및 통합

### 보존 대상 (절대 삭제 안됨!)
- ✅ backend/backfill/ - 실제 사용 중
- ✅ backend/backtest/ - 실제 사용 중
- ✅ backend/backtester/ - 실제 사용 중
- ✅ backend/cache/ - 필수 캐시 (334MB)
- ✅ backend/services/ - 핵심 로직
- ✅ backend/tests/ - 테스트

---

## 🚀 실행 방법

### 방법 1: 한 번에 실행
```bash
bash cleanup_all.sh
```
- ✅ 인터랙티브 진행 (각 단계에서 확인)
- ✅ 자동 검증 옵션
- ⚠️ 처음 사용 시 권장하지 않음

### 방법 2: 단계별 실행 (⭐ 권장)
```bash
# Priority 1: 로그, 백업, 보안 파일 (안전)
bash cleanup_priority_1.sh
git status  # 확인

# Priority 2: 분석 스크립트 (안전)
bash cleanup_priority_2.sh
git status  # 확인

# Priority 3: 폴더 통합 (신중)
bash cleanup_priority_3.sh
git status  # 확인
```

### 방법 3: 안전 모드 (⭐⭐ 가장 안전)
```bash
# Priority 1 실행 및 검증
bash cleanup_priority_1.sh
git status
cd backend && pytest && cd ..
# 문제 있으면: git reset --hard HEAD

# Priority 2 실행 및 검증
bash cleanup_priority_2.sh
git status
cd backend && pytest && cd ..
# 문제 있으면: git reset --hard HEAD

# Priority 3 실행 및 검증
bash cleanup_priority_3.sh
git status
cd backend && pytest && cd ..
# 문제 있으면: git reset --hard HEAD
```

---

## ✅ 안전성 보장

### 1. 롤백 가능 🔄
```bash
# 언제든 이전 상태로 복원
git reset --hard HEAD

# 특정 파일만 복원
git checkout HEAD -- backend/analyze_v2_winrate.py
```

### 2. 검증 절차 ✅
```bash
# 테스트
cd backend && pytest

# Import 체크
python -m py_compile *.py

# 로컬 서버
bash local.sh
```

### 3. 보존 확인 ✅
실제 사용 중인 폴더는 **절대 삭제되지 않습니다**:
- backfill/, backtest/, backtester/ (서비스에서 사용)
- backend/cache/ (성능 최적화 필수)
- backend/services/, backend/tests/ (핵심 코드)

---

## 🆘 문제 발생 시

### 즉시 롤백
```bash
git reset --hard HEAD
```

### 문서 참조
1. [CLEANUP_QUICK_REFERENCE.md](./CLEANUP_QUICK_REFERENCE.md) - 롤백 명령어
2. [CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md) - 문제 해결 섹션
3. [CLEANUP_PLAN.md](./CLEANUP_PLAN.md) - 충돌 가능성 섹션

---

## 📈 예상 효과

- 📦 **크기**: ~5.7MB 감소
- 🗑️ **파일**: ~50개 감소
- 🔒 **보안**: 민감 정보 제거 (AWS 정책, 전화번호)
- 🎯 **명확성**: 불필요 파일 제거로 코드베이스 명확화
- 🚀 **생산성**: 신입 온보딩 시간 20-30% 단축

---

## ⚡ 가장 빠른 시작

```bash
# 1. 이 문서 읽기 (지금 여기!)
cat CLEANUP_START_HERE.md

# 2. 빠른 참조 확인
cat CLEANUP_QUICK_REFERENCE.md

# 3. Priority 1만 실행 (가장 안전)
bash cleanup_priority_1.sh

# 4. 확인
git status
cd backend && pytest

# 5. 문제 없으면 commit
git add -A
git commit -m "chore: cleanup logs, backups, and security files (Priority 1)"
```

---

## 🎯 다음 단계

### 실행 후
1. ✅ `git status` - 변경 사항 확인
2. ✅ `cd backend && pytest` - 테스트 통과 확인
3. ✅ `bash local.sh` - 로컬 서버 시작 확인
4. ✅ Git commit

### 더 알아보기
- 📊 전체 요약: [CLEANUP_SUMMARY.md](./CLEANUP_SUMMARY.md)
- 📋 상세 계획: [CLEANUP_PLAN.md](./CLEANUP_PLAN.md)
- 🔧 실행 가이드: [CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md)

---

## 📞 도움말

- 💬 질문/문의: 프로젝트 리더에게 연락
- 📖 문서: [CLEANUP_INDEX.md](./CLEANUP_INDEX.md)에서 모든 문서 확인
- 🆘 긴급: `git reset --hard HEAD`로 즉시 롤백

---

**프로젝트 상태**: ✅ 실행 준비 완료  
**위험도**: 🟢 Low (순서 준수 시)  
**마지막 업데이트**: 2025-01-21

**시작하세요!** 👉 `cat CLEANUP_QUICK_REFERENCE.md`
