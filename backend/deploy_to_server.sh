#!/bin/bash
# 서버 배포 스크립트
# DB 마이그레이션 및 서비스 재시작 포함

set -e

echo "=========================================="
echo "서버 배포 시작"
echo "=========================================="

# 1. 최신 코드 가져오기
echo ""
echo "[1/4] 최신 코드 가져오기..."
git pull origin main

# 2. 의존성 설치
echo ""
echo "[2/4] 의존성 설치..."
source venv/bin/activate
pip install -r requirements.txt --quiet

# 3. DB 마이그레이션 실행
echo ""
echo "[3/4] DB 마이그레이션 실행..."
if [ -f "migrations/optimize_scan_rank_indexes.sql" ]; then
    echo "  - 인덱스 추가 중..."
    psql $DATABASE_URL -f migrations/optimize_scan_rank_indexes.sql
    echo "  ✅ 인덱스 추가 완료"
fi

# 4. 서비스 재시작
echo ""
echo "[4/4] 백엔드 서비스 재시작..."
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
echo "헬스 체크 중..."
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
echo ""
echo "다음 단계 (선택사항):"
echo "  - 잘못된 스캔 데이터 수정: python3 tools/fix_incorrect_scan_data.py --start 20250701 --no-dry-run"
echo ""

