-- market_conditions 테이블에 기관 수급 컬럼 추가

ALTER TABLE market_conditions
    ADD COLUMN IF NOT EXISTS institution_flow TEXT,
    ADD COLUMN IF NOT EXISTS institution_flow_label TEXT;

-- 기존 데이터에 기본값 설정
UPDATE market_conditions
SET
    institution_flow = COALESCE(institution_flow, 'neutral'),
    institution_flow_label = COALESCE(institution_flow_label, 'neutral')
WHERE institution_flow IS NULL OR institution_flow_label IS NULL;

-- 인덱스 추가 (선택사항)
CREATE INDEX IF NOT EXISTS idx_market_conditions_institution_flow
    ON market_conditions (institution_flow);

