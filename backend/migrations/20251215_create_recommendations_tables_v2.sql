/* =========================================================
   v3 추천 시스템 - 1단계 DB 스키마 (Postgres)
   ========================================================= */

-- UUID 확장 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid() 사용

/* -------------------------------
   1. 스캔 로그 (scan_results)
   ------------------------------- */
CREATE TABLE IF NOT EXISTS scan_results (
  scan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL,
  scanned_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  ticker TEXT NOT NULL,

  passed BOOLEAN NOT NULL,
  reason_codes TEXT[] NOT NULL,
  signals_raw JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scan_results_run
  ON scan_results (run_id);

CREATE INDEX IF NOT EXISTS idx_scan_results_ticker
  ON scan_results (ticker);

CREATE INDEX IF NOT EXISTS idx_scan_results_scanned_at
  ON scan_results (scanned_at);

COMMENT ON TABLE scan_results IS '스캔 로그: 일별/런별 스캔 통과 종목 기록 (사용자 의미 없음)';
COMMENT ON COLUMN scan_results.run_id IS '스캔 실행 ID (같은 날짜 여러 실행 구분)';
COMMENT ON COLUMN scan_results.ticker IS '종목 코드';
COMMENT ON COLUMN scan_results.passed IS '스캔 통과 여부';
COMMENT ON COLUMN scan_results.reason_codes IS '통과/실패 이유 코드 배열';
COMMENT ON COLUMN scan_results.signals_raw IS '원시 신호 데이터 (JSONB)';

/* -----------------------------------
   2. 추천 이벤트 (recommendations)
   ----------------------------------- */
CREATE TABLE IF NOT EXISTS recommendations (
  recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  ticker TEXT NOT NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- 추천 기준점 (불변)
  anchor_date DATE NOT NULL,
  anchor_close INTEGER NOT NULL,
  anchor_price_type TEXT NOT NULL
    CHECK (anchor_price_type = 'CLOSE'),
  anchor_source TEXT NOT NULL,

  -- 상태
  status TEXT NOT NULL
    CHECK (status IN (
      'ACTIVE',
      'WEAK_WARNING',
      'BROKEN',
      'ARCHIVED',
      'REPLACED'
    )),

  -- 대체 관계
  replaces_recommendation_id UUID NULL,
  replaced_by_recommendation_id UUID NULL,

  -- 재진입 제어
  cooldown_until DATE NULL,

  -- 추가 메타데이터 (하위 호환성)
  strategy TEXT,  -- 'v2_lite' 또는 'midterm'
  scanner_version TEXT NOT NULL DEFAULT 'v3',
  score DOUBLE PRECISION,
  score_label TEXT,
  indicators JSONB,
  flags JSONB,
  details JSONB,
  broken_at TIMESTAMPTZ,
  archived_at TIMESTAMPTZ
);

/* -------------------------------------------------
   3. ticker 당 ACTIVE 추천 1개만 허용 (핵심 제약)
   ------------------------------------------------- */
CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_recommendation_per_ticker
ON recommendations (ticker)
WHERE status = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_recommendations_ticker
  ON recommendations (ticker);

CREATE INDEX IF NOT EXISTS idx_recommendations_status
  ON recommendations (status);

CREATE INDEX IF NOT EXISTS idx_recommendations_anchor_date
  ON recommendations (anchor_date);

CREATE INDEX IF NOT EXISTS idx_recommendations_scanner_version
  ON recommendations (scanner_version);

CREATE INDEX IF NOT EXISTS idx_recommendations_created_at
  ON recommendations (created_at);

CREATE INDEX IF NOT EXISTS idx_recommendations_cooldown_until
  ON recommendations (cooldown_until)
  WHERE cooldown_until IS NOT NULL;

COMMENT ON TABLE recommendations IS '추천 이벤트: anchor_date/anchor_close 고정 저장, 상태 단방향 전이';
COMMENT ON COLUMN recommendations.anchor_date IS '추천 기준 거래일 (고정, 재계산 금지)';
COMMENT ON COLUMN recommendations.anchor_close IS '추천 기준 종가 (고정, 재계산 금지, INTEGER 단위: 원)';
COMMENT ON COLUMN recommendations.status IS '상태: ACTIVE, WEAK_WARNING, BROKEN, ARCHIVED, REPLACED (단방향 전이)';
COMMENT ON COLUMN recommendations.replaces_recommendation_id IS '이 추천이 대체한 추천 ID';
COMMENT ON COLUMN recommendations.replaced_by_recommendation_id IS '이 추천을 대체한 추천 ID';
COMMENT ON COLUMN recommendations.cooldown_until IS '재진입 쿨다운 종료일 (BROKEN 후)';

/* -------------------------------------------------
   4. 추천 상태 전이 로그 (권장)
   ------------------------------------------------- */
CREATE TABLE IF NOT EXISTS recommendation_state_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  recommendation_id UUID NOT NULL
    REFERENCES recommendations (recommendation_id)
    ON DELETE CASCADE,

  from_status TEXT NULL,
  to_status TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  reason_text TEXT,
  metadata JSONB,

  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reco_state_events_reco
  ON recommendation_state_events (recommendation_id);

CREATE INDEX IF NOT EXISTS idx_reco_state_events_to_status
  ON recommendation_state_events (to_status);

CREATE INDEX IF NOT EXISTS idx_reco_state_events_occurred_at
  ON recommendation_state_events (occurred_at);

COMMENT ON TABLE recommendation_state_events IS '추천 상태 변경 이벤트 로그 (감사 추적)';
COMMENT ON COLUMN recommendation_state_events.from_status IS '이전 상태';
COMMENT ON COLUMN recommendation_state_events.to_status IS '변경 후 상태';
COMMENT ON COLUMN recommendation_state_events.reason_code IS '상태 변경 이유 코드';
COMMENT ON COLUMN recommendation_state_events.reason_text IS '상태 변경 이유 텍스트';

/* -------------------------------------------------
   5. 함수: recommendations 업데이트 시 updated_at 자동 갱신
   ------------------------------------------------- */
CREATE OR REPLACE FUNCTION update_recommendations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_recommendations_updated_at ON recommendations;
CREATE TRIGGER trigger_update_recommendations_updated_at
    BEFORE UPDATE ON recommendations
    FOR EACH ROW
    EXECUTE FUNCTION update_recommendations_updated_at();

