#!/bin/bash

# 프론트엔드 배포 스크립트
# 사용법: ./scripts/deploy-frontend.sh [local|server]

set -e  # 오류 발생 시 스크립트 종료

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

# 배포 환경 확인
DEPLOY_ENV=${1:-local}
if [[ "$DEPLOY_ENV" != "local" && "$DEPLOY_ENV" != "server" ]]; then
    log_error "사용법: $0 [local|server]"
    exit 1
fi

log_info "프론트엔드 배포 시작 - 환경: $DEPLOY_ENV"

# 1. 사전 체크
log_info "1. 사전 체크 수행 중..."

# Node.js 버전 확인
if ! command -v node &> /dev/null; then
    log_error "Node.js가 설치되지 않았습니다."
    exit 1
fi

NODE_VERSION=$(node --version)
log_info "Node.js 버전: $NODE_VERSION"

# npm 버전 확인
if ! command -v npm &> /dev/null; then
    log_error "npm이 설치되지 않았습니다."
    exit 1
fi

NPM_VERSION=$(npm --version)
log_info "npm 버전: $NPM_VERSION"

# 프론트엔드 디렉토리 확인
if [ ! -d "frontend" ]; then
    log_error "frontend 디렉토리를 찾을 수 없습니다."
    exit 1
fi

cd frontend

# package.json 확인
if [ ! -f "package.json" ]; then
    log_error "package.json 파일을 찾을 수 없습니다."
    exit 1
fi

# 2. 테스트 실행 (서버 배포 시 건너뛰기)
if [ "$DEPLOY_ENV" = "local" ]; then
    log_info "2. 프론트엔드 테스트 실행 중..."
    
    # Jest 테스트 실행
    if [ -f "package.json" ] && grep -q '"test"' package.json; then
        log_info "Jest 테스트 실행..."
        if npm test -- --passWithNoTests --watchAll=false; then
            log_success "Jest 테스트 통과"
        else
            log_error "Jest 테스트 실패"
            exit 1
        fi
    else
        log_warning "테스트 스크립트가 없습니다. 테스트를 건너뜁니다."
    fi
else
    log_info "2. 서버 배포 모드 - 테스트 건너뛰기"
fi

# 3. 의존성 설치
log_info "3. 의존성 설치 중..."

log_info "npm 패키지 설치..."
if npm ci --production=false; then
    log_success "의존성 설치 완료"
else
    log_error "의존성 설치 실패"
    exit 1
fi

# 4. 코드 검증
log_info "4. 코드 검증 중..."

# TypeScript 타입 체크
if [ -f "tsconfig.json" ]; then
    log_info "TypeScript 타입 체크..."
    if npm run type-check; then
        log_success "TypeScript 타입 체크 통과"
    else
        log_error "TypeScript 타입 오류 발견"
        exit 1
    fi
fi

# 5. 빌드
log_info "5. 빌드 수행 중..."

# 이전 빌드 캐시 삭제
if [ -d ".next" ]; then
    log_info "이전 빌드 캐시 삭제..."
    rm -rf .next
fi

# Next.js 빌드
log_info "Next.js 빌드 실행..."
if npm run build; then
    log_success "빌드 완료"
else
    log_error "빌드 실패"
    exit 1
fi

# 6. 환경별 배포
if [ "$DEPLOY_ENV" = "local" ]; then
    log_info "6. 로컬 배포 수행 중..."
    
    # 기존 프로세스 완전 종료
    log_info "기존 프론트엔드 프로세스 종료 중..."
    
    # 포트 확인 및 설정
    PORT=${PORT:-3000}
    log_info "포트 $PORT 사용"
    
    # 포트 사용 중인 프로세스 확인
    if lsof -i :$PORT >/dev/null 2>&1; then
        log_warning "포트 $PORT가 사용 중입니다. 프로세스를 종료합니다."
        
        # 프로세스 ID 추출
        PIDS=$(lsof -ti :$PORT)
        for PID in $PIDS; do
            log_info "프로세스 $PID 종료 중..."
            kill -TERM $PID 2>/dev/null || true
        done
        
        # 3초 대기
        sleep 3
        
        # 여전히 실행 중인 프로세스 강제 종료
        if lsof -i :$PORT >/dev/null 2>&1; then
            log_warning "강제 종료가 필요합니다."
            PIDS=$(lsof -ti :$PORT)
            for PID in $PIDS; do
                kill -9 $PID 2>/dev/null || true
            done
            sleep 2
        fi
    fi
    
    # 일반적인 프로세스 종료
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    
    # 최종 확인
    if lsof -i :$PORT >/dev/null 2>&1; then
        log_error "포트 $PORT가 여전히 사용 중입니다. 수동으로 확인해주세요."
        lsof -i :$PORT
        exit 1
    fi
    
    log_success "기존 프로세스 종료 완료"
    
    # 프론트엔드 서버 시작
    log_info "프론트엔드 서버 시작..."
    PORT=$PORT npm start &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    
    # 서버 시작 대기
    sleep 10
    
    # 헬스 체크
    log_info "프론트엔드 서버 헬스 체크..."
    for i in {1..20}; do
        if curl -s http://localhost:$PORT >/dev/null 2>&1; then
            log_success "프론트엔드 서버가 정상적으로 시작되었습니다 (PID: $FRONTEND_PID)"
            break
        fi
        
        if [ $i -eq 20 ]; then
            log_error "프론트엔드 서버 시작 실패"
            log_info "서버 로그 확인:"
            ps aux | grep "next dev" || true
            log_info "포트 사용 상태:"
            lsof -i :$PORT || true
            exit 1
        fi
        
        log_info "헬스 체크 재시도 ($i/20)..."
        sleep 2
    done
    
elif [ "$DEPLOY_ENV" = "server" ]; then
    log_info "6. 서버 배포 수행 중..."
    
    # 서버 정보 확인
    if [ -z "$SERVER_HOST" ]; then
        log_error "SERVER_HOST 환경변수가 설정되지 않았습니다."
        exit 1
    fi
    
    # 서버에서 git pull 실행
    log_info "서버에서 git pull 실행..."
    ssh -o StrictHostKeyChecking=no ubuntu@$SERVER_HOST << 'EOF'
        cd /home/ubuntu/showmethestock
        git pull origin main
EOF
    
    # 서버에서 배포 실행
    log_info "서버에서 배포 실행..."
    ssh -o StrictHostKeyChecking=no ubuntu@$SERVER_HOST << 'EOF'
        cd /home/ubuntu/showmethestock/frontend
        
        # 의존성 설치
        npm ci --production=false
        
        # 빌드
        rm -rf .next
        NODE_ENV=production npm run build
        
        # 기존 프로세스 완전 종료
        sudo pkill -f 'next' || true
        sudo lsof -ti :3000 | xargs -r sudo kill -9 || true
        sleep 3
        
        # 프론트엔드 서비스 재시작
        sudo systemctl restart stock-finder-frontend
        
        # 서비스 상태 확인
        sleep 10
        if sudo systemctl is-active --quiet stock-finder-frontend; then
            echo "✅ 프론트엔드 서비스가 정상적으로 시작되었습니다."
        else
            echo "❌ 프론트엔드 서비스 시작 실패"
            exit 1
        fi
        
        # 헬스 체크
        for i in {1..15}; do
            if curl -s http://localhost:3000 > /dev/null 2>&1; then
                echo "✅ 프론트엔드 서버 헬스 체크 통과"
                break
            fi
            if [ $i -eq 15 ]; then
                echo "❌ 프론트엔드 서버 헬스 체크 실패"
                exit 1
            fi
            sleep 2
        done
EOF
    
    if [ $? -eq 0 ]; then
        log_success "서버 배포 완료"
    else
        log_error "서버 배포 실패"
        exit 1
    fi
fi

# 7. 배포 후 검증
log_info "7. 배포 후 검증 중..."

# 페이지 접근 테스트
PAGES=("/" "/customer-scanner" "/login" "/admin")
for page in "${PAGES[@]}"; do
    if curl -s http://localhost:3000$page > /dev/null 2>&1; then
        log_success "페이지 $page 접근 가능"
    else
        log_warning "페이지 $page 접근 실패"
    fi
done

# 8. 배포 완료
log_success "프론트엔드 배포가 성공적으로 완료되었습니다!"
log_info "프론트엔드 서버: http://localhost:3000"

# 배포 정보 저장
echo "{
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"environment\": \"$DEPLOY_ENV\",
    \"node_version\": \"$NODE_VERSION\",
    \"npm_version\": \"$NPM_VERSION\",
    \"frontend_pid\": \"$FRONTEND_PID\",
    \"port\": \"$PORT\",
    \"status\": \"success\"
}" > ../deploy-frontend.json

log_info "배포 정보가 deploy-frontend.json에 저장되었습니다."