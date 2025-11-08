# AWS 콘솔에서 IAM 권한 추가하기

## 🎯 목표
기존 EC2 인스턴스의 IAM 역할(`Session_Manager`)에 S3, Parameter Store, CloudWatch 권한 추가

---

## 1️⃣ AWS 콘솔 접속

**URL**: https://console.aws.amazon.com/iam/

---

## 2️⃣ IAM 역할 찾기

### 경로
```
IAM > 역할 > Session_Manager 검색 > Session_Manager 선택
```

**상단 검색창**에 `Session_Manager` 입력 후 클릭

---

## 3️⃣ S3 권한 추가

### 단계별 가이드

1. **권한** 탭 클릭
2. **권한 추가** 버튼 클릭
3. **정책 생성** 클릭 (기존 정책 사용 아님)
4. **JSON** 탭 선택
5. 아래 JSON 복사하여 붙여넣기

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

6. **정책 이름**: `stock-finder-s3-policy` 입력
7. **다음** 클릭
8. **정책 생성** 클릭

✅ **S3 권한 추가 완료**

---

## 4️⃣ SSM Parameter Store 권한 추가

1. **권한** 탭 > **권한 추가** 클릭
2. **정책 생성** 클릭
3. **JSON** 탭 선택
4. 아래 JSON 붙여넣기

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

5. **정책 이름**: `stock-finder-ssm-policy` 입력
6. **다음** > **정책 생성** 클릭

✅ **Parameter Store 권한 추가 완료**

---

## 5️⃣ CloudWatch Logs 권한 추가

1. **권한** 탭 > **권한 추가** 클릭
2. **정책 생성** 클릭
3. **JSON** 탭 선택
4. 아래 JSON 붙여넣기

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

5. **정책 이름**: `stock-finder-cloudwatch-policy` 입력
6. **다음** > **정책 생성** 클릭

✅ **CloudWatch 권한 추가 완료**

---

## ✅ 완료 확인

권한 탭에서 다음 3개 정책이 보이면 완료입니다:
- ✅ stock-finder-s3-policy
- ✅ stock-finder-ssm-policy
- ✅ stock-finder-cloudwatch-policy

**참고**: EC2 인스턴스는 이미 `Session_Manager` 역할을 사용 중이므로, 별도 설정 없이 바로 권한이 적용됩니다!



