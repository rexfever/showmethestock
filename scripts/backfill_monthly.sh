#!/bin/bash

# 월별 백필 실행 스크립트
# 사용법: ./backfill_monthly.sh 2024 1 [workers]

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
    echo "사용법: $0 <year> <month> [workers]"
    echo ""
    echo "매개변수:"
    echo "  year     연도 (예: 2024)"
    echo "  month    월 (1-12)"
    echo "  workers  병렬 워커 수 (기본값: 4)"
    echo ""
    echo "예시:"
    echo "  $0 2024 1        # 2024년 1월 전체"
    echo "  $0 2024 1 8      # 2024년 1월 전체 (8개 워커)"
    exit 1
}

# 매개변수 검증
if [ $# -lt 2 ]; then
    log_error "매개변수가 부족합니다."
    usage
fi

YEAR=$1
MONTH=$2
WORKERS=${3:-4}

# 연도 검증
if ! [[ "$YEAR" =~ ^[0-9]{4}$ ]] || [ "$YEAR" -lt 2020 ] || [ "$YEAR" -gt 2030 ]; then
    log_error "잘못된 연도: $YEAR (2020-2030 범위)"
    exit 1
fi

# 월 검증
if ! [[ "$MONTH" =~ ^[0-9]+$ ]] || [ "$MONTH" -lt 1 ] || [ "$MONTH" -gt 12 ]; then
    log_error "잘못된 월: $MONTH (1-12 범위)"
    exit 1
fi

# 워커 수 검증
if ! [[ "$WORKERS" =~ ^[0-9]+$ ]] || [ "$WORKERS" -lt 1 ] || [ "$WORKERS" -gt 16 ]; then
    log_error "워커 수는 1-16 사이의 숫자여야 합니다: $WORKERS"
    exit 1
fi

# 월의 첫째 날과 마지막 날 계산
START_DATE=$(printf "%04d-%02d-01" "$YEAR" "$MONTH")

# 다음 달의 첫째 날을 구한 후 하루 빼기 (macOS 호환)
if [ "$MONTH" -eq 12 ]; then
    NEXT_YEAR=$((YEAR + 1))
    NEXT_MONTH=1
else
    NEXT_YEAR=$YEAR
    NEXT_MONTH=$((MONTH + 1))
fi

NEXT_MONTH_FIRST=$(printf "%04d-%02d-01" "$NEXT_YEAR" "$NEXT_MONTH")
# macOS와 Linux 모두 지원
if date -j -v-1d -f "%Y-%m-%d" "$NEXT_MONTH_FIRST" "+%Y-%m-%d" >/dev/null 2>&1; then
    END_DATE=$(date -j -v-1d -f "%Y-%m-%d" "$NEXT_MONTH_FIRST" "+%Y-%m-%d")
else
    END_DATE=$(date -d "$NEXT_MONTH_FIRST - 1 day" +%Y-%m-%d)
fi

log_info "월별 백필 실행"
log_info "대상: ${YEAR}년 ${MONTH}월"
log_info "기간: $START_DATE ~ $END_DATE"
log_info "워커 수: $WORKERS"

# 프로젝트 루트 디렉토리 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 백필 실행 스크립트 호출
BACKFILL_SCRIPT="$SCRIPT_DIR/run_backfill.sh"

if [ ! -f "$BACKFILL_SCRIPT" ]; then
    log_error "백필 실행 스크립트를 찾을 수 없습니다: $BACKFILL_SCRIPT"
    exit 1
fi

log_info "백필 실행 스크립트 호출 중..."
if bash "$BACKFILL_SCRIPT" "$START_DATE" "$END_DATE" "$WORKERS"; then
    log_success "${YEAR}년 ${MONTH}월 백필 완료!"
else
    log_error "${YEAR}년 ${MONTH}월 백필 실패!"
    exit 1
fi