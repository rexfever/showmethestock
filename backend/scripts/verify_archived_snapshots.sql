-- =========================================================
-- ARCHIVED 스냅샷 검증 SQL
-- =========================================================

-- A) ARCHIVED 스냅샷 누락 여부
SELECT 
    COUNT(*) as missing_snapshot_count
FROM recommendations
WHERE status = 'ARCHIVED'
  AND scanner_version = 'v3'
  AND (archive_at IS NULL OR archive_return_pct IS NULL OR archive_reason IS NULL);

-- B) ARCHIVED 사유 분포
SELECT 
    archive_reason, 
    COUNT(*) as count
FROM recommendations
WHERE status = 'ARCHIVED'
  AND scanner_version = 'v3'
GROUP BY archive_reason
ORDER BY count DESC;

-- C) ARCHIVED 수익률 분포 확인
SELECT
    MIN(archive_return_pct) as min_return,
    MAX(archive_return_pct) as max_return,
    AVG(archive_return_pct) as avg_return,
    COUNT(*) as total_count,
    COUNT(CASE WHEN archive_return_pct > 2 THEN 1 END) as profit_count,
    COUNT(CASE WHEN archive_return_pct < -2 THEN 1 END) as loss_count,
    COUNT(CASE WHEN archive_return_pct BETWEEN -2 AND 2 THEN 1 END) as flat_count
FROM recommendations
WHERE status = 'ARCHIVED'
  AND scanner_version = 'v3'
  AND archive_return_pct IS NOT NULL;

-- D) ARCHIVED phase 분포
SELECT 
    archive_phase,
    COUNT(*) as count
FROM recommendations
WHERE status = 'ARCHIVED'
  AND scanner_version = 'v3'
GROUP BY archive_phase
ORDER BY count DESC;

-- E) archive_at 컬럼 존재 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'recommendations'
  AND column_name LIKE 'archive%'
ORDER BY column_name;

-- F) 스냅샷 완전성 확인 (모든 필수 필드가 있는지)
SELECT 
    COUNT(*) as complete_snapshots,
    COUNT(*) FILTER (WHERE archive_at IS NOT NULL 
                     AND archive_reason IS NOT NULL 
                     AND archive_return_pct IS NOT NULL) as fully_complete
FROM recommendations
WHERE status = 'ARCHIVED'
  AND scanner_version = 'v3';



