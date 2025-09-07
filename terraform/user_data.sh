#!/bin/bash

# EC2 인스턴스 초기화 스크립트
# 이 스크립트는 EC2 인스턴스가 시작될 때 자동으로 실행됩니다.

set -e

# 로그 파일 설정
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "=== Stock Finder 서버 초기화 시작 ==="

# 시스템 업데이트
echo "시스템을 업데이트합니다..."
apt-get update
apt-get upgrade -y

# 기본 패키지 설치
echo "기본 패키지를 설치합니다..."
apt-get install -y curl wget git unzip build-essential software-properties-common

# Python 3.11 설치
echo "Python 3.11을 설치합니다..."
add-apt-repository ppa:deadsnakes/ppa -y
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Python 기본 버전 설정
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# 필요한 시스템 패키지 설치
apt-get install -y libssl-dev libffi-dev python3-dev
apt-get install -y pkg-config libhdf5-dev libhdf5-serial-dev
apt-get install -y libatlas-base-dev libopenblas-dev liblapack-dev

# Node.js 18 설치
echo "Node.js 18을 설치합니다..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

# Nginx 설치
echo "Nginx를 설치합니다..."
apt-get install -y nginx
systemctl start nginx
systemctl enable nginx

# 방화벽 설정
echo "방화벽을 설정합니다..."
ufw allow 'Nginx Full'
ufw allow OpenSSH
ufw --force enable

# 프로젝트 클론
echo "프로젝트를 클론합니다..."
cd /home/ubuntu
git clone ${github_repo} showmethestock
cd showmethestock

# 백엔드 설정
echo "백엔드를 설정합니다..."
cd backend

# Python 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip

# 의존성 설치
pip install -r requirements.txt

# 환경변수 파일 생성
echo "환경변수 파일을 생성합니다..."
cat > .env << 'ENVEOF'
# Kiwoom API 설정
APP_KEY=JOk5fK6y436f8snVDvw8h0ii8PxnBxZE8QGf-m6Nk1s
APP_SECRET=MQ5i_x4reWBXTon9ntuW56fvPcgoN_xEmJNSpF9l3ks
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
ENVEOF

# 프론트엔드 설정
echo "프론트엔드를 설정합니다..."
cd ../frontend

# 의존성 설치
npm install

# 환경변수 파일 생성
cat > .env.local << 'ENVEOF'
NEXT_PUBLIC_API_URL=http://localhost:8010
ENVEOF

# 프론트엔드 빌드
npm run build

# Nginx 설정
echo "Nginx를 설정합니다..."
cat > /etc/nginx/sites-available/stock-finder << 'NGINXEOF'
server {
    listen 80;
    server_name _;
    
    # 보안 헤더
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # 프론트엔드 (Next.js 정적 파일)
    location / {
        root /home/ubuntu/showmethestock/frontend/out;
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
        alias /home/ubuntu/showmethestock/landing/;
        index index.html;
    }
    
    # 로그 설정
    access_log /var/log/nginx/stock-finder.access.log;
    error_log /var/log/nginx/stock-finder.error.log;
}
NGINXEOF

# 기본 설정 비활성화
rm -f /etc/nginx/sites-enabled/default

# 새 설정 활성화
ln -sf /etc/nginx/sites-available/stock-finder /etc/nginx/sites-enabled/

# Nginx 설정 테스트
nginx -t

# Nginx 재시작
systemctl restart nginx

# 백엔드 서비스 등록
echo "백엔드 서비스를 등록합니다..."
cat > /etc/systemd/system/stock-finder-backend.service << 'SERVICEEOF'
[Unit]
Description=Stock Finder Backend API
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/showmethestock/backend
Environment=PATH=/home/ubuntu/showmethestock/backend/venv/bin
Environment=PYTHONPATH=/home/ubuntu/showmethestock
ExecStart=/home/ubuntu/showmethestock/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8010 --workers 1
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=stock-finder-backend

[Install]
WantedBy=multi-user.target
SERVICEEOF

# systemd 데몬 리로드
systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
systemctl enable stock-finder-backend

# 서비스 시작
systemctl start stock-finder-backend

# 배포 스크립트 생성
echo "배포 스크립트를 생성합니다..."
cat > /home/ubuntu/deploy.sh << 'DEPLOYEOF'
#!/bin/bash

# 배포 스크립트
echo "Starting deployment..."

# 프로젝트 디렉토리로 이동
cd /home/ubuntu/showmethestock

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
DEPLOYEOF

# 실행 권한 부여
chmod +x /home/ubuntu/deploy.sh

# CloudWatch 에이전트 설치 (선택사항)
echo "CloudWatch 에이전트를 설치합니다..."
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E amazon-cloudwatch-agent.deb

# 서비스 상태 확인
echo "서비스 상태를 확인합니다..."
sleep 10

if systemctl is-active --quiet stock-finder-backend; then
    echo "✅ 백엔드 서비스가 성공적으로 시작되었습니다"
else
    echo "❌ 백엔드 서비스 시작에 실패했습니다"
    journalctl -u stock-finder-backend -n 20
fi

if systemctl is-active --quiet nginx; then
    echo "✅ Nginx가 성공적으로 시작되었습니다"
else
    echo "❌ Nginx 시작에 실패했습니다"
    systemctl status nginx
fi

echo "=== Stock Finder 서버 초기화 완료 ==="
echo "프론트엔드: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "백엔드 API: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8010"
echo "랜딩 페이지: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/landing/"



