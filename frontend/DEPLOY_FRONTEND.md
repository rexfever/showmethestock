# 프론트엔드 배포 가이드

## 배포 전 확인사항

1. ✅ 모든 변경사항이 GitHub에 푸시되었는지 확인
2. ✅ 로컬에서 빌드가 성공하는지 확인

## 배포 방법

### 서버에서 직접 배포

```bash
# 서버에 SSH 접속
ssh ubuntu@52.79.145.238
# 또는 SSH config 사용
ssh stock-finder

# 프론트엔드 디렉토리로 이동
cd /home/sohntech/showmethestock/frontend

# 최신 코드 가져오기
git pull origin main

# 의존성 설치
npm install

# 빌드
npm run build

# 프론트엔드 서비스 재시작
# PM2 사용 시
pm2 restart stock-finder-frontend

# 또는
pm2 restart all

# 또는 systemd 사용 시
sudo systemctl restart stock-finder-frontend
```

## 배포 후 확인

1. 브라우저에서 캐시 삭제 후 새로고침 (Ctrl+Shift+R 또는 Cmd+Shift+R)
2. 아이콘 변경 확인 (관찰 전략: ⏳)
3. 개발자 도구에서 네트워크 탭 확인

## 문제 발생 시

1. 빌드 오류 확인: `npm run build` 출력 확인
2. 서비스 상태 확인: `pm2 status` 또는 `sudo systemctl status stock-finder-frontend`
3. 로그 확인: `pm2 logs stock-finder-frontend` 또는 `sudo journalctl -u stock-finder-frontend -n 50`

