#!/bin/bash
# 서버에서 직접 실행하는 배포 스크립트
# 사용법: cd /home/ubuntu/showmethestock/backend && bash deploy_server_manual.sh

set -e

echo "=========================================="
echo "서버 배포 시작"
echo "=========================================="

# 1. 최신 코드 가져오기
echo ""
echo "[1/4] 최신 코드 가져오기..."
cd /home/ubuntu/showmethestock
git pull origin main

# 2. 의존성 설치
echo ""
echo "[2/4] 의존성 설치..."
cd backend
source venv/bin/activate
pip install -r requirements.txt --quiet

# FinanceDataReader 별도 설치 (requirements.txt에서 오류 발생)
echo "  FinanceDataReader 설치 중..."
pip install git+https://github.com/FinanceData/FinanceDataReader.git --quiet || echo "  ⚠️ FinanceDataReader 설치 실패 (이미 설치되어 있을 수 있음)"

# 3. 백엔드 서비스 재시작
echo ""
echo "[3/4] 백엔드 서비스 재시작..."
sudo systemctl restart stock-finder-backend

# 서비스 상태 확인
sleep 3
if sudo systemctl is-active --quiet stock-finder-backend; then
    echo "  ✅ 백엔드 서비스가 정상적으로 시작되었습니다."
else
    echo "  ❌ 백엔드 서비스 시작 실패"
    exit 1
fi

# 헬스 체크
echo ""
echo "[4/4] 헬스 체크 중..."
for i in {1..10}; do
    if curl -s http://localhost:8010/health > /dev/null 2>&1; then
        echo "  ✅ 백엔드 서버 헬스 체크 통과"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "  ❌ 백엔드 서버 헬스 체크 실패"
        exit 1
    fi
    sleep 2
done

echo ""
echo "=========================================="
echo "✅ 서버 배포 완료"
echo "=========================================="

