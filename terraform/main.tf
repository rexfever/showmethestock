# Terraform 설정 - 스톡인사이트 AWS 인프라
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# AWS Provider 설정
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "stock-finder"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# VPC 설정 (기본 VPC 사용)
data "aws_vpc" "default" {
  default = true
}

# 서브넷 설정 (기본 서브넷 사용)
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# 보안 그룹
resource "aws_security_group" "stock_finder_sg" {
  name_prefix = "stock-finder-sg-"
  description = "Security group for Stock Finder application"
  vpc_id      = data.aws_vpc.default.id

  # SSH 접속
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # 백엔드 API
  ingress {
    description = "Backend API"
    from_port   = 8010
    to_port     = 8010
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # 모든 아웃바운드 트래픽 허용
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "stock-finder-sg"
  }
}

# 키 페어
resource "aws_key_pair" "stock_finder_key" {
  key_name   = "stock-finder-key"
  public_key = file(var.public_key_path)
}

# EC2 인스턴스
resource "aws_instance" "stock_finder_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.stock_finder_key.key_name
  vpc_security_group_ids = [aws_security_group.stock_finder_sg.id]
  subnet_id              = data.aws_subnets.default.ids[0]

  # 스토리지 설정
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.volume_size
    delete_on_termination = true
    encrypted             = true
  }

  # 사용자 데이터 스크립트
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    github_repo = var.github_repo
  }))

  # 모니터링 활성화
  monitoring = true

  tags = {
    Name = "stock-finder-server"
  }
}

# Elastic IP (선택사항)
resource "aws_eip" "stock_finder_eip" {
  count    = var.create_eip ? 1 : 0
  instance = aws_instance.stock_finder_server.id
  domain   = "vpc"

  tags = {
    Name = "stock-finder-eip"
  }
}

# Route 53 호스팅 존 (도메인이 있는 경우)
resource "aws_route53_zone" "stock_finder_zone" {
  count = var.domain_name != "" ? 1 : 0
  name  = var.domain_name

  tags = {
    Name = "stock-finder-zone"
  }
}

# Route 53 A 레코드
resource "aws_route53_record" "stock_finder_record" {
  count   = var.domain_name != "" ? 1 : 0
  zone_id = aws_route53_zone.stock_finder_zone[0].zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300

  records = [var.create_eip ? aws_eip.stock_finder_eip[0].public_ip : aws_instance.stock_finder_server.public_ip]
}

# S3 버킷 (백업용)
resource "aws_s3_bucket" "stock_finder_backup" {
  count  = var.create_backup_bucket ? 1 : 0
  bucket = "${var.project_name}-backup-${random_id.bucket_suffix[0].hex}"

  tags = {
    Name = "stock-finder-backup"
  }
}

# S3 버킷 버전 관리
resource "aws_s3_bucket_versioning" "stock_finder_backup_versioning" {
  count  = var.create_backup_bucket ? 1 : 0
  bucket = aws_s3_bucket.stock_finder_backup[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 버킷 암호화
resource "aws_s3_bucket_server_side_encryption_configuration" "stock_finder_backup_encryption" {
  count  = var.create_backup_bucket ? 1 : 0
  bucket = aws_s3_bucket.stock_finder_backup[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 랜덤 ID (S3 버킷명용)
resource "random_id" "bucket_suffix" {
  count       = var.create_backup_bucket ? 1 : 0
  byte_length = 4
}

# CloudWatch 로그 그룹
resource "aws_cloudwatch_log_group" "stock_finder_logs" {
  name              = "/aws/ec2/stock-finder"
  retention_in_days = 7

  tags = {
    Name = "stock-finder-logs"
  }
}

# CloudWatch 알람 (CPU 사용률)
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "stock-finder-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ec2 cpu utilization"
  alarm_actions       = []

  dimensions = {
    InstanceId = aws_instance.stock_finder_server.id
  }
}

# CloudWatch 알람 (디스크 사용률)
resource "aws_cloudwatch_metric_alarm" "high_disk" {
  alarm_name          = "stock-finder-high-disk"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DiskSpaceUtilization"
  namespace           = "System/Linux"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors disk utilization"
  alarm_actions       = []

  dimensions = {
    InstanceId = aws_instance.stock_finder_server.id
    Filesystem = "/dev/nvme0n1p1"
    MountPath  = "/"
  }
}



