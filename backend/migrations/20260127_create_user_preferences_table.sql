-- user_preferences 테이블 생성
-- 사용자별 추천 방식 설정 저장

CREATE TABLE IF NOT EXISTS user_preferences (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
    recommendation_type TEXT NOT NULL DEFAULT 'daily',  -- 'daily' 또는 'conditional'
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT user_preferences_type_check CHECK (recommendation_type IN ('daily', 'conditional'))
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

COMMENT ON TABLE user_preferences IS '사용자별 추천 방식 설정';
COMMENT ON COLUMN user_preferences.user_id IS '사용자 ID';
COMMENT ON COLUMN user_preferences.recommendation_type IS '추천 방식: daily(일일 추천) 또는 conditional(조건 추천)';

