#!/bin/bash
# DB 데이터 확인 스크립트 (간단 버전)

# .env 파일에서 DATABASE_URL 읽기
if [ -f backend/.env ]; then
    export $(grep -v '^#' backend/.env | grep DATABASE_URL | xargs)
fi

# DATABASE_URL이 없으면 기본값 사용
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL 환경 변수가 설정되지 않았습니다."
    echo "   기본값 사용: postgresql://stockfinder@localhost/stockfinder"
    DATABASE_URL="postgresql://stockfinder@localhost/stockfinder"
fi

echo "🔍 DB 데이터 확인 중..."
echo "   연결: ${DATABASE_URL%%@*}@***"
echo ""

# PostgreSQL에 연결하여 쿼리 실행
psql "$DATABASE_URL" <<EOF
-- 전체 레코드 수
SELECT '전체 레코드 수' as info, COUNT(*)::text as value FROM scan_rank
UNION ALL
-- 실제 추천 종목 수
SELECT '실제 추천 종목 수 (NORESULT 제외)' as info, COUNT(*)::text as value FROM scan_rank WHERE code != 'NORESULT'
UNION ALL
-- anchor_close 있음
SELECT 'anchor_close 있음' as info, COUNT(*)::text as value FROM scan_rank WHERE code != 'NORESULT' AND anchor_close IS NOT NULL AND anchor_close > 0
UNION ALL
-- anchor_close 없음
SELECT 'anchor_close 없음' as info, COUNT(*)::text as value FROM scan_rank WHERE code != 'NORESULT' AND (anchor_close IS NULL OR anchor_close <= 0);

-- scanner_version별 통계
\echo ''
\echo '📊 scanner_version별 통계:'
SELECT 
    COALESCE(scanner_version, 'NULL') as version,
    COUNT(*)::text as total,
    COUNT(CASE WHEN code != 'NORESULT' THEN 1 END)::text as candidates,
    MIN(date)::text as min_date,
    MAX(date)::text as max_date
FROM scan_rank
GROUP BY scanner_version
ORDER BY scanner_version;

-- 최근 10일 데이터
\echo ''
\echo '📅 최근 10일 데이터:'
SELECT 
    date::text,
    COALESCE(scanner_version, 'NULL') as version,
    COUNT(*)::text as total,
    COUNT(CASE WHEN code != 'NORESULT' THEN 1 END)::text as candidates
FROM scan_rank
GROUP BY date, scanner_version
ORDER BY date DESC, scanner_version
LIMIT 20;

-- 2025-12-10 데이터
\echo ''
\echo '📅 2025-12-10 데이터:'
SELECT 
    code,
    name,
    COALESCE(scanner_version, 'NULL') as version,
    COALESCE(close_price::text, 'NULL') as close_price,
    COALESCE(anchor_close::text, 'NULL') as anchor_close
FROM scan_rank
WHERE date = '2025-12-10' AND code != 'NORESULT'
ORDER BY scanner_version, code
LIMIT 10;

-- 한국항공우주(047810) 데이터
\echo ''
\echo '📊 한국항공우주(047810) 데이터:'
SELECT 
    date::text,
    COALESCE(scanner_version, 'NULL') as version,
    COALESCE(close_price::text, 'NULL') as close_price,
    COALESCE(anchor_close::text, 'NULL') as anchor_close
FROM scan_rank
WHERE code = '047810'
ORDER BY date DESC
LIMIT 10;
EOF



