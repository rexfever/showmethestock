#!/bin/bash

# 롤백 스크립트
# 사용법: ./scripts/rollback.sh [local|server] [backend|frontend|all]

set -e  # 오류 발생 시 스크립트 종료

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_header() {
    echo -e "${PURPLE}[ROLLBACK]${NC} $1"
}

# 롤백 환경 및 대상 확인
ROLLBACK_ENV=${1:-local}
ROLLBACK_TARGET=${2:-all}

if [[ "$ROLLBACK_ENV" != "local" && "$ROLLBACK_ENV" != "server" ]]; then
    log_error "사용법: $0 [local|server] [backend|frontend|all]"
    exit 1
fi

if [[ "$ROLLBACK_TARGET" != "backend" && "$ROLLBACK_TARGET" != "frontend" && "$ROLLBACK_TARGET" != "all" ]]; then
    log_error "사용법: $0 [local|server] [backend|frontend|all]"
    exit 1
fi

log_header "🔄 롤백 시작"
log_info "환경: $ROLLBACK_ENV"
log_info "대상: $ROLLBACK_TARGET"
echo ""

# 확인 메시지
log_warning "⚠️  롤백을 수행하면 현재 배포가 이전 상태로 되돌아갑니다."
read -p "정말 롤백을 수행하시겠습니까? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "롤백이 취소되었습니다."
    exit 0
fi

# 롤백 시작 시간 기록
ROLLBACK_START_TIME=$(date +%s)

# 1. 백엔드 롤백
if [[ "$ROLLBACK_TARGET" == "backend" || "$ROLLBACK_TARGET" == "all" ]]; then
    log_header "1. 백엔드 롤백"
    
    if [ "$ROLLBACK_ENV" = "local" ]; then
        log_info "로컬 백엔드 롤백..."
        
        # 기존 프로세스 종료
        if [ -f "backend.pid" ]; then
            BACKEND_PID=$(cat backend.pid)
            if kill $BACKEND_PID 2>/dev/null; then
                log_success "백엔드 프로세스 종료 (PID: $BACKEND_PID)"
            fi
            rm -f backend.pid
        fi
        
        # Git을 사용한 롤백
        if [ -d ".git" ]; then
            log_info "Git을 사용한 백엔드 코드 롤백..."
            cd backend
            git checkout HEAD~1 -- .
            cd ..
            log_success "백엔드 코드 롤백 완료"
        fi
        
        # 백엔드 재시작
        log_info "백엔드 서비스 재시작..."
        if [ -f "scripts/deploy-backend.sh" ]; then
            chmod +x scripts/deploy-backend.sh
            ./scripts/deploy-backend.sh local
        fi
        
    elif [ "$ROLLBACK_ENV" = "server" ]; then
        log_info "서버 백엔드 롤백..."
        
        if [ -z "$SERVER_HOST" ]; then
            log_error "SERVER_HOST 환경변수가 설정되지 않았습니다."
            exit 1
        fi
        
        ssh ubuntu@$SERVER_HOST << 'EOF'
            cd /home/ubuntu/showmethestock/backend
            
            # Git을 사용한 롤백
            git checkout HEAD~1 -- .
            
            # 의존성 재설치
            pip3 install -r requirements.txt --quiet
            
            # 백엔드 서비스 재시작
            sudo systemctl restart stock-finder-backend
            
            # 서비스 상태 확인
            sleep 5
            if sudo systemctl is-active --quiet stock-finder-backend; then
                echo "✅ 백엔드 서비스 롤백 완료"
            else
                echo "❌ 백엔드 서비스 롤백 실패"
                exit 1
            fi
EOF
        
        if [ $? -eq 0 ]; then
            log_success "서버 백엔드 롤백 완료"
        else
            log_error "서버 백엔드 롤백 실패"
            exit 1
        fi
    fi
    echo ""
fi

# 2. 프론트엔드 롤백
if [[ "$ROLLBACK_TARGET" == "frontend" || "$ROLLBACK_TARGET" == "all" ]]; then
    log_header "2. 프론트엔드 롤백"
    
    if [ "$ROLLBACK_ENV" = "local" ]; then
        log_info "로컬 프론트엔드 롤백..."
        
        # 기존 프로세스 종료
        if [ -f "frontend.pid" ]; then
            FRONTEND_PID=$(cat frontend.pid)
            if kill $FRONTEND_PID 2>/dev/null; then
                log_success "프론트엔드 프로세스 종료 (PID: $FRONTEND_PID)"
            fi
            rm -f frontend.pid
        fi
        
        # Git을 사용한 롤백
        if [ -d ".git" ]; then
            log_info "Git을 사용한 프론트엔드 코드 롤백..."
            cd frontend
            git checkout HEAD~1 -- .
            cd ..
            log_success "프론트엔드 코드 롤백 완료"
        fi
        
        # 프론트엔드 재시작
        log_info "프론트엔드 서비스 재시작..."
        if [ -f "scripts/deploy-frontend.sh" ]; then
            chmod +x scripts/deploy-frontend.sh
            ./scripts/deploy-frontend.sh local
        fi
        
    elif [ "$ROLLBACK_ENV" = "server" ]; then
        log_info "서버 프론트엔드 롤백..."
        
        if [ -z "$SERVER_HOST" ]; then
            log_error "SERVER_HOST 환경변수가 설정되지 않았습니다."
            exit 1
        fi
        
        ssh ubuntu@$SERVER_HOST << 'EOF'
            cd /home/ubuntu/showmethestock/frontend
            
            # Git을 사용한 롤백
            git checkout HEAD~1 -- .
            
            # 의존성 재설치
            npm ci --production=false
            
            # 빌드
            rm -rf .next
            npm run build
            
            # 프론트엔드 서비스 재시작
            sudo systemctl restart stock-finder-frontend
            
            # 서비스 상태 확인
            sleep 10
            if sudo systemctl is-active --quiet stock-finder-frontend; then
                echo "✅ 프론트엔드 서비스 롤백 완료"
            else
                echo "❌ 프론트엔드 서비스 롤백 실패"
                exit 1
            fi
EOF
        
        if [ $? -eq 0 ]; then
            log_success "서버 프론트엔드 롤백 완료"
        else
            log_error "서버 프론트엔드 롤백 실패"
            exit 1
        fi
    fi
    echo ""
fi

# 3. 롤백 후 검증
log_header "3. 롤백 후 검증"

# 서비스 상태 확인
if [[ "$ROLLBACK_ENV" == "local" ]]; then
    log_info "로컬 서비스 상태 확인..."
    
    # 백엔드 확인
    if [[ "$ROLLBACK_TARGET" == "backend" || "$ROLLBACK_TARGET" == "all" ]]; then
        if curl -s http://localhost:8010/health > /dev/null 2>&1; then
            log_success "백엔드 서비스 정상"
        else
            log_error "백엔드 서비스 오류"
        fi
    fi
    
    # 프론트엔드 확인
    if [[ "$ROLLBACK_TARGET" == "frontend" || "$ROLLBACK_TARGET" == "all" ]]; then
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            log_success "프론트엔드 서비스 정상"
        else
            log_error "프론트엔드 서비스 오류"
        fi
    fi
fi

# 4. 롤백 완료
ROLLBACK_END_TIME=$(date +%s)
ROLLBACK_DURATION=$((ROLLBACK_END_TIME - ROLLBACK_START_TIME))

log_header "🎉 롤백 완료!"
log_success "롤백 시간: ${ROLLBACK_DURATION}초"
log_info "환경: $ROLLBACK_ENV"
log_info "대상: $ROLLBACK_TARGET"

if [[ "$ROLLBACK_ENV" == "local" ]]; then
    if [[ "$ROLLBACK_TARGET" == "backend" || "$ROLLBACK_TARGET" == "all" ]]; then
        log_info "백엔드: http://localhost:8010"
    fi
    if [[ "$ROLLBACK_TARGET" == "frontend" || "$ROLLBACK_TARGET" == "all" ]]; then
        log_info "프론트엔드: http://localhost:3000"
    fi
fi

# 롤백 정보 저장
echo "{
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"environment\": \"$ROLLBACK_ENV\",
    \"target\": \"$ROLLBACK_TARGET\",
    \"duration_seconds\": $ROLLBACK_DURATION,
    \"status\": \"success\"
}" > rollback-summary.json

log_info "롤백 요약이 rollback-summary.json에 저장되었습니다."

# 5. 다음 단계 안내
log_header "📋 다음 단계"
log_info "1. 애플리케이션 기능 테스트"
log_info "2. 문제 원인 분석"
log_info "3. 수정 후 재배포"

echo ""
log_success "롤백이 성공적으로 완료되었습니다! 🔄"