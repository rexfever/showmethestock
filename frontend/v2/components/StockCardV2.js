/**
 * Scanner V2용 종목 카드 컴포넌트
 * 일반 투자자에게 실용적이고 이해하기 쉬운 정보를 제공합니다.
 */
export default function StockCardV2({ item, onViewChart }) {
  const {
    ticker,
    name,
    score,
    score_label,
    strategy,
    current_price,
    change_rate,
    flags = {},
    market,
    recommended_price,
    recommended_date,
    current_return
  } = item;

  // 전략별 색상 및 아이콘
  const strategyConfig = {
    스윙: { color: 'blue', icon: '⚡', desc: '단기 매매 (3~10일)' },
    포지션: { color: 'green', icon: '📈', desc: '중기 추세 추종 (2주~3개월)' },
    장기: { color: 'purple', icon: '🌱', desc: '장기 투자 (3개월 이상)' },
    관찰: { color: 'gray', icon: '👀', desc: '관심 종목 (매수 대기)' }
  };

  const strategyInfo = strategyConfig[strategy] || strategyConfig.관찰;

  // 평가 레이블 색상
  const scoreLabelConfig = {
    '강력 추천': { color: 'red', icon: '🔥' },
    '추천': { color: 'orange', icon: '⭐' },
    '관심 종목': { color: 'yellow', icon: '👀' },
    '후보 종목': { color: 'gray', icon: '📋' }
  };

  const labelInfo = scoreLabelConfig[score_label] || scoreLabelConfig['후보 종목'];

  // 매매 가이드 정보
  const targetProfit = flags.target_profit ? (flags.target_profit * 100).toFixed(1) : null;
  const stopLoss = flags.stop_loss ? (flags.stop_loss * 100).toFixed(1) : null;
  const holdingPeriod = flags.holding_period || null;

  // 전략별 설명
  const getStrategyDescription = (strategy) => {
    const descriptions = {
      스윙: '골든크로스와 거래량 확대 등 모멘텀 지표가 강해 단기 매매에 적합합니다.',
      포지션: 'TEMA, OBV 등 추세 지표가 강해 중기 추세를 따라 수익을 실현할 수 있습니다.',
      장기: '기본 신호와 추세 지표가 있어 안정적인 장기 수익을 목표로 합니다.',
      관찰: '현재 점수가 낮아 매수 시점을 기다리는 것을 권장합니다.'
    };
    return descriptions[strategy] || '';
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-4">
      {/* 종목 헤더 */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-bold text-gray-900 truncate">
              {name}
            </h3>
          </div>
          <div className="flex items-center space-x-2 mt-1">
            <span className="text-xs text-gray-500 font-mono">
              {ticker}
            </span>
            {market && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                {market}
              </span>
            )}
          </div>
        </div>
        <div className="text-right ml-4">
          <div className="text-2xl font-bold text-gray-900">
            {current_price > 0 ? `${current_price.toLocaleString()}원` : '데이터 없음'}
          </div>
          <div className={`text-sm font-semibold ${change_rate > 0 ? 'text-red-500' : change_rate < 0 ? 'text-blue-500' : 'text-gray-500'}`}>
            {change_rate !== 0 ? `${change_rate > 0 ? '+' : ''}${change_rate.toFixed(2)}%` : '데이터 없음'}
          </div>
        </div>
      </div>

      {/* 점수 및 평가 */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <div className="text-2xl font-bold text-blue-600">
            {score.toFixed(1)}점
          </div>
          <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-${labelInfo.color}-100 text-${labelInfo.color}-700`}>
            {labelInfo.icon} {score_label}
          </span>
        </div>
      </div>

      {/* 전략 배지 */}
      <div className="flex items-center space-x-2">
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-${strategyInfo.color}-100 text-${strategyInfo.color}-700`}>
          {strategyInfo.icon} {strategy}
        </span>
      </div>

      {/* 매매 가이드 */}
      {targetProfit && stopLoss && holdingPeriod && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">💡</span>
            <h4 className="font-semibold text-blue-900">매매 가이드</h4>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">목표 수익률:</span>
              <span className="font-bold text-green-600">+{targetProfit}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">손절 기준:</span>
              <span className="font-bold text-red-600">{stopLoss}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">보유 기간:</span>
              <span className="font-bold text-blue-600">{holdingPeriod}</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-blue-200">
            <p className="text-xs text-blue-700">
              {getStrategyDescription(strategy)}
            </p>
          </div>
        </div>
      )}

      {/* 추천일 대비 수익률 표시 */}
      {recommended_date && recommended_price && current_return !== undefined && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">📊</span>
            <h4 className="font-semibold text-blue-900">추천일 대비 수익률</h4>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">추천일:</span>
              <span className="font-medium text-gray-800">
                {recommended_date ? `${recommended_date.slice(0,4)}년 ${recommended_date.slice(4,6)}월 ${recommended_date.slice(6,8)}일` : '-'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">추천가:</span>
              <span className="font-medium text-gray-800">
                {recommended_price ? `${recommended_price.toLocaleString()}원` : '-'}
              </span>
            </div>
            <div className="flex justify-between items-center pt-2 border-t border-blue-200">
              <span className="text-gray-600 font-semibold">현재 수익률:</span>
              <span className={`text-lg font-bold ${current_return > 0 ? 'text-red-500' : current_return < 0 ? 'text-blue-500' : 'text-gray-500'}`}>
                {current_return > 0 ? '+' : ''}{current_return.toFixed(2)}%
                {current_return > 0 ? ' 📈' : current_return < 0 ? ' 📉' : ''}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 액션 버튼 */}
      <div className="flex items-center justify-between pt-3 border-t">
        <button 
          className="text-blue-500 hover:text-blue-700 text-sm font-medium"
          onClick={() => onViewChart(ticker)}
        >
          📊 차트 & 기업정보
        </button>
      </div>
    </div>
  );
}


