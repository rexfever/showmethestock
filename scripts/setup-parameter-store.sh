#!/bin/bash

# AWS Parameter Store 설정 스크립트
APP_NAME="showmethestock"
ENV=${1:-dev}  # 기본값: dev

echo "AWS Parameter Store 설정 중... (환경: $ENV)"

# Kiwoom API 설정
aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/app_key" \
    --value "YOUR_KIWOOM_APP_KEY" \
    --type "SecureString" \
    --overwrite

aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/app_secret" \
    --value "YOUR_KIWOOM_APP_SECRET" \
    --type "SecureString" \
    --overwrite

# 카카오페이 설정
aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/kakao/admin_key" \
    --value "YOUR_KAKAO_ADMIN_KEY" \
    --type "SecureString" \
    --overwrite

aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/kakao/pay_cid" \
    --value "YOUR_KAKAO_PAY_CID" \
    --type "String" \
    --overwrite

# 네이버페이 설정
aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/naver/pay_client_id" \
    --value "YOUR_NAVER_PAY_CLIENT_ID" \
    --type "String" \
    --overwrite

aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/naver/pay_client_secret" \
    --value "YOUR_NAVER_PAY_CLIENT_SECRET" \
    --type "SecureString" \
    --overwrite

# 포트원 설정
aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/portone/imp_key" \
    --value "YOUR_PORTONE_IMP_KEY" \
    --type "String" \
    --overwrite

aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/portone/imp_secret" \
    --value "YOUR_PORTONE_IMP_SECRET" \
    --type "SecureString" \
    --overwrite

# 토스페이먼츠 설정
aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/toss/client_key" \
    --value "YOUR_TOSS_CLIENT_KEY" \
    --type "String" \
    --overwrite

aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/toss/secret_key" \
    --value "YOUR_TOSS_SECRET_KEY" \
    --type "SecureString" \
    --overwrite

# 데이터베이스 설정
aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/database/url" \
    --value "sqlite:///./database.db" \
    --type "String" \
    --overwrite

# 기타 설정
aws ssm put-parameter \
    --name "/$APP_NAME/$ENV/base_url" \
    --value "https://your-domain.com" \
    --type "String" \
    --overwrite

echo "Parameter Store 설정 완료!"
echo "사용법: export USE_PARAMETER_STORE=true"