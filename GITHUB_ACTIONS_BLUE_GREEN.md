# 🚀 GitHub Actions Blue-Green 배포 가이드

## 📋 개요

GitHub Actions를 활용한 **Blue-Green 무중단 배포** 시스템을 구축했습니다. 이 시스템은 **0초 다운타임**으로 안전하고 효율적인 배포를 제공합니다.

## 🔧 구현된 워크플로우

### 1. 🔵 Blue-Green 배포 (`blue-green-deploy.yml`)

#### **트리거:**
- **자동**: `main` 브랜치에 push 시
- **수동**: GitHub Actions 탭에서 수동 실행 가능

#### **주요 기능:**
- ✅ **환경 자동 감지** (Blue ↔ Green)
- ✅ **데이터베이스 자동 백업**
- ✅ **무중단 배포** (0초 다운타임)
- ✅ **자동 헬스체크**
- ✅ **트래픽 전환**
- ✅ **이전 환경 정리**
- ✅ **배포 후 검증**

#### **배포 프로세스:**
```
1. 사전 검증 → 2. DB 백업 → 3. 새 환경 배포 → 4. 트래픽 전환 → 5. 이전 환경 정리 → 6. 검증
```

### 2. 🔄 긴급 롤백 (`rollback.yml`)

#### **트리거:**
- **수동**: GitHub Actions 탭에서 수동 실행

#### **주요 기능:**
- ✅ **즉시 롤백** (몇 초 내)
- ✅ **롤백 사유 기록**
- ✅ **현재 상태 백업**
- ✅ **안전한 트래픽 전환**
- ✅ **롤백 후 검증**

#### **사용법:**
1. GitHub Actions → `Emergency Rollback` 선택
2. 롤백 대상 환경 선택 (Blue/Green)
3. 롤백 사유 입력
4. 실행

### 3. 🏥 헬스 모니터링 (`health-monitor.yml`)

#### **트리거:**
- **자동**: 매 5분마다 실행
- **수동**: GitHub Actions 탭에서 수동 실행

#### **주요 기능:**
- ✅ **실시간 서비스 모니터링**
- ✅ **데이터베이스 상태 확인**
- ✅ **시스템 리소스 모니터링**
- ✅ **응답 시간 측정**
- ✅ **자동 알림**

## 🚀 사용법

### **자동 배포 (권장)**

#### **1. 코드 푸시로 자동 배포:**
```bash
# 코드 변경 후
git add .
git commit -m "새 기능 추가"
git push origin main

# GitHub Actions가 자동으로 Blue-Green 배포 실행
```

#### **2. 배포 진행 상황 확인:**
1. GitHub 저장소 → **Actions** 탭
2. **Blue-Green Deploy to EC2** 워크플로우 클릭
3. 실시간 배포 로그 확인

### **수동 배포**

#### **1. 특정 환경으로 배포:**
1. GitHub Actions → **Blue-Green Deploy to EC2**
2. **Run workflow** 클릭
3. **Target environment** 선택:
   - `auto`: 자동 감지 (권장)
   - `blue`: Blue 환경으로 강제 배포
   - `green`: Green 환경으로 강제 배포

#### **2. 긴급 롤백:**
1. GitHub Actions → **Emergency Rollback**
2. **Run workflow** 클릭
3. **Target environment** 선택 (Blue/Green)
4. **Rollback reason** 입력
5. 실행

### **모니터링**

#### **1. 자동 모니터링:**
- 매 5분마다 자동 실행
- 문제 발생 시 GitHub Actions에서 확인 가능

#### **2. 수동 모니터링:**
1. GitHub Actions → **Health Monitor**
2. **Run workflow** 클릭
3. **Check duration** 설정 (기본: 5분)

## 📊 배포 상태 확인

### **GitHub Actions 대시보드:**
- **녹색 체크**: 배포 성공
- **빨간 X**: 배포 실패
- **노란 원**: 배포 진행 중

### **서버 상태 확인:**
```bash
# 현재 환경 확인
curl http://sohntech.ai.kr

# 백엔드 헬스체크
curl http://sohntech.ai.kr/api/health

# 서비스 상태 확인
ssh ubuntu@sohntech.ai.kr 'sudo systemctl status stock-finder-backend-blue'
ssh ubuntu@sohntech.ai.kr 'sudo systemctl status stock-finder-backend-green'
```

## 🔧 설정 요구사항

### **GitHub Secrets 설정:**
다음 secrets가 설정되어 있어야 합니다:

```
EC2_HOST=sohntech.ai.kr
EC2_USERNAME=ubuntu
EC2_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----...
```

### **서버 설정:**
- **SSH 접근** 가능
- **systemd 서비스** 지원
- **Nginx** 설치 및 설정
- **Python 3.11+** 및 **Node.js 18+**

## 📈 모니터링 및 알림

### **자동 모니터링:**
- **매 5분마다** 헬스체크 실행
- **서비스 상태**, **DB 연결**, **시스템 리소스** 확인
- **문제 감지 시** GitHub Actions에서 실패 표시

### **수동 알림 설정 (선택사항):**
```yaml
# Slack 알림 예시
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## 🚨 문제 해결

### **배포 실패 시:**

#### **1. 로그 확인:**
1. GitHub Actions → 실패한 워크플로우 클릭
2. 실패한 단계의 로그 확인

#### **2. 수동 롤백:**
1. GitHub Actions → **Emergency Rollback**
2. 이전 환경으로 롤백 실행

#### **3. 서버 직접 확인:**
```bash
# 서버 접속
ssh ubuntu@sohntech.ai.kr

# 서비스 상태 확인
sudo systemctl status stock-finder-backend-blue
sudo systemctl status stock-finder-backend-green

# 로그 확인
sudo journalctl -u stock-finder-backend-blue -f
sudo journalctl -u stock-finder-backend-green -f
```

### **일반적인 문제들:**

#### **1. 서비스 시작 실패:**
- **원인**: 의존성 설치 실패, 포트 충돌
- **해결**: 로그 확인 후 수동 재시작

#### **2. 헬스체크 실패:**
- **원인**: 서비스 응답 지연, DB 연결 문제
- **해결**: 서비스 재시작, DB 상태 확인

#### **3. 트래픽 전환 실패:**
- **원인**: Nginx 설정 오류, 새 환경 문제
- **해결**: 자동 롤백 실행

## 📋 배포 체크리스트

### **배포 전:**
- [ ] 코드 커밋 및 푸시 완료
- [ ] 테스트 통과 확인
- [ ] GitHub Secrets 설정 확인
- [ ] 서버 연결 상태 확인

### **배포 중:**
- [ ] GitHub Actions 로그 모니터링
- [ ] 각 단계별 성공 확인
- [ ] 헬스체크 통과 확인

### **배포 후:**
- [ ] 웹사이트 접속 확인
- [ ] 주요 기능 테스트
- [ ] 모니터링 시스템 확인
- [ ] 이전 환경 정리 확인

## 🎯 장점

### **✅ 무중단 배포:**
- **0초 다운타임**으로 서비스 중단 없음
- **사용자 경험** 향상
- **비즈니스 연속성** 보장

### **✅ 안전한 롤백:**
- **즉시 롤백** 가능 (몇 초 내)
- **자동 롤백** 시스템
- **데이터 손실 방지**

### **✅ 자동화:**
- **GitHub Actions** 기반 완전 자동화
- **수동 개입 최소화**
- **일관된 배포 프로세스**

### **✅ 모니터링:**
- **실시간 헬스체크**
- **자동 알림 시스템**
- **상세한 로그 기록**

## 🚀 결론

**GitHub Actions Blue-Green 배포 시스템**을 통해:

- ✅ **무중단 배포** 구현
- ✅ **자동화된 배포 프로세스**
- ✅ **안전한 롤백 시스템**
- ✅ **실시간 모니터링**

**이제 안전하고 효율적인 배포가 완전히 자동화되었습니다!** 🎉
