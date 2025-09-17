#!/bin/bash

# 개발 서버 통합 실행 스크립트
echo "🚀 개발 서버 시작 중..."

# 프로젝트 루트로 이동
cd "$(dirname "$0")"

# 기존 프로세스 정리
echo "기존 프로세스 정리 중..."
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

# 백엔드 시작
echo "📡 백엔드 서버 시작 중..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --reload --host 0.0.0.0 --port 8010 > backend.log 2>&1 &
BACKEND_PID=$!
echo "백엔드 PID: $BACKEND_PID"

# 프론트엔드 시작
echo "🌐 프론트엔드 서버 시작 중..."
cd ../frontend
nohup npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "프론트엔드 PID: $FRONTEND_PID"

# 서버 시작 대기
echo "서버 시작 대기 중..."
sleep 5

# 상태 확인
echo ""
echo "✅ 서버가 시작되었습니다!"
echo "📡 백엔드: http://localhost:8010"
echo "🌐 프론트엔드: http://localhost:3000"
echo ""
echo "📋 관리 명령어:"
echo "  - 로그 확인: tail -f backend/backend.log"
echo "  - 로그 확인: tail -f frontend/frontend.log"
echo "  - 프로세스 종료: pkill -f 'uvicorn main:app' && pkill -f 'next dev'"
echo ""
echo "프로세스 ID:"
echo "  - 백엔드: $BACKEND_PID"
echo "  - 프론트엔드: $FRONTEND_PID"
