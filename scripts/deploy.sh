#!/bin/bash

# 통합 배포 스크립트
# 사용법: ./scripts/deploy.sh [local|server] [backend|frontend|all]

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
    echo -e "${PURPLE}[DEPLOY]${NC} $1"
}

# 배포 환경 및 대상 확인
DEPLOY_ENV=${1:-local}
DEPLOY_TARGET=${2:-all}

if [[ "$DEPLOY_ENV" != "local" && "$DEPLOY_ENV" != "server" ]]; then
    log_error "사용법: $0 [local|server] [backend|frontend|all]"
    exit 1
fi

if [[ "$DEPLOY_TARGET" != "backend" && "$DEPLOY_TARGET" != "frontend" && "$DEPLOY_TARGET" != "all" ]]; then
    log_error "사용법: $0 [local|server] [backend|frontend|all]"
    exit 1
fi

log_header "🚀 통합 배포 시작"
log_info "환경: $DEPLOY_ENV"
log_info "대상: $DEPLOY_TARGET"
echo ""

# 배포 시작 시간 기록
DEPLOY_START_TIME=$(date +%s)

# 1. 사전 체크
log_header "1. 사전 체크 수행"
log_info "Git 상태 확인..."

# Git 상태 확인
if [ -d ".git" ]; then
    if ! git diff --quiet; then
        log_warning "커밋되지 않은 변경사항이 있습니다."
        read -p "계속 진행하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "배포가 취소되었습니다."
            exit 0
        fi
    fi
    
    # 현재 브랜치 확인
    CURRENT_BRANCH=$(git branch --show-current)
    log_info "현재 브랜치: $CURRENT_BRANCH"
    
    # 최신 커밋 정보
    LAST_COMMIT=$(git log -1 --oneline)
    log_info "최신 커밋: $LAST_COMMIT"
else
    log_warning "Git 저장소가 아닙니다."
fi

# 2. 백엔드 배포
if [[ "$DEPLOY_TARGET" == "backend" || "$DEPLOY_TARGET" == "all" ]]; then
    log_header "2. 백엔드 배포"
    
    if [ -f "scripts/deploy-backend.sh" ]; then
        chmod +x scripts/deploy-backend.sh
        if ./scripts/deploy-backend.sh $DEPLOY_ENV; then
            log_success "백엔드 배포 완료"
        else
            log_error "백엔드 배포 실패"
            exit 1
        fi
    else
        log_error "백엔드 배포 스크립트를 찾을 수 없습니다."
        exit 1
    fi
    echo ""
fi

# 3. 프론트엔드 배포
if [[ "$DEPLOY_TARGET" == "frontend" || "$DEPLOY_TARGET" == "all" ]]; then
    log_header "3. 프론트엔드 배포"
    
    if [ -f "scripts/deploy-frontend.sh" ]; then
        chmod +x scripts/deploy-frontend.sh
        if ./scripts/deploy-frontend.sh $DEPLOY_ENV; then
            log_success "프론트엔드 배포 완료"
        else
            log_error "프론트엔드 배포 실패"
            exit 1
        fi
    else
        log_error "프론트엔드 배포 스크립트를 찾을 수 없습니다."
        exit 1
    fi
    echo ""
fi

# 4. 통합 테스트
log_header "4. 통합 테스트"
log_info "전체 시스템 테스트 실행..."

# 백엔드와 프론트엔드가 모두 배포된 경우 통합 테스트
if [[ "$DEPLOY_TARGET" == "all" ]]; then
    if [ -f "run_admin_tests.sh" ]; then
        chmod +x run_admin_tests.sh
        if ./run_admin_tests.sh; then
            log_success "통합 테스트 완료"
        else
            log_warning "통합 테스트에서 일부 실패가 발생했습니다."
        fi
    else
        log_warning "통합 테스트 스크립트를 찾을 수 없습니다."
    fi
fi

# 5. 배포 후 검증
log_header "5. 배포 후 검증"

# 서비스 상태 확인
if [[ "$DEPLOY_ENV" == "local" ]]; then
    log_info "로컬 서비스 상태 확인..."
    
    # 백엔드 확인
    if [[ "$DEPLOY_TARGET" == "backend" || "$DEPLOY_TARGET" == "all" ]]; then
        if curl -s http://localhost:8010/health > /dev/null 2>&1; then
            log_success "백엔드 서비스 정상"
        else
            log_error "백엔드 서비스 오류"
        fi
    fi
    
    # 프론트엔드 확인
    if [[ "$DEPLOY_TARGET" == "frontend" || "$DEPLOY_TARGET" == "all" ]]; then
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            log_success "프론트엔드 서비스 정상"
        else
            log_error "프론트엔드 서비스 오류"
        fi
    fi
fi

# 6. 배포 완료
DEPLOY_END_TIME=$(date +%s)
DEPLOY_DURATION=$((DEPLOY_END_TIME - DEPLOY_START_TIME))

log_header "🎉 배포 완료!"
log_success "배포 시간: ${DEPLOY_DURATION}초"
log_info "환경: $DEPLOY_ENV"
log_info "대상: $DEPLOY_TARGET"

if [[ "$DEPLOY_ENV" == "local" ]]; then
    if [[ "$DEPLOY_TARGET" == "backend" || "$DEPLOY_TARGET" == "all" ]]; then
        log_info "백엔드: http://localhost:8010"
        log_info "API 문서: http://localhost:8010/docs"
    fi
    if [[ "$DEPLOY_TARGET" == "frontend" || "$DEPLOY_TARGET" == "all" ]]; then
        log_info "프론트엔드: http://localhost:3000"
    fi
fi

# 배포 정보 저장
echo "{
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"environment\": \"$DEPLOY_ENV\",
    \"target\": \"$DEPLOY_TARGET\",
    \"duration_seconds\": $DEPLOY_DURATION,
    \"git_branch\": \"$CURRENT_BRANCH\",
    \"git_commit\": \"$LAST_COMMIT\",
    \"status\": \"success\"
}" > deploy-summary.json

log_info "배포 요약이 deploy-summary.json에 저장되었습니다."

# 7. 다음 단계 안내
log_header "📋 다음 단계"
log_info "1. 브라우저에서 애플리케이션 접속 확인"
log_info "2. 주요 기능 테스트"
log_info "3. 로그 모니터링"
log_info "4. 필요시 롤백 스크립트 실행"

echo ""
log_success "배포가 성공적으로 완료되었습니다! 🚀"