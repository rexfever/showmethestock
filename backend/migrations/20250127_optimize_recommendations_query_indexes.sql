-- 성능 최적화: recommendations 테이블 복합 인덱스 추가
-- 날짜: 2025-01-27
-- 목적: status + scanner_version 조합 쿼리 성능 향상

-- 1. status + scanner_version 복합 인덱스 (가장 자주 사용되는 쿼리)
CREATE INDEX IF NOT EXISTS idx_recommendations_status_scanner_version
ON recommendations (status, scanner_version)
WHERE status IN ('ACTIVE', 'WEAK_WARNING', 'BROKEN', 'ARCHIVED');

-- 2. status + scanner_version + anchor_date 복합 인덱스 (정렬 최적화)
CREATE INDEX IF NOT EXISTS idx_recommendations_status_scanner_anchor_date
ON recommendations (status, scanner_version, anchor_date DESC)
WHERE status IN ('ACTIVE', 'WEAK_WARNING', 'BROKEN', 'ARCHIVED');

-- 3. status + scanner_version + broken_at 복합 인덱스 (needs-attention 쿼리 최적화)
CREATE INDEX IF NOT EXISTS idx_recommendations_status_scanner_broken_at
ON recommendations (status, scanner_version, broken_at DESC NULLS LAST, anchor_date DESC)
WHERE status IN ('WEAK_WARNING', 'BROKEN');

COMMENT ON INDEX idx_recommendations_status_scanner_version IS 'status + scanner_version 조합 쿼리 최적화';
COMMENT ON INDEX idx_recommendations_status_scanner_anchor_date IS 'status + scanner_version + anchor_date 정렬 최적화';
COMMENT ON INDEX idx_recommendations_status_scanner_broken_at IS 'needs-attention 쿼리 최적화 (BROKEN/WEAK_WARNING)';


