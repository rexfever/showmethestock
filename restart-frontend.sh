#!/bin/bash

echo "프론트엔드 재시작 중..."

# 1. 모든 Next.js 프로세스 강제 종료
echo "기존 프로세스 종료 중..."
pkill -9 -f "next dev" 2>/dev/null || true
pkill -9 -f "node.*next" 2>/dev/null || true

# 2. 포트 3000 사용 중인 프로세스 확인 및 종료
PORT_PID=$(lsof -ti:3000 2>/dev/null || true)
if [ ! -z "$PORT_PID" ]; then
    echo "포트 3000 사용 중인 프로세스 종료: $PORT_PID"
    kill -9 $PORT_PID 2>/dev/null || true
fi

# 3. 잠시 대기
echo "프로세스 정리 대기 중..."
sleep 3

# 4. 프론트엔드 디렉토리로 이동
cd /home/ubuntu/showmethestock/frontend

# 5. 로그 파일 정리
echo "로그 파일 정리 중..."
> frontend.log

# 6. 프론트엔드 시작
echo "프론트엔드 시작 중..."
nohup npm run dev > frontend.log 2>&1 &

# 7. 시작 확인
echo "프론트엔드 시작 확인 중..."
sleep 5

if ps aux | grep -q "next dev" | grep -v grep; then
    echo "✅ 프론트엔드가 성공적으로 시작되었습니다."
    echo "로그: tail -f /home/ubuntu/showmethestock/frontend/frontend.log"
else
    echo "❌ 프론트엔드 시작에 실패했습니다."
    echo "로그 확인: cat /home/ubuntu/showmethestock/frontend/frontend.log"
fi
