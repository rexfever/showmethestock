#!/bin/bash
# 서버 DB 마이그레이션 실행 스크립트

echo "=== 서버 DB 마이그레이션 실행 ==="
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

# 마이그레이션 실행
echo ""
echo "🚀 서버 DB 마이그레이션 시작..."
cd "$(dirname "$0")/.."

# 1. returns 컬럼 JSONB 변환
echo ""
echo "1️⃣ returns 컬럼 JSONB 변환..."
python3 << 'PYEOF'
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['DATABASE_URL'] = os.environ.get('SERVER_DATABASE_URL')
os.environ['SERVER_DATABASE_URL'] = os.environ.get('SERVER_DATABASE_URL')

# db_manager 재로드
import importlib
if 'db_manager' in sys.modules:
    importlib.reload(sys.modules['db_manager'])

from migrations.convert_returns_to_jsonb import convert_returns_to_jsonb
convert_returns_to_jsonb()
PYEOF

# 2. returns 데이터 업데이트
echo ""
echo "2️⃣ returns 데이터 업데이트..."
python3 << 'PYEOF'
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['DATABASE_URL'] = os.environ.get('SERVER_DATABASE_URL')
os.environ['SERVER_DATABASE_URL'] = os.environ.get('SERVER_DATABASE_URL')

# db_manager 재로드
import importlib
if 'db_manager' in sys.modules:
    importlib.reload(sys.modules['db_manager'])

from migrations.update_returns_data import main
main()
PYEOF

echo ""
echo "✅ 서버 DB 마이그레이션 완료!"

