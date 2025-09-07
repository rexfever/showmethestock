# Terraform 변수 정의

# AWS 리전
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"  # 서울
}

# 환경
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

# 프로젝트명
variable "project_name" {
  description = "Project name"
  type        = string
  default     = "stock-finder"
}

# 인스턴스 타입
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

# 볼륨 크기
variable "volume_size" {
  description = "EBS volume size in GB"
  type        = number
  default     = 30
}

# 공개 키 경로
variable "public_key_path" {
  description = "Path to the public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

# GitHub 저장소
variable "github_repo" {
  description = "GitHub repository URL"
  type        = string
  default     = "https://github.com/rexfever/showmethestock.git"
}

# 도메인명 (선택사항)
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# Elastic IP 생성 여부
variable "create_eip" {
  description = "Whether to create an Elastic IP"
  type        = bool
  default     = false
}

# 백업 S3 버킷 생성 여부
variable "create_backup_bucket" {
  description = "Whether to create a backup S3 bucket"
  type        = bool
  default     = false
}

# 태그
variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default = {
    Project     = "stock-finder"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}



