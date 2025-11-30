import React from 'react';

const StockTable = ({ 
  scanResults, 
  sortBy, 
  onSortChange, 
  selectedDate, 
  addToPortfolio, 
  removeFromPortfolio, 
  portfolioItems 
}) => {
  const getReturnColor = (returnRate) => {
    if (returnRate > 0) return 'text-red-500';
    if (returnRate < 0) return 'text-blue-500';
    return 'text-gray-500';
  };

  const formatReturn = (returnData) => {
    if (!returnData) return 'N/A';
    const current = returnData.current_return || 0;
    const high = returnData.high_return || 0;
    const low = returnData.low_return || 0;
    return {
      current: current.toFixed(1),
      high: high.toFixed(1),
      low: low.toFixed(1)
    };
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">추천 종목</h3>
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">정렬:</label>
            <select
              value={sortBy}
              onChange={(e) => onSortChange(e.target.value)}
              className="text-sm border border-gray-300 rounded px-2 py-1"
            >
              <option value="price">현재가</option>
              <option value="score">점수</option>
              <option value="volume">거래량</option>
              <option value="change">등락률</option>
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                종목
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                현재가
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                등락률
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                거래량
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                점수
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                매매전략
              </th>
              {selectedDate && selectedDate !== new Date().toISOString().split('T')[0] && (
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  수익률 정보
                </th>
              )}
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                액션
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {scanResults.map((stock, index) => {
              const isInPortfolio = portfolioItems.has(stock.ticker);
              const returns = formatReturn(stock.returns);
              
              return (
                <tr key={`${stock.ticker}-${index}`} className="hover:bg-gray-50">
                  <td className="px-4 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{stock.name}</div>
                      <div className="text-sm text-gray-500">{stock.ticker}</div>
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                    {stock.close_price ? stock.close_price.toLocaleString() : 'N/A'}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm">
                    <span className={stock.change_rate > 0 ? 'text-red-500' : stock.change_rate < 0 ? 'text-blue-500' : 'text-gray-500'}>
                      {(() => {
                        const rate = stock.change_rate;
                        if (rate === null || rate === undefined) return 'N/A';
                        if (rate === 0) return '0%';
                        
                        // 백엔드에서 이미 퍼센트 형태로 반환됨 (0.57 = 0.57%)
                        // 안전장치: 매우 작은 소수 형태(0.0057)가 올 경우에만 변환
                        // 0.01 미만이고 0이 아닌 경우만 소수 형태로 간주
                        const displayRate = Math.abs(rate) < 0.01 && rate !== 0.0 ? rate * 100 : rate;
                        return `${rate > 0 ? '+' : ''}${displayRate.toFixed(2)}%`;
                      })()}
                    </span>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                    {stock.volume ? stock.volume.toLocaleString() : 'N/A'}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="text-sm font-medium text-gray-900">{stock.score}</div>
                      <div className="ml-2 w-16 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full" 
                          style={{ width: `${(stock.score / 15) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                    {stock.strategy || 'N/A'}
                  </td>
                  {selectedDate && selectedDate !== new Date().toISOString().split('T')[0] && (
                    <td className="px-4 py-4 whitespace-nowrap text-sm">
                      <div className="flex space-x-2">
                        <span className={`font-medium ${getReturnColor(parseFloat(returns.current))}`}>
                          {returns.current}%
                        </span>
                        <span className="text-gray-500">({returns.high}%/{returns.low}%)</span>
                      </div>
                    </td>
                  )}
                  <td className="px-4 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => {
                          const naverUrl = `https://finance.naver.com/item/main.naver?code=${stock.ticker}`;
                          window.open(naverUrl, '_blank');
                        }}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        📊 차트 & 기업정보
                      </button>
                      <button
                        onClick={() => isInPortfolio ? removeFromPortfolio(stock.ticker) : addToPortfolio(stock.ticker, stock.name)}
                        className={isInPortfolio ? "text-red-600 hover:text-red-900" : "text-green-600 hover:text-green-900"}
                      >
                        {isInPortfolio ? '❤️ 제거' : '❤️ 관심등록'}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StockTable;
