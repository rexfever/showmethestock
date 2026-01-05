/* =========================================================
   recommendations 테이블에 broken_return_pct 컬럼 추가
   BROKEN 상태일 때 종료 시점 수익률을 저장
   ========================================================= */

-- broken_return_pct 컬럼 추가 (BROKEN 상태일 때 사용)
ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS broken_return_pct NUMERIC(10,2);

COMMENT ON COLUMN recommendations.broken_return_pct IS 'BROKEN 전환 시 수익률 (%) - 종료 시점 고정';

-- 인덱스 추가 (BROKEN 조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_recommendations_broken_return_pct
ON recommendations (broken_return_pct)
WHERE broken_return_pct IS NOT NULL;

