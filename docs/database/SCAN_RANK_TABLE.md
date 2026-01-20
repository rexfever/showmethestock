# scan_rank 테이블 문서

## 개요

`scan_rank` 테이블은 스캔 결과를 저장하는 테이블입니다. 각 스캔 날짜별로 추천된 종목들의 정보를 저장합니다.

## 테이블 스키마

```sql
CREATE TABLE IF NOT EXISTS scan_rank (
    date                DATE NOT NULL,
    code                TEXT NOT NULL,
    name                TEXT,
    score               DOUBLE PRECISION,
    score_label         TEXT,
    current_price       DOUBLE PRECISION,
    close_price         DOUBLE PRECISION,
    volume              BIGINT,
    change_rate         DOUBLE PRECISION,
    market              TEXT,
    strategy            TEXT,
    indicators          JSONB,
    trend               TEXT,
    flags               TEXT,
    details             JSONB,
    returns             JSONB,
    recurrence          JSONB,
    scanner_version     TEXT NOT NULL DEFAULT 'v1',
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (date, code, scanner_version)
);
```

## 컬럼 설명

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `date` | DATE | NOT NULL | 스캔 날짜 |
| `code` | TEXT | NOT NULL | 종목 코드 |
| `name` | TEXT | NULL | 종목명 |
| `score` | DOUBLE PRECISION | NULL | 스캔 점수 |
| `score_label` | TEXT | NULL | 점수 레이블 (예: "Strong", "Watch") |
| `current_price` | DOUBLE PRECISION | NULL | 현재가 |
| `close_price` | DOUBLE PRECISION | NULL | 종가 (스캔 시점) |
| `volume` | BIGINT | NULL | 거래량 |
| `change_rate` | DOUBLE PRECISION | NULL | 등락률 (퍼센트, 예: 1.59 = 1.59%) |
| `market` | TEXT | NULL | 시장 구분 (KOSPI, KOSDAQ) |
| `strategy` | TEXT | NULL | 매매 전략 (Swing, Position, Long-term) |
| `indicators` | JSONB | NULL | 기술적 지표 (JSON 형식) |
| `trend` | TEXT | NULL | 추세 정보 (JSON 형식) |
| `flags` | TEXT | NULL | 플래그 정보 (JSON 형식) |
| `details` | JSONB | NULL | 상세 정보 (JSON 형식) |
| `returns` | JSONB | NULL | 수익률 정보 (JSON 형식) |
| `recurrence` | JSONB | NULL | 재등장 정보 (JSON 형식) |
| `scanner_version` | TEXT | NOT NULL, DEFAULT 'v1' | 스캐너 버전 (v1 또는 v2) |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | 생성 시간 |

## Primary Key

- **복합 키**: `(date, code, scanner_version)`
- 같은 날짜, 같은 종목이라도 스캐너 버전이 다르면 별도로 저장됨
- V1과 V2 스캔 결과를 동시에 보관 가능

## 인덱스

```sql
CREATE INDEX IF NOT EXISTS idx_scan_rank_score ON scan_rank(score);
CREATE INDEX IF NOT EXISTS idx_scan_rank_market ON scan_rank(market);
CREATE INDEX IF NOT EXISTS idx_scan_rank_scanner_version ON scan_rank(scanner_version);
CREATE INDEX IF NOT EXISTS idx_scan_rank_date_version ON scan_rank(date, scanner_version);
```

## 주요 필드 설명

### change_rate (등락률)

- **형식**: 퍼센트 (예: `1.59` = 1.59%)
- **저장 방식**: 퍼센트로 통일 저장
- **계산 방법**: `((현재가 - 전일종가) / 전일종가) * 100`
- **호환성**: 기존 소수 형식 데이터는 API에서 자동으로 퍼센트로 변환

### scanner_version (스캐너 버전)

- **가능한 값**: `v1`, `v2`
- **기본값**: `v1`
- **용도**: V1과 V2 스캔 결과를 구분하여 저장
- **조회 시**: 버전별로 별도 조회 가능

### indicators (기술적 지표)

JSON 형식으로 저장되는 기술적 지표:
```json
{
  "TEMA": 70617.31,
  "DEMA": 70368.53,
  "MACD_OSC": -271.51,
  "RSI_TEMA": 56.84,
  "OBV": 2373376,
  "VOL": 112340,
  "close": 70400,
  "change_rate": 1.59
}
```

## 조회 예시

### 특정 날짜의 스캔 결과 조회

```sql
-- V1 스캔 결과
SELECT * FROM scan_rank 
WHERE date = '2025-11-21' AND scanner_version = 'v1'
ORDER BY score DESC;

-- V2 스캔 결과
SELECT * FROM scan_rank 
WHERE date = '2025-11-21' AND scanner_version = 'v2'
ORDER BY score DESC;

-- 모든 버전의 스캔 결과
SELECT * FROM scan_rank 
WHERE date = '2025-11-21'
ORDER BY scanner_version, score DESC;
```

### 최신 스캔 결과 조회

```sql
-- 최신 스캔 날짜 확인
SELECT MAX(date) FROM scan_rank;

-- 최신 V1 스캔 결과
SELECT * FROM scan_rank 
WHERE date = (SELECT MAX(date) FROM scan_rank WHERE scanner_version = 'v1')
  AND scanner_version = 'v1'
ORDER BY score DESC;
```

## API 엔드포인트

### 스캔 실행 및 저장

```bash
GET /scan?date=20251121
```

- 스캔 실행 후 결과를 `scan_rank` 테이블에 저장
- 현재 활성화된 스캐너 버전으로 저장

### 스캔 결과 조회

```bash
GET /scan-by-date/20251121
GET /latest-scan
```

- `scan_rank` 테이블에서 조회
- 버전별로 별도 조회 가능

## 데이터 저장 로직

### 저장 함수

`backend/services/scan_service.py`의 `save_scan_snapshot()` 함수가 담당:

```python
def save_scan_snapshot(scan_items: List[Dict], today_as_of: str, scanner_version: str = None):
    # scanner_version이 없으면 현재 활성화된 버전 사용
    # 기존 데이터 삭제 후 새로 저장
    # change_rate는 퍼센트로 저장
```

### 저장 형식

- `change_rate`: 퍼센트로 저장 (예: `1.59` = 1.59%)
- `scanner_version`: 현재 활성화된 버전 자동 설정
- `date`: `YYYYMMDD` 형식의 문자열을 DATE 타입으로 변환

## 마이그레이션

### scanner_version 컬럼 추가

기존 테이블에 `scanner_version` 컬럼을 추가하는 마이그레이션:

```sql
-- 마이그레이션 스크립트: backend/sql/add_scanner_version_to_scan_rank.sql
ALTER TABLE scan_rank 
ADD COLUMN IF NOT EXISTS scanner_version TEXT NOT NULL DEFAULT 'v1';

-- 기존 데이터는 모두 'v1'으로 설정
UPDATE scan_rank SET scanner_version = 'v1' WHERE scanner_version IS NULL;

-- Primary Key 변경
ALTER TABLE scan_rank DROP CONSTRAINT IF EXISTS scan_rank_pkey;
ALTER TABLE scan_rank ADD PRIMARY KEY (date, code, scanner_version);
```

## 주의사항

1. **Primary Key**: `(date, code, scanner_version)` 복합 키이므로 같은 날짜, 같은 종목이라도 버전이 다르면 별도 저장
2. **change_rate 형식**: 퍼센트로 통일 저장 (소수 형식 아님)
3. **날짜 형식**: `DATE` 타입 사용 (YYYY-MM-DD)
4. **JSON 필드**: `indicators`, `details`, `returns`, `recurrence`는 JSONB 타입

## 관련 파일

- `backend/services/scan_service.py`: 저장 로직
- `backend/main.py`: 조회 API
- `backend/sql/postgres_schema.sql`: 스키마 정의
- `backend/sql/add_scanner_version_to_scan_rank.sql`: 마이그레이션 스크립트

