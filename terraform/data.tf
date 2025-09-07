# 데이터 소스 정의

# 최신 Ubuntu 22.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# 가용 영역
data "aws_availability_zones" "available" {
  state = "available"
}

# 현재 AWS 계정 ID
data "aws_caller_identity" "current" {}

# 현재 AWS 리전
data "aws_region" "current" {}



