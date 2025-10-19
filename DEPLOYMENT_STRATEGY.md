# 🚀 AWS 서버 무중단 배포 전략

## 📊 현재 상황 분석

### ⚠️ 현재 문제점
- **단일 서버 운영** → 배포 실패 시 서비스 중단
- **직접 서비스 재시작** → 다운타임 발생
- **롤백 시간 지연** → 문제 발생 시 복구 시간 오래 걸림
- **DB 덮어쓰기 위험** → 데이터 손실 가능성

## 🎯 제안하는 배포 전략

## 1. 🔵 Blue-Green 배포 (권장)

### 구조
```
현재 운영: Blue 환경 (포트 8010, 3000)
새 배포: Green 환경 (포트 8011, 3001)
로드밸런서: Nginx로 트래픽 전환
```

### 장점
- ✅ **무중단 배포** (0초 다운타임)
- ✅ **즉시 롤백** 가능
- ✅ **안전한 테스트** 환경
- ✅ **DB 보호** (기존 DB 유지)

### 사용법
```bash
# Blue-Green 배포 실행
./scripts/blue-green-deploy.sh

# 특정 환경으로 배포
./scripts/blue-green-deploy.sh blue
./scripts/blue-green-deploy.sh green
```

## 2. 🏥 헬스체크 및 모니터링

### 기능
- **실시간 서비스 상태 모니터링**
- **응답 시간 측정**
- **DB 연결 상태 확인**
- **자동 알림 시스템**

### 사용법
```bash
# 전체 환경 헬스체크
./scripts/health-check.sh all

# 특정 환경 헬스체크
./scripts/health-check.sh blue
./scripts/health-check.sh green
```

## 3. 🔄 자동 롤백 시스템

### 기능
- **헬스체크 실패 시 자동 롤백**
- **설정 가능한 실패 임계값**
- **롤백 상태 알림**
- **수동 개입 시점 알림**

### 설정
```bash
# 환경변수 설정
export HEALTH_CHECK_INTERVAL=30  # 헬스체크 간격 (초)
export MAX_FAILURES=3           # 최대 실패 횟수
export ROLLBACK_TIMEOUT=300     # 롤백 타임아웃 (초)

# 자동 롤백 모니터링 시작
./scripts/auto-rollback.sh
```

## 4. 💾 데이터베이스 마이그레이션

### 기능
- **안전한 DB 스키마 변경**
- **자동 백업 및 복원**
- **마이그레이션 검증**
- **롤백 지원**

### 사용법
```bash
# 마이그레이션 실행
./scripts/database-migration.sh migrate

# 롤백 실행
./scripts/database-migration.sh rollback

# 스키마 검증
./scripts/database-migration.sh validate

# 백업 생성
./scripts/database-migration.sh backup
```

## 🔧 배포 프로세스

### 1. 사전 준비
```bash
# 1. 코드 커밋 및 푸시
git add .
git commit -m "배포 준비"
git push origin main

# 2. 헬스체크 실행
./scripts/health-check.sh all

# 3. DB 백업
./scripts/database-migration.sh backup
```

### 2. Blue-Green 배포
```bash
# 1. 새 환경에 배포
./scripts/blue-green-deploy.sh

# 2. 헬스체크 확인
./scripts/health-check.sh all

# 3. 수동 테스트 (선택사항)
curl http://sohntech.ai.kr
curl http://sohntech.ai.kr/api/health
```

### 3. 모니터링 설정
```bash
# 자동 롤백 모니터링 시작 (백그라운드)
nohup ./scripts/auto-rollback.sh > auto-rollback.log 2>&1 &

# 주기적 헬스체크 (cron 설정)
echo "*/5 * * * * /home/ubuntu/showmethestock/scripts/health-check.sh all" | crontab -
```

## 📋 배포 체크리스트

### 배포 전
- [ ] 코드 커밋 및 푸시 완료
- [ ] 테스트 통과 확인
- [ ] DB 백업 생성
- [ ] 현재 환경 헬스체크 통과
- [ ] 롤백 계획 수립

### 배포 중
- [ ] 새 환경 서비스 시작 확인
- [ ] 헬스체크 통과 확인
- [ ] 트래픽 전환 테스트
- [ ] 이전 환경 정리

### 배포 후
- [ ] 전체 시스템 헬스체크
- [ ] 주요 기능 테스트
- [ ] 모니터링 설정
- [ ] 알림 시스템 확인

## 🚨 비상 계획

### 배포 실패 시
1. **자동 롤백 실행**
   ```bash
   ./scripts/auto-rollback.sh
   ```

2. **수동 롤백 실행**
   ```bash
   ./scripts/rollback.sh server all
   ```

3. **DB 복원**
   ```bash
   ./scripts/database-migration.sh rollback
   ```

### 서비스 장애 시
1. **헬스체크 실행**
   ```bash
   ./scripts/health-check.sh all
   ```

2. **서비스 재시작**
   ```bash
   sudo systemctl restart stock-finder-backend-blue
   sudo systemctl restart stock-finder-frontend-blue
   ```

3. **Nginx 재시작**
   ```bash
   sudo systemctl restart nginx
   ```

## 📊 모니터링 대시보드

### 주요 메트릭
- **서비스 상태**: Blue/Green 환경별 상태
- **응답 시간**: 백엔드/프론트엔드 응답 시간
- **DB 상태**: 연결 상태 및 레코드 수
- **에러율**: HTTP 에러 응답 비율
- **리소스 사용률**: CPU, 메모리, 디스크

### 알림 설정
- **Slack/Discord**: 서비스 장애 알림
- **이메일**: 배포 완료/실패 알림
- **SMS**: 긴급 장애 알림

## 🔐 보안 고려사항

### DB 보호
- **자동 백업**: 매일 자동 백업 생성
- **암호화**: 민감한 데이터 암호화
- **접근 제어**: DB 접근 권한 관리

### 서비스 보안
- **HTTPS**: SSL/TLS 인증서 적용
- **방화벽**: 필요한 포트만 개방
- **로그 모니터링**: 보안 이벤트 로깅

## 💡 추가 개선 사항

### 단기 (1-2주)
- [ ] Blue-Green 배포 구현
- [ ] 헬스체크 시스템 구축
- [ ] 자동 롤백 시스템 구축
- [ ] DB 마이그레이션 시스템 구축

### 중기 (1-2개월)
- [ ] 로드밸런서 도입 (ALB)
- [ ] 컨테이너화 (Docker)
- [ ] CI/CD 파이프라인 구축
- [ ] 모니터링 대시보드 구축

### 장기 (3-6개월)
- [ ] 마이크로서비스 아키텍처
- [ ] 쿠버네티스 도입
- [ ] 멀티 리전 배포
- [ ] 자동 스케일링

## 🎯 결론

**Blue-Green 배포 방식**을 통해 **무중단 배포**를 구현하고, **헬스체크 및 자동 롤백 시스템**으로 **서비스 안정성**을 보장할 수 있습니다.

이 전략을 통해:
- ✅ **다운타임 제거** (0초 다운타임)
- ✅ **배포 위험 최소화** (즉시 롤백 가능)
- ✅ **서비스 안정성 향상** (자동 모니터링)
- ✅ **데이터 보호** (자동 백업 및 복원)

**현재 단일 서버 환경에서도 안전하고 효율적인 배포가 가능합니다!** 🚀
