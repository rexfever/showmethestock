# Terraform AWS 인프라 - 스톡인사이트

## 📋 개요

이 Terraform 설정은 스톡인사이트 애플리케이션을 위한 AWS 인프라를 자동으로 생성합니다.

## 🏗️ 생성되는 리소스

### **EC2 인스턴스**
- Ubuntu 22.04 LTS
- t2.micro (무료 티어)
- 30GB EBS 스토리지
- 자동 초기화 스크립트

### **네트워킹**
- 보안 그룹 (SSH, HTTP, HTTPS, API 포트)
- Elastic IP (선택사항)
- Route 53 호스팅 존 (도메인 설정 시)

### **모니터링**
- CloudWatch 로그 그룹
- CPU/디스크 사용률 알람
- CloudWatch 에이전트

### **백업**
- S3 버킷 (선택사항)
- 버전 관리 및 암호화

## 🚀 사용 방법

### **1. 사전 준비**

#### **SSH 키 생성**
```bash
# SSH 키 생성 (없는 경우)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/stock-finder-key

# 공개 키 확인
cat ~/.ssh/stock-finder-key.pub
```

#### **AWS CLI 설정**
```bash
# AWS CLI 설치 (Mac)
brew install awscli

# AWS CLI 설정
aws configure
# AWS Access Key ID: [YOUR_ACCESS_KEY]
# AWS Secret Access Key: [YOUR_SECRET_KEY]
# Default region: ap-northeast-2
# Default output format: json
```

### **2. Terraform 설정**

#### **변수 파일 생성**
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

#### **terraform.tfvars 수정**
```hcl
# 필수 설정
aws_region = "ap-northeast-2"
public_key_path = "~/.ssh/stock-finder-key.pub"
github_repo = "https://github.com/rexfever/showmethestock.git"

# 선택사항
domain_name = "your-domain.com"  # 도메인이 있는 경우
create_eip = true                # 고정 IP가 필요한 경우
create_backup_bucket = true      # 백업이 필요한 경우
```

### **3. 인프라 배포**

#### **Terraform 초기화**
```bash
terraform init
```

#### **배포 계획 확인**
```bash
terraform plan
```

#### **인프라 생성**
```bash
terraform apply
```

#### **배포 확인**
```bash
# 출력값 확인
terraform output

# SSH 접속
ssh -i ~/.ssh/stock-finder-key.pem ubuntu@$(terraform output -raw instance_public_ip)
```

### **4. 애플리케이션 배포**

인프라 생성 후 자동으로 애플리케이션이 배포됩니다. 수동 배포가 필요한 경우:

```bash
# 초기 배포
./deploy-aws.sh $(terraform output -raw instance_public_ip) ~/.ssh/stock-finder-key.pem

# 코드 업데이트
./quick-deploy.sh $(terraform output -raw instance_public_ip) ~/.ssh/stock-finder-key.pem
```

## 📊 모니터링

### **CloudWatch 로그**
```bash
# 로그 확인
aws logs describe-log-groups --log-group-name-prefix "/aws/ec2/stock-finder"

# 로그 스트림 확인
aws logs describe-log-streams --log-group-name "/aws/ec2/stock-finder"
```

### **알람 확인**
```bash
# CloudWatch 알람 확인
aws cloudwatch describe-alarms --alarm-names "stock-finder-high-cpu" "stock-finder-high-disk"
```

## 🔧 관리 명령어

### **인프라 관리**
```bash
# 상태 확인
terraform show

# 리소스 목록
terraform state list

# 특정 리소스 정보
terraform state show aws_instance.stock_finder_server

# 인프라 업데이트
terraform plan
terraform apply

# 인프라 삭제
terraform destroy
```

### **서비스 관리**
```bash
# SSH 접속
ssh -i ~/.ssh/stock-finder-key.pem ubuntu@$(terraform output -raw instance_public_ip)

# 서비스 상태 확인
sudo systemctl status stock-finder-backend nginx

# 서비스 재시작
sudo systemctl restart stock-finder-backend

# 로그 확인
sudo journalctl -u stock-finder-backend -f
```

## 💰 비용 정보

### **무료 티어 (1년간)**
- EC2 t2.micro: 750시간/월
- EBS 30GB: 무료
- 데이터 전송: 1GB/월

### **무료 티어 이후 예상 비용**
- EC2 t2.micro: ~$8.50/월
- EBS 30GB: ~$3.00/월
- Elastic IP: ~$3.65/월 (사용 시)
- Route 53: ~$0.50/월 (도메인 사용 시)
- **총 비용**: ~$11.50-15.65/월

## 🔐 보안 고려사항

### **네트워크 보안**
- 보안 그룹으로 포트 제한
- SSH는 현재 IP에서만 접근 가능
- HTTPS 리다이렉트 설정

### **데이터 보안**
- EBS 볼륨 암호화
- S3 버킷 암호화
- 환경변수 보안 관리

### **접근 제어**
- IAM 역할 및 정책
- 최소 권한 원칙
- 정기적인 보안 업데이트

## 🛠️ 문제 해결

### **일반적인 문제들**

#### **Terraform 초기화 실패**
```bash
# Provider 캐시 삭제
rm -rf .terraform
terraform init
```

#### **SSH 접속 실패**
```bash
# 키 파일 권한 확인
chmod 400 ~/.ssh/stock-finder-key.pem

# 보안 그룹 확인
aws ec2 describe-security-groups --group-ids $(terraform output -raw security_group_id)
```

#### **서비스 시작 실패**
```bash
# 로그 확인
ssh -i ~/.ssh/stock-finder-key.pem ubuntu@$(terraform output -raw instance_public_ip) 'sudo journalctl -u stock-finder-backend -n 50'

# 수동 시작 테스트
ssh -i ~/.ssh/stock-finder-key.pem ubuntu@$(terraform output -raw instance_public_ip) 'cd /home/ubuntu/showmethestock/backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8010'
```

## 📚 추가 리소스

- [Terraform AWS Provider 문서](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS EC2 사용자 가이드](https://docs.aws.amazon.com/ec2/)
- [CloudWatch 모니터링 가이드](https://docs.aws.amazon.com/cloudwatch/)

## 📞 지원

- **프로젝트**: 스톡인사이트 (Stock Insight)
- **회사**: 손테크 (Sontech)
- **이메일**: chicnova@gmail.com
- **전화**: 010-4220-0956

---

**마지막 업데이트**: 2025년 9월 5일



