# 데이터베이스 백업 아카이브

이 디렉토리에는 로컬 개발 중 생성된 데이터베이스 백업 파일들이 보관되어 있습니다.

## 📋 백업 파일 목록

### PostgreSQL 백업
- `db_backup_20251108_212334.tar.gz` (32KB)
  - 백업 일시: 2025년 11월 8일 21:23:34
  - 형식: tar.gz 압축
  
- `db_backup_before_market_conditions_20251109_141316.sql` (589KB)
  - 백업 일시: 2025년 11월 9일 14:13:16
  - 형식: SQL 덤프
  - 용도: market_conditions 테이블 확장 전 백업

## ⚠️ 중요 사항

### 현재 상태
- 이 백업들은 로컬 개발 환경의 PostgreSQL 백업입니다
- 프로덕션 백업은 서버에서 별도 관리됩니다
- 로컬 개발용 임시 백업입니다

### 보관 이유
1. **개발 중 안전장치**: 스키마 변경 전 백업
2. **롤백 대비**: 문제 발생 시 복원용
3. **데이터 비교**: 변경 전후 데이터 비교

### 삭제 가능 시점
- **우선순위**: 중간
- **조건**: 로컬 DB 정상 작동 확인 후
- **권장**: 1주일 후 삭제

## 🔄 복원 방법

### tar.gz 백업 복원
```bash
tar -xzf db_backup_20251108_212334.tar.gz
psql -U stockfinder -d stockfinder < backup.sql
```

### SQL 덤프 복원
```bash
psql -U stockfinder -d stockfinder < db_backup_before_market_conditions_20251109_141316.sql
```

## 🔗 현재 백업 시스템

### 서버 (프로덕션)
- **위치**: 서버의 `/home/ubuntu/showmethestock/backups/postgres/`
- **스케줄**: 매일 새벽 2시 자동 백업
- **보관 기간**: 7일
- **형식**: SQL 덤프 (gzip 압축)

### 로컬 (개발)
- 필요시 수동 백업
- `pg_dump stockfinder > backup_$(date +%Y%m%d_%H%M%S).sql`

## 📊 백업 크기

```
db_backup_20251108_212334.tar.gz: 32KB
db_backup_before_market_conditions_20251109_141316.sql: 589KB
총 크기: ~621KB
```

## 🗑️ 삭제 명령어

안전하게 삭제하려면:
```bash
# 프로젝트 루트에서
rm -rf archive/old_db_backups/
```

---

**마지막 업데이트**: 2025년 11월 9일

