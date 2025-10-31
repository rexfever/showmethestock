# S3 백업 설정 가이드

## 1. S3 버킷 생성
```bash
# AWS CLI 설정 (한 번만)
aws configure
# Access Key ID: [AWS 콘솔에서 생성]
# Secret Access Key: [AWS 콘솔에서 생성]
# Default region: ap-northeast-2
# Default output format: json

# S3 버킷 생성
aws s3 mb s3://showmethestock-db-backup --region ap-northeast-2
```

## 2. 생명주기 정책 설정 (자동 삭제)
```bash
# lifecycle.json 파일 생성
cat > lifecycle.json << 'EOF'
{
    "Rules": [
        {
            "ID": "DeleteOldBackups",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "daily/"
            },
            "Expiration": {
                "Days": 30
            }
        }
    ]
}
EOF

# 생명주기 정책 적용
aws s3api put-bucket-lifecycle-configuration \
    --bucket showmethestock-db-backup \
    --lifecycle-configuration file://lifecycle.json
```

## 3. crontab 업데이트 (S3 백업으로 변경)
```bash
# 기존 crontab 제거
crontab -r

# S3 백업으로 변경
echo '0 2 * * * /home/ubuntu/showmethestock/backend/s3_backup.sh >> /home/ubuntu/backup.log 2>&1' | crontab -
```

## 4. 테스트 실행
```bash
# 수동 테스트
/home/ubuntu/showmethestock/backend/s3_backup.sh

# S3 업로드 확인
aws s3 ls s3://showmethestock-db-backup/daily/
```

## 5. 복구 방법
```bash
# 특정 날짜 백업 다운로드
aws s3 cp s3://showmethestock-db-backup/daily/snapshots_20251028.db ./snapshots.db

# 전체 백업 목록 확인
aws s3 ls s3://showmethestock-db-backup/daily/ --recursive
```

## 비용 예상
- **S3 Standard**: $0.023/GB/월
- **DB 크기**: 약 1.2MB (snapshots.db)
- **월 비용**: 약 $0.001 (거의 무료)
- **30일 보관**: 약 $0.03/월

**매우 저렴하고 안전한 백업 솔루션입니다!**