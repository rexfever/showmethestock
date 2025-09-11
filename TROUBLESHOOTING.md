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

### 7. 프론트엔드 데이터 로딩 오류 (2025-09-10)

**증상**:
- "데이터 불러오는 중 오류가 발생했습니다" 메시지 표시
- PC에서는 정상 작동하지만 모바일에서 오류 발생
- 콘솔에 "Failed to fetch" 오류
- 프리미어 화면에서 데이터가 표시되지 않음

**원인**:
- API 응답 구조 변경: `data.data.rank` → `data.data.items`
- SSR과 클라이언트 API 호출 중복 실행
- useEffect 의존성 배열에 함수 포함으로 인한 무한 루프
- 정적 HTML 파일의 JavaScript 오류

**해결책**:
1. **API 응답 구조 통일**
   ```javascript
   // 잘못된 코드
   setScanResults(data.data.rank || []);
   
   // 올바른 코드
   setScanResults(data.data.items || []);
   ```

2. **SSR 데이터 우선 사용**
   ```javascript
   useEffect(() => {
     // SSR 데이터가 있으면 클라이언트 API 호출 생략
     if (initialData && initialData.length > 0) {
       setScanResults(initialData);
       setError(null);
       return;
     }
     
     // 초기 데이터가 없으면 API 호출
     if (!initialData || initialData.length === 0) {
       fetchScanResults();
     }
   }, [initialData]); // fetchScanResults 제거
   ```

3. **무한 루프 방지**
   ```javascript
   // 잘못된 코드
   useEffect(() => {
     fetchScanResults();
   }, [fetchScanResults]); // 함수 의존성으로 인한 무한 루프
   
   // 올바른 코드
   useEffect(() => {
     fetchScanResults();
   }, []); // 빈 의존성 배열
   ```

4. **정적 HTML 파일 수정**
   ```javascript
   // customer-scanner.html에서
   if (data && data.ok && data.data && data.data.items) {
       currentData = data.data.items; // rank → items로 변경
   }
   ```

### 8. 솔라피 알림톡 템플릿 변수 오류

**증상**:
- 알림톡 발송 실패
- 템플릿 변수가 치환되지 않음
- "데이터 형식이 올바르지 않습니다" 오류

**원인**:
- 솔라피 템플릿 변수명 불일치
- PF ID, 템플릿 ID 미설정
- 발신번호 미등록

**해결책**:
1. **솔라피 템플릿 변수 확인**
   ```python
   template_data = {
       "s_date": scan_date,      # 스캔일시
       "s_num": str(matched_count),  # 스캔된 종목 수
       "c_name": user_name       # 고객명
   }
   ```

2. **솔라피 설정 정보 업데이트**
   ```python
   payload = {
       "message": {
           "to": to,
           "from": "010-4220-0956",  # 솔라피에 등록된 발신번호
           "type": "ATA",
           "kakaoOptions": {
               "pfId": "실제_PF_ID",  # 솔라피에서 확인
               "templateId": "실제_템플릿_ID",  # 승인된 템플릿 ID
               "variables": template_data
           }
       }
   }
   ```

## 📋 2025-09-10 작업 완료 내역

### ✅ 완료된 작업:
1. **모바일 데이터 로딩 오류 해결**
   - SSR 데이터 우선 사용 로직 구현
   - useEffect 무한 루프 방지
   - 네트워크 상태 확인 및 타임아웃 설정

2. **프리미어 화면 데이터 표시 문제 해결**
   - API 응답 구조 수정 (`rank` → `items`)
   - SSR 기능 추가
   - 클라이언트 API 호출 최적화

3. **정적 HTML 파일 오류 수정**
   - `customer-scanner.html` API 응답 구조 수정
   - 서버 배포 및 Nginx 설정 재로드

4. **솔라피 알림톡 시스템 구현**
   - 템플릿 변수 시스템 구축 (`s_date`, `s_num`, `c_name`)
   - 스케줄러 자동 발송 기능
   - API 엔드포인트 수정

5. **문서 업데이트**
   - `KAKAO_ALIMTALK_TEMPLATE.md`에 로드맵 추가
   - 향후 개선 계획 문서화

### 🔄 진행 중인 작업:
- 솔라피 템플릿 등록 및 설정 정보 업데이트

### 📝 향후 계획:
1. **2단계**: 고객 등록 시스템 구축
2. **3단계**: 카카오톡 로그인 연동

## 💡 문제 해결 원칙

1. **로그 우선**: 항상 로그부터 확인
2. **단계별 접근**: 한 번에 하나씩 문제 해결
3. **백업 필수**: 변경 전 현재 상태 보존
4. **검증 완료**: 수정 후 반드시 테스트
5. **문서화**: 문제와 해결책 기록
6. **API 응답 구조 통일**: 모든 파일에서 동일한 구조 사용
7. **SSR 우선**: 서버 사이드 렌더링 데이터를 우선 사용
8. **의존성 배열 주의**: useEffect에서 함수 의존성 피하기
