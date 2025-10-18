#!/bin/bash

# 일일 포트폴리오 업데이트 cron 작업 설정
# 사용법: ./scripts/setup-daily-update-cron.sh

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

log_info "일일 포트폴리오 업데이트 cron 작업 설정 시작"

# 프로젝트 루트 디렉토리 확인
PROJECT_ROOT="/home/ubuntu/showmethestock"
if [ ! -d "$PROJECT_ROOT" ]; then
    log_error "프로젝트 루트 디렉토리를 찾을 수 없습니다: $PROJECT_ROOT"
    exit 1
fi

# Python 경로 확인
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    log_error "Python3를 찾을 수 없습니다."
    exit 1
fi

log_info "Python 경로: $PYTHON_PATH"

# 일일 업데이트 스크립트 생성
UPDATE_SCRIPT="$PROJECT_ROOT/scripts/daily-update.sh"
log_info "일일 업데이트 스크립트 생성: $UPDATE_SCRIPT"

cat > "$UPDATE_SCRIPT" << EOF
#!/bin/bash

# 일일 포트폴리오 업데이트 및 알림 스크립트
# 매일 오전 9시에 실행

cd $PROJECT_ROOT/backend
export PYTHONPATH=$PROJECT_ROOT/backend:$PYTHONPATH

# 로그 파일
LOG_FILE="$PROJECT_ROOT/logs/daily-update.log"
mkdir -p "$PROJECT_ROOT/logs"

# 일일 업데이트 실행
echo "\$(date): 일일 포트폴리오 업데이트 시작" >> \$LOG_FILE
$PYTHON_PATH daily_update_service.py >> \$LOG_FILE 2>&1
echo "\$(date): 일일 포트폴리오 업데이트 완료" >> \$LOG_FILE

# 일일 알림 전송
echo "\$(date): 일일 포트폴리오 알림 전송 시작" >> \$LOG_FILE
$PYTHON_PATH notification_service.py >> \$LOG_FILE 2>&1
echo "\$(date): 일일 포트폴리오 알림 전송 완료" >> \$LOG_FILE
EOF

# 실행 권한 부여
chmod +x "$UPDATE_SCRIPT"
log_success "일일 업데이트 스크립트 생성 완료"

# 기존 cron 작업 확인
log_info "기존 cron 작업 확인 중..."
if crontab -l 2>/dev/null | grep -q "daily-update.sh"; then
    log_warning "일일 업데이트 cron 작업이 이미 설정되어 있습니다."
    read -p "기존 작업을 교체하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "cron 작업 설정이 취소되었습니다."
        exit 0
    fi
fi

# cron 작업 추가
log_info "cron 작업 추가 중..."

# 기존 cron 작업 백업
crontab -l > /tmp/crontab_backup 2>/dev/null || touch /tmp/crontab_backup

# 일일 업데이트 cron 작업 추가 (매일 오전 9시)
CRON_JOB="0 9 * * * $UPDATE_SCRIPT"

# 기존 daily-update.sh 관련 cron 작업 제거
grep -v "daily-update.sh" /tmp/crontab_backup > /tmp/crontab_new || touch /tmp/crontab_new

# 새 cron 작업 추가
echo "$CRON_JOB" >> /tmp/crontab_new

# cron 작업 적용
crontab /tmp/crontab_new

# 임시 파일 정리
rm -f /tmp/crontab_backup /tmp/crontab_new

log_success "일일 업데이트 cron 작업 설정 완료"
log_info "실행 시간: 매일 오전 9시"
log_info "스크립트: $UPDATE_SCRIPT"
log_info "로그 파일: $PROJECT_ROOT/logs/daily-update.log"

# 현재 cron 작업 확인
log_info "현재 설정된 cron 작업:"
crontab -l | grep -E "(daily-update|포트폴리오)" || echo "관련 cron 작업이 없습니다."

log_success "일일 포트폴리오 업데이트 cron 설정이 완료되었습니다!"
