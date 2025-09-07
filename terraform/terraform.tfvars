# Terraform 변수 예시 파일
# 이 파일을 terraform.tfvars로 복사하고 실제 값으로 수정하세요

# AWS 리전
aws_region = "ap-northeast-2"  # 서울

# 환경
environment = "production"

# 프로젝트명
project_name = "stock-finder"

# 인스턴스 타입
instance_type = "t3.micro"  # 무료 티어

# 볼륨 크기 (GB)
volume_size = 30

# 공개 키 경로 (SSH 키)
public_key_path = "~/.ssh/id_rsa.pub"

# GitHub 저장소
github_repo = "https://github.com/rexfever/showmethestock.git"

# 도메인명 (선택사항)
domain_name = ""  # 예: "stock-finder.com"

# Elastic IP 생성 여부
create_eip = false

# 백업 S3 버킷 생성 여부
create_backup_bucket = false

# 추가 태그
tags = {
  Project     = "stock-finder"
  Environment = "production"
  ManagedBy   = "terraform"
  Owner       = "sontech"
}
