# 작업 워크플로우 가이드

## 🎯 작업 전 체크리스트

### 1. 현재 상태 파악
- [ ] 현재 작업 디렉토리 확인 (`pwd`)
- [ ] Git 상태 확인 (`git status`)
- [ ] 서버 상태 확인 (필요시)
- [ ] TODO 리스트 확인 및 업데이트

### 2. 작업 계획 수립
- [ ] 작업 목표 명확화
- [ ] 필요한 파일/도구 식별
- [ ] 작업 순서 정리
- [ ] 예상 문제점 및 해결 방안 준비

## 🔧 개발 작업 워크플로우

### 로컬 개발
1. **로컬 서비스 시작**
   ```bash
   # 백엔드 실행
   cd /Users/rexsmac/workspace/stock-finder/backend && source venv/bin/activate && PYTHONPATH=/Users/rexsmac/workspace/stock-finder nohup uvicorn main:app --host 127.0.0.1 --port 8010 > backend.log 2>&1 &
   
   # 프론트엔드 실행
   cd /Users/rexsmac/workspace/stock-finder/frontend && npm run dev
   ```

2. **코드 수정**
   - 파일 읽기 → 수정 → 검증
   - 린트 오류 확인 및 수정
   - 로컬 테스트 (`http://127.0.0.1:8010/`, `http://127.0.0.1:3000/`)

3. **Git 관리**
   ```bash
   git add .
   git commit -m "명확한 커밋 메시지"
   git push origin main
   ```

4. **서버 배포**
   ```bash
   # GitHub을 통한 배포 (권장)
   ssh -o StrictHostKeyChecking=no ubuntu@[IP] "cd /home/ubuntu/showmethestock && git pull origin main"
   
   # 또는 직접 파일 전송
   scp -o StrictHostKeyChecking=no [파일] ubuntu@[IP]:/home/ubuntu/showmethestock/
   ```

### 서버 관리
1. **서비스 상태 확인**
   ```bash
   ssh -o StrictHostKeyChecking=no ubuntu@[IP] "sudo systemctl status nginx"
   ssh -o StrictHostKeyChecking=no ubuntu@[IP] "ps aux | grep -E '(uvicorn|node)' | grep -v grep"
   ```

2. **서비스 재시작**
   ```bash
   # Nginx 재시작
   ssh -o StrictHostKeyChecking=no ubuntu@[IP] "sudo systemctl reload nginx"
   
   # 백엔드 재시작
   ssh -o StrictHostKeyChecking=no ubuntu@[IP] "cd /home/ubuntu/showmethestock/backend && source venv/bin/activate && nohup uvicorn main:app --host 0.0.0.0 --port 8010 > backend.log 2>&1 &"
   
   # 프론트엔드 재시작
   ssh -o StrictHostKeyChecking=no ubuntu@[IP] "cd /home/ubuntu/showmethestock/frontend && npm run build && nohup npm start > frontend.log 2>&1 &"
   ```

## 🚨 자주 발생하는 실수와 해결책

### 1. 터미널 명령 중단 문제
**문제**: Cursor에서 터미널 명령이 계속 중단됨
**해결책**:
- AWS CLI 사용 (SSH 키 없이도 가능)
- 단일 명령어로 실행
- GitHub을 통한 배포 방식 사용

### 2. Nginx 설정 오류
**문제**: SSL 설정 덮어쓰기, 문법 오류
**해결책**:
- 설정 변경 후 `sudo nginx -t`로 문법 검사
- Certbot 사용 후 설정 백업
- 단계별 설정 적용

### 3. 파일 권한 문제
**문제**: Permission denied 오류
**해결책**:
```bash
sudo chown -R ubuntu:ubuntu /home/ubuntu/showmethestock
sudo chmod -R 755 /home/ubuntu/showmethestock
```

### 4. Git 충돌 문제
**문제**: 로컬 변경사항과 원격 충돌
**해결책**:
```bash
git reset --hard HEAD
git clean -fd
git pull origin main
```

## 📋 작업별 체크리스트

### 새 기능 개발
- [ ] 요구사항 분석
- [ ] 백엔드 API 개발
- [ ] 프론트엔드 UI 개발
- [ ] 통합 테스트
- [ ] 배포 및 검증

### 버그 수정
- [ ] 문제 재현
- [ ] 원인 분석
- [ ] 수정 구현
- [ ] 테스트
- [ ] 배포

### 인프라 변경
- [ ] 현재 상태 백업
- [ ] 변경 계획 수립
- [ ] 단계별 적용
- [ ] 각 단계별 검증
- [ ] 롤백 계획 준비

## 🔍 검증 방법

### 웹사이트 테스트
```bash
# HTTP 상태 코드 확인
curl -s -o /dev/null -w "%{http_code}" https://sohntech.ai.kr/

# 페이지 내용 확인
curl -s https://sohntech.ai.kr/ | head -10

# API 테스트
curl -s https://sohntech.ai.kr/api/universe
```

### 서버 로그 확인
```bash
# Nginx 로그
ssh -o StrictHostKeyChecking=no ubuntu@[IP] "sudo tail -f /var/log/nginx/error.log"

# 백엔드 로그
ssh -o StrictHostKeyChecking=no ubuntu@[IP] "tail -f /home/ubuntu/showmethestock/backend/backend.log"

# 프론트엔드 로그
ssh -o StrictHostKeyChecking=no ubuntu@[IP] "tail -f /home/ubuntu/showmethestock/frontend/frontend.log"
```

## 📝 작업 기록

### 커밋 메시지 규칙
- `feat:` 새로운 기능
- `fix:` 버그 수정
- `update:` 기존 기능 개선
- `deploy:` 배포 관련
- `docs:` 문서 수정

### TODO 관리
- 작업 시작 시 TODO 리스트 생성
- 진행 상황 실시간 업데이트
- 완료된 작업 즉시 체크

## 🛡️ 안전 장치

### 백업 전략
- Git 커밋 전 코드 검토
- 서버 설정 변경 전 백업
- 중요한 파일은 별도 저장

### 롤백 계획
- 각 단계별 롤백 방법 준비
- 문제 발생 시 즉시 이전 상태로 복원
- 사용자에게 영향 최소화

## 📞 문제 해결 순서

1. **문제 파악**: 정확한 오류 메시지 확인
2. **로그 분석**: 관련 로그 파일 검토
3. **원인 추적**: 단계별 원인 분석
4. **해결 방안**: 가장 안전한 방법 선택
5. **검증**: 수정 후 정상 작동 확인
6. **문서화**: 문제와 해결책 기록

---

## 🎯 핵심 원칙

1. **단계별 진행**: 한 번에 하나씩, 검증하며 진행
2. **백업 우선**: 변경 전 항상 현재 상태 보존
3. **검증 필수**: 각 단계마다 정상 작동 확인
4. **문서화**: 모든 변경사항과 해결책 기록
5. **안전 우선**: 사용자 서비스 중단 최소화
