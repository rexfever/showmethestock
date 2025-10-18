#!/bin/bash
echo "🚀 통합 배포 시작"
echo "환경: $1, 대상: $2"

if [[ "$2" == "backend" || "$2" == "all" ]]; then
    echo "📦 백엔드 배포 중..."
    ./scripts/deploy-backend.sh
fi

if [[ "$2" == "frontend" || "$2" == "all" ]]; then
    echo "📦 프론트엔드 배포 중..."
    ./scripts/deploy-frontend.sh
fi

echo "✅ 통합 배포 완료"
