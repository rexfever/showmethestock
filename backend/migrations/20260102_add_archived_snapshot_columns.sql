/* =========================================================
   recommendations 테이블에 ARCHIVED 스냅샷 컬럼 추가
   ARCHIVED 전환 시점의 상태(손익/사유/시점)를 스냅샷으로 저장
   ========================================================= */

-- archive_at 컬럼 (이미 archived_at이 있지만 archive_at으로 통일)
-- archived_at이 있으면 그대로 사용, 없으면 추가
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'recommendations' 
        AND column_name = 'archive_at'
    ) THEN
        ALTER TABLE recommendations ADD COLUMN archive_at TIMESTAMPTZ;
        
        -- archived_at이 있으면 archive_at으로 복사
        UPDATE recommendations
        SET archive_at = archived_at
        WHERE archived_at IS NOT NULL AND archive_at IS NULL;
    END IF;
END $$;

-- archive_reason 컬럼 추가
ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS archive_reason VARCHAR(32);

-- archive_return_pct 컬럼 추가
ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS archive_return_pct NUMERIC(6,2);

-- archive_price 컬럼 추가
ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS archive_price NUMERIC;

-- archive_phase 컬럼 추가
ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS archive_phase VARCHAR(16);

-- 인덱스 추가 (ARCHIVED 조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_recommendations_archive_reason
ON recommendations (archive_reason)
WHERE archive_reason IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_recommendations_archive_at
ON recommendations (archive_at)
WHERE archive_at IS NOT NULL;

COMMENT ON COLUMN recommendations.archive_at IS 'ARCHIVED 전환 시점 (KST 기준, 스냅샷 시점)';
COMMENT ON COLUMN recommendations.archive_reason IS 'ARCHIVED 사유 (TTL_EXPIRED, NO_MOMENTUM, MANUAL_ARCHIVE)';
COMMENT ON COLUMN recommendations.archive_return_pct IS 'ARCHIVED 전환 시점의 수익률 (%)';
COMMENT ON COLUMN recommendations.archive_price IS 'ARCHIVED 전환 시점 가격';
COMMENT ON COLUMN recommendations.archive_phase IS '전환 시 국면 요약 (PROFIT, LOSS, FLAT)';



