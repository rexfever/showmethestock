#!/bin/bash

# 수동 데이터베이스 백업 스크립트
# 사용법: ./manual-backup.sh

set -e

PROJECT_DIR="/home/ubuntu/showmethestock"
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup-database.sh"

echo "🔧 수동 데이터베이스 백업 실행 중..."

# 백업 스크립트 실행
if [ -f "$BACKUP_SCRIPT" ]; then
    chmod +x "$BACKUP_SCRIPT"
    "$BACKUP_SCRIPT"
else
    echo "❌ 백업 스크립트를 찾을 수 없습니다: $BACKUP_SCRIPT"
    exit 1
fi

echo ""
echo "📋 백업 완료 후 확인사항:"
echo "1. 백업 파일이 생성되었는지 확인: ls -la /home/ubuntu/backups/"
echo "2. 백업 로그 확인: tail -f /home/ubuntu/backups/backup.log"
echo "3. cron 작업 상태 확인: crontab -l"




