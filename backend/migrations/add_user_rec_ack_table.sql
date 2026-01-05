-- user_rec_ack 테이블 생성
-- 사용자별 추천 인스턴스 확인(ack) 정보 저장

CREATE TABLE IF NOT EXISTS user_rec_ack (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    rec_date            DATE NOT NULL,
    rec_code            TEXT NOT NULL,
    rec_scanner_version TEXT NOT NULL DEFAULT 'v1',
    ack_type            TEXT NOT NULL DEFAULT 'BROKEN_VIEWED',
    acked_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, rec_date, rec_code, rec_scanner_version, ack_type)
);

CREATE INDEX IF NOT EXISTS idx_user_rec_ack_user_id ON user_rec_ack(user_id);
CREATE INDEX IF NOT EXISTS idx_user_rec_ack_rec ON user_rec_ack(rec_date, rec_code, rec_scanner_version);
CREATE INDEX IF NOT EXISTS idx_user_rec_ack_type ON user_rec_ack(ack_type);

COMMENT ON TABLE user_rec_ack IS '사용자별 추천 인스턴스 확인(ack) 정보';
COMMENT ON COLUMN user_rec_ack.user_id IS '사용자 ID';
COMMENT ON COLUMN user_rec_ack.rec_date IS '추천 날짜 (scan_rank.date)';
COMMENT ON COLUMN user_rec_ack.rec_code IS '종목 코드 (scan_rank.code)';
COMMENT ON COLUMN user_rec_ack.rec_scanner_version IS '스캐너 버전 (scan_rank.scanner_version)';
COMMENT ON COLUMN user_rec_ack.ack_type IS '확인 타입 (BROKEN_VIEWED 등)';
COMMENT ON COLUMN user_rec_ack.acked_at IS '확인 시각';


