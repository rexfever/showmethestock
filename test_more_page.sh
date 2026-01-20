#!/bin/bash

echo "🚀 더보기 페이지 브라우저 테스트"
echo "=================================="
echo ""

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 결과 카운터
PASS=0
FAIL=0

# 1. 백엔드 서버 상태 확인
echo "📋 1. 백엔드 서버 상태 확인"
echo "-------------------------------------------"
BACKEND_STATUS=$(curl -s http://localhost:8010/health 2>&1)
if echo "$BACKEND_STATUS" | grep -q "healthy"; then
    echo -e "${GREEN}✅ 백엔드 서버 정상 실행 중${NC}"
    echo "   응답: $BACKEND_STATUS"
    ((PASS++))
else
    echo -e "${RED}❌ 백엔드 서버 미실행${NC}"
    ((FAIL++))
    exit 1
fi
echo ""

# 2. 프론트엔드 서버 상태 확인
echo "📋 2. 프론트엔드 서버 상태 확인"
echo "-------------------------------------------"
FRONTEND_STATUS=$(curl -s -I http://localhost:3000 2>&1 | head -1)
if echo "$FRONTEND_STATUS" | grep -q "200 OK"; then
    echo -e "${GREEN}✅ 프론트엔드 서버 정상 실행 중${NC}"
    echo "   응답: $FRONTEND_STATUS"
    ((PASS++))
else
    echo -e "${RED}❌ 프론트엔드 서버 미실행${NC}"
    ((FAIL++))
    exit 1
fi
echo ""

# 3. 바텀메뉴 설정 API 테스트
echo "📋 3. 바텀메뉴 설정 API 테스트"
echo "-------------------------------------------"
MENU_ITEMS=$(curl -s http://localhost:8010/bottom-nav-menu-items)
echo "API 응답:"
echo "$MENU_ITEMS" | python3 -m json.tool
echo ""

US_STOCKS=$(echo "$MENU_ITEMS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('us_stocks', False))")
echo "미국주식 메뉴 상태: $US_STOCKS"

if [ "$US_STOCKS" = "True" ]; then
    echo -e "${GREEN}✅ 미국주식 메뉴 활성화됨${NC}"
    ((PASS++))
else
    echo -e "${YELLOW}⚠️  미국주식 메뉴 비활성화됨${NC}"
    ((PASS++))
fi
echo ""

# 4. 더보기 페이지 접속 테스트
echo "📋 4. 더보기 페이지 접속 테스트"
echo "-------------------------------------------"
MORE_PAGE=$(curl -s http://localhost:3000/more)

if echo "$MORE_PAGE" | grep -q "더보기"; then
    echo -e "${GREEN}✅ 더보기 페이지 로드 성공${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ 더보기 페이지 로드 실패${NC}"
    ((FAIL++))
fi
echo ""

# 5. 초기화면 설정 표시 확인
echo "📋 5. 초기화면 설정 표시 확인"
echo "-------------------------------------------"

# Next.js는 클라이언트 사이드 렌더링이므로 초기 HTML에는 없을 수 있음
# JavaScript가 실행된 후에 표시됨
echo "⚠️  Next.js 클라이언트 사이드 렌더링으로 인해"
echo "   초기 HTML에서는 확인 불가능"
echo "   실제 브라우저에서 확인 필요"
echo ""

# 6. API 엔드포인트 테스트
echo "📋 6. 관련 API 엔드포인트 테스트"
echo "-------------------------------------------"

# 6.1 바텀메뉴 링크 설정
echo "6.1 바텀메뉴 링크 설정 API"
BOTTOM_NAV_LINK=$(curl -s http://localhost:8010/bottom-nav-link)
echo "   응답: $BOTTOM_NAV_LINK"
if echo "$BOTTOM_NAV_LINK" | grep -q "link_type"; then
    echo -e "   ${GREEN}✅ API 정상${NC}"
    ((PASS++))
else
    echo -e "   ${RED}❌ API 오류${NC}"
    ((FAIL++))
fi
echo ""

# 6.2 바텀메뉴 노출 설정
echo "6.2 바텀메뉴 노출 설정 API"
BOTTOM_NAV_VISIBLE=$(curl -s http://localhost:8010/bottom-nav-visible)
echo "   응답: $BOTTOM_NAV_VISIBLE"
if echo "$BOTTOM_NAV_VISIBLE" | grep -q "is_visible"; then
    echo -e "   ${GREEN}✅ API 정상${NC}"
    ((PASS++))
else
    echo -e "   ${RED}❌ API 오류${NC}"
    ((FAIL++))
fi
echo ""

# 7. 테스트 결과 요약
echo "=================================="
echo "📊 테스트 결과 요약"
echo "=================================="
echo -e "${GREEN}통과: $PASS${NC}"
echo -e "${RED}실패: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ 모든 테스트 통과!${NC}"
    echo ""
    echo "🌐 브라우저에서 직접 확인:"
    echo "   http://localhost:3000/more"
    echo ""
    echo "📝 확인 사항:"
    if [ "$US_STOCKS" = "True" ]; then
        echo "   - 초기화면 설정이 표시되어야 함"
        echo "   - 한국주식추천/미국주식추천 옵션 표시"
    else
        echo "   - 초기화면 설정이 숨겨져야 함"
    fi
    exit 0
else
    echo -e "${RED}❌ 일부 테스트 실패${NC}"
    exit 1
fi
