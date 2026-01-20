/* =========================================================
   recommendations 테이블에 reason 및 archive_reason 컬럼 추가
   BROKEN 상태일 때 종료 사유를 저장 (reason)
   ARCHIVED 상태일 때 종료 사유를 저장 (archive_reason)
   ========================================================= */

-- reason 컬럼 추가 (BROKEN 상태일 때 사용)
ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS reason VARCHAR(32);

COMMENT ON COLUMN recommendations.reason IS 'BROKEN 상태 종료 사유 (TTL_EXPIRED, NO_MOMENTUM, MANUAL_ARCHIVE)';

-- archive_reason 컬럼 추가 (ARCHIVED 상태일 때 사용)
ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS archive_reason VARCHAR(32);

COMMENT ON COLUMN recommendations.archive_reason IS 'ARCHIVED 전환 시 종료 사유 (TTL_EXPIRED, NO_MOMENTUM, MANUAL_ARCHIVE)';

-- 인덱스 추가 (BROKEN 조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_recommendations_reason
ON recommendations (reason)
WHERE reason IS NOT NULL;

-- 인덱스 추가 (ARCHIVED 조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_recommendations_archive_reason
ON recommendations (archive_reason)
WHERE archive_reason IS NOT NULL;

-- archive_return_pct, archive_price, archive_phase 컬럼 추가 (ARCHIVED 스냅샷 정보)
ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS archive_return_pct NUMERIC(10,2);

COMMENT ON COLUMN recommendations.archive_return_pct IS 'ARCHIVED 전환 시 수익률 (%)';

ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS archive_price NUMERIC(10,2);

COMMENT ON COLUMN recommendations.archive_price IS 'ARCHIVED 전환 시 가격';

ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS archive_phase VARCHAR(16);

COMMENT ON COLUMN recommendations.archive_phase IS 'ARCHIVED 전환 시 단계 (PROFIT, LOSS, FLAT)';

