-- 마이그레이션: scan_rank 테이블에 anchor 필드 추가
-- 추천 기준 종가(anchor_close)를 생성 시점에 저장하여 재계산 방지

-- anchor_date: 추천 기준 거래일 (YYYY-MM-DD)
-- anchor_close: 추천 기준 종가 (정수, KRW)
-- anchor_price_type: 가격 타입 ("CLOSE" 또는 "ADJ_CLOSE")
-- anchor_source: 데이터 소스 (예: "KRX_EOD", "vendor", "internal_cache")

DO $$
BEGIN
    -- anchor_date 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'scan_rank' AND column_name = 'anchor_date'
    ) THEN
        ALTER TABLE scan_rank ADD COLUMN anchor_date DATE;
    END IF;

    -- anchor_close 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'scan_rank' AND column_name = 'anchor_close'
    ) THEN
        ALTER TABLE scan_rank ADD COLUMN anchor_close DOUBLE PRECISION;
    END IF;

    -- anchor_price_type 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'scan_rank' AND column_name = 'anchor_price_type'
    ) THEN
        ALTER TABLE scan_rank ADD COLUMN anchor_price_type TEXT DEFAULT 'CLOSE';
    END IF;

    -- anchor_source 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'scan_rank' AND column_name = 'anchor_source'
    ) THEN
        ALTER TABLE scan_rank ADD COLUMN anchor_source TEXT DEFAULT 'KRX_EOD';
    END IF;
END $$;

-- 인덱스 추가 (anchor_date로 조회 최적화)
CREATE INDEX IF NOT EXISTS idx_scan_rank_anchor_date ON scan_rank(anchor_date);

-- 코멘트 추가 (문서화)
COMMENT ON COLUMN scan_rank.anchor_date IS '추천 기준 거래일 (장 마감 기준, Asia/Seoul 타임존)';
COMMENT ON COLUMN scan_rank.anchor_close IS '추천 기준 종가 (정수, KRW, anchor_date의 공식 종가)';
COMMENT ON COLUMN scan_rank.anchor_price_type IS '가격 타입: CLOSE 또는 ADJ_CLOSE';
COMMENT ON COLUMN scan_rank.anchor_source IS '데이터 소스: KRX_EOD, vendor, internal_cache 등';


