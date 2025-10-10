#!/bin/bash

# 로컬 개발 환경 관리 스크립트
# 사용법: ./dev-local.sh [명령어]

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

# 로컬 상태 확인
check_status() {
    log_info "로컬 개발 환경 상태 확인 중..."
    
    # 백엔드 상태
    BACKEND_STATUS=$(ps aux | grep 'uvicorn main:app' | grep -v grep | wc -l)
    if [ "$BACKEND_STATUS" -gt 0 ]; then
        log_success "백엔드: 실행 중 (포트 8010)"
    else
        log_error "백엔드: 중지됨"
    fi
    
    # 프론트엔드 상태
    FRONTEND_STATUS=$(ps aux | grep 'next dev' | grep -v grep | wc -l)
    if [ "$FRONTEND_STATUS" -gt 0 ]; then
        log_success "프론트엔드: 실행 중 (포트 3000)"
    else
        log_error "프론트엔드: 중지됨"
    fi
    
    # API 연결 테스트
    if curl -s http://localhost:8010/ > /dev/null 2>&1; then
        log_success "백엔드 API: 응답 정상"
    else
        log_error "백엔드 API: 응답 없음"
    fi
    
    if curl -s http://localhost:3000/ > /dev/null 2>&1; then
        log_success "프론트엔드: 응답 정상"
    else
        log_error "프론트엔드: 응답 없음"
    fi
}

# 백엔드 시작
start_backend() {
    log_info "백엔드 시작 중..."
    
    if [ ! -d "backend" ]; then
        log_error "backend 디렉토리를 찾을 수 없습니다"
        return 1
    fi
    
    if [ ! -d "backend/venv" ]; then
        log_error "가상환경을 찾을 수 없습니다"
        return 1
    fi
    
    # 기존 프로세스 종료
    pkill -f 'uvicorn main:app' 2>/dev/null
    sleep 2
    
    # 백엔드 시작
    cd backend
    source venv/bin/activate
    nohup uvicorn main:app --host 0.0.0.0 --port 8010 --reload > backend.log 2>&1 &
    cd ..
    
    sleep 3
    if ps aux | grep 'uvicorn main:app' | grep -v grep > /dev/null; then
        log_success "백엔드 시작 완료"
    else
        log_error "백엔드 시작 실패"
    fi
}

# 프론트엔드 시작
start_frontend() {
    log_info "프론트엔드 시작 중..."
    
    if [ ! -d "frontend" ]; then
        log_error "frontend 디렉토리를 찾을 수 없습니다"
        return 1
    fi
    
    # 기존 프로세스 종료
    pkill -f 'next dev' 2>/dev/null
    sleep 2
    
    # 프론트엔드 시작
    cd frontend
    nohup npm run dev > frontend.log 2>&1 &
    cd ..
    
    sleep 5
    if ps aux | grep 'next dev' | grep -v grep > /dev/null; then
        log_success "프론트엔드 시작 완료"
    else
        log_error "프론트엔드 시작 실패"
    fi
}

# 백엔드 중지
stop_backend() {
    log_info "백엔드 중지 중..."
    if pkill -f 'uvicorn main:app'; then
        log_success "백엔드 중지 완료"
    else
        log_warning "실행 중인 백엔드 프로세스가 없습니다"
    fi
}

# 프론트엔드 중지
stop_frontend() {
    log_info "프론트엔드 중지 중..."
    if pkill -f 'next dev'; then
        log_success "프론트엔드 중지 완료"
    else
        log_warning "실행 중인 프론트엔드 프로세스가 없습니다"
    fi
}

# 전체 시작
start_all() {
    log_info "전체 개발 환경 시작 중..."
    start_backend
    start_frontend
    log_success "전체 개발 환경 시작 완료"
}

# 전체 중지
stop_all() {
    log_info "전체 개발 환경 중지 중..."
    stop_backend
    stop_frontend
    log_success "전체 개발 환경 중지 완료"
}

# 재시작
restart_all() {
    log_info "전체 개발 환경 재시작 중..."
    stop_all
    sleep 2
    start_all
    log_success "전체 개발 환경 재시작 완료"
}

# 로그 확인
check_logs() {
    log_info "로그 확인 중..."
    
    echo -e "\n${YELLOW}=== 백엔드 로그 (최근 10줄) ===${NC}"
    if [ -f "backend/backend.log" ]; then
        tail -10 backend/backend.log
    else
        echo "백엔드 로그 파일이 없습니다"
    fi
    
    echo -e "\n${YELLOW}=== 프론트엔드 로그 (최근 10줄) ===${NC}"
    if [ -f "frontend/frontend.log" ]; then
        tail -10 frontend/frontend.log
    else
        echo "프론트엔드 로그 파일이 없습니다"
    fi
}

# 의존성 설치
install_deps() {
    log_info "의존성 설치 중..."
    
    # 백엔드 의존성
    if [ -d "backend" ]; then
        log_info "백엔드 의존성 설치..."
        cd backend
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        source venv/bin/activate
        pip install -r requirements.txt
        cd ..
        log_success "백엔드 의존성 설치 완료"
    fi
    
    # 프론트엔드 의존성
    if [ -d "frontend" ]; then
        log_info "프론트엔드 의존성 설치..."
        cd frontend
        npm install
        cd ..
        log_success "프론트엔드 의존성 설치 완료"
    fi
}

# 도움말
show_help() {
    echo "로컬 개발 환경 관리 스크립트"
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
    echo "  logs        - 로그 확인"
    echo "  install     - 의존성 설치"
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
    "logs")
        check_logs
        ;;
    "install")
        install_deps
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
