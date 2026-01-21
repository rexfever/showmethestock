# 🗂️ showmethestock 정리 프로젝트 - 문서 인덱스

> **시작 지점**: 이 문서부터 읽으세요!

## 📌 빠른 네비게이션

### 👤 역할별 추천 경로

| 역할 | 시작 문서 | 다음 문서 |
|------|----------|----------|
| 🎯 **프로젝트 리더** | [CLEANUP_SUMMARY.md](#summary) | [CLEANUP_PLAN.md](#plan) |
| 👥 **검토자** | [CLEANUP_README.md](#readme) | [CLEANUP_PLAN.md](#plan) |
| 💻 **실행 담당자** | [CLEANUP_QUICK_REFERENCE.md](#quick) | [CLEANUP_EXECUTION_GUIDE.md](#guide) |
| ⚡ **빠른 참조** | [CLEANUP_QUICK_REFERENCE.md](#quick) | - |

### 📊 상황별 추천 문서

| 상황 | 추천 문서 |
|------|----------|
| 🆕 처음 접하는 경우 | [이 문서](#overview) → [CLEANUP_README.md](#readme) |
| 📋 전체 계획 이해 | [CLEANUP_SUMMARY.md](#summary) → [CLEANUP_PLAN.md](#plan) |
| 🚀 실제 실행 시 | [CLEANUP_EXECUTION_GUIDE.md](#guide) |
| ⚡ 명령어만 빠르게 | [CLEANUP_QUICK_REFERENCE.md](#quick) |
| 🆘 문제 발생 시 | [CLEANUP_EXECUTION_GUIDE.md](#guide) (문제 해결 섹션) |

---

## 📚 문서 구조

<a name="summary"></a>
### 1. 📊 [CLEANUP_SUMMARY.md](./CLEANUP_SUMMARY.md) ⭐ 추천 시작점
**"프로젝트 전체 요약"** - 가장 먼저 읽을 문서

- ✅ 완료된 작업 요약
- 📊 분석 결과 (표 형식)
- 🎯 실행 계획 개요
- ✅ 안전장치 설명
- 🚀 빠른 시작 가이드
- 📈 예상 효과
- ⚠️ 주의사항 하이라이트

**분량**: 381줄  
**읽는 시간**: 5-10분  
**대상**: 모든 사용자 (특히 프로젝트 리더)

---

<a name="readme"></a>
### 2. 📖 [CLEANUP_README.md](./CLEANUP_README.md)
**"프로젝트 소개 및 가이드"** - 프로젝트 개요

- 📚 문서 구조 설명
- 🚀 시작하기
- 📊 정리 요약
- 🎯 주요 특징
- 🔍 상세 정보
- ⚠️ 주의사항

**분량**: 296줄  
**읽는 시간**: 10-15분  
**대상**: 처음 접하는 사용자, 검토자

---

<a name="plan"></a>
### 3. 📋 [CLEANUP_PLAN.md](./CLEANUP_PLAN.md) 📘 메인 문서
**"상세 정리 계획서"** - 가장 포괄적인 문서

- 🎯 정리 전략 및 원칙
- 🔴 1순위: 즉시 삭제 (보안/백업/로그)
- 🟡 2순위: 분석 스크립트 처리
- 🟢 3순위: 폴더 정리 및 통합
- 🔵 특별 고려사항 (cache, backfill 등)
- 📝 .gitignore 업데이트
- ⚠️ 충돌 가능성 체크
- 🎯 실행 순서 상세
- 📊 예상 효과 상세

**분량**: 611줄  
**읽는 시간**: 20-30분  
**대상**: 프로젝트 리더, 검토자, 심층 분석 필요 시

---

<a name="guide"></a>
### 4. 📖 [CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md) 🔧 실행 매뉴얼
**"단계별 실행 가이드"** - 실제 작업 시 필수

- 🎯 빠른 시작
- 📦 각 스크립트 상세 설명
- ⚠️ 주의사항 (실행 전/중/후)
- 🧪 검증 절차
- 📊 예상 결과
- 🚫 절대 하지 말 것
- 🔄 선택적 추가 정리
- 📝 정리 후 할 일
- 🆘 문제 해결 (Q&A)
- ✅ 체크리스트

**분량**: 392줄  
**읽는 시간**: 15-20분  
**대상**: 실행 담당자 (실행 전 필독)

---

<a name="quick"></a>
### 5. ⚡ [CLEANUP_QUICK_REFERENCE.md](./CLEANUP_QUICK_REFERENCE.md) 🚀 빠른 참조
**"빠른 참조 카드"** - 1페이지 요약

- ⚡ 빠른 실행 명령어
- 📊 한눈에 보는 요약 표
- 🎯 삭제 대상 요약
- ✅ 보존 대상 요약
- 🔍 검증 명령어
- 🚨 롤백 명령어
- 📈 예상 효과

**분량**: 109줄  
**읽는 시간**: 2-3분  
**대상**: 빠른 참조 필요 시

---

## 🛠️ 실행 스크립트

### [cleanup_priority_1.sh](./cleanup_priority_1.sh)
**로그, 백업, 보안 파일 제거**

- 백업 파일 삭제 (.env.backup*)
- 보안 위험 파일 삭제
- 로그 파일 삭제
- Coverage 파일 삭제

**분량**: 57줄  
**위험도**: 🟢 Low  
**실행 시간**: < 1분

---

### [cleanup_priority_2.sh](./cleanup_priority_2.sh)
**분석 스크립트 아카이브**

- 분석 스크립트 → backend/archive/analysis_scripts_2025/
- 유틸리티 스크립트 → backend/scripts/one_time_scripts/
- README 자동 생성

**분량**: 79줄  
**위험도**: 🟢 Low  
**실행 시간**: < 1분

---

### [cleanup_priority_3.sh](./cleanup_priority_3.sh)
**폴더 정리 및 통합**

- SQLite 아카이브 통합
- Nginx 설정 아카이브
- admin_scanner 삭제
- docs.zip 삭제
- README 자동 생성

**분량**: 140줄  
**위험도**: 🟡 Medium  
**실행 시간**: < 2분

---

## 🎯 추천 읽기 순서

### 🆕 처음 사용하는 경우
```
1. CLEANUP_INDEX.md (이 문서) ← 지금 여기
2. CLEANUP_SUMMARY.md         ← 전체 요약
3. CLEANUP_README.md          ← 프로젝트 소개
4. CLEANUP_PLAN.md            ← 상세 계획 (필요시)
```

### ⚡ 빠르게 시작하려면
```
1. CLEANUP_QUICK_REFERENCE.md ← 빠른 참조
2. cleanup_priority_1.sh 실행
3. cleanup_priority_2.sh 실행
4. cleanup_priority_3.sh 실행
```

### 🔍 상세히 이해하려면
```
1. CLEANUP_SUMMARY.md         ← 전체 요약
2. CLEANUP_PLAN.md            ← 상세 분석
3. CLEANUP_EXECUTION_GUIDE.md ← 실행 가이드
4. 스크립트 실행
```

---

<a name="overview"></a>
## 📊 프로젝트 개요

### 목표
showmethestock 레포지토리의 불필요한 파일을 식별하고 안전하게 정리

### 분석 결과
- **총 대상**: ~50개 파일/폴더
- **절감 크기**: ~5.7MB
- **보안 위험**: 2개 파일 식별 🔴
- **로그 파일**: 20개 (~260KB)

### 실행 방법
```bash
# 3단계로 안전하게 정리
bash cleanup_priority_1.sh  # 로그, 백업, 보안 (🟢 안전)
bash cleanup_priority_2.sh  # 분석 스크립트 (🟢 안전)
bash cleanup_priority_3.sh  # 폴더 통합 (🟡 신중)

# 검증
cd backend && pytest

# 커밋
git add -A && git commit -m "chore: cleanup unnecessary files"
```

### 예상 효과
- 📦 **크기**: 5.7MB 절감
- 🔒 **보안**: 민감 정보 제거
- 🎯 **명확성**: 불필요 파일 제거
- 🚀 **생산성**: 온보딩 시간 단축

---

## ✅ 안전성

### 보존 확인 ✅
다음 항목은 **절대 삭제되지 않습니다**:
- ✅ backend/backfill/ (실제 사용 중)
- ✅ backend/backtest/ (실제 사용 중)
- ✅ backend/backtester/ (실제 사용 중)
- ✅ backend/cache/ (필수 캐시)
- ✅ backend/services/ (핵심 로직)
- ✅ backend/tests/ (테스트)

### 롤백 가능 ✅
```bash
# 언제든 복원 가능
git reset --hard HEAD
```

### 3단계 검증 ✅
```bash
1. pytest        # 테스트 통과 확인
2. py_compile    # Import 에러 확인
3. local.sh      # 로컬 서버 시작 확인
```

---

## 📈 통계

### 문서 통계
| 파일 | 줄 수 | 크기 | 용도 |
|------|-------|------|------|
| CLEANUP_SUMMARY.md | 381줄 | ~14KB | 전체 요약 |
| CLEANUP_README.md | 296줄 | ~8.4KB | 프로젝트 소개 |
| CLEANUP_PLAN.md | 611줄 | ~17KB | 상세 계획 |
| CLEANUP_EXECUTION_GUIDE.md | 392줄 | ~9.4KB | 실행 가이드 |
| CLEANUP_QUICK_REFERENCE.md | 109줄 | ~2.9KB | 빠른 참조 |
| **총계** | **1,789줄** | **~52KB** | - |

### 스크립트 통계
| 스크립트 | 줄 수 | 대상 | 위험도 |
|---------|-------|------|--------|
| cleanup_priority_1.sh | 57줄 | 로그/백업 | 🟢 Low |
| cleanup_priority_2.sh | 79줄 | 스크립트 | 🟢 Low |
| cleanup_priority_3.sh | 140줄 | 폴더 | 🟡 Medium |
| **총계** | **276줄** | - | - |

**전체 프로젝트**: 2,065줄 코드/문서

---

## 🎓 프로젝트 하이라이트

### ✨ 특징
- ✅ **포괄적 분석**: 전체 레포지토리 스캔 (67,597개 파일 분석)
- ✅ **안전 설계**: 3단계 우선순위, 이동 우선 전략
- ✅ **자동화**: 실행 가능한 쉘 스크립트 3개
- ✅ **문서화**: 체계적인 5개 문서 (1,789줄)
- ✅ **검증**: pytest, py_compile, local.sh 3단계
- ✅ **롤백**: git으로 언제든 복원 가능

### 🎯 설계 원칙
1. **안전성 우선**: 삭제보다 이동, 단계별 진행
2. **명확한 문서화**: 각 파일의 용도와 위험도 명시
3. **자동화**: 반복 작업은 스크립트로
4. **검증**: 실행 후 반드시 테스트
5. **복구 가능**: Git으로 완전 복원 보장

---

## 🚀 시작하기

### 1️⃣ 처음 사용하는 경우
```bash
# 1. 요약 읽기 (5분)
less CLEANUP_SUMMARY.md

# 2. 프로젝트 소개 읽기 (10분)
less CLEANUP_README.md

# 3. 빠른 참조 확인 (2분)
less CLEANUP_QUICK_REFERENCE.md

# 4. 실행 가이드 읽기 (15분)
less CLEANUP_EXECUTION_GUIDE.md

# 5. 실행
bash cleanup_priority_1.sh
```

### 2️⃣ 빠르게 시작하려면
```bash
# 빠른 참조만 보고 바로 실행
cat CLEANUP_QUICK_REFERENCE.md
bash cleanup_priority_1.sh && \
bash cleanup_priority_2.sh && \
bash cleanup_priority_3.sh
```

### 3️⃣ 안전 모드 (권장)
```bash
# 1단계씩 실행하고 검증
bash cleanup_priority_1.sh
git status
cd backend && pytest && cd ..

bash cleanup_priority_2.sh
git status
cd backend && pytest && cd ..

bash cleanup_priority_3.sh
git status
cd backend && pytest && cd ..
```

---

## 📞 지원

### 문제 발생 시
1. 🆘 **즉시 롤백**: `git reset --hard HEAD`
2. 📖 **문서 참조**: [CLEANUP_EXECUTION_GUIDE.md](./CLEANUP_EXECUTION_GUIDE.md) → 문제 해결 섹션
3. 💬 **문의**: 프로젝트 리더에게 연락

### 자주 묻는 질문
- Q: 어떤 문서를 먼저 읽어야 하나요?
  - A: [CLEANUP_SUMMARY.md](#summary) 먼저, 그 다음 [CLEANUP_README.md](#readme)

- Q: 실행 시 문제가 생기면?
  - A: `git reset --hard HEAD`로 즉시 롤백하세요

- Q: Priority 3만 건너뛰어도 되나요?
  - A: 네, Priority 1, 2만 실행해도 주요 효과를 얻을 수 있습니다

---

## ✅ 준비 상태

- ✅ **분석 완료**: 전체 레포지토리 스캔 완료
- ✅ **계획 수립**: 3단계 우선순위 계획 완료
- ✅ **스크립트 작성**: 3개 실행 스크립트 완성
- ✅ **문서화 완료**: 5개 문서 작성 완료
- ✅ **.gitignore 업데이트**: 로그/캐시 패턴 추가
- ✅ **안전장치 구축**: 롤백 가능, 검증 절차 포함

**상태**: 🟢 **Ready for Execution**

---

**마지막 업데이트**: 2025-01-21  
**문서 버전**: 1.0  
**프로젝트 상태**: ✅ 실행 준비 완료
