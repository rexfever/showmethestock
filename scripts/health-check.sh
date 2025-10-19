#!/bin/bash

# 헬스체크 및 모니터링 스크립트
# 사용법: ./scripts/health-check.sh [blue|green|all]

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

# 환경 설정
TARGET_ENV=${1:-all}

# 헬스체크 함수
check_backend() {
    local env=$1
    local port=$2
    
    log_info "백엔드 헬스체크 ($env, 포트: $port)..."
    
    # 서비스 상태 확인
    if sudo systemctl is-active --quiet stock-finder-backend-$env; then
        log_success "백엔드 서비스 실행 중"
    else
        log_error "백엔드 서비스 중지됨"
        return 1
    fi
    
    # API 응답 확인
    if curl -s -f http://localhost:$port/health > /dev/null 2>&1; then
        log_success "백엔드 API 응답 정상"
    else
        log_error "백엔드 API 응답 실패"
        return 1
    fi
    
    # 응답 시간 측정
    response_time=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:$port/health)
    log_info "백엔드 응답 시간: ${response_time}초"
    
    return 0
}

check_frontend() {
    local env=$1
    local port=$2
    
    log_info "프론트엔드 헬스체크 ($env, 포트: $port)..."
    
    # 서비스 상태 확인
    if sudo systemctl is-active --quiet stock-finder-frontend-$env; then
        log_success "프론트엔드 서비스 실행 중"
    else
        log_error "프론트엔드 서비스 중지됨"
        return 1
    fi
    
    # 웹 페이지 응답 확인
    if curl -s -f http://localhost:$port > /dev/null 2>&1; then
        log_success "프론트엔드 웹페이지 응답 정상"
    else
        log_error "프론트엔드 웹페이지 응답 실패"
        return 1
    fi
    
    # 응답 시간 측정
    response_time=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:$port)
    log_info "프론트엔드 응답 시간: ${response_time}초"
    
    return 0
}

check_database() {
    log_info "데이터베이스 헬스체크..."
    
    # DB 파일 존재 확인
    local db_files=("snapshots.db" "portfolio.db" "email_verifications.db" "news_data.db")
    
    for db_file in "${db_files[@]}"; do
        if [ -f "/home/ubuntu/showmethestock/backend/$db_file" ]; then
            log_success "DB 파일 존재: $db_file"
        else
            log_warning "DB 파일 없음: $db_file"
        fi
    done
    
    # DB 연결 테스트
    if python3 -c "
import sqlite3
import sys
try:
    conn = sqlite3.connect('/home/ubuntu/showmethestock/backend/snapshots.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM scan_rank')
    count = cursor.fetchone()[0]
    conn.close()
    print(f'✅ DB 연결 성공: scan_rank 테이블에 {count}개 레코드')
except Exception as e:
    print(f'❌ DB 연결 실패: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log_success "데이터베이스 연결 정상"
    else
        log_error "데이터베이스 연결 실패"
        return 1
    fi
    
    return 0
}

check_nginx() {
    log_info "Nginx 헬스체크..."
    
    # Nginx 서비스 상태
    if sudo systemctl is-active --quiet nginx; then
        log_success "Nginx 서비스 실행 중"
    else
        log_error "Nginx 서비스 중지됨"
        return 1
    fi
    
    # Nginx 설정 검증
    if sudo nginx -t > /dev/null 2>&1; then
        log_success "Nginx 설정 정상"
    else
        log_error "Nginx 설정 오류"
        return 1
    fi
    
    # 외부 접근 확인
    if curl -s -f http://sohntech.ai.kr > /dev/null 2>&1; then
        log_success "외부 접근 정상"
    else
        log_error "외부 접근 실패"
        return 1
    fi
    
    return 0
}

# 메인 헬스체크
main() {
    echo "🏥 헬스체크 시작"
    echo "대상: $TARGET_ENV"
    echo ""
    
    local overall_status=0
    
    # Blue 환경 체크
    if [[ "$TARGET_ENV" == "blue" || "$TARGET_ENV" == "all" ]]; then
        echo "🔵 Blue 환경 체크"
        if ! check_backend "blue" "8010"; then overall_status=1; fi
        if ! check_frontend "blue" "3000"; then overall_status=1; fi
        echo ""
    fi
    
    # Green 환경 체크
    if [[ "$TARGET_ENV" == "green" || "$TARGET_ENV" == "all" ]]; then
        echo "🟢 Green 환경 체크"
        if ! check_backend "green" "8011"; then overall_status=1; fi
        if ! check_frontend "green" "3001"; then overall_status=1; fi
        echo ""
    fi
    
    # 공통 체크
    echo "🔧 공통 시스템 체크"
    if ! check_database; then overall_status=1; fi
    if ! check_nginx; then overall_status=1; fi
    echo ""
    
    # 결과 출력
    if [ $overall_status -eq 0 ]; then
        log_success "🎉 모든 헬스체크 통과!"
        exit 0
    else
        log_error "❌ 일부 헬스체크 실패"
        exit 1
    fi
}

# 스크립트 실행
main "$@"
