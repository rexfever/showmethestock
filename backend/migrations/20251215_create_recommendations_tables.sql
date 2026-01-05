-- 마이그레이션: v3 추천 시스템 리팩터링
-- 스캔(로그) vs 추천(이벤트) 분리
-- 날짜: 2025-12-15

-- 1. scan_results 테이블: 스캔 로그 (일별/런별 스캔 통과 종목 기록)
CREATE TABLE IF NOT EXISTS scan_results (
    id                  BIGSERIAL PRIMARY KEY,
    scan_date           DATE NOT NULL,
    scan_run_id        TEXT DEFAULT '',  -- 스캔 실행 ID (같은 날짜 여러 실행 구분)
    ticker              TEXT NOT NULL,
    name                TEXT,
    score               DOUBLE PRECISION,
    score_label         TEXT,
    strategy            TEXT,  -- 'v2_lite' 또는 'midterm'
    scanner_version     TEXT NOT NULL DEFAULT 'v3',
    indicators          JSONB,
    flags               JSONB,
    details             JSONB,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (scan_date, scan_run_id, ticker, scanner_version)
);

CREATE INDEX IF NOT EXISTS idx_scan_results_scan_date ON scan_results(scan_date);
CREATE INDEX IF NOT EXISTS idx_scan_results_ticker ON scan_results(ticker);
CREATE INDEX IF NOT EXISTS idx_scan_results_scanner_version ON scan_results(scanner_version);
CREATE INDEX IF NOT EXISTS idx_scan_results_date_version ON scan_results(scan_date, scanner_version);

COMMENT ON TABLE scan_results IS '스캔 로그: 일별/런별 스캔 통과 종목 기록 (사용자 의미 없음)';
COMMENT ON COLUMN scan_results.scan_run_id IS '스캔 실행 ID (같은 날짜 여러 실행 구분)';
COMMENT ON COLUMN scan_results.ticker IS '종목 코드';

-- 2. recommendations 테이블: 추천 이벤트 (anchor_date/anchor_close 고정 저장)
CREATE TABLE IF NOT EXISTS recommendations (
    id                  BIGSERIAL PRIMARY KEY,
    ticker              TEXT NOT NULL,
    name                TEXT,
    status              TEXT NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, WEAK_WARNING, BROKEN, ARCHIVED
    anchor_date         DATE NOT NULL,  -- 추천 기준 거래일 (고정, 재계산 금지)
    anchor_close        DOUBLE PRECISION NOT NULL,  -- 추천 기준 종가 (고정, 재계산 금지)
    anchor_price_type   TEXT DEFAULT 'CLOSE',  -- CLOSE 또는 ADJ_CLOSE
    anchor_source       TEXT DEFAULT 'KRX_EOD',  -- 데이터 소스
    strategy            TEXT,  -- 'v2_lite' 또는 'midterm'
    scanner_version     TEXT NOT NULL DEFAULT 'v3',
    score               DOUBLE PRECISION,
    score_label         TEXT,
    indicators          JSONB,
    flags               JSONB,
    details             JSONB,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    broken_at           TIMESTAMP WITH TIME ZONE,  -- BROKEN 전이 시각
    archived_at         TIMESTAMP WITH TIME ZONE,  -- ARCHIVED 전이 시각
    -- 동일 ticker는 동시 ACTIVE 1개만 (partial unique index)
    CONSTRAINT recommendations_status_check CHECK (status IN ('ACTIVE', 'WEAK_WARNING', 'BROKEN', 'ARCHIVED'))
);

-- 동일 ticker는 동시 ACTIVE 1개만 제약 (partial unique index)
CREATE UNIQUE INDEX IF NOT EXISTS idx_recommendations_ticker_active 
    ON recommendations(ticker) 
    WHERE status = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_recommendations_ticker ON recommendations(ticker);
CREATE INDEX IF NOT EXISTS idx_recommendations_status ON recommendations(status);
CREATE INDEX IF NOT EXISTS idx_recommendations_anchor_date ON recommendations(anchor_date);
CREATE INDEX IF NOT EXISTS idx_recommendations_scanner_version ON recommendations(scanner_version);
CREATE INDEX IF NOT EXISTS idx_recommendations_created_at ON recommendations(created_at);

COMMENT ON TABLE recommendations IS '추천 이벤트: anchor_date/anchor_close 고정 저장, 상태 단방향 전이';
COMMENT ON COLUMN recommendations.anchor_date IS '추천 기준 거래일 (고정, 재계산 금지)';
COMMENT ON COLUMN recommendations.anchor_close IS '추천 기준 종가 (고정, 재계산 금지)';
COMMENT ON COLUMN recommendations.status IS '상태: ACTIVE, WEAK_WARNING, BROKEN, ARCHIVED (단방향 전이)';

-- 3. recommendation_state_events 테이블: 상태 변경 이벤트 로그 (권장)
CREATE TABLE IF NOT EXISTS recommendation_state_events (
    id                  BIGSERIAL PRIMARY KEY,
    recommendation_id   BIGINT NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    from_status         TEXT,
    to_status           TEXT NOT NULL,
    reason              TEXT,  -- 상태 변경 이유
    metadata            JSONB,  -- 추가 메타데이터 (current_return, stop_loss 등)
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_state_events_recommendation_id 
    ON recommendation_state_events(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_state_events_to_status 
    ON recommendation_state_events(to_status);
CREATE INDEX IF NOT EXISTS idx_recommendation_state_events_created_at 
    ON recommendation_state_events(created_at);

COMMENT ON TABLE recommendation_state_events IS '추천 상태 변경 이벤트 로그 (감사 추적)';
COMMENT ON COLUMN recommendation_state_events.from_status IS '이전 상태';
COMMENT ON COLUMN recommendation_state_events.to_status IS '변경 후 상태';
COMMENT ON COLUMN recommendation_state_events.reason IS '상태 변경 이유';

-- 4. 함수: recommendations 업데이트 시 updated_at 자동 갱신
CREATE OR REPLACE FUNCTION update_recommendations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_recommendations_updated_at
    BEFORE UPDATE ON recommendations
    FOR EACH ROW
    EXECUTE FUNCTION update_recommendations_updated_at();

