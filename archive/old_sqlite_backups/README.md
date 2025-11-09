# SQLite 백업 아카이브

이 디렉토리에는 PostgreSQL로 마이그레이션하기 전의 SQLite 데이터베이스 백업들이 보관되어 있습니다.

## 📋 백업 목록

### db_backup_20251105_211336
- **백업 일시**: 2025년 11월 5일 21:13:36
- **백업 내용**: 
  - portfolio.db (48KB)
  - email_verifications.db (12KB)
  - news_data.db (16KB)
  - snapshots.db (1.1MB)

### backup_20251011_015753_stable
- **백업 일시**: 2025년 10월 11일 01:57:53
- **백업 타입**: 안정 버전 (stable)
- **백업 내용**:
  - portfolio.db (28KB)
  - email_verifications.db (12KB)
  - news_data.db (16KB)
  - snapshots.db (48KB)

## ⚠️ 중요 사항

### 현재 상태
- PostgreSQL로 완전 마이그레이션 완료
- 이 백업들은 SQLite 시절의 데이터입니다
- 참조용으로만 보관

### 보관 이유
1. **히스토리 보존**: 시스템 변경 이력 추적
2. **데이터 검증**: 마이그레이션 전후 데이터 비교
3. **긴급 복구**: 만약의 경우 참조 가능

### 삭제 권장 시점
- PostgreSQL 운영 3개월 이상 안정화 후
- 디스크 공간 부족 시 우선 삭제 대상

## 📊 백업 크기

```
db_backup_20251105_211336: ~1.2MB
backup_20251011_015753_stable: ~104KB
총 크기: ~1.3MB
```

## 🔗 관련 문서

- 현재 백업 시스템: `manuals/SERVER_DEPLOYMENT_MANUAL_20251109.md`
- PostgreSQL 백업: `backups/postgres/`

---

**마지막 업데이트**: 2025년 11월 9일

