# AWS 배포 메뉴얼 - 스톡인사이트

## 📋 목차
1. [사전 준비사항](#사전-준비사항)
2. [AWS 계정 설정](#aws-계정-설정)
3. [EC2 인스턴스 생성](#ec2-인스턴스-생성)
4. [서버 환경 구성](#서버-환경-구성)
5. [프로젝트 배포](#프로젝트-배포)
6. [Nginx 설정](#nginx-설정)
7. [서비스 자동화](#서비스-자동화)
8. [도메인 및 SSL 설정](#도메인-및-ssl-설정)
9. [모니터링 및 유지보수](#모니터링-및-유지보수)
10. [문제 해결](#문제-해결)

---

## 사전 준비사항

### 필수 요구사항
- AWS 계정 (신용카드 등록 필요)
- 도메인 (선택사항, Route 53에서 구매 가능)
- GitHub 계정
- SSH 클라이언트 (Windows: PuTTY, Mac/Linux: 기본 터미널)

### 예상 비용
- **EC2 t2.micro**: 무료 (1년간)
- **도메인**: $12/년 (Route 53)
- **총 비용**: 월 $1 (도메인 비용만)

---

## AWS 계정 설정

### 1. AWS 계정 생성
1. [AWS Console](https://aws.amazon.com) 접속
2. "Create an AWS Account" 클릭
3. 계정 정보 입력 (이메일, 비밀번호, 계정명)
4. **중요**: 신용카드 등록 (무료 티어 한도 내에서는 과금 안됨)
5. 전화번호 인증 완료

### 2. IAM 사용자 생성 (보안 강화)
1. AWS Console → IAM → Users → Create user
2. 사용자명: `stock-finder-admin`
3. 권한: `AdministratorAccess` (개발용)
4. Access Key 생성 및 다운로드 (CSV 파일 보관)

### 3. 리전 선택
- **권장**: `ap-northeast-2` (서울)
- AWS Console 우상단에서 리전 변경

---

## EC2 인스턴스 생성

### 1. EC2 대시보드 접속
1. AWS Console → EC2 → Launch Instance

### 2. AMI 선택
- **Name**: Ubuntu Server 22.04 LTS
- **Architecture**: 64-bit (x86)
- **Type**: Free tier eligible

### 3. 인스턴스 타입
- **Instance type**: t2.micro (Free tier eligible)
- **vCPUs**: 1
- **Memory**: 1 GiB
- **Storage**: EBS only

### 4. 키 페어 생성
1. "Create new key pair" 클릭
2. **Key pair name**: `stock-finder-key`
3. **Key pair type**: RSA
4. **Private key file format**: .pem
5. "Create key pair" 클릭
6. **중요**: .pem 파일을 안전한 곳에 보관

### 5. 네트워크 설정
- **VPC**: Default VPC
- **Subnet**: Default subnet
- **Auto-assign public IP**: Enable
- **Security group**: Create new security group
  - **Name**: `stock-finder-sg`
  - **Description**: Security group for Stock Finder
  - **Inbound rules**:
    - SSH (22) - My IP
    - HTTP (80) - Anywhere (0.0.0.0/0)
    - HTTPS (443) - Anywhere (0.0.0.0/0)
    - Custom TCP (8010) - Anywhere (0.0.0.0/0) (개발용)

### 6. 스토리지 설정
- **Volume type**: gp3
- **Size**: 30 GiB (Free tier)
- **Encryption**: Default encryption

### 7. 인스턴스 시작
1. "Launch instance" 클릭
2. 인스턴스 ID 확인 및 대기 (약 2-3분)

---

## 서버 환경 구성

### 1. SSH 접속
```bash
# Mac/Linux
chmod 400 stock-finder-key.pem
ssh -i stock-finder-key.pem ubuntu@YOUR_EC2_PUBLIC_IP

# Windows (PuTTY)
# .pem 파일을 .ppk로 변환 후 접속
```

### 2. 시스템 업데이트
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip
```

### 3. Python 3.11 설치
```bash
# Python 3.11 설치
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# 기본 Python 버전 설정
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1
```

### 4. Node.js 18 설치
```bash
# NodeSource 저장소 추가
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

# Node.js 설치
sudo apt-get install -y nodejs

# 버전 확인
node --version  # v18.x.x
npm --version   # 9.x.x
```

### 5. Nginx 설치
```bash
sudo apt install -y nginx

# Nginx 시작 및 자동 시작 설정
sudo systemctl start nginx
sudo systemctl enable nginx

# 방화벽 설정
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw --force enable
```

### 6. 필요한 시스템 패키지 설치
```bash
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
sudo apt install -y pkg-config libhdf5-dev libhdf5-serial-dev
sudo apt install -y libatlas-base-dev libopenblas-dev liblapack-dev
```

---

## 프로젝트 배포

### 1. 프로젝트 클론
```bash
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/stock-finder.git
cd stock-finder
```

### 2. 백엔드 설정
```bash
cd backend

# Python 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
nano .env
```

### 3. 환경변수 설정 (.env 파일)
```bash
# Kiwoom API 설정
APP_KEY=your_app_key_here
APP_SECRET=your_app_secret_here
API_BASE=https://api.kiwoom.com
TOKEN_PATH=/oauth2/token

# 스캔 설정
UNIVERSE_KOSPI=100
UNIVERSE_KOSDAQ=100
RSI_THRESHOLD=43
MACD_OSC_MIN=-20
VOL_MA5_MULT=0.9
RSI_MODE=standard
MIN_SIGNALS=2

# KakaoTalk 설정 (선택사항)
KAKAO_API_KEY=your_kakao_api_key
KAKAO_SENDER_KEY=your_sender_key
KAKAO_TEMPLATE_ID=your_template_id
```

### 4. 프론트엔드 빌드
```bash
cd ../frontend

# 의존성 설치
npm install

# 환경변수 설정
nano .env.local
```

### 5. 프론트엔드 환경변수 (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://YOUR_EC2_IP:8010
```

### 6. 프론트엔드 빌드
```bash
npm run build
```

### 7. 백엔드 테스트
```bash
cd ../backend
source venv/bin/activate

# 백엔드 서버 시작 (테스트용)
uvicorn main:app --host 0.0.0.0 --port 8010

# 다른 터미널에서 테스트
curl http://YOUR_EC2_IP:8010/scan
```

---

## Nginx 설정

### 1. Nginx 설정 파일 생성
```bash
sudo nano /etc/nginx/sites-available/stock-finder
```

### 2. Nginx 설정 내용
```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;
    
    # 보안 헤더
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # 프론트엔드 (Next.js 정적 파일)
    location / {
        root /home/ubuntu/stock-finder/frontend/out;
        try_files $uri $uri/ /index.html;
        
        # 캐싱 설정
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # 백엔드 API
    location /api/ {
        proxy_pass http://127.0.0.1:8010/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS 설정
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
        
        # OPTIONS 요청 처리
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
            add_header Access-Control-Max-Age 1728000;
            add_header Content-Type 'text/plain; charset=utf-8';
            add_header Content-Length 0;
            return 204;
        }
    }
    
    # 랜딩 페이지
    location /landing/ {
        alias /home/ubuntu/stock-finder/landing/;
        index index.html;
    }
    
    # 로그 설정
    access_log /var/log/nginx/stock-finder.access.log;
    error_log /var/log/nginx/stock-finder.error.log;
}
```

### 3. Nginx 설정 활성화
```bash
# 기본 설정 비활성화
sudo rm /etc/nginx/sites-enabled/default

# 새 설정 활성화
sudo ln -s /etc/nginx/sites-available/stock-finder /etc/nginx/sites-enabled/

# Nginx 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx
```

---

## 서비스 자동화

### 1. 백엔드 서비스 파일 생성
```bash
sudo nano /etc/systemd/system/stock-finder-backend.service
```

### 2. 서비스 파일 내용
```ini
[Unit]
Description=Stock Finder Backend API
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/stock-finder/backend
Environment=PATH=/home/ubuntu/stock-finder/backend/venv/bin
Environment=PYTHONPATH=/home/ubuntu/stock-finder
ExecStart=/home/ubuntu/stock-finder/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8010 --workers 1
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=stock-finder-backend

[Install]
WantedBy=multi-user.target
```

### 3. 서비스 시작 및 설정
```bash
# systemd 데몬 리로드
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable stock-finder-backend

# 서비스 시작
sudo systemctl start stock-finder-backend

# 서비스 상태 확인
sudo systemctl status stock-finder-backend

# 로그 확인
sudo journalctl -u stock-finder-backend -f
```

### 4. 자동 배포 스크립트 생성
```bash
nano /home/ubuntu/deploy.sh
```

### 5. 배포 스크립트 내용
```bash
#!/bin/bash

# 배포 스크립트
echo "Starting deployment..."

# 프로젝트 디렉토리로 이동
cd /home/ubuntu/stock-finder

# 최신 코드 가져오기
git pull origin main

# 백엔드 재시작
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart stock-finder-backend

# 프론트엔드 재빌드
cd ../frontend
npm install
npm run build

# Nginx 재시작
sudo systemctl restart nginx

echo "Deployment completed!"
```

### 6. 스크립트 실행 권한 부여
```bash
chmod +x /home/ubuntu/deploy.sh
```

---

## 도메인 및 SSL 설정

### 1. Route 53에서 도메인 구매 (선택사항)
1. AWS Console → Route 53 → Registered domains
2. "Register domain" 클릭
3. 원하는 도메인명 입력 및 구매

### 2. DNS 설정
1. Route 53 → Hosted zones
2. 도메인 선택 → Create record
3. **Record type**: A
4. **Value**: EC2 Public IP
5. **TTL**: 300

### 3. SSL 인증서 설정 (Let's Encrypt)
```bash
# Certbot 설치
sudo apt install -y certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com

# 자동 갱신 테스트
sudo certbot renew --dry-run
```

### 4. Nginx SSL 설정 업데이트
```bash
sudo nano /etc/nginx/sites-available/stock-finder
```

### 5. SSL 설정 추가
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL 인증서 설정
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL 보안 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 기존 설정들...
}

# HTTP에서 HTTPS로 리다이렉트
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 모니터링 및 유지보수

### 1. 로그 모니터링
```bash
# 백엔드 로그
sudo journalctl -u stock-finder-backend -f

# Nginx 로그
sudo tail -f /var/log/nginx/stock-finder.access.log
sudo tail -f /var/log/nginx/stock-finder.error.log

# 시스템 로그
sudo tail -f /var/log/syslog
```

### 2. 시스템 리소스 모니터링
```bash
# CPU 및 메모리 사용량
htop

# 디스크 사용량
df -h

# 네트워크 연결
netstat -tulpn
```

### 3. 백업 스크립트 생성
```bash
nano /home/ubuntu/backup.sh
```

### 4. 백업 스크립트 내용
```bash
#!/bin/bash

# 백업 디렉토리 생성
BACKUP_DIR="/home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 프로젝트 백업
cp -r /home/ubuntu/stock-finder $BACKUP_DIR/

# 환경변수 백업
cp /home/ubuntu/stock-finder/backend/.env $BACKUP_DIR/

# Nginx 설정 백업
cp /etc/nginx/sites-available/stock-finder $BACKUP_DIR/

# 7일 이상 된 백업 삭제
find /home/ubuntu/backups -type d -mtime +7 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

### 5. 정기 백업 설정 (Cron)
```bash
# Crontab 편집
crontab -e

# 매일 새벽 2시에 백업 실행
0 2 * * * /home/ubuntu/backup.sh
```

---

## 문제 해결

### 1. 일반적인 문제들

#### 백엔드 서비스가 시작되지 않는 경우
```bash
# 서비스 상태 확인
sudo systemctl status stock-finder-backend

# 로그 확인
sudo journalctl -u stock-finder-backend -n 50

# 수동으로 서비스 시작 테스트
cd /home/ubuntu/stock-finder/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8010
```

#### Nginx 설정 오류
```bash
# Nginx 설정 테스트
sudo nginx -t

# Nginx 로그 확인
sudo tail -f /var/log/nginx/error.log

# Nginx 재시작
sudo systemctl restart nginx
```

#### 포트 충돌 문제
```bash
# 포트 사용 확인
sudo netstat -tulpn | grep :8010
sudo netstat -tulpn | grep :80

# 프로세스 종료
sudo kill -9 PID_NUMBER
```

### 2. 성능 최적화

#### 메모리 부족 시
```bash
# 스왑 파일 생성
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### 디스크 공간 부족 시
```bash
# 불필요한 파일 정리
sudo apt autoremove -y
sudo apt autoclean
sudo journalctl --vacuum-time=7d

# 로그 파일 정리
sudo truncate -s 0 /var/log/nginx/*.log
```

### 3. 보안 강화

#### 방화벽 설정
```bash
# UFW 상태 확인
sudo ufw status

# SSH 포트 변경 (선택사항)
sudo nano /etc/ssh/sshd_config
# Port 2222로 변경

# SSH 재시작
sudo systemctl restart ssh
```

#### 자동 보안 업데이트
```bash
# unattended-upgrades 설치
sudo apt install -y unattended-upgrades

# 설정 활성화
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 배포 완료 체크리스트

- [ ] AWS 계정 생성 및 EC2 인스턴스 생성
- [ ] 서버 환경 구성 (Python, Node.js, Nginx)
- [ ] 프로젝트 클론 및 의존성 설치
- [ ] 환경변수 설정
- [ ] 백엔드 서비스 등록 및 시작
- [ ] 프론트엔드 빌드
- [ ] Nginx 설정 및 활성화
- [ ] 도메인 연결 (선택사항)
- [ ] SSL 인증서 설정 (선택사항)
- [ ] 모니터링 설정
- [ ] 백업 스크립트 설정

---

## 연락처 및 지원

- **프로젝트**: 스톡인사이트 (Stock Insight)
- **회사**: 손테크 (Sontech)
- **이메일**: chicnova@gmail.com
- **전화**: 010-4220-0956
- **주소**: 서울시 송파구 올림픽로 435, 115동 1804호(신천동, 파크리오)

---

**마지막 업데이트**: 2025년 9월 5일
**버전**: 1.0
