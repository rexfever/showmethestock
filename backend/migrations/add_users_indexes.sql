-- users 테이블 성능 최적화 인덱스 추가
-- 로그인 성능 개선을 위한 인덱스

-- provider + provider_id 복합 인덱스 (소셜 로그인 조회 최적화)
CREATE INDEX IF NOT EXISTS idx_users_provider_provider_id 
ON users(provider, provider_id);

-- provider_id 단일 인덱스 (provider_id만으로 조회하는 경우)
CREATE INDEX IF NOT EXISTS idx_users_provider_id 
ON users(provider_id);

-- is_active 인덱스 (활성 사용자 필터링)
CREATE INDEX IF NOT EXISTS idx_users_is_active 
ON users(is_active) WHERE is_active = true;




















