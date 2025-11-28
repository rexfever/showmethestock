/**
 * 날짜별 스캔 결과 섹션 컴포넌트
 */
import StockCardV2 from './StockCardV2';
import MarketRegimeCard from './MarketRegimeCard';

export default function DateSection({ date, stocks, marketCondition, isLoading, onViewChart }) {
  // 날짜 포맷팅
  const formatDate = (dateStr) => {
    if (!dateStr || dateStr.length !== 8) return dateStr;
    try {
      const year = dateStr.slice(0, 4);
      const month = dateStr.slice(4, 6);
      const day = dateStr.slice(6, 8);
      const dateObj = new Date(`${year}-${month}-${day}`);
      const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
      const weekday = weekdays[dateObj.getDay()];
      return `${year}년 ${parseInt(month)}월 ${parseInt(day)}일 (${weekday})`;
    } catch (e) {
      return dateStr;
    }
  };

  const formattedDate = formatDate(date);
  const hasStocks = stocks && stocks.length > 0;

  return (
    <div className="mb-6">
      {/* 날짜 헤더 */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-xl">📅</span>
            <h2 className="text-lg font-bold text-gray-900">{formattedDate}</h2>
          </div>
          <div className="text-sm text-gray-600">
            추천 종목: <span className="font-semibold text-blue-600">{hasStocks ? stocks.length : 0}개</span>
          </div>
        </div>
      </div>

      {/* 내용 */}
      {isLoading ? (
        <div className="p-4 text-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
          <p className="text-gray-500 text-sm mt-2">로딩 중...</p>
        </div>
      ) : !hasStocks ? (
        // 추천 종목이 없는 경우
        <div className="p-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
            <p className="text-gray-600 text-lg mb-2">추천 종목이 없습니다</p>
            <p className="text-gray-400 text-sm mb-4">
              현재 시장 조건에서 매칭되는 종목이 없습니다.
            </p>
            {marketCondition && (
              <div className="mt-4">
                <MarketRegimeCard marketCondition={marketCondition} />
              </div>
            )}
          </div>
        </div>
      ) : (
        // 추천 종목이 있는 경우
        <div className="p-4 space-y-4">
          {marketCondition && (
            <div className="mb-4">
              <MarketRegimeCard marketCondition={marketCondition} />
            </div>
          )}
          {stocks.map((stock, index) => (
            <StockCardV2
              key={stock.ticker || index}
              item={stock}
              onViewChart={onViewChart}
            />
          ))}
        </div>
      )}
    </div>
  );
}

