# 기존 IAM 역할에 권한 추가하기

## 기존 역할: Session_Manager (또는 다른 기존 역할)

### AWS 콘솔 경로
IAM > 역할 > **기존 역할 선택** (예: Session_Manager)

---

## 정책 추가: S3 권한

### 인라인 정책 추가
1. **권한** 탭 > **권한 추가** > **정책 생성**
2. **JSON** 탭 선택
3. 아래 JSON 붙여넣기

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

4. 정책 이름: `stock-finder-s3-policy`
5. **정책 생성**

---

## 정책 추가: SSM Parameter Store 권한

### 인라인 정책 추가
1. **권한** 탭 > **권한 추가** > **정책 생성**
2. **JSON** 탭 선택
3. 아래 JSON 붙여넣기

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

4. 정책 이름: `stock-finder-ssm-policy`
5. **정책 생성**

---

## 정책 추가: CloudWatch Logs 권한

### 인라인 정책 추가
1. **권한** 탭 > **권한 추가** > **정책 생성**
2. **JSON** 탭 선택
3. 아래 JSON 붙여넣기

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

4. 정책 이름: `stock-finder-cloudwatch-policy`
5. **정책 생성**

---

## 완료

이제 기존 IAM 역할에 다음 권한이 추가되었습니다:
- ✅ S3 권한 (stock-finder-* 버킷)
- ✅ SSM Parameter Store 권한 (/stock-finder/*)
- ✅ CloudWatch Logs 권한

**참고**: EC2 인스턴스는 이미 이 역할을 사용하고 있으므로, 추가 설정 없이 바로 권한이 적용됩니다.



