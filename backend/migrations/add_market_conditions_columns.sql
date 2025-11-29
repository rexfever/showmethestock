-- market_conditions 테이블에 누락된 컬럼 추가
-- 일별 등락률 및 미국 레짐 소스 데이터 저장용

-- 1. 누락된 컬럼 추가
ALTER TABLE market_conditions
    ADD COLUMN IF NOT EXISTS sentiment_score NUMERIC(5,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS institution_flow TEXT,
    ADD COLUMN IF NOT EXISTS institution_flow_label TEXT,
    ADD COLUMN IF NOT EXISTS trend_metrics JSONB DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS breadth_metrics JSONB DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS flow_metrics JSONB DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS sector_metrics JSONB DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS volatility_metrics JSONB DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS foreign_flow_label TEXT,
    ADD COLUMN IF NOT EXISTS volume_trend_label TEXT,
    ADD COLUMN IF NOT EXISTS adjusted_params JSONB DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS analysis_notes TEXT,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- 2. 미국 레짐 소스 데이터 컬럼 추가
ALTER TABLE market_conditions
    ADD COLUMN IF NOT EXISTS spy_return DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS qqq_return DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS vix_close DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS spy_close DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS qqq_close DOUBLE PRECISION;

-- 3. 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_market_conditions_date_desc
    ON market_conditions (date DESC);

CREATE INDEX IF NOT EXISTS idx_market_conditions_sentiment
    ON market_conditions (market_sentiment);

