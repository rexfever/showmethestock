# 서버 배포 지시사항 (2025-11-18)

## 배포 완료 상태
- ✅ 로컬 커밋 완료
- ✅ GitHub 푸시 완료 (커밋: `a632cdb`)
- ⚠️ 서버 배포 필요 (SSH 접속 실패로 수동 배포 필요)

## 서버 배포 절차

### 1. 서버 접속
```bash
ssh ubuntu@sohntech.ai.kr
```

### 2. 프로젝트 디렉토리로 이동
```bash
cd /home/ubuntu/showmethestock
```

### 3. 최신 코드 가져오기
```bash
git pull origin main
```

### 4. 백엔드 서비스 재시작
```bash
# systemd 사용 시
sudo systemctl restart stock-finder-backend

# 또는 PM2 사용 시
pm2 restart backend
```

### 5. 배포 확인
```bash
# 서비스 상태 확인
sudo systemctl status stock-finder-backend

# 또는 PM2 상태 확인
pm2 status

# 로그 확인
sudo journalctl -u stock-finder-backend -f --lines 50
```

## 배포된 변경사항

### 핵심 기능
- **장기 추세와 단기 급락 구분 로직**
  - 파일: `backend/market_analyzer.py`
  - 변경: `lookback_days` 5일 → 10일
  - 추가: 조정 판단 로직 (장기 상승 추세 중 단기 급락 시 조정으로 판단)

### 문서
- `backend/docs/analysis/LONG_TERM_TREND_VS_SHORT_TERM_SHOCK.md`
- `backend/docs/analysis/NOVEMBER_MARKET_ANALYSIS_SUMMARY.md`
- `backend/docs/deployment/DEPLOYMENT_PLAN_20251118.md`

## 배포 후 확인 사항

### 1. 서비스 정상 동작 확인
```bash
# 헬스 체크
curl http://localhost:8010/health
```

### 2. 로그 확인
```bash
# 장세 분석 로그 확인
sudo journalctl -u stock-finder-backend | grep "장기 상승 추세 중 단기 조정"
```

### 3. 스캔 테스트
```bash
# 오늘 날짜로 스캔 실행 (테스트)
curl "http://localhost:8010/scan?date=$(date +%Y%m%d)"
```

## 롤백 방법 (문제 발생 시)

```bash
cd /home/ubuntu/showmethestock
git log --oneline -5  # 이전 커밋 확인
git reset --hard <이전_커밋_해시>  # 예: ed0e2a4
sudo systemctl restart stock-finder-backend
```

## 참고
- 배포 계획서: `backend/docs/deployment/DEPLOYMENT_PLAN_20251118.md`
- 상세 분석: `backend/docs/analysis/LONG_TERM_TREND_VS_SHORT_TERM_SHOCK.md`

