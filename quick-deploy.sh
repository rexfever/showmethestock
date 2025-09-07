#!/bin/bash

# 빠른 배포 스크립트 - 코드 업데이트만
# 사용법: ./quick-deploy.sh [EC2_PUBLIC_IP] [KEY_FILE_PATH]

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 사용법 출력
usage() {
    echo "사용법: $0 <EC2_PUBLIC_IP> <KEY_FILE_PATH>"
    echo "예시: $0 3.34.123.456 ~/Downloads/stock-finder-key.pem"
    exit 1
}

# 인자 확인
if [ $# -ne 2 ]; then
    usage
fi

EC2_IP=$1
KEY_FILE=$2

# 키 파일 존재 확인
if [ ! -f "$KEY_FILE" ]; then
    log_error "키 파일을 찾을 수 없습니다: $KEY_FILE"
    exit 1
fi

log_info "빠른 배포를 시작합니다..."
log_info "EC2 IP: $EC2_IP"

# 원격 배포 스크립트 실행
ssh -i "$KEY_FILE" ubuntu@$EC2_IP '/home/ubuntu/deploy.sh'

log_success "빠른 배포 완료!"
echo ""
echo "📋 접속 정보:"
echo "  - 프론트엔드: http://$EC2_IP"
echo "  - 백엔드 API: http://$EC2_IP:8010"
echo "  - 랜딩 페이지: http://$EC2_IP/landing/"



