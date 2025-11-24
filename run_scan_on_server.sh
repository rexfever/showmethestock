#!/bin/bash
# AWS 서버에서 11월 17일 스캔 실행 스크립트

# 서버 정보
SERVER_IP="52.79.145.238"
SERVER_USER="ubuntu"
SCAN_DATE="20251117"

echo "=========================================="
echo "AWS 서버에서 스캔 실행"
echo "=========================================="
echo "서버: $SERVER_USER@$SERVER_IP"
echo "날짜: $SCAN_DATE"
echo ""

# SSH 접속 방법 안내
echo "다음 명령어로 서버에 접속하세요:"
echo ""
echo "방법 1: SSH config 사용 (권장)"
echo "  ssh stock-server"
echo ""
echo "방법 2: 직접 접속"
echo "  ssh ubuntu@52.79.145.238"
echo ""
echo "서버 접속 후 다음 명령어를 실행하세요:"
echo ""
echo "  cd /home/ubuntu/showmethestock"
echo "  git pull origin main"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  python3 run_scan_date.py --date $SCAN_DATE"
echo ""
echo "=========================================="

# 자동 실행 시도 (SSH 키가 설정되어 있을 경우)
if [ -f ~/.ssh/id_rsa ] || [ -f ~/.ssh/id_ed25519 ]; then
    echo "SSH 키를 찾았습니다. 자동 실행을 시도합니다..."
    echo ""
    
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP << EOF
cd /home/ubuntu/showmethestock
git pull origin main
cd backend
source venv/bin/activate
python3 run_scan_date.py --date $SCAN_DATE
EOF
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ 스캔 실행 완료"
    else
        echo ""
        echo "⚠️ 자동 실행 실패. 위의 수동 명령어를 사용하세요."
    fi
else
    echo "SSH 키를 찾을 수 없습니다. 수동으로 접속하여 실행하세요."
fi

