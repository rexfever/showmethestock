-- market_regime_daily 테이블 생성 (Regime v3/v4 지원)
-- 이 스크립트는 테이블이 없을 경우 생성하고, v4 필드를 추가합니다.

-- 1. 기본 테이블 생성 (v3 구조)
CREATE TABLE IF NOT EXISTS market_regime_daily (
    date DATE PRIMARY KEY,
    us_prev_sentiment VARCHAR(20) NOT NULL DEFAULT 'neutral',
    kr_sentiment VARCHAR(20) NOT NULL DEFAULT 'neutral', 
    us_preopen_sentiment VARCHAR(20) NOT NULL DEFAULT 'none',
    final_regime VARCHAR(20) NOT NULL DEFAULT 'neutral',
    us_metrics JSONB,
    kr_metrics JSONB,
    us_preopen_metrics JSONB,
    run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version VARCHAR(20) NOT NULL DEFAULT 'regime_v3'
);

-- 2. Regime v4 필드 추가
ALTER TABLE market_regime_daily 
    ADD COLUMN IF NOT EXISTS us_futures_score FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS us_futures_regime VARCHAR(20) DEFAULT 'neutral',
    ADD COLUMN IF NOT EXISTS dxy FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- 3. 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_market_regime_daily_date ON market_regime_daily(date);
CREATE INDEX IF NOT EXISTS idx_market_regime_daily_final_regime ON market_regime_daily(final_regime);
CREATE INDEX IF NOT EXISTS idx_market_regime_daily_version ON market_regime_daily(version);
CREATE INDEX IF NOT EXISTS idx_market_regime_daily_us_futures_regime ON market_regime_daily(us_futures_regime);
CREATE INDEX IF NOT EXISTS idx_market_regime_daily_updated_at ON market_regime_daily(updated_at);

-- 4. 테이블 코멘트
COMMENT ON TABLE market_regime_daily IS '일별 레짐 분석 결과 저장 테이블 (Regime v3/v4)';
COMMENT ON COLUMN market_regime_daily.date IS '분석 날짜';
COMMENT ON COLUMN market_regime_daily.us_prev_sentiment IS '미국 전일 센티먼트';
COMMENT ON COLUMN market_regime_daily.kr_sentiment IS '한국 센티먼트';
COMMENT ON COLUMN market_regime_daily.us_preopen_sentiment IS '미국 장전 센티먼트';
COMMENT ON COLUMN market_regime_daily.final_regime IS '최종 레짐 (bull/neutral/bear/crash)';
COMMENT ON COLUMN market_regime_daily.us_metrics IS '미국 시장 지표 (JSONB)';
COMMENT ON COLUMN market_regime_daily.kr_metrics IS '한국 시장 지표 (JSONB)';
COMMENT ON COLUMN market_regime_daily.us_preopen_metrics IS '미국 장전 지표 (JSONB)';
COMMENT ON COLUMN market_regime_daily.version IS '레짐 분석 버전 (regime_v3, regime_v4)';
COMMENT ON COLUMN market_regime_daily.us_futures_score IS '미국 선물 점수 (v4)';
COMMENT ON COLUMN market_regime_daily.us_futures_regime IS '미국 선물 레짐 (v4)';
COMMENT ON COLUMN market_regime_daily.dxy IS '달러 인덱스 (v4)';




































