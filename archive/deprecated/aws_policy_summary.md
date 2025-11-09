# AWS IAM 정책 JSON 요약

## 1️⃣ S3 권한 정책 (stock-finder-s3-policy)

### 용도
S3 버킷 접근 권한 (파일 읽기/쓰기/삭제)

### JSON
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",      // S3 객체 조회
        "s3:PutObject",      // S3 객체 업로드
        "s3:DeleteObject",   // S3 객체 삭제
        "s3:ListBucket"      // S3 버킷 목록 조회
      ],
      "Resource": [
        "arn:aws:s3:::stock-finder-*",    // stock-finder로 시작하는 버킷
        "arn:aws:s3:::stock-finder-*/*"    // 그 버킷 안의 모든 파일
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets",   // 모든 버킷 목록 조회
        "s3:GetBucketLocation"   // 버킷 위치 정보 조회
      ],
      "Resource": "*"  // 모든 리소스
    }
  ]
}
```

---

## 2️⃣ SSM Parameter Store 권한 정책 (stock-finder-ssm-policy)

### 용도
Parameter Store 접근 권한 (설정 값 저장/조회)

### JSON
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",           // 파라미터 조회
        "ssm:GetParameters",          // 여러 파라미터 조회
        "ssm:GetParametersByPath",    // 경로별 파라미터 조회
        "ssm:PutParameter",            // 파라미터 저장
        "ssm:DeleteParameter",        // 파라미터 삭제
        "ssm:DescribeParameters"       // 파라미터 목록 조회
      ],
      "Resource": "arn:aws:ssm:ap-northeast-2:*:parameter/stock-finder/*"
      // /stock-finder/ 로 시작하는 파라미터만 접근 가능
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",      // 암호 복호화
        "kms:Encrypt",      // 암호 암호화
        "kms:DescribeKey"   // 암호 키 정보 조회
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "ssm.ap-northeast-2.amazonaws.com"
        }
      }
      // SSM에서 사용하는 암호화 키만 사용 가능
    }
  ]
}
```

---

## 3️⃣ CloudWatch Logs 권한 정책 (stock-finder-cloudwatch-policy)

### 용도
CloudWatch Logs 로그 쓰기 권한

### JSON
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",      // 로그 그룹 생성
        "logs:CreateLogStream",     // 로그 스트림 생성
        "logs:PutLogEvents",        // 로그 이벤트 기록
        "logs:DescribeLogStreams"   // 로그 스트림 조회
      ],
      "Resource": "arn:aws:logs:ap-northeast-2:*:*"
      // ap-northeast-2 (서울 리전)의 모든 CloudWatch Logs
    }
  ]
}
```

---

## 📋 요약

| 정책 이름 | 용도 | 주요 권한 |
|---------|------|---------|
| **stock-finder-s3-policy** | S3 버킷 접근 | GetObject, PutObject, DeleteObject, ListBucket |
| **stock-finder-ssm-policy** | Parameter Store 접근 | GetParameter, PutParameter, DeleteParameter |
| **stock-finder-cloudwatch-policy** | CloudWatch Logs 접근 | CreateLogGroup, PutLogEvents |

### 리소스 범위
- **S3**: `stock-finder-*` 버킷만 접근 가능
- **Parameter Store**: `/stock-finder/*` 경로만 접근 가능
- **CloudWatch Logs**: ap-northeast-2 리전 모든 로그

### 보안
- 최소 권한 원칙 적용 (필요한 범위만 허용)
- 특정 리소스만 접근 가능하도록 제한



