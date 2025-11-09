# SQLite Export 데이터 아카이브

이 디렉토리에는 SQLite 데이터베이스에서 추출한 export 데이터가 보관되어 있습니다.

## 📋 Export 목록

### export_data/
- **생성 일시**: 2025년 10월 8일
- **용도**: 부분 데이터 추출
- **내용**:
  - portfolio.db (28KB)
  - email_verifications.db (12KB)
  - news_data.db (16KB)
  - snapshots.db (44KB)
- **총 크기**: ~100KB

### export_data_full/
- **생성 일시**: 2025년 10월 9일
- **용도**: 전체 데이터 추출
- **내용**:
  - backend/portfolio.db (28KB)
  - backend/email_verifications.db (12KB)
  - backend/news_data.db (16KB)
  - backend/snapshots.db (44KB)
- **총 크기**: ~100KB

## ⚠️ 중요 사항

### 현재 상태
- 이 export 데이터는 SQLite → PostgreSQL 마이그레이션 과정에서 생성된 중간 데이터입니다
- PostgreSQL 마이그레이션 완료 후 더 이상 필요하지 않습니다

### 보관 이유
1. **마이그레이션 검증**: 데이터 이전 과정 추적
2. **데이터 비교**: 원본과 마이그레이션 데이터 비교
3. **문제 해결**: 마이그레이션 이슈 발생 시 참조

### 삭제 권장
- **우선순위**: 높음 (가장 먼저 삭제 가능)
- **조건**: PostgreSQL 정상 운영 확인 후
- **이유**: 중복 데이터, 공간 절약

## 📊 총 크기

```
export_data: ~100KB
export_data_full: ~100KB
총 크기: ~200KB
```

## 🗑️ 삭제 명령어

안전하게 삭제하려면:
```bash
# 프로젝트 루트에서
rm -rf archive/old_sqlite_exports/export_data
rm -rf archive/old_sqlite_exports/export_data_full
```

## 🔗 관련 문서

- PostgreSQL 마이그레이션: `backend/migrations/sqlite_to_postgres.py`
- 현재 데이터베이스: PostgreSQL 16

---

**마지막 업데이트**: 2025년 11월 9일

