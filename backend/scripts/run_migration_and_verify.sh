#!/bin/bash
# v3 추천 시스템 리팩터링 마이그레이션 실행 및 검증 스크립트

set -e

echo "🚀 v3 추천 시스템 리팩터링 마이그레이션 시작"
echo ""

# 1. DB 마이그레이션 실행
echo "📊 1단계: DB 스키마 마이그레이션 실행"
psql -h localhost -U postgres -d showmethestock -f backend/migrations/20251215_create_recommendations_tables.sql
echo "✅ DB 스키마 마이그레이션 완료"
echo ""

# 2. 백필 스크립트 실행 (dry-run 먼저)
echo "📦 2단계: 백필 스크립트 실행 (dry-run)"
python3 backend/scripts/backfill_recommendations.py --dry-run
echo ""

# 사용자 확인
read -p "백필을 실제로 실행하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "📦 백필 스크립트 실행 (실제 저장)"
    python3 backend/scripts/backfill_recommendations.py
    echo "✅ 백필 완료"
else
    echo "⏭️ 백필 건너뜀"
fi
echo ""

# 3. 한국항공우주(047810) 검증
echo "🔍 3단계: 한국항공우주(047810) 검증"
python3 backend/scripts/backfill_recommendations.py --verify --ticker 047810
echo ""

echo "✅ 모든 작업 완료!"



