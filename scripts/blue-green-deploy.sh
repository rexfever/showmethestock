#!/bin/bash

# Blue-Green 무중단 배포 스크립트
# 사용법: ./scripts/blue-green-deploy.sh [blue|green]

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 로그 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${PURPLE}[BLUE-GREEN]${NC} $1"; }

# 환경 설정
TARGET_ENV=${1:-green}
CURRENT_ENV=""
NEW_ENV=""

# 현재 환경 확인
if curl -s http://localhost:8010/health > /dev/null 2>&1; then
    CURRENT_ENV="blue"
    NEW_ENV="green"
elif curl -s http://localhost:8011/health > /dev/null 2>&1; then
    CURRENT_ENV="green"
    NEW_ENV="blue"
else
    log_warning "현재 운영 중인 환경을 찾을 수 없습니다. Blue 환경으로 시작합니다."
    CURRENT_ENV="none"
    NEW_ENV="blue"
fi

log_header "🚀 Blue-Green 배포 시작"
log_info "현재 환경: $CURRENT_ENV"
log_info "배포 대상: $NEW_ENV"
echo ""

# 1. 새 환경 준비
log_header "1. 새 환경 준비"

# 포트 설정
if [ "$NEW_ENV" = "blue" ]; then
    BACKEND_PORT=8010
    FRONTEND_PORT=3000
else
    BACKEND_PORT=8011
    FRONTEND_PORT=3001
fi

log_info "백엔드 포트: $BACKEND_PORT"
log_info "프론트엔드 포트: $FRONTEND_PORT"

# 2. 백엔드 배포
log_header "2. 백엔드 배포 ($NEW_ENV)"

# 백엔드 서비스 파일 생성
sudo tee /etc/systemd/system/stock-finder-backend-$NEW_ENV.service > /dev/null << EOF
[Unit]
Description=Stock Finder Backend API ($NEW_ENV)
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/showmethestock/backend
Environment=PATH=/home/ubuntu/showmethestock/backend/venv/bin
Environment=PYTHONPATH=/home/ubuntu/showmethestock
ExecStart=/home/ubuntu/showmethestock/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --workers 1
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=stock-finder-backend-$NEW_ENV

[Install]
WantedBy=multi-user.target
EOF

# systemd 데몬 리로드
sudo systemctl daemon-reload

# 백엔드 서비스 시작
sudo systemctl start stock-finder-backend-$NEW_ENV
sudo systemctl enable stock-finder-backend-$NEW_ENV

# 백엔드 헬스체크
log_info "백엔드 헬스체크 중..."
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        log_success "백엔드 서비스 정상 시작"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "백엔드 서비스 시작 실패"
        sudo systemctl stop stock-finder-backend-$NEW_ENV
        exit 1
    fi
    sleep 2
done

# 3. 프론트엔드 배포
log_header "3. 프론트엔드 배포 ($NEW_ENV)"

# 프론트엔드 서비스 파일 생성
sudo tee /etc/systemd/system/stock-finder-frontend-$NEW_ENV.service > /dev/null << EOF
[Unit]
Description=Stock Finder Frontend ($NEW_ENV)
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/showmethestock/frontend
Environment=NODE_ENV=production
Environment=PORT=$FRONTEND_PORT
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=stock-finder-frontend-$NEW_ENV

[Install]
WantedBy=multi-user.target
EOF

# systemd 데몬 리로드
sudo systemctl daemon-reload

# 프론트엔드 서비스 시작
sudo systemctl start stock-finder-frontend-$NEW_ENV
sudo systemctl enable stock-finder-frontend-$NEW_ENV

# 프론트엔드 헬스체크
log_info "프론트엔드 헬스체크 중..."
for i in {1..30}; do
    if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        log_success "프론트엔드 서비스 정상 시작"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "프론트엔드 서비스 시작 실패"
        sudo systemctl stop stock-finder-frontend-$NEW_ENV
        sudo systemctl stop stock-finder-backend-$NEW_ENV
        exit 1
    fi
    sleep 2
done

# 4. Nginx 설정 업데이트
log_header "4. 트래픽 전환 준비"

# Nginx 설정 백업
sudo cp /etc/nginx/sites-available/stock-finder /etc/nginx/sites-available/stock-finder.backup.$(date +%Y%m%d_%H%M%S)

# 새 환경으로 Nginx 설정 업데이트
sudo tee /etc/nginx/sites-available/stock-finder > /dev/null << EOF
server {
    listen 80;
    server_name sohntech.ai.kr;

    # 프론트엔드 프록시
    location / {
        proxy_pass http://localhost:$FRONTEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # 백엔드 API 프록시
    location /api/ {
        proxy_pass http://localhost:$BACKEND_PORT/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # 로그 설정
    access_log /var/log/nginx/stock-finder.access.log;
    error_log /var/log/nginx/stock-finder.error.log;
}
EOF

# Nginx 설정 테스트
if sudo nginx -t; then
    log_success "Nginx 설정 검증 완료"
else
    log_error "Nginx 설정 오류"
    # 백업 복원
    sudo cp /etc/nginx/sites-available/stock-finder.backup.$(date +%Y%m%d_%H%M%S) /etc/nginx/sites-available/stock-finder
    exit 1
fi

# 5. 트래픽 전환
log_header "5. 트래픽 전환"

# Nginx 재시작
sudo systemctl reload nginx

# 최종 헬스체크
log_info "최종 헬스체크 중..."
sleep 5

if curl -s http://sohntech.ai.kr > /dev/null 2>&1; then
    log_success "트래픽 전환 성공"
else
    log_error "트래픽 전환 실패"
    # 롤백
    sudo cp /etc/nginx/sites-available/stock-finder.backup.$(date +%Y%m%d_%H%M%S) /etc/nginx/sites-available/stock-finder
    sudo systemctl reload nginx
    exit 1
fi

# 6. 이전 환경 정리
if [ "$CURRENT_ENV" != "none" ]; then
    log_header "6. 이전 환경 정리"
    
    log_info "이전 환경 ($CURRENT_ENV) 서비스 중지..."
    sudo systemctl stop stock-finder-backend-$CURRENT_ENV
    sudo systemctl stop stock-finder-frontend-$CURRENT_ENV
    sudo systemctl disable stock-finder-backend-$CURRENT_ENV
    sudo systemctl disable stock-finder-frontend-$CURRENT_ENV
    
    log_success "이전 환경 정리 완료"
fi

# 7. 배포 완료
log_header "🎉 Blue-Green 배포 완료!"
log_success "현재 운영 환경: $NEW_ENV"
log_success "백엔드 포트: $BACKEND_PORT"
log_success "프론트엔드 포트: $FRONTEND_PORT"
log_success "다운타임: 0초"

# 배포 정보 저장
echo "{
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"deployment_type\": \"blue-green\",
    \"current_env\": \"$NEW_ENV\",
    \"previous_env\": \"$CURRENT_ENV\",
    \"backend_port\": $BACKEND_PORT,
    \"frontend_port\": $FRONTEND_PORT,
    \"downtime_seconds\": 0,
    \"status\": \"success\"
}" > blue-green-deploy-summary.json

log_info "배포 요약이 blue-green-deploy-summary.json에 저장되었습니다."

echo ""
log_success "무중단 배포가 성공적으로 완료되었습니다! 🚀"
