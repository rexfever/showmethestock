#!/bin/bash

# 서버 개발 환경 관리 스크립트
# 사용법: ./dev-server.sh [명령어]

# 서버 설정
SERVER_IP="52.79.145.238"
SERVER_USER="ubuntu"
SERVER_PATH="/home/ubuntu/showmethestock"

# SSH 연결 옵션 (타임아웃 개선)
SSH_OPTS="-o ConnectTimeout=30 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -o TCPKeepAlive=yes"

# 색상 코드
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

# 서버 상태 확인
check_status() {
    log_info "서버 상태 확인 중..."
    
    # 백엔드 상태
    BACKEND_STATUS=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "ps aux | grep 'uvicorn main:app' | grep -v grep | wc -l")
    if [ "$BACKEND_STATUS" -gt 0 ]; then
        log_success "백엔드: 실행 중"
    else
        log_error "백엔드: 중지됨"
    fi
    
    # 프론트엔드 상태
    FRONTEND_STATUS=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "ps aux | grep 'next' | grep -v grep | wc -l")
    if [ "$FRONTEND_STATUS" -gt 0 ]; then
        log_success "프론트엔드: 실행 중"
    else
        log_error "프론트엔드: 중지됨"
    fi
    
    # 스케줄러 상태
    SCHEDULER_STATUS=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "ps aux | grep 'scheduler.py' | grep -v grep | wc -l")
    if [ "$SCHEDULER_STATUS" -gt 0 ]; then
        log_success "스케줄러: 실행 중"
    else
        log_error "스케줄러: 중지됨"
    fi
    
    # 웹 서비스 상태
    WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://sohntech.ai.kr)
    if [ "$WEB_STATUS" = "200" ]; then
        log_success "웹 서비스: 정상 (HTTP $WEB_STATUS)"
    else
        log_error "웹 서비스: 오류 (HTTP $WEB_STATUS)"
    fi
}

# 백엔드 시작
start_backend() {
    log_info "서버 백엔드 시작 중..."
    
    # 기존 프로세스 종료
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "pkill -f 'uvicorn main:app'"
    sleep 2
    
    # 백엔드 시작
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $SERVER_PATH/backend && source venv/bin/activate && nohup uvicorn main:app --host 0.0.0.0 --port 8010 > backend.log 2>&1 &"
    
    sleep 5
    BACKEND_STATUS=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "ps aux | grep 'uvicorn main:app' | grep -v grep | wc -l")
    if [ "$BACKEND_STATUS" -gt 0 ]; then
        log_success "서버 백엔드 시작 완료"
    else
        log_error "서버 백엔드 시작 실패"
    fi
}

# 프론트엔드 시작
start_frontend() {
    log_info "서버 프론트엔드 시작 중..."
    
    # 기존 프로세스 종료
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "pkill -f 'next'"
    sleep 2
    
    # 프론트엔드 시작
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $SERVER_PATH/frontend && nohup npm run dev > frontend.log 2>&1 &"
    
    sleep 10
    FRONTEND_STATUS=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "ps aux | grep 'next' | grep -v grep | wc -l")
    if [ "$FRONTEND_STATUS" -gt 0 ]; then
        log_success "서버 프론트엔드 시작 완료"
    else
        log_error "서버 프론트엔드 시작 실패"
    fi
}

# 스케줄러 시작
start_scheduler() {
    log_info "서버 스케줄러 시작 중..."
    
    # 기존 프로세스 종료
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "pkill -f 'scheduler.py'"
    sleep 2
    
    # 스케줄러 시작
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $SERVER_PATH && nohup ./start-scheduler.sh > scheduler.log 2>&1 &"
    
    sleep 5
    SCHEDULER_STATUS=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "ps aux | grep 'scheduler.py' | grep -v grep | wc -l")
    if [ "$SCHEDULER_STATUS" -gt 0 ]; then
        log_success "서버 스케줄러 시작 완료"
    else
        log_error "서버 스케줄러 시작 실패"
    fi
}

# 백엔드 중지
stop_backend() {
    log_info "서버 백엔드 중지 중..."
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "pkill -f 'uvicorn main:app'"
    log_success "서버 백엔드 중지 완료"
}

# 프론트엔드 중지
stop_frontend() {
    log_info "서버 프론트엔드 중지 중..."
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "pkill -f 'next'"
    log_success "서버 프론트엔드 중지 완료"
}

# 스케줄러 중지
stop_scheduler() {
    log_info "서버 스케줄러 중지 중..."
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "pkill -f 'scheduler.py'"
    log_success "서버 스케줄러 중지 완료"
}

# 전체 시작
start_all() {
    log_info "서버 전체 시작 중..."
    start_backend
    start_frontend
    start_scheduler
    log_success "서버 전체 시작 완료"
}

# 전체 중지
stop_all() {
    log_info "서버 전체 중지 중..."
    stop_backend
    stop_frontend
    stop_scheduler
    log_success "서버 전체 중지 완료"
}

# 재시작
restart_all() {
    log_info "서버 전체 재시작 중..."
    stop_all
    sleep 3
    start_all
    log_success "서버 전체 재시작 완료"
}

# 코드 배포
deploy() {
    log_info "서버 코드 배포 중..."
    
    # 서버에서 git pull
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $SERVER_PATH && git stash && git pull origin main"
    
    if [ $? -eq 0 ]; then
        log_success "서버 코드 배포 완료"
        log_info "서비스 재시작을 권장합니다: ./dev-server.sh restart"
    else
        log_error "서버 코드 배포 실패"
    fi
}

# 로그 확인
check_logs() {
    log_info "서버 로그 확인 중..."
    
    echo -e "\n${YELLOW}=== 백엔드 로그 (최근 10줄) ===${NC}"
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $SERVER_PATH/backend && tail -10 backend.log"
    
    echo -e "\n${YELLOW}=== 프론트엔드 로그 (최근 10줄) ===${NC}"
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $SERVER_PATH/frontend && tail -10 frontend.log"
    
    echo -e "\n${YELLOW}=== 스케줄러 로그 (최근 10줄) ===${NC}"
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $SERVER_PATH && tail -10 scheduler.log"
}

# 도움말
show_help() {
    echo "서버 개발 환경 관리 스크립트"
    echo ""
    echo "사용법: $0 [명령어]"
    echo ""
    echo "명령어:"
    echo "  status      - 상태 확인"
    echo "  start       - 전체 시작"
    echo "  stop        - 전체 중지"
    echo "  restart     - 전체 재시작"
    echo "  start-backend   - 백엔드만 시작"
    echo "  stop-backend    - 백엔드만 중지"
    echo "  start-frontend  - 프론트엔드만 시작"
    echo "  stop-frontend   - 프론트엔드만 중지"
    echo "  start-scheduler - 스케줄러만 시작"
    echo "  stop-scheduler  - 스케줄러만 중지"
    echo "  deploy      - 코드 배포"
    echo "  logs        - 로그 확인"
    echo "  help        - 도움말 표시"
}

# 메인 로직
case "$1" in
    "status")
        check_status
        ;;
    "start")
        start_all
        ;;
    "stop")
        stop_all
        ;;
    "restart")
        restart_all
        ;;
    "start-backend")
        start_backend
        ;;
    "stop-backend")
        stop_backend
        ;;
    "start-frontend")
        start_frontend
        ;;
    "stop-frontend")
        stop_frontend
        ;;
    "start-scheduler")
        start_scheduler
        ;;
    "stop-scheduler")
        stop_scheduler
        ;;
    "deploy")
        deploy
        ;;
    "logs")
        check_logs
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        log_error "알 수 없는 명령어: $1"
        show_help
        exit 1
        ;;
esac
