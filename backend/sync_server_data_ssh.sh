#!/bin/bash
# SSH 터널링을 통한 서버 DB 동기화 스크립트

echo "=== SSH 터널링을 통한 서버 DB 동기화 ==="
echo ""

# SSH 터널 생성 (백그라운드)
SSH_TUNNEL_PID=$(ps aux | grep "ssh.*5433:localhost:5432.*sohntech" | grep -v grep | awk '{print $2}')

if [ -z "$SSH_TUNNEL_PID" ]; then
    echo "🔗 SSH 터널 생성 중..."
    ssh -f -N -L 5433:localhost:5432 ubuntu@sohntech.ai.kr
    sleep 2
    echo "✅ SSH 터널 생성 완료 (로컬 포트 5433 -> 서버 localhost:5432)"
else
    echo "✅ 기존 SSH 터널 사용 중 (PID: $SSH_TUNNEL_PID)"
fi

# 환경 변수 설정
export SERVER_DATABASE_URL="postgresql://stockfinder:stockfinder_pass@localhost:5433/stockfinder"

# 동기화 실행
echo ""
echo "🚀 동기화 시작..."
cd "$(dirname "$0")"
python3 sync_server_data.py

# SSH 터널 종료 (선택사항)
# kill $SSH_TUNNEL_PID

