#!/bin/bash
# v3 추천 시스템 완전 검증 스크립트

set -e

echo "=========================================="
echo "v3 추천 시스템 완전 검증 시작"
echo "=========================================="

# 1. DB 마이그레이션 실행
echo ""
echo "[1단계] DB 마이그레이션 실행"
echo "----------------------------------------"
psql -h localhost -U postgres -d showmethestock -f backend/migrations/20251215_create_recommendations_tables_v2.sql
if [ $? -eq 0 ]; then
    echo "✅ 마이그레이션 성공"
else
    echo "❌ 마이그레이션 실패"
    exit 1
fi

# 2. backfill 전 검증 SQL 실행
echo ""
echo "[2단계] backfill 전 검증 SQL 실행"
echo "----------------------------------------"
echo ""
echo "(A) 중복 ACTIVE 탐지:"
psql -h localhost -U postgres -d showmethestock -c "
SELECT ticker, COUNT(*) as count
FROM recommendations
WHERE status = 'ACTIVE'
GROUP BY ticker
HAVING COUNT(*) > 1;
"

echo ""
echo "(B) 047810 이력 확인:"
psql -h localhost -U postgres -d showmethestock -c "
SELECT 
    recommendation_id,
    anchor_date,
    status,
    created_at,
    anchor_close
FROM recommendations
WHERE ticker = '047810'
ORDER BY created_at DESC;
"

# 3. backfill dry-run
echo ""
echo "[3단계] backfill dry-run"
echo "----------------------------------------"
python3 backend/scripts/backfill_recommendations.py --dry-run

# 사용자 확인
read -p "backfill을 실제로 실행하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    # 4. backfill 실제 실행
    echo ""
    echo "[4단계] backfill 실제 실행"
    echo "----------------------------------------"
    python3 backend/scripts/backfill_recommendations.py
    
    # 5. backfill 후 검증 SQL 재실행
    echo ""
    echo "[5단계] backfill 후 검증 SQL 재실행"
    echo "----------------------------------------"
    echo ""
    echo "(A) 중복 ACTIVE 탐지:"
    psql -h localhost -U postgres -d showmethestock -c "
    SELECT ticker, COUNT(*) as count
    FROM recommendations
    WHERE status = 'ACTIVE'
    GROUP BY ticker
    HAVING COUNT(*) > 1;
    "
    
    echo ""
    echo "(B) 047810 이력 확인:"
    psql -h localhost -U postgres -d showmethestock -c "
    SELECT 
        recommendation_id,
        anchor_date,
        status,
        created_at,
        anchor_close
    FROM recommendations
    WHERE ticker = '047810'
    ORDER BY created_at DESC;
    "
else
    echo "⏭️ backfill 건너뜀"
fi

# 6. Python 검증 스크립트 실행
echo ""
echo "[6단계] Python 검증 스크립트 실행"
echo "----------------------------------------"
python3 backend/scripts/verify_v3_implementation.py

echo ""
echo "=========================================="
echo "검증 완료"
echo "=========================================="



