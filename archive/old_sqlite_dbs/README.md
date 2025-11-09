# SQLite 데이터베이스 아카이브

이 디렉토리에는 PostgreSQL로 마이그레이션하기 전에 사용하던 SQLite 데이터베이스 파일들이 보관되어 있습니다.

## 📋 파일 목록

### 주요 데이터베이스
- `portfolio.db` - 사용자 포트폴리오 데이터
- `email_verifications.db` - 이메일 인증 데이터
- `news_data.db` - 뉴스 데이터
- `snapshots.db` - 스캔 스냅샷 데이터
- `users.db` - 사용자 데이터

### 기타
- `invalid_db_path.db` - 테스트용 빈 파일
- `backend/` - 중복 백엔드 폴더

## ⚠️ 중요 사항

### 현재 상태
- **PostgreSQL로 완전 마이그레이션 완료** (2025-11-08)
- 이 SQLite 파일들은 더 이상 사용되지 않습니다
- 모든 데이터는 PostgreSQL로 이전되었습니다

### 보관 이유
1. **데이터 백업**: 만약의 경우를 대비한 원본 데이터 보존
2. **참조용**: 마이그레이션 검증 시 원본 데이터 비교
3. **롤백 대비**: 긴급 상황 시 참조 가능

### 삭제 가능 시점
다음 조건이 모두 충족되면 안전하게 삭제 가능:
- [ ] PostgreSQL 운영 30일 이상 안정적 운영
- [ ] 데이터 무결성 검증 완료
- [ ] 백업 시스템 정상 작동 확인
- [ ] 모든 기능 정상 작동 확인

## 📊 마이그레이션 정보

- **마이그레이션 일자**: 2025년 11월 8일
- **마이그레이션 방법**: `backend/migrations/sqlite_to_postgres.py`
- **PostgreSQL 버전**: 16
- **데이터 검증**: 완료

## 🔗 관련 문서

- PostgreSQL 마이그레이션 가이드: `manuals/SERVER_DEPLOYMENT_MANUAL_20251109.md`
- DB 관리 가이드: `DB_MANAGEMENT.md`
- 마이그레이션 스크립트: `backend/migrations/sqlite_to_postgres.py`

---

**마지막 업데이트**: 2025년 11월 9일

