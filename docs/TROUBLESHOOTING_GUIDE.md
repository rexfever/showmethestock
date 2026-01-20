# 문제 해결 가이드

**최종 업데이트**: 2025-11-24

## 📋 목차

1. [일반적인 문제](#일반적인-문제)
2. [데이터베이스 문제](#데이터베이스-문제)
3. [API 문제](#api-문제)
4. [스캔 문제](#스캔-문제)
5. [배포 문제](#배포-문제)
6. [성능 문제](#성능-문제)

---

## 일반적인 문제

### 1. 포트 충돌

**증상**: `ERROR: [Errno 48] Address already in use`

**해결**:

```bash
# 로컬
# 8010 포트 사용 프로세스 확인 및 종료
lsof -ti:8010 | xargs kill -9

# 3000 포트 사용 프로세스 확인 및 종료
lsof -ti:3000 | xargs kill -9

# 서버
sudo lsof -ti:8010 | xargs sudo kill -9
sudo lsof -ti:3000 | xargs sudo kill -9
```

### 2. 모듈 import 오류

**증상**: `ModuleNotFoundError: No module named 'xxx'`

**해결**:

```bash
# 가상환경 활성화 확인
source venv/bin/activate

# 패키지 재설치
pip install -r requirements.txt

# PostgreSQL 관련 패키지 추가 설치
pip install psycopg psycopg-binary psycopg-pool python-dotenv
```

### 3. 환경 변수 미설정

**증상**: `DATABASE_URL is not configured`

**해결**:

```bash
# .env 파일 존재 확인
ls -la backend/.env

# .env 파일 내용 확인
cat backend/.env | grep DATABASE_URL

# 없다면 생성 (로컬 개발 메뉴얼 참조)
```

---

## 데이터베이스 문제

### 1. PostgreSQL 연결 실패

**증상**: `psycopg.OperationalError: connection failed`

**해결**:

#### 로컬

```bash
# PostgreSQL 서비스 상태 확인
# macOS:
brew services list | grep postgresql

# Ubuntu:
sudo systemctl status postgresql

# 서비스 재시작
# macOS:
brew services restart postgresql@16

# Ubuntu:
sudo systemctl restart postgresql

# 연결 테스트
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -c "SELECT 1;"
```

#### 서버

```bash
# PostgreSQL 서비스 상태 확인
sudo systemctl status postgresql

# 서비스 재시작
sudo systemctl restart postgresql

# 연결 테스트
sudo -u postgres psql -d stockfinder -c "SELECT 1;"
```

### 2. 테이블이 존재하지 않음

**증상**: `relation "table_name" does not exist`

**해결**:

```bash
cd backend

# 스키마 재적용
# 로컬 (macOS):
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -f sql/postgres_schema.sql
/usr/local/opt/postgresql@16/bin/psql -d stockfinder -f sql/add_scanner_settings.sql

# 로컬 (Ubuntu):
psql -d stockfinder -f sql/postgres_schema.sql
psql -d stockfinder -f sql/add_scanner_settings.sql

# 서버:
sudo -u postgres psql -d stockfinder -f sql/postgres_schema.sql
sudo -u postgres psql -d stockfinder -f sql/add_scanner_settings.sql

# 테이블 확인
psql -d stockfinder -c "\dt"
```

### 3. 날짜 형식 오류

**증상**: `ValueError: time data '2025-11-24 00:00:00+09' does not match format '%Y%m%d'`

**해결**:

- 최신 코드 사용 (날짜 처리 개선 완료)
- `date_helper.py`의 `normalize_date()` 함수 사용
- DB 스키마가 최신인지 확인

### 4. 데이터베이스 백업/복원

**백업**:

```bash
# 로컬
/usr/local/opt/postgresql@16/bin/pg_dump -d stockfinder > backup_$(date +%Y%m%d).sql

# 서버
sudo -u postgres pg_dump stockfinder > backup_$(date +%Y%m%d).sql
```

**복원**:

```bash
# 로컬
/usr/local/opt/postgresql@16/bin/psql -d stockfinder < backup_20251124.sql

# 서버
sudo -u postgres psql stockfinder < backup_20251124.sql
```

---

## API 문제

### 1. 키움 API 연결 실패

**증상**: `키움 API 연결 실패` 또는 `401 Unauthorized`

**해결**:

1. `.env` 파일의 `APP_KEY`, `APP_SECRET` 확인
2. 키움증권 개발자 센터에서 API 키 발급 상태 확인
3. API 키 만료 여부 확인
4. 주말/공휴일에는 데이터 조회 불가 (정상)

### 2. API Rate Limit

**증상**: `429 Too Many Requests`

**해결**:

- OHLCV 캐시 활용 (자동 적용됨)
- 요청 간격 조정 (`RATE_LIMIT_DELAY_MS` 환경 변수)
- 디스크 캐시 활용 (과거 날짜)

### 3. API 응답 지연

**증상**: API 호출이 느림

**해결**:

- 캐시 상태 확인: `GET /health` 또는 로그 확인
- 디스크 캐시 활용 (백테스트 시)
- 네트워크 상태 확인

---

## 스캔 문제

### 1. 스캔 결과가 0개

**증상**: 스캔 실행 후 결과가 없음

**원인 확인**:

1. **시장 상황**: 약세장일 경우 필터 조건이 강화됨
2. **Fallback 로직**: 활성화 여부 확인
3. **Scanner 버전**: V1/V2 차이 확인

**해결**:

```bash
# Scanner 설정 확인
# DB에서:
sudo -u postgres psql -d stockfinder -c "SELECT * FROM scanner_settings;"

# .env에서:
cat backend/.env | grep SCANNER

# Fallback 활성화 확인
cat backend/.env | grep FALLBACK_ENABLE
```

### 2. 스캔이 너무 느림

**증상**: 스캔 실행 시간이 오래 걸림

**해결**:

- OHLCV 캐시 활용 확인
- 유니버스 크기 조정 (`UNIVERSE_KOSPI`, `UNIVERSE_KOSDAQ`)
- 병렬 처리 확인 (기본 활성화)

### 3. 스캔 결과가 일관되지 않음

**증상**: 같은 날짜 스캔 결과가 다름

**원인**:

- 실시간 데이터 변경 (장중)
- 캐시 TTL 만료 후 재조회
- Scanner 버전 차이 (V1 vs V2)

**해결**:

- 스캔 결과는 DB에 저장되어 있음 (`scan_rank` 테이블)
- DB에서 조회하여 확인

---

## 배포 문제

### 1. 서비스가 시작되지 않음

**증상**: `systemctl start` 실패

**해결**:

```bash
# 서비스 상태 확인
sudo systemctl status stock-finder-backend

# 로그 확인
sudo journalctl -u stock-finder-backend -n 50

# 설정 파일 확인
sudo systemctl cat stock-finder-backend

# 수동 실행으로 오류 확인
cd /home/ubuntu/showmethestock/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8010
```

### 2. Git Pull 실패

**증상**: `error: The following untracked working tree files would be overwritten`

**해결**:

```bash
# 변경사항 백업
git stash

# 또는 특정 파일 백업
mkdir -p ~/temp_backup
mv <파일명> ~/temp_backup/

# Git Pull 재시도
git pull origin main
```

### 3. 환경 변수 누락

**증상**: 배포 후 기능이 동작하지 않음

**해결**:

- `.env` 파일은 Git에 추적되지 않음
- 서버의 `.env` 파일 수동 확인/수정 필요
- 배포 시 `.env` 파일 백업 확인

---

## 성능 문제

### 1. 메모리 부족

**증상**: `MemoryError` 또는 서버 응답 지연

**해결**:

```bash
# 메모리 사용량 확인
free -h

# 프로세스별 메모리 사용량
ps aux --sort=-%mem | head -10

# 캐시 크기 확인
# OHLCV 캐시 통계 확인 (API 또는 로그)
```

### 2. 디스크 공간 부족

**증상**: `No space left on device`

**해결**:

```bash
# 디스크 사용량 확인
df -h

# 큰 파일 찾기
du -sh /home/ubuntu/showmethestock/* | sort -h

# OHLCV 캐시 크기 확인
du -sh /home/ubuntu/showmethestock/backend/cache/ohlcv

# 오래된 캐시 파일 삭제 (선택사항)
find /home/ubuntu/showmethestock/backend/cache/ohlcv -name "*.pkl" -mtime +30 -delete
```

### 3. CPU 사용률 높음

**증상**: 서버 응답 지연

**해결**:

```bash
# CPU 사용률 확인
top

# 프로세스별 CPU 사용량
ps aux --sort=-%cpu | head -10

# 스캔 실행 중인지 확인
# 스케줄러 확인
```

---

## 로그 확인

### 로컬

```bash
# 백엔드 로그
tail -f backend/backend.log

# 또는 uvicorn 출력 확인 (터미널)
```

### 서버

```bash
# 백엔드 서비스 로그
sudo journalctl -u stock-finder-backend -f

# 최근 100줄
sudo journalctl -u stock-finder-backend -n 100

# 특정 시간대
sudo journalctl -u stock-finder-backend --since "2025-11-24 10:00:00"

# 프론트엔드 서비스 로그
sudo journalctl -u stock-finder-frontend -f
```

---

## 긴급 대응

### 1. 서비스 완전 중단

**증상**: 모든 기능이 동작하지 않음

**대응**:

```bash
# 1. 서비스 상태 확인
sudo systemctl status stock-finder-backend
sudo systemctl status stock-finder-frontend

# 2. 서비스 재시작
sudo systemctl restart stock-finder-backend
sudo systemctl restart stock-finder-frontend

# 3. PostgreSQL 확인
sudo systemctl status postgresql

# 4. Nginx 확인
sudo systemctl status nginx
```

### 2. 데이터베이스 손상

**증상**: DB 쿼리 실패

**대응**:

```bash
# 1. 백업 확인
ls -lh /home/ubuntu/showmethestock/backups/postgres/

# 2. 최신 백업으로 복원
sudo -u postgres psql stockfinder < /path/to/backup.sql

# 3. 또는 특정 테이블만 복원
```

### 3. 롤백 필요

**증상**: 배포 후 문제 발생

**대응**:

```bash
# 1. 이전 커밋 확인
cd /home/ubuntu/showmethestock
git log --oneline -10

# 2. 이전 커밋으로 롤백
git checkout <commit_hash>

# 3. 서비스 재시작
sudo systemctl restart stock-finder-backend
```

---

## 추가 리소스

- [로컬 개발 환경 구성](./deployment/LOCAL_DEVELOPMENT_SETUP.md#문제-해결)
- [서버 운영 메뉴얼](./deployment/SERVER_OPERATION_MANUAL.md#문제-해결)
- [프로젝트 개요](./PROJECT_OVERVIEW.md)

---

**마지막 업데이트**: 2025년 11월 24일

