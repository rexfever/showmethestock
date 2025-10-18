# 배포 스크립트 가이드

이 디렉토리는 안전하고 체계적인 배포를 위한 스크립트들을 포함합니다.

## 📁 파일 구조

```
scripts/
├── deploy.sh              # 통합 배포 스크립트
├── deploy-backend.sh      # 백엔드 전용 배포 스크립트
├── deploy-frontend.sh     # 프론트엔드 전용 배포 스크립트
├── rollback.sh            # 롤백 스크립트
└── README.md              # 이 파일
```

## 🚀 사용법

### 1. 통합 배포

```bash
# 로컬 전체 배포 (백엔드 + 프론트엔드)
./scripts/deploy.sh local all

# 백엔드만 배포
./scripts/deploy.sh local backend

# 프론트엔드만 배포
./scripts/deploy.sh local frontend
```

### 2. 개별 배포

```bash
# 백엔드만 배포
./scripts/deploy-backend.sh

# 프론트엔드만 배포
./scripts/deploy-frontend.sh
```

### 3. 롤백

```bash
# 전체 롤백
./scripts/rollback.sh local all

# 백엔드만 롤백
./scripts/rollback.sh local backend

# 프론트엔드만 롤백
./scripts/rollback.sh local frontend
```

## 🔧 배포 프로세스

### 백엔드 배포 프로세스

1. **코드 검증**: Python 문법 검사
2. **의존성 설치**: pip install -r requirements.txt
3. **기존 프로세스 종료**: 실행 중인 백엔드 프로세스 종료
4. **서버 시작**: uvicorn으로 백엔드 서버 시작

### 프론트엔드 배포 프로세스

1. **의존성 설치**: npm ci --production=false
2. **빌드 캐시 삭제**: rm -rf .next
3. **빌드**: npm run build
4. **기존 프로세스 종료**: 실행 중인 프론트엔드 프로세스 종료
5. **서버 시작**: Next.js 개발 서버 시작

## ⚠️ 주의사항

### 배포 전 체크리스트

- [ ] Git 상태 확인 (커밋되지 않은 변경사항)
- [ ] 테스트 통과 확인
- [ ] 환경변수 설정 확인

### 배포 중 주의사항

- 배포 중에는 다른 작업을 하지 마세요
- 오류 발생 시 스크립트가 자동으로 중단됩니다

### 배포 후 체크리스트

- [ ] 서비스 헬스 체크 통과
- [ ] 주요 기능 테스트
- [ ] 로그 확인

## 🔄 롤백 가이드

### 언제 롤백해야 하나요?

- 배포 후 서비스가 정상 작동하지 않을 때
- 심각한 버그가 발견되었을 때
- 성능 저하가 발생했을 때

### 롤백 프로세스

1. **문제 확인**: 서비스 상태 확인, 로그 분석
2. **롤백 실행**: `./scripts/rollback.sh [환경] [대상]`
3. **롤백 후 검증**: 서비스 정상 작동 확인

## 🛠️ 트러블슈팅

### 자주 발생하는 문제

1. **포트 충돌**
   ```bash
   # 포트 사용 중인 프로세스 확인
   lsof -i :3000
   lsof -i :8010
   
   # 프로세스 종료
   kill -9 [PID]
   ```

2. **의존성 설치 실패**
   ```bash
   # 캐시 삭제 후 재설치
   npm cache clean --force
   pip cache purge
   ```

3. **권한 문제**
   ```bash
   # 스크립트 실행 권한 부여
   chmod +x scripts/*.sh
   ```

## 📞 지원

배포 관련 문제가 발생하면:

1. 로그 파일 확인
2. 트러블슈팅 가이드 참조
3. 필요시 롤백 실행

---

**⚠️ 중요**: 항상 배포 스크립트를 사용하여 배포하세요. 수동 배포는 실수와 문제를 야기할 수 있습니다.
