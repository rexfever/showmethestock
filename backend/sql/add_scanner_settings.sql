-- 스캐너 설정 테이블 추가
-- 생성일: 2025-11-21
-- 설명: 스캐너 버전 및 V2 활성화 여부를 DB에서 관리하기 위한 테이블

CREATE TABLE IF NOT EXISTS scanner_settings(
    id SERIAL PRIMARY KEY,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_by TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_scanner_settings_key ON scanner_settings(setting_key);

-- 기본값 설정
INSERT INTO scanner_settings (setting_key, setting_value, description)
VALUES 
    ('scanner_version', 'v1', '스캐너 버전 (v1 또는 v2)'),
    ('scanner_v2_enabled', 'false', '스캐너 V2 활성화 여부 (true 또는 false)')
ON CONFLICT (setting_key) DO NOTHING;

-- 테이블 코멘트
COMMENT ON TABLE scanner_settings IS '스캐너 설정 관리 테이블 - 스캐너 버전 및 V2 활성화 여부를 DB에서 관리';
COMMENT ON COLUMN scanner_settings.setting_key IS '설정 키 (예: scanner_version, scanner_v2_enabled)';
COMMENT ON COLUMN scanner_settings.setting_value IS '설정 값 (예: v1, v2, true, false)';
COMMENT ON COLUMN scanner_settings.description IS '설정 설명';
COMMENT ON COLUMN scanner_settings.updated_by IS '최종 수정자 이메일';
COMMENT ON COLUMN scanner_settings.updated_at IS '최종 수정 시간';
COMMENT ON COLUMN scanner_settings.created_at IS '생성 시간';

