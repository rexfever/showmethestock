/**
 * V3 전용 날짜별 스캔 결과 섹션 컴포넌트
 * v3 케이스에 따라 장세 카드와 Empty State를 표시합니다.
 */
import StockCardV3 from './StockCardV3';
import V3MarketRegimeCard from './V3MarketRegimeCard';

/**
 * 휴장일 판단 함수
 * @returns {boolean} 현재가 휴장일(토/일)이면 true
 */
function isMarketClosedToday() {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0 = 일요일, 6 = 토요일
  return dayOfWeek === 0 || dayOfWeek === 6;
}

/**
 * 날짜 문자열(YYYYMMDD)이 오늘 날짜인지 확인
 * @param {string} dateStr - YYYYMMDD 형식 날짜 문자열
 * @returns {boolean} 오늘 날짜이면 true
 */
function isToday(dateStr) {
  if (!dateStr || dateStr.length !== 8) return false;
  try {
    const today = new Date();
    const todayStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`;
    return dateStr === todayStr;
  } catch (e) {
    return false;
  }
}

export default function V3DateSection({ date, stocks, marketCondition, v3CaseInfo, isLoading, onViewChart, onScrollToHistory, mockCaseType }) {
  // 날짜 포맷팅 (휴장 표시 포함)
  const formatDate = (dateStr, showHoliday = false) => {
    if (!dateStr || dateStr.length !== 8) return dateStr;
    try {
      const year = dateStr.slice(0, 4);
      const month = dateStr.slice(4, 6);
      const day = dateStr.slice(6, 8);
      const dateObj = new Date(`${year}-${month}-${day}`);
      const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
      const weekday = weekdays[dateObj.getDay()];
      const baseDate = `${year}년 ${parseInt(month)}월 ${parseInt(day)}일 (${weekday})`;
      return showHoliday ? `${baseDate} · 휴장` : baseDate;
    } catch (e) {
      return dateStr;
    }
  };

  // 오늘 날짜인지 확인
  const isTodayDate = isToday(date);
  // 오늘이 휴장일인지 확인
  const isClosedToday = isMarketClosedToday() && isTodayDate;
  
  const formattedDate = formatDate(date, isClosedToday);
  
  // v2와 동일한 제외 필터 적용 (프론트엔드 안전장치)
  const filterExcludedStocks = (stockList) => {
    if (!stockList) return [];
    
    // 제외 키워드 (v2와 동일)
    const inverseEtfKeywords = ["인버스", "레버리지", "2X", "3X"];
    const bondEtfKeywords = ["국채", "채권", "회사채", "머니마켓", "금리"];
    
    return stockList.filter(stock => {
      // NORESULT 제외
      if (!stock || !stock.ticker || stock.ticker === 'NORESULT') {
        return false;
      }
      
      // 종목명으로 ETF 필터링
      const stockName = stock.name || '';
      if (inverseEtfKeywords.some(keyword => stockName.includes(keyword))) {
        return false;
      }
      if (bondEtfKeywords.some(keyword => stockName.includes(keyword))) {
        return false;
      }
      
      return true;
    });
  };
  
  // NORESULT와 ETF를 제외한 실제 추천 종목만 카운트
  const actualStocks = filterExcludedStocks(stocks);
  const hasStocks = actualStocks.length > 0;
  
  // 개발용: mockCaseType이 있으면 강제 적용
  let effectiveV3CaseInfo = v3CaseInfo;
  if (mockCaseType && process.env.NODE_ENV === 'development') {
    const mockCases = {
      '1': {
        has_recommendations: true,
        active_engines: ["v2lite", "midterm"],
        scan_date: date.length === 8 ? `${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}` : date,
        engine_labels: { v2lite: "단기 반응형", midterm: "중기 추세형" }
      },
      '2': {
        has_recommendations: true,
        active_engines: ["midterm"],
        scan_date: date.length === 8 ? `${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}` : date,
        engine_labels: { v2lite: "단기 반응형", midterm: "중기 추세형" }
      },
      '3': {
        has_recommendations: true,
        active_engines: ["v2lite"],
        scan_date: date.length === 8 ? `${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}` : date,
        engine_labels: { v2lite: "단기 반응형", midterm: "중기 추세형" }
      },
      '4': {
        has_recommendations: false,
        active_engines: [],
        scan_date: date.length === 8 ? `${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}` : date,
        engine_labels: { v2lite: "단기 반응형", midterm: "중기 추세형" }
      }
    };
    effectiveV3CaseInfo = mockCases[mockCaseType];
  }
  
  // 케이스 D 판별 (둘 다 없음)
  // 실제 데이터가 있으면 v3CaseInfo.has_recommendations가 false여도 표시
  const isCaseD = effectiveV3CaseInfo && !effectiveV3CaseInfo.has_recommendations && actualStocks.length === 0;
  
  // 디버깅: 데이터 확인 (isCaseD 정의 이후)
  console.log(`[V3DateSection] ${date}:`, {
    stocksCount: stocks?.length || 0,
    actualStocksCount: actualStocks.length,
    hasStocks: hasStocks,
    v3CaseInfo: v3CaseInfo,
    has_recommendations: v3CaseInfo?.has_recommendations,
    isCaseD: isCaseD,
    stocks: stocks?.slice(0, 2) // 처음 2개만 로그
  });

  return (
    <div id={`date-section-${date}`} className="mb-6">
      {/* 날짜 헤더 */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-xl">📅</span>
              <h2 className="text-lg font-bold text-gray-900">{formattedDate}</h2>
            </div>
            <div className="text-sm text-gray-600">
              추천 종목: <span className="font-semibold text-blue-600">{actualStocks.length}개</span>
            </div>
          </div>
        </div>
        
        {/* 휴장일 안내 (오늘 날짜이고 휴장일일 때만 표시) */}
        {isClosedToday && (
          <div className="bg-gray-50 border-t border-gray-200 px-4 py-2">
            <div className="text-sm text-gray-600">
              시장이 열리지 않는 날입니다. 다음 거래일에 확인하세요.
            </div>
          </div>
        )}
        
        {/* 전역 컨텍스트 고정 문구 (모든 날짜 섹션에 표시) */}
        <div className="bg-blue-50 border-t border-blue-200 px-4 py-3">
          <div className="text-sm text-blue-800 leading-relaxed">
            <div className="font-medium mb-1">이 추천은 장 마감 후 기준으로 생성되었습니다.</div>
            <div>다음 거래일의 흐름을 기준으로 대응하세요.</div>
          </div>
        </div>
      </div>

      {/* 내용 */}
      {isLoading ? (
        <div className="p-4 text-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
          <p className="text-gray-500 text-sm mt-2">로딩 중...</p>
        </div>
      ) : isCaseD ? (
        // 케이스 D: 추천 없는 날 - 단일 안내 카드만 표시
        <div className="p-4">
          {/* V3 장세 카드 */}
          {effectiveV3CaseInfo && (
            <div className="mb-4">
              <V3MarketRegimeCard v3CaseInfo={effectiveV3CaseInfo} />
            </div>
          )}
          
          {/* 추천 없는 날 안내 카드 */}
          <div className="bg-white rounded-lg shadow-sm border-2 border-gray-200 p-6">
            {/* 상태 헤더 */}
            <div className="mb-4">
              <div className="text-lg font-bold text-gray-700 mb-2">
                오늘은 추천 종목이 없습니다
              </div>
            </div>
            
            {/* 설명 */}
            <div className="text-sm text-gray-600 leading-relaxed mb-3">
              장 마감 기준으로 조건을 만족한 종목이 없었습니다.
              <br />
              무리한 대응보다는 시장 흐름을 지켜보는 날입니다.
            </div>
          </div>
        </div>
      ) : (
        // 케이스 A/B/C: 추천 종목이 있는 경우
        <div className="p-4 space-y-4">
          {/* V3 장세 카드 */}
          {effectiveV3CaseInfo && (
            <V3MarketRegimeCard v3CaseInfo={effectiveV3CaseInfo} />
          )}
          
          {/* 추천 종목 리스트 - V3 전용 카드 사용 */}
          {actualStocks.length > 0 ? (
            actualStocks.map((stock, index) => {
              // 디버깅: stock 데이터 확인
              if (process.env.NODE_ENV === 'development' && index === 0) {
                console.log('[V3DateSection] First stock data:', stock);
              }
              
              if (!stock || !stock.ticker) {
                console.warn('[V3DateSection] Invalid stock item:', stock);
                return null;
              }
              
              return (
                <StockCardV3
                  key={stock.ticker || `stock-${index}`}
                  item={stock}
                  onViewChart={onViewChart}
                  isClosedToday={isClosedToday}
                />
              );
            })
          ) : (
            <div className="text-center py-8 text-gray-500">
              추천 종목이 없습니다.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
