#!/bin/bash

# 백엔드 배포 스크립트
# 사용법: ./scripts/deploy-backend.sh [local|server]

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

log_info "백엔드 배포 시작 - 환경: $DEPLOY_ENV"

# 1. 사전 체크
log_info "1. 사전 체크 수행 중..."

# Python 버전 확인
if ! command -v python3 &> /dev/null; then
    log_error "Python3가 설치되지 않았습니다."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
log_info "Python 버전: $PYTHON_VERSION"

# 백엔드 디렉토리 확인
if [ ! -d "backend" ]; then
    log_error "backend 디렉토리를 찾을 수 없습니다."
    exit 1
fi

cd backend

# requirements.txt 확인
if [ ! -f "requirements.txt" ]; then
    log_error "requirements.txt 파일을 찾을 수 없습니다."
    exit 1
fi

# 2. 테스트 실행
log_info "2. 백엔드 테스트 실행 중..."

# 단위 테스트 실행
if [ -f "test_admin_rescan.py" ]; then
    log_info "관리자 재스캔 테스트 실행..."
    if python3 test_admin_rescan.py; then
        log_success "관리자 재스캔 테스트 통과"
    else
        log_error "관리자 재스캔 테스트 실패"
        exit 1
    fi
fi

# 3. 의존성 설치
log_info "3. 의존성 설치 중..."

if [ -f "requirements.txt" ]; then
    log_info "Python 패키지 설치..."
    pip3 install -r requirements.txt --quiet
    log_success "의존성 설치 완료"
else
    log_warning "requirements.txt가 없습니다."
fi

# 4. 코드 검증
log_info "4. 코드 검증 중..."

# Python 문법 검사
log_info "Python 문법 검사..."
if python3 -m py_compile main.py; then
    log_success "Python 문법 검사 통과"
else
    log_error "Python 문법 오류 발견"
    exit 1
fi

# 5. 환경별 배포
if [ "$DEPLOY_ENV" = "local" ]; then
    log_info "5. 로컬 배포 수행 중..."
    
    # 기존 프로세스 완전 종료
    log_info "기존 백엔드 프로세스 종료 중..."
    
    # 포트 8010 사용 중인 프로세스 확인
    if lsof -i :8010 >/dev/null 2>&1; then
        log_warning "포트 8010이 사용 중입니다. 프로세스를 종료합니다."
        
        # 프로세스 ID 추출
        PIDS=$(lsof -ti :8010)
        for PID in $PIDS; do
            log_info "프로세스 $PID 종료 중..."
            kill -TERM $PID 2>/dev/null || true
        done
        
        # 3초 대기
        sleep 3
        
        # 여전히 실행 중인 프로세스 강제 종료
        if lsof -i :8010 >/dev/null 2>&1; then
            log_warning "강제 종료가 필요합니다."
            PIDS=$(lsof -ti :8010)
            for PID in $PIDS; do
                kill -9 $PID 2>/dev/null || true
            done
            sleep 2
        fi
    fi
    
    # 일반적인 프로세스 종료
    pkill -f "python3.*main.py" 2>/dev/null || true
    pkill -f "uvicorn.*main:app" 2>/dev/null || true
    
    # 최종 확인
    if lsof -i :8010 >/dev/null 2>&1; then
        log_error "포트 8010이 여전히 사용 중입니다. 수동으로 확인해주세요."
        lsof -i :8010
        exit 1
    fi
    
    log_success "기존 프로세스 종료 완료"
    
    # 백엔드 서버 시작
    log_info "백엔드 서버 시작..."
    if [ -f "start.py" ]; then
        python3 start.py &
        BACKEND_PID=$!
        echo $BACKEND_PID > ../backend.pid
    else
        # uvicorn으로 직접 시작
        uvicorn main:app --host 0.0.0.0 --port 8010 --reload &
        BACKEND_PID=$!
        echo $BACKEND_PID > ../backend.pid
    fi
    
    # 서버 시작 대기
    sleep 5
    
    # 헬스 체크
    log_info "백엔드 서버 헬스 체크..."
    for i in {1..15}; do
        if curl -s http://localhost:8010/health >/dev/null 2>&1; then
            log_success "백엔드 서버가 정상적으로 시작되었습니다 (PID: $BACKEND_PID)"
            break
        fi
        
        if [ $i -eq 15 ]; then
            log_error "백엔드 서버 시작 실패"
            log_info "서버 로그 확인:"
            ps aux | grep uvicorn
            log_info "포트 사용 상태:"
            lsof -i :8010 || true
            exit 1
        fi
        
        log_info "헬스 체크 재시도 ($i/15)..."
        sleep 2
    done
    
elif [ "$DEPLOY_ENV" = "server" ]; then
    log_info "5. 서버 배포 수행 중..."
    
    # 서버 정보 확인
    if [ -z "$SERVER_HOST" ]; then
        log_error "SERVER_HOST 환경변수가 설정되지 않았습니다."
        exit 1
    fi
    
    # 서버에 코드 업로드
    log_info "서버에 코드 업로드..."
    rsync -avz --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
        ./ ubuntu@$SERVER_HOST:/home/ubuntu/showmethestock/backend/
    
    # 서버에서 배포 실행
    log_info "서버에서 배포 실행..."
    ssh ubuntu@$SERVER_HOST << 'EOF'
        cd /home/ubuntu/showmethestock/backend
        
        # 의존성 설치
        pip3 install -r requirements.txt --quiet
        
        # 기존 프로세스 완전 종료
        sudo pkill -f 'python.*main.py' || true
        sudo pkill -f 'uvicorn.*main:app' || true
        sudo lsof -ti :8010 | xargs -r sudo kill -9 || true
        sleep 3
        
        # 백엔드 서비스 재시작
        sudo systemctl restart stock-finder-backend
        
        # 서비스 상태 확인
        sleep 5
        if sudo systemctl is-active --quiet stock-finder-backend; then
            echo "✅ 백엔드 서비스가 정상적으로 시작되었습니다."
        else
            echo "❌ 백엔드 서비스 시작 실패"
            exit 1
        fi
        
        # 헬스 체크
        for i in {1..10}; do
            if curl -s http://localhost:8010/health > /dev/null 2>&1; then
                echo "✅ 백엔드 서버 헬스 체크 통과"
                break
            fi
            if [ $i -eq 10 ]; then
                echo "❌ 백엔드 서버 헬스 체크 실패"
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

# 6. 배포 후 검증
log_info "6. 배포 후 검증 중..."

# API 엔드포인트 테스트
ENDPOINTS=("/health" "/scan" "/latest-scan")
for endpoint in "${ENDPOINTS[@]}"; do
    if curl -s http://localhost:8010$endpoint > /dev/null 2>&1; then
        log_success "API 엔드포인트 $endpoint 정상"
    else
        log_warning "API 엔드포인트 $endpoint 응답 없음"
    fi
done

# 7. 배포 완료
log_success "백엔드 배포가 성공적으로 완료되었습니다!"
log_info "백엔드 서버: http://localhost:8010"
log_info "API 문서: http://localhost:8010/docs"

# 배포 정보 저장
echo "{
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"environment\": \"$DEPLOY_ENV\",
    \"python_version\": \"$PYTHON_VERSION\",
    \"backend_pid\": \"$BACKEND_PID\",
    \"status\": \"success\"
}" > ../deploy-backend.json

log_info "배포 정보가 deploy-backend.json에 저장되었습니다."