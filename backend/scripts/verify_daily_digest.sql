-- =========================================================
-- daily_digest 검증 SQL
-- =========================================================

-- A) 오늘 상태 전이 분포
SELECT 
    status, 
    COUNT(*) as count
FROM recommendations
WHERE status_changed_at >= CURRENT_DATE
  AND status_changed_at < CURRENT_DATE + INTERVAL '1 day'
  AND scanner_version = 'v3'
GROUP BY status
ORDER BY count DESC;

-- B) 신규 추천 검증
SELECT 
    COUNT(*) as new_recommendations_count
FROM recommendations
WHERE anchor_date = CURRENT_DATE
  AND status IN ('ACTIVE', 'WEAK_WARNING')
  AND scanner_version = 'v3';

-- C) 신규 BROKEN 검증
SELECT 
    COUNT(*) as new_broken_count
FROM recommendations
WHERE status = 'BROKEN'
  AND status_changed_at >= CURRENT_DATE
  AND status_changed_at < CURRENT_DATE + INTERVAL '1 day'
  AND scanner_version = 'v3';

-- D) 신규 ARCHIVED 검증
SELECT 
    COUNT(*) as new_archived_count
FROM recommendations
WHERE status = 'ARCHIVED'
  AND status_changed_at >= CURRENT_DATE
  AND status_changed_at < CURRENT_DATE + INTERVAL '1 day'
  AND scanner_version = 'v3';

-- E) status_changed_at 컬럼 존재 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'recommendations'
  AND column_name = 'status_changed_at';

-- F) status_changed_at 인덱스 확인
SELECT 
    indexname, 
    indexdef
FROM pg_indexes
WHERE tablename = 'recommendations'
  AND indexname LIKE '%status_changed_at%';



