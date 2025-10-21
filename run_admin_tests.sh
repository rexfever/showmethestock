#!/bin/bash

# 관리자 재스캔 기능 테스트 실행 스크립트

echo "🚀 관리자 재스캔 기능 테스트 시작"
echo "=================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 백엔드 서버 상태 확인
check_backend() {
    print_status "백엔드 서버 상태 확인 중..."
    
    if curl -s http://localhost:8010/health > /dev/null 2>&1; then
        print_success "백엔드 서버가 실행 중입니다"
        return 0
    else
        print_error "백엔드 서버가 실행되지 않았습니다"
        return 1
    fi
}

# 프론트엔드 서버 상태 확인
check_frontend() {
    print_status "프론트엔드 서버 상태 확인 중..."
    
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        print_success "프론트엔드 서버가 실행 중입니다"
        return 0
    else
        print_warning "프론트엔드 서버가 실행되지 않았습니다"
        return 1
    fi
}

# 백엔드 서버 시작
start_backend() {
    print_status "백엔드 서버 시작 중..."
    
    cd backend
    if [ -f "start.py" ]; then
        python3 start.py &
        BACKEND_PID=$!
        echo $BACKEND_PID > ../backend.pid
        
        # 서버 시작 대기
        sleep 5
        
        if check_backend; then
            print_success "백엔드 서버가 성공적으로 시작되었습니다 (PID: $BACKEND_PID)"
            cd ..
            return 0
        else
            print_error "백엔드 서버 시작에 실패했습니다"
            cd ..
            return 1
        fi
    else
        print_error "start.py 파일을 찾을 수 없습니다"
        cd ..
        return 1
    fi
}

# 프론트엔드 서버 시작
start_frontend() {
    print_status "프론트엔드 서버 시작 중..."
    
    cd frontend
    PORT=3000 npm run dev &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    
    # 서버 시작 대기
    sleep 10
    
    if check_frontend; then
        print_success "프론트엔드 서버가 성공적으로 시작되었습니다 (PID: $FRONTEND_PID)"
        cd ..
        return 0
    else
        print_warning "프론트엔드 서버 시작에 실패했습니다"
        cd ..
        return 1
    fi
}

# 서버 종료
stop_servers() {
    print_status "서버 종료 중..."
    
    # 백엔드 서버 종료
    if [ -f "backend.pid" ]; then
        BACKEND_PID=$(cat backend.pid)
        if kill $BACKEND_PID 2>/dev/null; then
            print_success "백엔드 서버가 종료되었습니다 (PID: $BACKEND_PID)"
        fi
        rm -f backend.pid
    fi
    
    # 프론트엔드 서버 종료
    if [ -f "frontend.pid" ]; then
        FRONTEND_PID=$(cat frontend.pid)
        if kill $FRONTEND_PID 2>/dev/null; then
            print_success "프론트엔드 서버가 종료되었습니다 (PID: $FRONTEND_PID)"
        fi
        rm -f frontend.pid
    fi
}

# 백엔드 테스트 실행
run_backend_tests() {
    print_status "백엔드 테스트 실행 중..."
    
    cd backend
    
    # 단위 테스트
    if [ -f "test_admin_rescan.py" ]; then
        print_status "관리자 재스캔 단위 테스트 실행..."
        python3 test_admin_rescan.py
        echo ""
    fi
    
    # 통합 테스트
    if [ -f "test_integration_admin.py" ]; then
        print_status "관리자 재스캔 통합 테스트 실행..."
        python3 test_integration_admin.py
        echo ""
    fi
    
    cd ..
}

# 프론트엔드 테스트 실행
run_frontend_tests() {
    print_status "프론트엔드 테스트 실행 중..."
    
    cd frontend
    
    # Jest 테스트 실행
    if [ -f "package.json" ]; then
        print_status "관리자 페이지 테스트 실행..."
        npm test -- __tests__/pages/admin.test.js --verbose
        echo ""
    fi
    
    cd ..
}

# 메인 실행 함수
main() {
    # 서버 상태 확인
    BACKEND_RUNNING=$(check_backend && echo "true" || echo "false")
    FRONTEND_RUNNING=$(check_frontend && echo "true" || echo "false")
    
    # 필요한 서버 시작
    if [ "$BACKEND_RUNNING" = "false" ]; then
        if ! start_backend; then
            print_error "백엔드 서버를 시작할 수 없습니다. 테스트를 중단합니다."
            exit 1
        fi
    fi
    
    if [ "$FRONTEND_RUNNING" = "false" ]; then
        start_frontend
    fi
    
    # 테스트 실행
    echo ""
    print_status "테스트 실행 시작..."
    echo "========================"
    
    # 백엔드 테스트
    run_backend_tests
    
    # 프론트엔드 테스트 (서버가 실행 중인 경우에만)
    if [ "$FRONTEND_RUNNING" = "true" ] || check_frontend; then
        run_frontend_tests
    else
        print_warning "프론트엔드 서버가 실행되지 않아 프론트엔드 테스트를 건너뜁니다"
    fi
    
    echo ""
    print_success "모든 테스트가 완료되었습니다!"
    
    # 서버 종료 (스크립트에서 시작한 경우에만)
    if [ "$BACKEND_RUNNING" = "false" ] || [ "$FRONTEND_RUNNING" = "false" ]; then
        echo ""
        read -p "서버를 종료하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            stop_servers
        else
            print_status "서버가 계속 실행 중입니다"
        fi
    fi
}

# 스크립트 종료 시 정리
cleanup() {
    print_status "정리 중..."
    stop_servers
}

# 시그널 핸들러 설정
trap cleanup EXIT INT TERM

# 메인 함수 실행
main "$@"












