# 로컬/서버 구동 가이드

## 🖥️ 로컬 PC 구동 방법

### 1. 백엔드 실행

```bash
# 1. 백엔드 디렉토리로 이동
cd /Users/rexsmac/workspace/stock-finder/backend

# 2. 가상환경 활성화
source venv/bin/activate

# 3. PYTHONPATH 설정하여 백엔드 실행
PYTHONPATH=/Users/rexsmac/workspace/stock-finder nohup uvicorn main:app --host 127.0.0.1 --port 8010 > backend.log 2>&1 &
```

**백엔드 확인:**
```bash
# 상태 확인
curl http://127.0.0.1:8010/
# 응답: {"status":"running"}

# 환경 정보 확인
curl http://127.0.0.1:8010/environment
# 응답: 로컬 환경 정보 (environment: "local", is_local: true)
```

### 2. 프론트엔드 실행

```bash
# 1. 프론트엔드 디렉토리로 이동
cd /Users/rexsmac/workspace/stock-finder/frontend

# 2. 개발 서버 실행
npm run dev
```

**프론트엔드 확인:**
```bash
# 브라우저에서 접속
http://localhost:3000
# 또는
http://127.0.0.1:3000
```

### 3. 로컬 환경 특징

- **환경 감지**: 자동으로 "local" 환경으로 감지
- **호스트명**: `Rexsui-MacBook-Pro.local`
- **IP 주소**: `192.168.219.103` (로컬 네트워크)
- **사용자**: `rexsmac`
- **작업 디렉토리**: `/Users/rexsmac/workspace/stock-finder`

## 🌐 서버 구동 방법

### 1. AWS EC2 서버 접속

```bash
# SSH로 서버 접속
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207

# 또는 AWS CLI 사용
aws ec2-instance-connect send-ssh-public-key --instance-id i-0b06210468b99267e --availability-zone ap-northeast-2a --instance-os-user ubuntu --ssh-public-key file://~/.ssh/id_rsa.pub
```

### 2. 서버에서 백엔드 실행

```bash
# 1. 프로젝트 디렉토리로 이동
cd /home/ubuntu/showmethestock/backend

# 2. 가상환경 활성화
source venv/bin/activate

# 3. PYTHONPATH 설정하여 백엔드 실행
PYTHONPATH=/home/ubuntu/showmethestock nohup uvicorn main:app --host 0.0.0.0 --port 8010 > backend.log 2>&1 &
```

### 3. 서버에서 프론트엔드 실행

```bash
# 1. 프론트엔드 디렉토리로 이동
cd /home/ubuntu/showmethestock/frontend

# 2. 빌드 및 실행
npm run build && nohup npm start > frontend.log 2>&1 &
```

### 4. 서버 환경 특징

- **환경 감지**: 자동으로 "server" 환경으로 감지
- **호스트명**: `ip-172-31-12-241` (AWS EC2)
- **IP 주소**: `172.31.12.241` (내부), `52.79.61.207` (외부)
- **사용자**: `ubuntu`
- **작업 디렉토리**: `/home/ubuntu/showmethestock`

## 🔧 환경별 설정 차이

### 로컬 환경 설정
```python
# backend/environment.py에서 자동 설정
{
    "debug": True,
    "log_level": "DEBUG",
    "universe_kospi": 10,  # 테스트용 적은 수
    "universe_kosdaq": 10,
    "rate_limit_delay_ms": 100,  # 빠른 테스트
}
```

### 서버 환경 설정
```python
# backend/environment.py에서 자동 설정
{
    "debug": False,
    "log_level": "INFO",
    "universe_kospi": 100,  # 전체 데이터
    "universe_kosdaq": 100,
    "rate_limit_delay_ms": 250,  # 안전한 속도
}
```

## 🚀 빠른 시작 명령어

### 로컬 PC
```bash
# 백엔드만 실행
cd /Users/rexsmac/workspace/stock-finder/backend && source venv/bin/activate && PYTHONPATH=/Users/rexsmac/workspace/stock-finder nohup uvicorn main:app --host 127.0.0.1 --port 8010 > backend.log 2>&1 &

# 프론트엔드 실행
cd /Users/rexsmac/workspace/stock-finder/frontend && npm run dev
```

### 서버
```bash
# 백엔드 실행
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock/backend && source venv/bin/activate && PYTHONPATH=/home/ubuntu/showmethestock nohup uvicorn main:app --host 0.0.0.0 --port 8010 > backend.log 2>&1 &"

# 프론트엔드 실행
ssh -o StrictHostKeyChecking=no ubuntu@52.79.61.207 "cd /home/ubuntu/showmethestock/frontend && npm run build && nohup npm start > frontend.log 2>&1 &"
```

## 🔍 서비스 확인 방법

### 로컬 PC
```bash
# 백엔드 확인
curl http://127.0.0.1:8010/
curl http://127.0.0.1:8010/environment

# 프론트엔드 확인
curl http://127.0.0.1:3000/
```

### 서버
```bash
# 백엔드 확인
curl http://52.79.61.207:8010/
curl http://52.79.61.207:8010/environment

# 프론트엔드 확인 (Nginx를 통해)
curl https://sohntech.ai.kr/scanner/
curl https://sohntech.ai.kr/api/environment
```

## 🛠️ 문제 해결

### 로컬 PC 문제
1. **포트 충돌**: `lsof -i :8010` 또는 `lsof -i :3000`으로 확인
2. **PYTHONPATH 오류**: 반드시 절대 경로로 설정
3. **npm 오류**: `frontend` 디렉토리에서 실행 확인

### 서버 문제
1. **권한 문제**: `sudo chown -R ubuntu:ubuntu /home/ubuntu/showmethestock`
2. **포트 문제**: `sudo netstat -tlnp | grep -E ':(80|443|3000|8010)'`
3. **Nginx 문제**: `sudo systemctl status nginx`

## 📋 체크리스트

### 로컬 PC 시작 전
- [ ] 가상환경 활성화 확인
- [ ] PYTHONPATH 설정 확인
- [ ] 포트 사용 가능 확인
- [ ] npm 의존성 설치 확인

### 서버 시작 전
- [ ] SSH 접속 가능 확인
- [ ] 파일 권한 확인
- [ ] Nginx 상태 확인
- [ ] SSL 인증서 유효성 확인

### 시작 후 확인
- [ ] 백엔드 API 응답 확인
- [ ] 프론트엔드 접속 확인
- [ ] 환경 감지 정상 확인
- [ ] 로그 오류 확인

---

## 💡 팁

1. **로컬 개발**: 백엔드만 실행해도 API 테스트 가능
2. **서버 배포**: GitHub을 통한 자동 배포 권장
3. **환경 구분**: 코드에서 `config.is_local` 또는 `config.is_server`로 구분
4. **로그 확인**: `tail -f backend.log` 또는 `tail -f frontend.log`
