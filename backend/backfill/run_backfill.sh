#!/bin/bash

# 백필 실행 스크립트
# 사용법: ./run_backfill.sh 2020-01-01 2025-06-30 8

START_DATE=${1:-"2024-01-01"}
END_DATE=${2:-"2024-12-31"}
WORKERS=${3:-4}

echo "🚀 백필 실행 시작"
echo "📅 기간: $START_DATE ~ $END_DATE"
echo "👥 워커 수: $WORKERS"
echo ""

# Python 경로 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."

# 백필 실행
python backfill_runner.py --start "$START_DATE" --end "$END_DATE" --workers "$WORKERS"

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo ""
    echo "✅ 백필 완료! 검증을 시작합니다..."
    echo ""
    
    # 검증 실행
    python backfill_verifier.py --start "$START_DATE" --end "$END_DATE"
    
    VERIFY_RESULT=$?
    
    if [ $VERIFY_RESULT -eq 0 ]; then
        echo ""
        echo "🎉 백필 및 검증 모두 성공!"
    else
        echo ""
        echo "⚠️ 백필은 완료되었으나 검증에서 문제가 발견되었습니다."
    fi
else
    echo ""
    echo "❌ 백필 실행 중 오류가 발생했습니다."
fi

exit $RESULT