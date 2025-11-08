#!/bin/bash

# EC2에 영향을 주지 않고 IAM 리소스만 생성하는 스크립트

echo "IAM 리소스만 생성합니다 (EC2 인스턴스는 변경하지 않습니다)..."

# 1. IAM 역할 및 정책만 apply
terraform apply -target=aws_iam_role.ec2_role
terraform apply -target=aws_iam_instance_profile.ec2_profile
terraform apply -target=aws_iam_role_policy.s3_policy
terraform apply -target=aws_iam_role_policy.ssm_policy
terraform apply -target=aws_iam_role_policy.cloudwatch_policy

echo "IAM 리소스 생성 완료"
echo "이제 기존 EC2 인스턴스에 IAM 프로파일을 수동으로 연결해야 합니다."



