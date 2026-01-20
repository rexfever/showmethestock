#!/bin/bash
# 전체 배포 스크립트 (백엔드 + 프론트엔드)
# 사용법: bash deploy_all.sh

set -e

echo "=========================================="
echo "전체 서버 배포 시작"
echo "=========================================="

# 1. 백엔드 배포
echo ""
echo "=========================================="
echo "[1/2] 백엔드 배포"
echo "=========================================="
cd /home/ubuntu/showmethestock/backend
bash deploy_server_manual.sh

# 2. 프론트엔드 배포
echo ""
echo "=========================================="
echo "[2/2] 프론트엔드 배포"
echo "=========================================="
cd /home/ubuntu/showmethestock/frontend
bash deploy_server_manual.sh

echo ""
echo "=========================================="
echo "✅ 전체 배포 완료"
echo "=========================================="

