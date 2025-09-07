# 빠른 명령어 모음

## 🔧 자주 사용하는 명령어

### 서버 접속 및 상태 확인
```bash
# 서버 상태 확인
aws ec2 describe-instances --filters "Name=tag:Name,Values=*" --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress,Tags[?Key==`Name`].Value|[0]]' --output table

# SSH 접속
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207

# 서비스 상태 확인
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo systemctl status nginx"
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "ps aux | grep -E '(uvicorn|node)' | grep -v grep"
```

### Git 작업
```bash
# 로컬 작업
git add .
git commit -m "작업 내용"
git push origin main

# 서버 업데이트
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock && git pull origin main"
```

### 파일 전송
```bash
# 파일 업로드
scp -o StrictHostKeyChecking=no [파일명] ubuntu@52.79.61.207:/home/ubuntu/showmethestock/

# 디렉토리 업로드
scp -r -o StrictHostKeyChecking=no [디렉토리명] ubuntu@52.79.61.207:/home/ubuntu/showmethestock/
```

### 서비스 관리
```bash
# Nginx 재시작
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo systemctl reload nginx"

# 백엔드 재시작
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock/backend && source venv/bin/activate && nohup uvicorn main:app --host 0.0.0.0 --port 8010 > backend.log 2>&1 &"

# 프론트엔드 재시작
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock/frontend && npm run build && nohup npm start > frontend.log 2>&1 &"
```

### 웹사이트 테스트
```bash
# HTTP 상태 확인
curl -s -o /dev/null -w "%{http_code}" https://sohntech.ai.kr/
curl -s -o /dev/null -w "%{http_code}" https://sohntech.ai.kr/scanner
curl -s -o /dev/null -w "%{http_code}" https://sohntech.ai.kr/api/universe

# 페이지 내용 확인
curl -s https://sohntech.ai.kr/ | head -10
```

### 로그 확인
```bash
# Nginx 에러 로그
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo tail -10 /var/log/nginx/error.log"

# 백엔드 로그
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "tail -10 /home/ubuntu/showmethestock/backend/backend.log"

# 프론트엔드 로그
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "tail -10 /home/ubuntu/showmethestock/frontend/frontend.log"
```

## 🚨 문제 해결 명령어

### 권한 문제 해결
```bash
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo chown -R ubuntu:ubuntu /home/ubuntu/showmethestock && sudo chmod -R 755 /home/ubuntu/showmethestock"
```

### Git 충돌 해결
```bash
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock && git reset --hard HEAD && git clean -fd && git pull origin main"
```

### SSL 인증서 갱신
```bash
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo certbot --nginx -d sohntech.ai.kr -d www.sohntech.ai.kr --non-interactive --agree-tos --email chicnova@gmail.com --redirect"
```

### 프로세스 종료
```bash
# 특정 프로세스 종료
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo pkill -f uvicorn"
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo pkill -f node"
```

## 📋 체크리스트

### 배포 전 체크
- [ ] 로컬에서 코드 테스트 완료
- [ ] Git 커밋 및 푸시 완료
- [ ] 서버 상태 정상 확인
- [ ] 백업 완료 (필요시)

### 배포 후 체크
- [ ] 웹사이트 접속 확인
- [ ] API 동작 확인
- [ ] 로그 오류 확인
- [ ] 사용자 기능 테스트

## 🔍 디버깅 명령어

### 네트워크 연결 확인
```bash
# 포트 확인
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "sudo netstat -tlnp | grep -E ':(80|443|3000|8010)'"

# 프로세스 확인
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "ps aux | grep -E '(nginx|uvicorn|node)'"
```

### 디스크 사용량 확인
```bash
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "df -h"
```

### 메모리 사용량 확인
```bash
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "free -h"
```

## 📝 유용한 팁

1. **명령어 히스토리**: `history` 명령어로 이전 명령어 확인
2. **백그라운드 실행**: `nohup` 명령어로 백그라운드 프로세스 실행
3. **로그 실시간 모니터링**: `tail -f` 명령어로 실시간 로그 확인
4. **파일 권한 확인**: `ls -la` 명령어로 파일 권한 확인
5. **네트워크 테스트**: `curl` 명령어로 HTTP 요청 테스트
