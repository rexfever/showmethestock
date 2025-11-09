-- 장세 분석 검증용 테이블
CREATE TABLE IF NOT EXISTS market_analysis_validation (
    id SERIAL PRIMARY KEY,
    analysis_date DATE NOT NULL,
    analysis_time TIME NOT NULL,
    kospi_return DOUBLE PRECISION,
    kospi_close DOUBLE PRECISION,
    kospi_prev_close DOUBLE PRECISION,
    samsung_return DOUBLE PRECISION,
    samsung_close DOUBLE PRECISION,
    samsung_prev_close DOUBLE PRECISION,
    data_available BOOLEAN DEFAULT FALSE,
    data_complete BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(analysis_date, analysis_time)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_market_validation_date ON market_analysis_validation(analysis_date);
CREATE INDEX IF NOT EXISTS idx_market_validation_time ON market_analysis_validation(analysis_time);

COMMENT ON TABLE market_analysis_validation IS '장세 분석 데이터 확정 시점 검증용 테이블';
COMMENT ON COLUMN market_analysis_validation.analysis_date IS '분석 대상 날짜';
COMMENT ON COLUMN market_analysis_validation.analysis_time IS '분석 실행 시간 (15:31~15:40)';
COMMENT ON COLUMN market_analysis_validation.data_available IS 'API 데이터 조회 가능 여부';
COMMENT ON COLUMN market_analysis_validation.data_complete IS '당일 종가 데이터 완전성 여부';

