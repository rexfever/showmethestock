# 문제 해결 가이드

## 🚨 자주 발생하는 문제와 해결책

### 1. 터미널 명령 중단 문제

**증상**: Cursor에서 터미널 명령이 계속 중단되거나 응답하지 않음

**원인**:
- Cursor IDE의 터미널 세션 불안정
- SSH 연결 문제
- 로컬 환경 설정 문제

**해결책**:
1. **AWS CLI 사용** (권장)
   ```bash
   # SSH 키 없이도 서버 접속 가능
   aws ec2-instance-connect send-ssh-public-key --instance-id i-0b06210468b99267e --availability-zone ap-northeast-2a --instance-os-user ubuntu --ssh-public-key file://~/.ssh/id_rsa.pub
   ```

2. **단일 명령어 실행**
   ```bash
   # 복잡한 명령어를 하나로 합치기
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock && git pull origin main && sudo systemctl reload nginx"
   ```

3. **GitHub을 통한 배포**
   ```bash
   # 로컬에서 푸시 후 서버에서 pull
   git push origin main
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock && git pull origin main"
   ```

### 2. Nginx 설정 오류

**증상**: 
- `nginx: [emerg] "alias" directive is not allowed here`
- `nginx: configuration file /etc/nginx/nginx.conf test failed`

**원인**:
- Nginx 설정 문법 오류
- SSL 설정과의 충돌
- 잘못된 location 블록 구조

**해결책**:
1. **설정 문법 검사**
   ```bash
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo nginx -t"
   ```

2. **단계별 설정 적용**
   ```bash
   # 1단계: 기본 설정 적용
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo cp /home/ubuntu/showmethestock/nginx_config_simple /etc/nginx/sites-available/default"
   
   # 2단계: 문법 검사
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo nginx -t"
   
   # 3단계: SSL 설정 추가
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo certbot --nginx -d sohntech.ai.kr -d www.sohntech.ai.kr --non-interactive --agree-tos --email chicnova@gmail.com --redirect"
   ```

3. **설정 백업 및 복원**
   ```bash
   # 백업
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup"
   
   # 복원
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo cp /etc/nginx/sites-available/default.backup /etc/nginx/sites-available/default"
   ```

### 3. 파일 권한 문제

**증상**: 
- `Permission denied`
- `unable to create file: Permission denied`

**원인**:
- 파일 소유권 문제
- 디렉토리 권한 부족
- Nginx 사용자 권한 문제

**해결책**:
```bash
# 파일 소유권 변경
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo chown -R ubuntu:ubuntu /home/ubuntu/showmethestock"

# 파일 권한 설정
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo chmod -R 755 /home/ubuntu/showmethestock"

# Nginx 사용자 권한 설정
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo chown -R www-data:www-data /home/ubuntu/showmethestock/landing"
```

### 4. Git 충돌 문제

**증상**:
- `error: Your local changes to the following files would be overwritten by merge`
- `error: The following untracked working tree files would be overwritten by merge`

**원인**:
- 서버에 로컬 변경사항 존재
- 추적되지 않는 파일과의 충돌

**해결책**:
```bash
# 강제 리셋 및 정리
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock && git reset --hard HEAD && git clean -fd && git pull origin main"
```

### 5. 서비스 시작 실패

**증상**:
- `ModuleNotFoundError: No module named 'backend'`
- `Port 8010 already in use`
- `npm: command not found`

**원인**:
- Python 경로 문제
- 포트 충돌
- Node.js/npm 설치 문제

**해결책**:
1. **Python 경로 설정**
   ```bash
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock/backend && source venv/bin/activate && PYTHONPATH=/home/ubuntu/showmethestock nohup uvicorn backend.main:app --host 0.0.0.0 --port 8010 > backend.log 2>&1 &"
   ```

2. **포트 충돌 해결**
   ```bash
   # 기존 프로세스 종료
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo pkill -f uvicorn"
   
   # 새로 시작
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock/backend && source venv/bin/activate && nohup uvicorn main:app --host 0.0.0.0 --port 8010 > backend.log 2>&1 &"
   ```

3. **Node.js/npm 재설치**
   ```bash
   ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs"
   ```

### 6. SSL 인증서 문제

**증상**:
- `SSL_do_handshake() failed`
- `Certificate not yet due for renewal`

**원인**:
- SSL 인증서 만료
- 인증서 설정 오류
- 도메인 설정 문제

**해결책**:
```bash
# 인증서 갱신
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo certbot renew --dry-run"

# 수동 갱신
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo certbot --nginx -d sohntech.ai.kr -d www.sohntech.ai.kr --non-interactive --agree-tos --email chicnova@gmail.com --redirect"
```

## 🔍 문제 진단 방법

### 1. 로그 분석
```bash
# Nginx 에러 로그
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo tail -20 /var/log/nginx/error.log"

# 시스템 로그
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo journalctl -u nginx -n 20"

# 애플리케이션 로그
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "tail -20 /home/ubuntu/showmethestock/backend/backend.log"
```

### 2. 서비스 상태 확인
```bash
# 서비스 상태
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo systemctl status nginx"
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "ps aux | grep -E '(uvicorn|node)' | grep -v grep"

# 포트 확인
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo netstat -tlnp | grep -E ':(80|443|3000|8010)'"
```

### 3. 네트워크 테스트
```bash
# 로컬 연결 테스트
curl -s -o /dev/null -w "%{http_code}" https://sohntech.ai.kr/
curl -s -o /dev/null -w "%{http_code}" https://sohntech.ai.kr/api/universe

# 서버 내부 테스트
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "curl -s -o /dev/null -w '%{http_code}' http://localhost:8010/api/universe"
```

## 🛡️ 예방 조치

### 1. 정기적인 백업
```bash
# 설정 파일 백업
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo cp /etc/nginx/sites-available/default /home/ubuntu/nginx_backup_$(date +%Y%m%d).conf"

# 코드 백업
git tag backup-$(date +%Y%m%d)
git push origin backup-$(date +%Y%m%d)
```

### 2. 모니터링 설정
```bash
# 로그 모니터링
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo tail -f /var/log/nginx/access.log | grep -E '(40[0-9]|50[0-9])'"
```

### 3. 자동화 스크립트
```bash
# 배포 스크립트 생성
cat > deploy.sh << 'EOF'
#!/bin/bash
echo "Starting deployment..."
git add .
git commit -m "Auto deployment $(date)"
git push origin main
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock && git pull origin main && sudo systemctl reload nginx"
echo "Deployment completed!"
EOF
chmod +x deploy.sh
```

## 📞 긴급 상황 대응

### 1. 서비스 완전 중단 시
```bash
# 모든 서비스 재시작
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo systemctl restart nginx"
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock/backend && source venv/bin/activate && nohup uvicorn main:app --host 0.0.0.0 --port 8010 > backend.log 2>&1 &"
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock/frontend && npm run build && nohup npm start > frontend.log 2>&1 &"
```

### 2. 롤백 절차
```bash
# 이전 버전으로 롤백
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock && git log --oneline -5"
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock && git reset --hard [이전_커밋_해시]"
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo systemctl reload nginx"
```

---

## 💡 문제 해결 원칙

1. **로그 우선**: 항상 로그부터 확인
2. **단계별 접근**: 한 번에 하나씩 문제 해결
3. **백업 필수**: 변경 전 현재 상태 보존
4. **검증 완료**: 수정 후 반드시 테스트
5. **문서화**: 문제와 해결책 기록
