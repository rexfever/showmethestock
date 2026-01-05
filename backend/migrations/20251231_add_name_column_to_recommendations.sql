-- recommendations 테이블에 name 컬럼 추가 (성능 최적화)
-- 종목명을 DB에 저장하여 매번 API 호출하지 않도록 함

ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS name TEXT;

CREATE INDEX IF NOT EXISTS idx_recommendations_name 
ON recommendations (name) 
WHERE name IS NOT NULL;

COMMENT ON COLUMN recommendations.name IS '종목명 (성능 최적화: API 호출 제거)';


