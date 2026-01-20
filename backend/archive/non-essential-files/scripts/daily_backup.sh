#!/bin/bash

# 일일 DB 백업 스크립트
BACKUP_DIR="/home/ubuntu/showmethestock/backend/backups"
DATE=$(date +%Y%m%d)

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# DB 파일들 백업
cd /home/ubuntu/showmethestock/backend

cp snapshots.db $BACKUP_DIR/snapshots_$DATE.db
cp portfolio.db $BACKUP_DIR/portfolio_$DATE.db
cp email_verifications.db $BACKUP_DIR/email_verifications_$DATE.db
cp news_data.db $BACKUP_DIR/news_data_$DATE.db

# 30일 이전 백업 파일 삭제
find $BACKUP_DIR -name "*.db" -mtime +30 -delete

echo "$(date): DB 백업 완료 - $DATE"