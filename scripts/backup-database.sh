#!/bin/bash

# 데이터베이스 일단위 백업 스크립트
# 사용법: ./backup-database.sh

set -e

# 설정
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/home/ubuntu/showmethestock"
BACKEND_DIR="$PROJECT_DIR/backend"

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"

echo "🗄️  데이터베이스 백업 시작 - $DATE"

# 백엔드 디렉토리로 이동
cd "$BACKEND_DIR"

# 데이터베이스 파일들 백업
echo "📦 포트폴리오 데이터베이스 백업 중..."
if [ -f "portfolio.db" ]; then
    cp portfolio.db "$BACKUP_DIR/portfolio_$DATE.db"
    echo "✅ portfolio.db 백업 완료"
else
    echo "⚠️  portfolio.db 파일이 없습니다"
fi

echo "📦 스캔 결과 데이터베이스 백업 중..."
if [ -f "snapshots.db" ]; then
    cp snapshots.db "$BACKUP_DIR/snapshots_$DATE.db"
    echo "✅ snapshots.db 백업 완료"
else
    echo "⚠️  snapshots.db 파일이 없습니다"
fi

echo "📦 이메일 인증 데이터베이스 백업 중..."
if [ -f "email_verifications.db" ]; then
    cp email_verifications.db "$BACKUP_DIR/email_verifications_$DATE.db"
    echo "✅ email_verifications.db 백업 완료"
else
    echo "⚠️  email_verifications.db 파일이 없습니다"
fi

echo "📦 뉴스 데이터 데이터베이스 백업 중..."
if [ -f "news_data.db" ]; then
    cp news_data.db "$BACKUP_DIR/news_data_$DATE.db"
    echo "✅ news_data.db 백업 완료"
else
    echo "⚠️  news_data.db 파일이 없습니다"
fi

# 스캔 결과 JSON 파일들 백업
echo "📦 스캔 결과 JSON 파일들 백업 중..."
if [ -d "snapshots" ]; then
    tar -czf "$BACKUP_DIR/snapshots_$DATE.tar.gz" snapshots/
    echo "✅ snapshots 디렉토리 백업 완료"
else
    echo "⚠️  snapshots 디렉토리가 없습니다"
fi

# 30일 이상 된 백업 파일 삭제
echo "🧹 오래된 백업 파일 정리 중..."
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
echo "✅ 30일 이상 된 백업 파일 삭제 완료"

# 백업 파일 목록 출력
echo ""
echo "📋 현재 백업 파일 목록:"
ls -la "$BACKUP_DIR" | grep -E "\.(db|tar\.gz)$" | tail -10

echo ""
echo "✅ 데이터베이스 백업 완료!"
echo "📁 백업 위치: $BACKUP_DIR"
echo "📅 백업 시간: $DATE"




