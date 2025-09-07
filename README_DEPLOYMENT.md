# AWS 배포 가이드 - 스톡인사이트

## 🚀 빠른 배포

### 1. 초기 배포 (처음 한 번만)
```bash
./deploy-aws.sh [EC2_PUBLIC_IP] [KEY_FILE_PATH]
```

**예시:**
```bash
./deploy-aws.sh 3.34.123.456 ~/Downloads/stock-finder-key.pem
```

### 2. 코드 업데이트 배포 (매번)
```bash
./quick-deploy.sh [EC2_PUBLIC_IP] [KEY_FILE_PATH]
```

**예시:**
```bash
./quick-deploy.sh 3.34.123.456 ~/Downloads/stock-finder-key.pem
```

---

## 📋 사전 준비사항

### AWS에서 준비할 것들
1. **EC2 인스턴스 생성**
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: t2.micro (무료 티어)
   - Key pair: 새로 생성 (예: `stock-finder-key`)
   - Security group: SSH(22), HTTP(80), HTTPS(443), Custom TCP(8010)

2. **키 파일 다운로드**
   - EC2 Console → Key Pairs → 다운로드
   - 파일명: `stock-finder-key.pem`

---

## 🔧 스크립트 기능

### `deploy-aws.sh` (초기 배포)
- ✅ 서버 환경 구성 (Python 3.11, Node.js 18, Nginx)
- ✅ 프로젝트 클론 및 의존성 설치
- ✅ 환경변수 설정
- ✅ Nginx 설정
- ✅ 백엔드 서비스 등록
- ✅ 프론트엔드 빌드
- ✅ 자동 배포 스크립트 생성

### `quick-deploy.sh` (코드 업데이트)
- ✅ 최신 코드 가져오기
- ✅ 백엔드 재시작
- ✅ 프론트엔드 재빌드
- ✅ Nginx 재시작

---

## 📱 배포 후 접속 정보

### 웹 서비스
- **프론트엔드**: `http://[EC2_IP]`
- **백엔드 API**: `http://[EC2_IP]:8010`
- **랜딩 페이지**: `http://[EC2_IP]/landing/`

### API 엔드포인트
- **스캔**: `GET http://[EC2_IP]:8010/scan`
- **유니버스**: `GET http://[EC2_IP]:8010/universe`
- **포지션**: `GET http://[EC2_IP]:8010/positions`

---

## 🛠️ 관리 명령어

### 서비스 관리
```bash
# 서비스 상태 확인
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo systemctl status stock-finder-backend'

# 서비스 재시작
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo systemctl restart stock-finder-backend'

# 서비스 중지
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo systemctl stop stock-finder-backend'
```

### 로그 확인
```bash
# 백엔드 로그
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo journalctl -u stock-finder-backend -f'

# Nginx 로그
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo tail -f /var/log/nginx/stock-finder.access.log'
```

### 코드 업데이트
```bash
# 원격 배포 스크립트 실행
ssh -i [KEY_FILE] ubuntu@[EC2_IP] '/home/ubuntu/deploy.sh'
```

---

## 🔍 문제 해결

### 일반적인 문제들

#### 1. SSH 연결 실패
```bash
# 키 파일 권한 확인
chmod 400 [KEY_FILE]

# 연결 테스트
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'echo "연결 성공"'
```

#### 2. 서비스 시작 실패
```bash
# 로그 확인
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo journalctl -u stock-finder-backend -n 50'

# 수동 시작 테스트
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'cd /home/ubuntu/showmethestock/backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8010'
```

#### 3. Nginx 설정 오류
```bash
# 설정 테스트
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo nginx -t'

# Nginx 재시작
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo systemctl restart nginx'
```

#### 4. 포트 충돌
```bash
# 포트 사용 확인
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo netstat -tulpn | grep :8010'
```

---

## 📊 모니터링

### 시스템 리소스
```bash
# CPU 및 메모리 사용량
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'htop'

# 디스크 사용량
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'df -h'

# 네트워크 연결
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'netstat -tulpn'
```

### 서비스 상태
```bash
# 모든 서비스 상태
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo systemctl status stock-finder-backend nginx'

# 서비스 로그
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo journalctl -u stock-finder-backend --since "1 hour ago"'
```

---

## 🔐 보안 설정

### 방화벽 상태
```bash
# UFW 상태 확인
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo ufw status'
```

### SSL 인증서 (선택사항)
```bash
# Let's Encrypt 설치
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo apt install -y certbot python3-certbot-nginx'

# SSL 인증서 발급 (도메인이 있는 경우)
ssh -i [KEY_FILE] ubuntu@[EC2_IP] 'sudo certbot --nginx -d your-domain.com'
```

---

## 💰 비용 정보

### AWS 무료 티어
- **EC2 t2.micro**: 1년간 무료 (750시간/월)
- **EBS 스토리지**: 30GB 무료
- **데이터 전송**: 1GB/월 무료

### 예상 비용 (무료 티어 이후)
- **EC2 t2.micro**: 약 $8.50/월
- **EBS 30GB**: 약 $3.00/월
- **총 비용**: 약 $11.50/월

---

## 📞 지원

- **프로젝트**: 스톡인사이트 (Stock Insight)
- **회사**: 손테크 (Sontech)
- **이메일**: chicnova@gmail.com
- **전화**: 010-4220-0956

---

**마지막 업데이트**: 2025년 9월 5일



