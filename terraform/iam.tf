# IAM 역할 - EC2 인스턴스용
resource "aws_iam_role" "ec2_role" {
  name = "stock-finder-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "stock-finder-ec2-role"
  }
}

# IAM 인스턴스 프로파일
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "stock-finder-ec2-profile"
  role = aws_iam_role.ec2_role.name

  tags = {
    Name = "stock-finder-ec2-profile"
  }
}

# S3 권한 정책
resource "aws_iam_role_policy" "s3_policy" {
  name = "stock-finder-s3-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::stock-finder-*",
          "arn:aws:s3:::stock-finder-*/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets",
          "s3:GetBucketLocation"
        ]
        Resource = "*"
      }
    ]
  })
}

# SSM Parameter Store 권한 정책
resource "aws_iam_role_policy" "ssm_policy" {
  name = "stock-finder-ssm-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath",
          "ssm:PutParameter",
          "ssm:DeleteParameter",
          "ssm:DescribeParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/stock-finder/*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# CloudWatch Logs 권한 정책 (기존 모니터링 지원)
resource "aws_iam_role_policy" "cloudwatch_policy" {
  name = "stock-finder-cloudwatch-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })
}



