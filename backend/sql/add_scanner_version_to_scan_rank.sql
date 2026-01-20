-- scan_rank 테이블에 scanner_version 컬럼 추가
-- 생성일: 2025-11-21
-- 설명: V1과 V2 스캔 결과를 별도로 저장하기 위한 마이그레이션

-- 1. 기존 Primary Key 제약조건 제거
ALTER TABLE scan_rank DROP CONSTRAINT IF EXISTS scan_rank_pkey;

-- 2. scanner_version 컬럼 추가 (기본값: 'v1' - 기존 데이터 호환성)
ALTER TABLE scan_rank ADD COLUMN IF NOT EXISTS scanner_version TEXT NOT NULL DEFAULT 'v1';

-- 3. 새로운 Primary Key 설정 (date, code, scanner_version)
ALTER TABLE scan_rank ADD CONSTRAINT scan_rank_pkey PRIMARY KEY (date, code, scanner_version);

-- 4. 인덱스 추가 (조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_scan_rank_scanner_version ON scan_rank(scanner_version);
CREATE INDEX IF NOT EXISTS idx_scan_rank_date_version ON scan_rank(date, scanner_version);

-- 5. 기존 데이터 확인 (모두 v1으로 설정됨)
SELECT COUNT(*) as total_records, 
       COUNT(DISTINCT scanner_version) as version_count,
       scanner_version
FROM scan_rank 
GROUP BY scanner_version;

-- 테이블 코멘트
COMMENT ON COLUMN scan_rank.scanner_version IS '스캐너 버전 (v1 또는 v2)';

