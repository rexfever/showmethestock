-- DB 데이터 존재 유무 확인 SQL 쿼리

-- 1. 전체 레코드 수
SELECT COUNT(*) as total_records FROM scan_rank;

-- 2. 실제 추천 종목 수 (NORESULT 제외)
SELECT COUNT(*) as actual_candidates FROM scan_rank WHERE code != 'NORESULT';

-- 3. scanner_version별 통계
SELECT 
    scanner_version,
    COUNT(*) as total,
    COUNT(CASE WHEN code != 'NORESULT' THEN 1 END) as candidates,
    MIN(date) as min_date,
    MAX(date) as max_date
FROM scan_rank
GROUP BY scanner_version
ORDER BY scanner_version;

-- 4. 최근 10일 데이터
SELECT 
    date,
    scanner_version,
    COUNT(*) as total,
    COUNT(CASE WHEN code != 'NORESULT' THEN 1 END) as candidates
FROM scan_rank
GROUP BY date, scanner_version
ORDER BY date DESC, scanner_version
LIMIT 20;

-- 5. anchor_close 필드 통계
SELECT 
    COUNT(*) as total,
    COUNT(anchor_close) as has_anchor_close,
    COUNT(CASE WHEN anchor_close IS NULL OR anchor_close <= 0 THEN 1 END) as missing_anchor_close,
    ROUND(COUNT(anchor_close)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as coverage_pct
FROM scan_rank
WHERE code != 'NORESULT';

-- 6. 2025-12-10 데이터 확인
SELECT 
    code, name, scanner_version, 
    close_price, anchor_close, anchor_date, anchor_source
FROM scan_rank
WHERE date = '2025-12-10' AND code != 'NORESULT'
ORDER BY scanner_version, code
LIMIT 20;

-- 7. 한국항공우주(047810) 데이터 확인
SELECT 
    date, scanner_version, 
    close_price, anchor_close, anchor_date, anchor_source
FROM scan_rank
WHERE code = '047810'
ORDER BY date DESC
LIMIT 10;

-- 8. 날짜별 데이터 존재 여부 (최근 30일)
SELECT 
    date,
    COUNT(DISTINCT scanner_version) as versions,
    COUNT(*) as total_records,
    COUNT(CASE WHEN code != 'NORESULT' THEN 1 END) as candidates
FROM scan_rank
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date
ORDER BY date DESC;



