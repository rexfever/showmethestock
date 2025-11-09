-- Market Conditions table extension (draft) - 2025-11-09

ALTER TABLE market_conditions
    ADD COLUMN IF NOT EXISTS sentiment_score NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS trend_metrics JSONB,
    ADD COLUMN IF NOT EXISTS breadth_metrics JSONB,
    ADD COLUMN IF NOT EXISTS flow_metrics JSONB,
    ADD COLUMN IF NOT EXISTS sector_metrics JSONB,
    ADD COLUMN IF NOT EXISTS volatility_metrics JSONB,
    ADD COLUMN IF NOT EXISTS foreign_flow_label TEXT,
    ADD COLUMN IF NOT EXISTS volume_trend_label TEXT,
    ADD COLUMN IF NOT EXISTS adjusted_params JSONB,
    ADD COLUMN IF NOT EXISTS analysis_notes TEXT,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

UPDATE market_conditions
SET
    sentiment_score = COALESCE(sentiment_score, 0.00),
    adjusted_params = COALESCE(adjusted_params, '{}'::jsonb),
    trend_metrics = COALESCE(trend_metrics, '{}'::jsonb),
    breadth_metrics = COALESCE(breadth_metrics, '{}'::jsonb),
    flow_metrics = COALESCE(flow_metrics, '{}'::jsonb),
    sector_metrics = COALESCE(sector_metrics, '{}'::jsonb),
    volatility_metrics = COALESCE(volatility_metrics, '{}'::jsonb),
    foreign_flow_label = COALESCE(foreign_flow_label, foreign_flow),
    volume_trend_label = COALESCE(volume_trend_label, volume_trend),
    updated_at = NOW()
WHERE TRUE;

CREATE INDEX IF NOT EXISTS idx_market_conditions_date_desc
    ON market_conditions (date DESC);

CREATE INDEX IF NOT EXISTS idx_market_conditions_sentiment
    ON market_conditions (market_sentiment);
