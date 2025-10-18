#!/bin/bash

# 매일 현재 수익률 업데이트를 위한 cron 설정 스크립트

SCRIPT_DIR="/Users/rexsmac/workspace/stock-finder/backend"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
UPDATER_SCRIPT="$SCRIPT_DIR/daily_returns_updater.py"
LOG_FILE="$SCRIPT_DIR/daily_returns_update.log"

echo "=== 평일 장 마감 후 현재 수익률 업데이트 Cron 설정 ==="
echo "스크립트 경로: $UPDATER_SCRIPT"
echo "로그 파일: $LOG_FILE"
echo ""

# cron 작업 정의 (평일 오후 4시에 실행 - 장 마감 후, 주말 제외)
CRON_JOB="0 16 * * 1-5 cd $SCRIPT_DIR && $PYTHON_PATH $UPDATER_SCRIPT >> $LOG_FILE 2>&1"

echo "추가할 cron 작업:"
echo "$CRON_JOB"
echo ""

# 기존 cron 작업 확인
echo "현재 cron 작업 확인:"
crontab -l 2>/dev/null | grep "daily_returns_updater" || echo "기존 작업 없음"
echo ""

# 사용자 확인
read -p "이 cron 작업을 추가하시겠습니까? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 기존 crontab 백업
    crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || touch /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S)
    
    # 기존 daily_returns_updater 관련 cron 작업 제거
    (crontab -l 2>/dev/null | grep -v "daily_returns_updater") | crontab -
    
    # 새로운 cron 작업 추가
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    
    echo "✅ Cron 작업이 성공적으로 추가되었습니다!"
    echo ""
    echo "현재 cron 작업 목록:"
    crontab -l
    echo ""
    echo "로그는 다음 위치에서 확인할 수 있습니다:"
    echo "$LOG_FILE"
    echo ""
    echo "수동 실행 테스트:"
    echo "cd $SCRIPT_DIR && $PYTHON_PATH $UPDATER_SCRIPT"
else
    echo "❌ Cron 작업 추가가 취소되었습니다."
fi

echo ""
echo "=== 설정 완료 ==="
