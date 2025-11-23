# AWS 콘솔에서 IAM 권한 설정 가이드

## 1. IAM 역할 생성

### AWS 콘솔 경로
IAM > 역할 > 역할 만들기

### 역할 설정
1. **신뢰할 유형**: AWS 서비스 선택
2. **사용 사례**: EC2 선택
3. **역할 이름**: `stock-finder-ec2-role` 입력

## 2. 권한 정책 추가

### S3 정책 (첫 번째 인라인 정책)

**정책 이름**: `stock-finder-s3-policy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::stock-finder-*",
        "arn:aws:s3:::stock-finder-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation"
      ],
      "Resource": "*"
    }
  ]
}
```

### SSM Parameter Store 정책 (두 번째 인라인 정책)

**정책 이름**: `stock-finder-ssm-policy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "ssm:PutParameter",
        "ssm:DeleteParameter",
        "ssm:DescribeParameters"
      ],
      "Resource": "arn:aws:ssm:ap-northeast-2:*:parameter/stock-finder/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:Encrypt",
        "kms:DescribeKey"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "ssm.ap-northeast-2.amazonaws.com"
        }
      }
    }
  ]
}
```

### CloudWatch Logs 정책 (세 번째 인라인 정책)

**정책 이름**: `stock-finder-cloudwatch-policy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:ap-northeast-2:*:*"
    }
  ]
}
```

## 3. IAM 인스턴스 프로파일 생성

### AWS 콘솔 경로
IAM > 역할 > stock-finder-ec2-role 선택 > "인스턴스 프로파일" 탭

또는:

IAM > 액세스 관리 > 인스턴스 프로파일 > 인스턴스 프로파일 생성

- **이름**: `stock-finder-ec2-profile`
- **역할**: `stock-finder-ec2-role` 선택

## 4. EC2 인스턴스에 프로파일 연결

### AWS 콘솔 경로
EC2 > 인스턴스 > 해당 인스턴스 선택 > 작업 > 보안 > IAM 역할 수정

- **IAM 역할**: `stock-finder-ec2-role` 선택
- 저장

## 참고사항
- EC2 인스턴스가 재시작되지 않습니다
- 기존 서비스는 계속 실행됩니다
- 별도의 다운타임 없이 권한이 적용됩니다




