# 코드 유지보수 가이드

## 현재 브랜치 구조

### 브랜치 분리 완료
- **`main`** (로컬/서버): `1cdce0e` - 스캐너 V2 및 버전별 저장 기능
- **`feature/project-cleanup`** (GitHub): `28197c3` - 프로젝트 정리 및 보안 강화 (10개 커밋)

## 유지보수 방법

### 1. 현재 코드(main)에서 작업 계속하기

```bash
# 로컬에서
git checkout main
git reset --hard 1cdce0e  # 필요시 현재 커밋으로 고정

# 작업 후 커밋
git add .
git commit -m "작업 내용"
git push origin main  # 또는 새로운 브랜치로 푸시
```

### 2. 서버에서 main 브랜치 유지

```bash
# 서버에서
cd /home/ubuntu/showmethestock
git checkout main
git reset --hard 1cdce0e  # 현재 커밋으로 고정
```

### 3. GitHub의 변경사항 확인 (필요시)

```bash
# feature/project-cleanup 브랜치 확인
git fetch origin
git checkout feature/project-cleanup
git log --oneline -10

# 다시 main으로 돌아오기
git checkout main
```

### 4. 선택적 병합 (필요시)

```bash
# feature/project-cleanup의 특정 변경사항만 가져오기
git checkout main
git cherry-pick <커밋해시>  # 필요한 커밋만 선택
```

## 주의사항

1. **origin/main은 현재 `28197c3`을 가리킴**
   - 로컬/서버의 main은 `1cdce0e`로 유지
   - `git pull origin main` 실행 시 충돌 발생 가능

2. **새로운 작업은 별도 브랜치로**
   ```bash
   git checkout -b feature/new-feature
   # 작업 후
   git push origin feature/new-feature
   ```

3. **서버 배포 시**
   ```bash
   # 서버에서
   git fetch origin
   git checkout main
   git reset --hard <작업한_커밋해시>
   ```

## 브랜치 상태 요약

- **로컬 main**: `1cdce0e` (스캐너 V2 기능)
- **서버 main**: `1cdce0e` (스캐너 V2 기능)
- **origin/main**: `28197c3` (프로젝트 정리)
- **origin/feature/project-cleanup**: `28197c3` (프로젝트 정리)

## 권장 워크플로우

1. 새로운 기능 개발: `feature/xxx` 브랜치 생성
2. 현재 main 유지: `1cdce0e` 기준으로 작업
3. 필요시 병합: `feature/project-cleanup`의 변경사항 선택적 적용

