import React from 'react';

const MarketGuide = ({ marketGuide }) => {
  if (!marketGuide) return null;

  const getConditionIcon = (condition) => {
    switch (condition) {
      case '강세': return '🚀';
      case '상승': return '📈';
      case '중립': return '⚖️';
      case '약세': return '⚠️';
      case '급락': return '🔴';
      default: return '📊';
    }
  };

  const getConditionColor = (condition) => {
    switch (condition) {
      case '강세': return 'bg-green-50 border-green-200 text-green-700';
      case '상승': return 'bg-blue-50 border-blue-200 text-blue-700';
      case '중립': return 'bg-yellow-50 border-yellow-200 text-yellow-700';
      case '약세': return 'bg-orange-50 border-orange-200 text-orange-700';
      case '급락': return 'bg-red-50 border-red-200 text-red-700';
      default: return 'bg-gray-50 border-gray-200 text-gray-700';
    }
  };

  return (
    <div className={`bg-white rounded-lg shadow-sm border p-4 ${getConditionColor(marketGuide.market_condition)}`}>
      <span className="text-sm">
        {getConditionIcon(marketGuide.market_condition)} {marketGuide.guide_message}
      </span>
    </div>
  );
};

export default MarketGuide;