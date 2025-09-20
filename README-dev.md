# 개발 환경 관리 가이드

## 📋 스크립트 개요

### 🖥️ 환경별 관리
- **`local.sh`** - 로컬 환경 관리
- **`server.sh`** - 서버 환경 관리 (SSH 원격 제어)
- **`monitor.sh`** - 로컬/서버 통합 모니터링

### 🚀 배포
- **`deploy-aws.sh`** - AWS 전체 배포 (초기 설정용)

## 🚀 빠른 시작

### 로컬 환경
```bash
# 상태 확인
./local.sh status

# 전체 시작
./local.sh start

# 전체 중지
./local.sh stop

# 재시작
./local.sh restart
```

### 서버 관리
```bash
# 서버 상태 확인
./server.sh status

# 서버 전체 시작
./server.sh start

# 코드 배포
./server.sh deploy

# 서버 재시작
./server.sh restart
```

### 모니터링
```bash
# 상태 요약
./monitor.sh summary

# 일회성 확인
./monitor.sh check

# 지속적 모니터링
./monitor.sh start
```

## 📖 상세 명령어

### local.sh (로컬 관리)
```bash
./local.sh status          # 상태 확인
./local.sh start           # 전체 시작
./local.sh stop            # 전체 중지
./local.sh restart         # 전체 재시작
./local.sh start-backend   # 백엔드만 시작
./local.sh stop-backend    # 백엔드만 중지
./local.sh start-frontend  # 프론트엔드만 시작
./local.sh stop-frontend   # 프론트엔드만 중지
./local.sh logs            # 로그 확인
./local.sh install         # 의존성 설치
```

### server.sh (서버 관리)
```bash
./server.sh status         # 상태 확인
./server.sh start          # 전체 시작
./server.sh stop           # 전체 중지
./server.sh restart        # 전체 재시작
./server.sh start-backend  # 백엔드만 시작
./server.sh stop-backend   # 백엔드만 중지
./server.sh start-frontend # 프론트엔드만 시작
./server.sh stop-frontend  # 프론트엔드만 중지
./server.sh start-scheduler # 스케줄러만 시작
./server.sh stop-scheduler  # 스케줄러만 중지
./server.sh deploy         # 코드 배포
./server.sh logs           # 로그 확인
```

### monitor.sh (모니터링)
```bash
./monitor.sh check         # 일회성 상태 확인
./monitor.sh start         # 지속적 모니터링
./monitor.sh logs          # 실시간 로그 모니터링
./monitor.sh summary       # 상태 요약
```

## 🌐 접속 URL

### 로컬 개발 환경
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8010
- **고객 스캐너**: http://localhost:3000/customer-scanner

### 서버 환경
- **웹 서비스**: https://sohntech.ai.kr
- **고객 스캐너**: https://sohntech.ai.kr/customer-scanner

## 🔧 개발 워크플로우

### 1. 개발 시작
```bash
# 로컬 환경 시작
./local.sh start

# 상태 확인
./monitor.sh summary
```

### 2. 개발 중
```bash
# 실시간 로그 모니터링
./monitor.sh logs

# 로컬 재시작 (코드 변경 후)
./local.sh restart
```

### 3. 서버 배포
```bash
# 코드 배포
./server.sh deploy

# 서버 재시작
./server.sh restart

# 배포 확인
./server.sh status
```

### 4. 개발 종료
```bash
# 로컬 환경 중지
./local.sh stop
```

## 🚨 문제 해결

### 로컬 환경 문제
```bash
# 의존성 재설치
./local.sh install

# 전체 재시작
./local.sh restart

# 로그 확인
./local.sh logs
```

### 서버 환경 문제
```bash
# 서버 상태 확인
./server.sh status

# 서버 재시작
./server.sh restart

# 서버 로그 확인
./server.sh logs
```

### 모니터링
```bash
# 전체 상태 확인
./monitor.sh check

# 지속적 모니터링 (자동 복구)
./monitor.sh start
```

## 📝 로그 파일 위치

### 로컬
- **백엔드**: `backend/backend.log`
- **프론트엔드**: `frontend/frontend.log`

### 서버
- **백엔드**: `/home/ubuntu/showmethestock/backend/backend.log`
- **프론트엔드**: `/home/ubuntu/showmethestock/frontend/frontend.log`
- **스케줄러**: `/home/ubuntu/showmethestock/scheduler.log`

## 🔄 자동화

### 지속적 모니터링
```bash
# 백그라운드에서 모니터링 시작
nohup ./monitor.sh start > monitor.log 2>&1 &
```

### 정기적 상태 확인
```bash
# 5분마다 상태 확인
watch -n 300 './monitor.sh summary'
```
