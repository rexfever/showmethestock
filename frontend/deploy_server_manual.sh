#!/bin/bash
# 서버에서 직접 실행하는 프론트엔드 배포 스크립트
# 사용법: cd /home/ubuntu/showmethestock/frontend && bash deploy_server_manual.sh

set -e

echo "=========================================="
echo "프론트엔드 배포 시작"
echo "=========================================="

# 1. 최신 코드 가져오기
echo ""
echo "[1/5] 최신 코드 가져오기..."
cd /home/ubuntu/showmethestock
git pull origin main

# 2. 의존성 설치
echo ""
echo "[2/5] 의존성 설치..."
cd frontend
npm install

# 3. 이전 빌드 캐시 삭제
echo ""
echo "[3/5] 이전 빌드 캐시 삭제..."
rm -rf .next

# 4. 빌드
echo ""
echo "[4/5] 프론트엔드 빌드 중..."
npm run build

# 5. 프론트엔드 서비스 재시작
echo ""
echo "[5/5] 프론트엔드 서비스 재시작..."

# PM2 사용 시
if command -v pm2 &> /dev/null; then
    pm2 restart stock-finder-frontend || pm2 restart all
    sleep 3
    if pm2 list | grep -q "stock-finder-frontend.*online"; then
        echo "  ✅ 프론트엔드 서비스가 정상적으로 시작되었습니다."
    else
        echo "  ❌ 프론트엔드 서비스 시작 실패"
        exit 1
    fi
# systemd 사용 시
elif systemctl list-unit-files | grep -q "stock-finder-frontend"; then
    sudo systemctl restart stock-finder-frontend
    sleep 3
    if sudo systemctl is-active --quiet stock-finder-frontend; then
        echo "  ✅ 프론트엔드 서비스가 정상적으로 시작되었습니다."
    else
        echo "  ❌ 프론트엔드 서비스 시작 실패"
        exit 1
    fi
# 직접 실행 중인 경우
else
    echo "  ⚠️  PM2 또는 systemd 서비스가 없습니다. 수동으로 재시작하세요."
    echo "  실행 명령: PORT=3000 npm run start"
fi

# 헬스 체크
echo ""
echo "헬스 체크 중..."
for i in {1..10}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "  ✅ 프론트엔드 서버 헬스 체크 통과"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "  ❌ 프론트엔드 서버 헬스 체크 실패"
        exit 1
    fi
    sleep 2
done

echo ""
echo "=========================================="
echo "✅ 프론트엔드 배포 완료"
echo "=========================================="
echo ""
echo "⚠️  브라우저 캐시를 삭제하고 새로고침하세요 (Ctrl+Shift+R 또는 Cmd+Shift+R)"

