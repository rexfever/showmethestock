# Terraform 출력값 정의

# EC2 인스턴스 정보
output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.stock_finder_server.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.stock_finder_server.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.stock_finder_server.public_dns
}

output "instance_private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.stock_finder_server.private_ip
}

# Elastic IP (생성된 경우)
output "elastic_ip" {
  description = "Elastic IP address"
  value       = var.create_eip ? aws_eip.stock_finder_eip[0].public_ip : null
}

# 보안 그룹 ID
output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.stock_finder_sg.id
}

# 키 페어 이름
output "key_pair_name" {
  description = "Name of the key pair"
  value       = aws_key_pair.stock_finder_key.key_name
}

# 접속 정보
output "ssh_connection" {
  description = "SSH connection command"
  value       = "ssh -i ~/.ssh/stock-finder-key.pem ubuntu@${aws_instance.stock_finder_server.public_ip}"
}

# 웹 서비스 URL
output "web_urls" {
  description = "Web service URLs"
  value = {
    frontend    = "http://${aws_instance.stock_finder_server.public_ip}"
    backend_api = "http://${aws_instance.stock_finder_server.public_ip}:8010"
    landing     = "http://${aws_instance.stock_finder_server.public_ip}/landing/"
  }
}

# 도메인 정보 (설정된 경우)
output "domain_info" {
  description = "Domain information"
  value = var.domain_name != "" ? {
    domain_name = var.domain_name
    zone_id     = aws_route53_zone.stock_finder_zone[0].zone_id
    nameservers = aws_route53_zone.stock_finder_zone[0].name_servers
  } : null
}

# S3 백업 버킷 (생성된 경우)
output "backup_bucket" {
  description = "S3 backup bucket name"
  value       = var.create_backup_bucket ? aws_s3_bucket.stock_finder_backup[0].bucket : null
}

# CloudWatch 로그 그룹
output "log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.stock_finder_logs.name
}

# 배포 명령어
output "deploy_commands" {
  description = "Deployment commands"
  value = {
    initial_deploy = "./deploy-aws.sh ${aws_instance.stock_finder_server.public_ip} ~/.ssh/stock-finder-key.pem"
    quick_deploy   = "./quick-deploy.sh ${aws_instance.stock_finder_server.public_ip} ~/.ssh/stock-finder-key.pem"
  }
}



