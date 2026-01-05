/* =========================================================
   recommendations 테이블에 status_changed_at 컬럼 추가
   상태 전이 시점을 명확히 기록하기 위한 컬럼
   ========================================================= */

-- status_changed_at 컬럼 추가 (KST 기준 저장)
ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMPTZ;

-- 기존 레코드의 status_changed_at 초기화
-- created_at을 기본값으로 사용 (초기 생성 시점)
UPDATE recommendations
SET status_changed_at = created_at
WHERE status_changed_at IS NULL;

-- 기본값 설정 (신규 레코드용)
ALTER TABLE recommendations
ALTER COLUMN status_changed_at SET DEFAULT NOW();

-- NOT NULL 제약 추가 (기본값 설정 후)
ALTER TABLE recommendations
ALTER COLUMN status_changed_at SET NOT NULL;

-- 인덱스 추가 (일일 집계 쿼리 성능 향상)
CREATE INDEX IF NOT EXISTS idx_recommendations_status_changed_at
ON recommendations (status_changed_at)
WHERE status_changed_at IS NOT NULL;

-- 인덱스 추가 (상태 + 시점 조합 쿼리)
CREATE INDEX IF NOT EXISTS idx_recommendations_status_changed_at_status
ON recommendations (status, status_changed_at)
WHERE status IN ('BROKEN', 'ARCHIVED');

COMMENT ON COLUMN recommendations.status_changed_at IS '상태 변경 시점 (KST 기준, status 값이 변경될 때만 갱신)';

