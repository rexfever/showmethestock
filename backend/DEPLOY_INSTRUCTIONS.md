# 서버 배포 가이드

## 배포 전 확인사항

1. ✅ 모든 변경사항이 GitHub에 푸시되었는지 확인
2. ✅ 테스트가 통과했는지 확인
3. ✅ 프론트엔드 빌드가 필요한 경우 빌드 완료 확인

## 배포 방법

### 방법 1: SSH로 직접 배포 (권장)

```bash
# 서버에 SSH 접속
ssh ubuntu@52.79.145.238

# 또는 SSH config 사용
ssh stock-finder

# 배포 스크립트 실행
cd /home/sohntech/showmethestock/backend
bash deploy_server_manual.sh
```

### 방법 2: 프론트엔드도 함께 배포

```bash
# 서버 접속 후
cd /home/sohntech/showmethestock

# 백엔드 배포
cd backend
bash deploy_server_manual.sh

# 프론트엔드 배포
cd ../frontend
npm install
npm run build
sudo systemctl restart stock-finder-frontend  # 또는 PM2 사용
```

## 배포 후 확인

1. 백엔드 헬스 체크: `curl http://localhost:8010/health`
2. 서비스 상태 확인: `sudo systemctl status stock-finder-backend`
3. 로그 확인: `sudo journalctl -u stock-finder-backend -n 50`

## 문제 발생 시

1. 서비스 재시작: `sudo systemctl restart stock-finder-backend`
2. 로그 확인: `sudo journalctl -u stock-finder-backend -f`
3. 롤백: `git checkout <이전-커밋>` 후 재배포

