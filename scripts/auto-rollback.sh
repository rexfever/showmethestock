#!/bin/bash

# 자동 롤백 스크립트
# 헬스체크 실패 시 자동으로 이전 환경으로 롤백

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 로그 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 설정
HEALTH_CHECK_INTERVAL=30  # 헬스체크 간격 (초)
MAX_FAILURES=3           # 최대 실패 횟수
ROLLBACK_TIMEOUT=300     # 롤백 타임아웃 (초)

# 현재 환경 확인
get_current_env() {
    if curl -s http://localhost:8010/health > /dev/null 2>&1; then
        echo "blue"
    elif curl -s http://localhost:8011/health > /dev/null 2>&1; then
        echo "green"
    else
        echo "none"
    fi
}

# 헬스체크 실행
run_health_check() {
    local env=$1
    local port=$2
    
    # 백엔드 체크
    if ! curl -s -f http://localhost:$port/health > /dev/null 2>&1; then
        return 1
    fi
    
    # 프론트엔드 체크
    local frontend_port
    if [ "$env" = "blue" ]; then
        frontend_port=3000
    else
        frontend_port=3001
    fi
    
    if ! curl -s -f http://localhost:$frontend_port > /dev/null 2>&1; then
        return 1
    fi
    
    return 0
}

# 롤백 실행
rollback_to_previous_env() {
    local current_env=$1
    local previous_env
    
    if [ "$current_env" = "blue" ]; then
        previous_env="green"
    elif [ "$current_env" = "green" ]; then
        previous_env="blue"
    else
        log_error "롤백할 이전 환경을 찾을 수 없습니다."
        return 1
    fi
    
    log_warning "🔄 자동 롤백 시작: $current_env → $previous_env"
    
    # 이전 환경 포트 설정
    local backend_port frontend_port
    if [ "$previous_env" = "blue" ]; then
        backend_port=8010
        frontend_port=3000
    else
        backend_port=8011
        frontend_port=3001
    fi
    
    # 이전 환경 서비스 시작
    log_info "이전 환경 서비스 시작 중..."
    sudo systemctl start stock-finder-backend-$previous_env
    sudo systemctl start stock-finder-frontend-$previous_env
    
    # 서비스 시작 대기
    sleep 10
    
    # 이전 환경 헬스체크
    if run_health_check "$previous_env" "$backend_port"; then
        log_success "이전 환경 헬스체크 통과"
        
        # Nginx 설정 업데이트
        log_info "Nginx 설정 업데이트 중..."
        sudo tee /etc/nginx/sites-available/stock-finder > /dev/null << EOF
server {
    listen 80;
    server_name sohntech.ai.kr;

    # 프론트엔드 프록시
    location / {
        proxy_pass http://localhost:$frontend_port;
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
        proxy_pass http://localhost:$backend_port/;
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
        
        # Nginx 재시작
        sudo systemctl reload nginx
        
        # 최종 확인
        sleep 5
        if curl -s -f http://sohntech.ai.kr > /dev/null 2>&1; then
            log_success "롤백 성공: $previous_env 환경으로 전환 완료"
            
            # 현재 환경 서비스 중지
            sudo systemctl stop stock-finder-backend-$current_env
            sudo systemctl stop stock-finder-frontend-$current_env
            
            # 알림 전송 (선택사항)
            send_notification "롤백 완료" "자동 롤백이 성공적으로 완료되었습니다. 현재 환경: $previous_env"
            
            return 0
        else
            log_error "롤백 후 최종 확인 실패"
            return 1
        fi
    else
        log_error "이전 환경 헬스체크 실패"
        return 1
    fi
}

# 알림 전송 (선택사항)
send_notification() {
    local title=$1
    local message=$2
    
    # Slack, Discord, 이메일 등으로 알림 전송 가능
    log_info "알림: $title - $message"
    
    # 예시: curl을 사용한 Slack 알림
    # curl -X POST -H 'Content-type: application/json' \
    #     --data "{\"text\":\"$title: $message\"}" \
    #     YOUR_SLACK_WEBHOOK_URL
}

# 메인 모니터링 루프
main() {
    log_info "🤖 자동 롤백 모니터링 시작"
    log_info "헬스체크 간격: ${HEALTH_CHECK_INTERVAL}초"
    log_info "최대 실패 횟수: ${MAX_FAILURES}회"
    echo ""
    
    local failure_count=0
    local last_check_time=$(date +%s)
    
    while true; do
        local current_env=$(get_current_env)
        
        if [ "$current_env" = "none" ]; then
            log_error "운영 중인 환경이 없습니다."
            exit 1
        fi
        
        # 포트 설정
        local backend_port
        if [ "$current_env" = "blue" ]; then
            backend_port=8010
        else
            backend_port=8011
        fi
        
        # 헬스체크 실행
        if run_health_check "$current_env" "$backend_port"; then
            if [ $failure_count -gt 0 ]; then
                log_success "헬스체크 복구됨 (환경: $current_env)"
                failure_count=0
            fi
        else
            failure_count=$((failure_count + 1))
            log_warning "헬스체크 실패 ($failure_count/$MAX_FAILURES) - 환경: $current_env"
            
            if [ $failure_count -ge $MAX_FAILURES ]; then
                log_error "최대 실패 횟수 도달. 자동 롤백 실행..."
                
                if rollback_to_previous_env "$current_env"; then
                    log_success "자동 롤백 완료"
                    failure_count=0
                else
                    log_error "자동 롤백 실패"
                    send_notification "롤백 실패" "자동 롤백이 실패했습니다. 수동 개입이 필요합니다."
                    exit 1
                fi
            fi
        fi
        
        # 다음 체크까지 대기
        sleep $HEALTH_CHECK_INTERVAL
    done
}

# 스크립트 실행
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
