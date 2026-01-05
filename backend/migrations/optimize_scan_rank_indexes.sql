-- scan_rank 테이블 쿼리 성능 최적화를 위한 인덱스 추가
-- 날짜 범위 조회 + 정렬 최적화

-- 1. 날짜 범위 + 버전 + 점수 정렬을 위한 복합 인덱스 (DESC 정렬 지원)
-- ORDER BY date DESC, score DESC 쿼리 최적화
CREATE INDEX IF NOT EXISTS idx_scan_rank_date_version_score_desc 
ON scan_rank(date DESC, scanner_version, score DESC);

-- 2. 특정 날짜 + 버전 + 점수 정렬 (가장 많이 사용되는 패턴)
CREATE INDEX IF NOT EXISTS idx_scan_rank_date_version_score 
ON scan_rank(date, scanner_version, score DESC);

-- 3. 버전별 최신 날짜 조회 최적화
CREATE INDEX IF NOT EXISTS idx_scan_rank_version_date_desc 
ON scan_rank(scanner_version, date DESC);

-- 4. 코드 기반 조회 (포트폴리오 등에서 사용)
CREATE INDEX IF NOT EXISTS idx_scan_rank_code_date 
ON scan_rank(code, date DESC);

-- 기존 인덱스는 유지 (다른 쿼리 패턴에서 사용 가능)
-- idx_scan_rank_date_version: (date, scanner_version) - 유지
-- idx_scan_rank_score: (score) - 유지
-- idx_scan_rank_market: (market) - 유지

-- 인덱스 통계 업데이트
ANALYZE scan_rank;



































