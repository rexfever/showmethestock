# 데이터베이스 관리 가이드

## 🚨 중요 규칙

### ❌ 절대 금지 사항
- **데이터베이스 파일 삭제 금지**
- **테이블 DROP/TRUNCATE 금지**
- **전체 데이터 DELETE 금지**
- **백업 없는 DB 조작 금지**

### 📁 보호 대상 파일
- `snapshots.db` - 메인 DB (사용자, 포지션, 스캔 결과)
- `portfolio.db` - 포트폴리오 관리
- `email_verifications.db` - 이메일 인증
- `news_data.db` - 뉴스 데이터

## 🔧 안전한 DB 작업

### 백업 생성
```bash
# 백업 폴더 생성
mkdir -p /home/ubuntu/showmethestock/backend/backups

# 백업 실행
cd /home/ubuntu/showmethestock/backend
cp snapshots.db backups/snapshots_backup_$(date +%Y%m%d_%H%M%S).db
cp portfolio.db backups/portfolio_backup_$(date +%Y%m%d_%H%M%S).db
```

### 데이터 조회 (안전)
```bash
# 테이블 목록 확인
sqlite3 snapshots.db '.tables'

# 데이터 개수 확인
sqlite3 snapshots.db 'SELECT COUNT(*) FROM users;'
sqlite3 snapshots.db 'SELECT COUNT(*) FROM scan_rank;'

# 최근 데이터 확인
sqlite3 snapshots.db 'SELECT * FROM scan_rank ORDER BY date DESC LIMIT 5;'
```

### 허용되는 작업
```bash
# 특정 날짜 데이터만 삭제 (스캔 갱신용)
sqlite3 snapshots.db "DELETE FROM scan_rank WHERE date='2025-10-28';"

# 데이터 추가
sqlite3 snapshots.db "INSERT INTO scan_rank (...) VALUES (...);"

# 데이터 수정
sqlite3 snapshots.db "UPDATE scan_rank SET score=8.0 WHERE date='2025-10-28' AND code='005930';"
```

## 🆘 문제 발생 시

### 데이터 손실 시 복구
```bash
# 백업에서 복원
cd /home/ubuntu/showmethestock/backend
cp backups/snapshots_backup_YYYYMMDD_HHMMSS.db snapshots.db

# 특정 테이블만 복원
sqlite3 backups/snapshots_backup_YYYYMMDD_HHMMSS.db '.dump scan_rank' | sqlite3 snapshots.db
```

### 긴급 연락처
- **개발자**: chicnova@gmail.com
- **전화**: 010-4220-0956

## 📊 현재 DB 현황

### snapshots.db
- users: 8명
- positions: 19개
- scan_rank: 564개 (2025-06-15 ~ 2025-10-28)
- 기타: payments, subscriptions, send_logs 등

### 백업 정책
- 매일 자동 백업 권장
- 중요 작업 전 수동 백업 필수
- 백업 파일은 최소 30일 보관

---

**⚠️ 이 가이드를 반드시 준수하여 데이터 손실을 방지하세요!**