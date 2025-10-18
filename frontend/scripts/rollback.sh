#!/bin/bash
echo "🔄 롤백 시작"
echo "환경: $1, 대상: $2"

if [[ "$2" == "backend" || "$2" == "all" ]]; then
    echo "📦 백엔드 롤백 중..."
    pkill -f "python3.*main.py" || true
    cd backend && git checkout HEAD~1 -- . && cd ..
    ./scripts/deploy-backend.sh
fi

if [[ "$2" == "frontend" || "$2" == "all" ]]; then
    echo "📦 프론트엔드 롤백 중..."
    pkill -f "next dev" || true
    cd frontend && git checkout HEAD~1 -- . && cd ..
    ./scripts/deploy-frontend.sh
fi

echo "✅ 롤백 완료"
