#!/bin/bash

# Terraform 배포 스크립트
# 사용법: ./deploy.sh [init|plan|apply|destroy|output]

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

# 사용법 출력
usage() {
    echo "사용법: $0 [init|plan|apply|destroy|output|status]"
    echo ""
    echo "명령어:"
    echo "  init    - Terraform 초기화"
    echo "  plan    - 배포 계획 확인"
    echo "  apply   - 인프라 생성/업데이트"
    echo "  destroy - 인프라 삭제"
    echo "  output  - 출력값 확인"
    echo "  status  - 현재 상태 확인"
    echo ""
    echo "예시:"
    echo "  $0 init"
    echo "  $0 plan"
    echo "  $0 apply"
    exit 1
}

# Terraform 디렉토리로 이동
cd "$(dirname "$0")"

# 명령어 확인
if [ $# -eq 0 ]; then
    usage
fi

COMMAND=$1

case $COMMAND in
    "init")
        log_info "Terraform을 초기화합니다..."
        terraform init
        log_success "Terraform 초기화 완료"
        ;;
    
    "plan")
        log_info "배포 계획을 확인합니다..."
        terraform plan
        ;;
    
    "apply")
        log_warning "인프라를 생성/업데이트합니다..."
        log_warning "이 작업은 AWS 리소스를 생성하거나 수정할 수 있습니다."
        read -p "계속하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            terraform apply -auto-approve
            log_success "인프라 배포 완료"
            echo ""
            log_info "배포된 리소스 정보:"
            terraform output
        else
            log_info "배포가 취소되었습니다."
        fi
        ;;
    
    "destroy")
        log_error "⚠️  경고: 이 작업은 모든 인프라를 삭제합니다!"
        log_error "삭제될 리소스:"
        terraform plan -destroy
        echo ""
        read -p "정말로 삭제하시겠습니까? (yes 입력): " -r
        if [[ $REPLY == "yes" ]]; then
            terraform destroy -auto-approve
            log_success "인프라 삭제 완료"
        else
            log_info "삭제가 취소되었습니다."
        fi
        ;;
    
    "output")
        log_info "현재 출력값:"
        terraform output
        ;;
    
    "status")
        log_info "현재 상태:"
        terraform show
        ;;
    
    *)
        log_error "알 수 없는 명령어: $COMMAND"
        usage
        ;;
esac



