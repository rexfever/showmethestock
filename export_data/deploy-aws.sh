#!/bin/bash

# AWS 배포 스크립트 - 스톡인사이트
# 사용법: ./deploy-aws.sh [EC2_PUBLIC_IP] [KEY_FILE_PATH]

set -e  # 오류 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 사용법 출력
usage() {
    echo "사용법: $0 <EC2_PUBLIC_IP> <KEY_FILE_PATH>"
    echo "예시: $0 3.34.123.456 ~/Downloads/stock-finder-key.pem"
    exit 1
}

# 인자 확인
if [ $# -ne 2 ]; then
    usage
fi

EC2_IP=$1
KEY_FILE=$2

# 키 파일 존재 확인
if [ ! -f "$KEY_FILE" ]; then
    log_error "키 파일을 찾을 수 없습니다: $KEY_FILE"
    exit 1
fi

# 키 파일 권한 설정
chmod 400 "$KEY_FILE"

log_info "AWS 배포를 시작합니다..."
log_info "EC2 IP: $EC2_IP"
log_info "키 파일: $KEY_FILE"

# SSH 연결 테스트
log_info "SSH 연결을 테스트합니다..."
if ! ssh -i "$KEY_FILE" -o ConnectTimeout=10 -o StrictHostKeyChecking=no ubuntu@$EC2_IP "echo 'SSH 연결 성공'" > /dev/null 2>&1; then
    log_error "SSH 연결에 실패했습니다. EC2 IP와 키 파일을 확인해주세요."
    exit 1
fi
log_success "SSH 연결 성공"

# 서버 환경 구성
log_info "서버 환경을 구성합니다..."

ssh -i "$KEY_FILE" ubuntu@$EC2_IP << 'EOF'
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 시스템 업데이트
log_info "시스템을 업데이트합니다..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip build-essential

# Python 3.11 설치
log_info "Python 3.11을 설치합니다..."
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Python 기본 버전 설정
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# 필요한 시스템 패키지 설치
sudo apt install -y libssl-dev libffi-dev python3-dev
sudo apt install -y pkg-config libhdf5-dev libhdf5-serial-dev
sudo apt install -y libatlas-base-dev libopenblas-dev liblapack-dev

# Node.js 18 설치
log_info "Node.js 18을 설치합니다..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Nginx 설치
log_info "Nginx를 설치합니다..."
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# 방화벽 설정
log_info "방화벽을 설정합니다..."
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw --force enable

log_success "서버 환경 구성 완료"
EOF

log_success "서버 환경 구성 완료"

# 프로젝트 배포
log_info "프로젝트를 배포합니다..."

ssh -i "$KEY_FILE" ubuntu@$EC2_IP << 'EOF'
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 기존 프로젝트 디렉토리 제거 (있다면)
if [ -d "/home/ubuntu/showmethestock" ]; then
    log_warning "기존 프로젝트 디렉토리를 제거합니다..."
    rm -rf /home/ubuntu/showmethestock
fi

# 프로젝트 클론
log_info "프로젝트를 클론합니다..."
cd /home/ubuntu
git clone https://github.com/rexfever/showmethestock.git
cd showmethestock

# 백엔드 설정
log_info "백엔드를 설정합니다..."
cd backend

# Python 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip

# 의존성 설치
pip install -r requirements.txt

# 환경변수 파일 생성
log_info "환경변수 파일을 생성합니다..."
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

log_success "백엔드 설정 완료"

# 프론트엔드 설정
log_info "프론트엔드를 설정합니다..."
cd ../frontend

# 의존성 설치
npm install

# 환경변수 파일 생성
cat > .env.local << 'ENVEOF'
NEXT_PUBLIC_API_URL=http://EC2_IP_PLACEHOLDER:8010
ENVEOF

# EC2 IP로 교체
sed -i "s/EC2_IP_PLACEHOLDER/$EC2_IP/g" .env.local

# 프론트엔드 빌드
npm run build

log_success "프론트엔드 설정 완료"
EOF

log_success "프로젝트 배포 완료"

# Nginx 설정
log_info "Nginx를 설정합니다..."

ssh -i "$KEY_FILE" ubuntu@$EC2_IP << EOF
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "\${BLUE}[INFO]\${NC} \$1"
}

log_success() {
    echo -e "\${GREEN}[SUCCESS]\${NC} \$1"
}

log_warning() {
    echo -e "\${YELLOW}[WARNING]\${NC} \$1"
}

log_error() {
    echo -e "\${RED}[ERROR]\${NC} \$1"
}

# Nginx 설정 파일 생성
log_info "Nginx 설정 파일을 생성합니다..."
sudo tee /etc/nginx/sites-available/stock-finder > /dev/null << 'NGINXEOF'
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
        try_files \$uri \$uri/ /index.html;
        
        # 캐싱 설정
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # 백엔드 API
    location /api/ {
        proxy_pass http://127.0.0.1:8010/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # CORS 설정
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
        
        # OPTIONS 요청 처리
        if (\$request_method = 'OPTIONS') {
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
sudo rm -f /etc/nginx/sites-enabled/default

# 새 설정 활성화
sudo ln -sf /etc/nginx/sites-available/stock-finder /etc/nginx/sites-enabled/

# Nginx 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx

log_success "Nginx 설정 완료"
EOF

log_success "Nginx 설정 완료"

# 백엔드 서비스 등록
log_info "백엔드 서비스를 등록합니다..."

ssh -i "$KEY_FILE" ubuntu@$EC2_IP << 'EOF'
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 백엔드 서비스 파일 생성
log_info "백엔드 서비스 파일을 생성합니다..."
sudo tee /etc/systemd/system/stock-finder-backend.service > /dev/null << 'SERVICEEOF'
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
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable stock-finder-backend

# 서비스 시작
sudo systemctl start stock-finder-backend

# 서비스 상태 확인
sleep 5
if sudo systemctl is-active --quiet stock-finder-backend; then
    log_success "백엔드 서비스가 성공적으로 시작되었습니다"
else
    log_error "백엔드 서비스 시작에 실패했습니다"
    sudo journalctl -u stock-finder-backend -n 20
    exit 1
fi

log_success "백엔드 서비스 등록 완료"
EOF

log_success "백엔드 서비스 등록 완료"

# 배포 스크립트 생성
log_info "배포 스크립트를 생성합니다..."

ssh -i "$KEY_FILE" ubuntu@$EC2_IP << 'EOF'
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 배포 스크립트 생성
log_info "배포 스크립트를 생성합니다..."
tee /home/ubuntu/deploy.sh > /dev/null << 'DEPLOYEOF'
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

log_success "배포 스크립트 생성 완료"
EOF

log_success "배포 스크립트 생성 완료"

# 최종 테스트
log_info "배포를 테스트합니다..."

# 백엔드 API 테스트
if curl -s "http://$EC2_IP:8010/scan" > /dev/null; then
    log_success "백엔드 API 테스트 성공"
else
    log_warning "백엔드 API 테스트 실패 (서비스가 아직 시작 중일 수 있음)"
fi

# 프론트엔드 테스트
if curl -s "http://$EC2_IP" > /dev/null; then
    log_success "프론트엔드 테스트 성공"
else
    log_warning "프론트엔드 테스트 실패"
fi

# 랜딩 페이지 테스트
if curl -s "http://$EC2_IP/landing/" > /dev/null; then
    log_success "랜딩 페이지 테스트 성공"
else
    log_warning "랜딩 페이지 테스트 실패"
fi

echo ""
log_success "🎉 AWS 배포가 완료되었습니다!"
echo ""
echo "📋 배포 정보:"
echo "  - EC2 IP: $EC2_IP"
echo "  - 프론트엔드: http://$EC2_IP"
echo "  - 백엔드 API: http://$EC2_IP:8010"
echo "  - 랜딩 페이지: http://$EC2_IP/landing/"
echo ""
echo "🔧 관리 명령어:"
echo "  - 서비스 상태: ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl status stock-finder-backend'"
echo "  - 서비스 재시작: ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo systemctl restart stock-finder-backend'"
echo "  - 로그 확인: ssh -i $KEY_FILE ubuntu@$EC2_IP 'sudo journalctl -u stock-finder-backend -f'"
echo "  - 코드 업데이트: ssh -i $KEY_FILE ubuntu@$EC2_IP '/home/ubuntu/deploy.sh'"
echo ""
echo "📚 다음 단계:"
echo "  1. 도메인 연결 (Route 53)"
echo "  2. SSL 인증서 설정 (Let's Encrypt)"
echo "  3. 모니터링 설정"
echo ""
log_info "배포 완료! 🚀"



