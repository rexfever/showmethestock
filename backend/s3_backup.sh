#!/bin/bash

# S3 DB 백업 스크립트
BACKUP_DIR="/home/ubuntu/showmethestock/backend/backups"
DATE=$(date +%Y%m%d)
S3_BUCKET="showmethestock-db-backup"

# 로컬 백업 먼저 실행
/home/ubuntu/showmethestock/backend/daily_backup.sh

# S3에 업로드
cd $BACKUP_DIR
aws s3 cp snapshots_$DATE.db s3://$S3_BUCKET/daily/snapshots_$DATE.db
aws s3 cp portfolio_$DATE.db s3://$S3_BUCKET/daily/portfolio_$DATE.db
aws s3 cp email_verifications_$DATE.db s3://$S3_BUCKET/daily/email_verifications_$DATE.db
aws s3 cp news_data_$DATE.db s3://$S3_BUCKET/daily/news_data_$DATE.db

echo "$(date): S3 백업 완료 - s3://$S3_BUCKET/daily/"