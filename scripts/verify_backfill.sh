#!/bin/bash

# 백필 검증 스크립트
# 사용법: ./verify_backfill.sh 2024-01-01 2024-01-31

set -e

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

# 사용법 출력
usage() {
    echo "사용법: $0 <start_date> <end_date>"
    echo ""
    echo "매개변수:"
    echo "  start_date  시작 날짜 (YYYY-MM-DD 형식)"
    echo "  end_date    종료 날짜 (YYYY-MM-DD 형식)"
    echo ""
    echo "예시:"
    echo "  $0 2024-01-01 2024-01-31"
    exit 1
}

# 날짜 형식 검증 (macOS 호환)
validate_date() {
    local date=$1
    # macOS와 Linux 모두 지원
    if date -j -f "%Y-%m-%d" "$date" "+%Y-%m-%d" >/dev/null 2>&1; then
        return 0
    elif date -d "$date" >/dev/null 2>&1; then
        return 0
    else
        log_error "잘못된 날짜 형식: $date (YYYY-MM-DD 형식을 사용하세요)"
        exit 1
    fi
}

# 매개변수 검증
if [ $# -ne 2 ]; then
    log_error "매개변수가 올바르지 않습니다."
    usage
fi

START_DATE=$1
END_DATE=$2

# 날짜 형식 검증
validate_date "$START_DATE"
validate_date "$END_DATE"

# 프로젝트 루트 디렉토리 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

log_info "프로젝트 루트: $PROJECT_ROOT"
log_info "백엔드 디렉토리: $BACKEND_DIR"

# 백엔드 디렉토리 존재 확인
if [ ! -d "$BACKEND_DIR" ]; then
    log_error "백엔드 디렉토리를 찾을 수 없습니다: $BACKEND_DIR"
    exit 1
fi

# 백필 모듈 존재 확인
BACKFILL_DIR="$BACKEND_DIR/backfill"
if [ ! -d "$BACKFILL_DIR" ]; then
    log_error "백필 디렉토리를 찾을 수 없습니다: $BACKFILL_DIR"
    exit 1
fi

# Python 가상환경 활성화 (있는 경우)
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    log_info "Python 가상환경 활성화 중..."
    source "$PROJECT_ROOT/venv/bin/activate"
elif [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    log_info "Python 가상환경 활성화 중..."
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# 환경변수 설정
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

log_info "백필 검증 시작"
log_info "기간: $START_DATE ~ $END_DATE"

# 검증 실행
cd "$BACKFILL_DIR"

log_info "백필 검증 스크립트 실행 중..."
if python run_verifier_standalone.py --start "$START_DATE" --end "$END_DATE"; then
    log_success "백필 검증 완료! 모든 검사를 통과했습니다."
    exit 0
else
    log_warning "백필 검증에서 일부 이슈가 발견되었습니다."
    log_info "상세한 내용은 위의 검증 리포트를 확인하세요."
    exit 1
fi