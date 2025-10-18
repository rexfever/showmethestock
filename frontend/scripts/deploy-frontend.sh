#!/bin/bash
echo "🚀 프론트엔드 배포 시작"
cd frontend
npm ci --production=false
rm -rf .next
npm run build
pkill -f "next dev" || true
PORT=3000 npm run dev &
echo "✅ 프론트엔드 배포 완료"
