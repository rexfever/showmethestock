#!/bin/bash

# 데이터베이스 백업 cron 작업 설정 스크립트
# 사용법: ./setup-backup-cron.sh

set -e

PROJECT_DIR="/home/ubuntu/showmethestock"
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup-database.sh"

echo "⏰ 데이터베이스 백업 cron 작업 설정 중..."

# 백업 스크립트가 존재하는지 확인
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "❌ 백업 스크립트를 찾을 수 없습니다: $BACKUP_SCRIPT"
    exit 1
fi

# 백업 스크립트에 실행 권한 부여
chmod +x "$BACKUP_SCRIPT"

# 현재 crontab 백업
crontab -l > /tmp/crontab_backup 2>/dev/null || touch /tmp/crontab_backup

# 기존 백업 작업 제거 (중복 방지)
grep -v "backup-database.sh" /tmp/crontab_backup > /tmp/crontab_new || touch /tmp/crontab_new

# 새로운 백업 작업 추가 (매일 새벽 2시에 실행)
echo "0 2 * * * $BACKUP_SCRIPT >> /home/ubuntu/backups/backup.log 2>&1" >> /tmp/crontab_new

# crontab 적용
crontab /tmp/crontab_new

# 임시 파일 정리
rm -f /tmp/crontab_backup /tmp/crontab_new

echo "✅ cron 작업 설정 완료!"
echo "📅 매일 새벽 2시에 자동 백업됩니다"
echo "📁 백업 로그: /home/ubuntu/backups/backup.log"

# 현재 crontab 확인
echo ""
echo "📋 현재 cron 작업 목록:"
crontab -l





