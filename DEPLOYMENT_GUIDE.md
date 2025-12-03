# 배포 가이드

## 변경사항 요약

### 커밋 정보
- **최신 커밋 해시**: 7351cf073
- **최신 커밋 메시지**: fix: 현재가 표시 이슈 해결 및 수익률 계산 로직 개선
- **이전 커밋 해시**: 49e385f9a
- **이전 커밋 메시지**: feat: current_price 변수명 명확화 및 가격 표시 로직 개선

### 변경된 파일
1. `backend/main.py` - 변수명 명확화
2. `backend/services/returns_service.py` - get_kst_now() 사용
3. `frontend/v2/components/StockCardV2.js` - 가격 표시 단순화
4. `frontend/pages/customer-scanner.js` - 가격 표시 단순화
5. `frontend/components/v2/StockCardV2.js` - 가격 표시 단순화

---

## 서버 배포 방법

### 방법 1: SSH로 직접 배포 (권장)

```bash
# 서버에 SSH 접속
ssh ubuntu@your-server-ip

# 프로젝트 디렉토리로 이동
cd /home/ubuntu/showmethestock

# 전체 배포 실행
bash deploy_all.sh
```

### 방법 2: 백엔드만 배포

```bash
cd /home/ubuntu/showmethestock/backend
bash deploy_server_manual.sh
```

### 방법 3: 프론트엔드만 배포

```bash
cd /home/ubuntu/showmethestock/frontend
bash deploy_server_manual.sh
```

---

## 배포 후 확인 사항

### 1. 백엔드 헬스 체크
```bash
curl http://localhost:8010/health
```

### 2. 프론트엔드 헬스 체크
```bash
curl http://localhost:3000
```

### 3. API 테스트
```bash
# 최신 스캔 조회
curl http://localhost:8010/latest-scan

# current_price가 오늘 종가로 표시되는지 확인
```

### 4. 프론트엔드 확인
- 브라우저에서 스캐너 페이지 접속
- 종목 카드의 가격이 오늘 종가로 표시되는지 확인
- 브라우저 캐시 삭제 후 새로고침 (Ctrl+Shift+R 또는 Cmd+Shift+R)

---

## 롤백 방법

문제 발생 시 이전 커밋으로 롤백:

```bash
cd /home/ubuntu/showmethestock
git reset --hard e91e35d4b  # 이전 커밋
bash deploy_all.sh
```

---

## 주의사항

1. **브라우저 캐시**: 프론트엔드 변경사항은 브라우저 캐시 삭제 필요
2. **서비스 재시작**: 배포 후 자동으로 재시작되지만, 수동 확인 권장
3. **데이터베이스**: 이번 변경사항은 DB 스키마 변경 없음

---

**배포 일시**: 2025-11-27
**배포 상태**: ✅ Git 푸시 완료 (7351cf073), 서버 배포 진행 중

