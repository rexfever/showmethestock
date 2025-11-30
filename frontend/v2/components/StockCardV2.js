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
    current_return,
    returns = {}
  } = item;
  
  // returns 객체에서 max_return, min_return 추출
  const max_return = returns.max_return || (current_return > 0 ? current_return : 0);
  const min_return = returns.min_return || (current_return < 0 ? current_return : 0);

  // 전략별 색상 및 아이콘
  const strategyConfig = {
    스윙: { color: 'blue', icon: '⚡', desc: '단기 매매 (3~10일)' },
    포지션: { color: 'green', icon: '📈', desc: '중기 추세 추종 (2주~3개월)' },
    장기: { color: 'purple', icon: '🌱', desc: '장기 투자 (3개월 이상)' },
    관찰: { color: 'gray', icon: '⏳', desc: '관심 종목 (매수 대기)' }
  };

  const strategyInfo = strategyConfig[strategy] || strategyConfig.관찰;
  
  // Tailwind 동적 클래스 문제 해결: 전략별 명시적 클래스명 매핑
  const strategyClassName = {
    '스윙': 'bg-blue-100 text-blue-700',
    '포지션': 'bg-green-100 text-green-700',
    '장기': 'bg-purple-100 text-purple-700',
    '관찰': 'bg-gray-100 text-gray-700'
  }[strategy] || 'bg-gray-100 text-gray-700';

  // 평가 레이블 색상
  const scoreLabelConfig = {
    '강력 추천': { color: 'red', icon: '🔥' },
    '강한 매수': { color: 'red', icon: '🔥' },  // 백엔드 호환
    '추천': { color: 'orange', icon: '⭐' },
    '매수 후보': { color: 'orange', icon: '⭐' },  // 백엔드 호환
    '관심 종목': { color: 'yellow', icon: '👀' },
    '후보 종목': { color: 'gray', icon: '📋' }
  };

  // 백엔드 label을 프론트엔드 label로 매핑
  const normalizedLabel = score_label === '강한 매수' ? '강력 추천' :
                          score_label === '매수 후보' ? '추천' :
                          score_label;
  
  const labelInfo = scoreLabelConfig[normalizedLabel] || scoreLabelConfig['후보 종목'];
  
  // Tailwind 동적 클래스 문제 해결: 명시적 클래스명 매핑
  const labelClassName = {
    '강력 추천': 'bg-red-100 text-red-700',
    '강한 매수': 'bg-red-100 text-red-700',
    '추천': 'bg-orange-100 text-orange-700',
    '매수 후보': 'bg-orange-100 text-orange-700',
    '관심 종목': 'bg-yellow-100 text-yellow-700',
    '후보 종목': 'bg-gray-100 text-gray-700'
  }[normalizedLabel] || 'bg-gray-100 text-gray-700';

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
            {(() => {
              const rate = change_rate;
              if (rate === null || rate === undefined) return '데이터 없음';
              if (rate === 0) return '0%';
              
              // 백엔드에서 이미 퍼센트 형태로 반환됨 (0.57 = 0.57%)
              // 안전장치: 매우 작은 소수 형태(0.0057)가 올 경우에만 변환
              // 0.01 미만이고 0이 아닌 경우만 소수 형태로 간주
              const displayRate = Math.abs(rate) < 0.01 && rate !== 0.0 ? rate * 100 : rate;
              return `${rate > 0 ? '+' : ''}${displayRate.toFixed(2)}%`;
            })()}
          </div>
        </div>
      </div>

      {/* 점수 및 평가 */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <div className="flex flex-col">
            <div className="text-2xl font-bold text-blue-600">
              {score.toFixed(1)}점
            </div>
            <div className="text-xs text-gray-500">
              만점: 15점
            </div>
          </div>
          <span 
            className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${labelClassName}`}
            title={
              normalizedLabel === '강력 추천' ? '점수 10점 이상 - 강한 매수 신호' :
              normalizedLabel === '추천' ? '점수 8점 이상 - 매수 후보' :
              normalizedLabel === '관심 종목' ? '점수 6점 이상 - 관심 종목' :
              '점수 6점 미만 - 후보 종목'
            }
          >
            {labelInfo.icon} {normalizedLabel}
          </span>
        </div>
      </div>

      {/* 전략 배지 */}
      <div className="flex items-center space-x-2">
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${strategyClassName}`}>
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
      {recommended_date && recommended_price && current_return !== undefined && current_return !== null && (
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
            {/* 목표 달성 여부 및 손절 기준 표시 */}
            {targetProfit && (
              (() => {
                const targetReturn = parseFloat(targetProfit);
                const stopLossValue = stopLoss ? parseFloat(stopLoss) : null;
                
                // 목표 달성 여부 (현재 수익률 기준)
                const isAchieved = current_return >= targetReturn;
                
                // 목표 달성 후 수익률 감소 여부 (최고 수익률이 목표를 넘었지만 현재는 낮음)
                const wasAchievedButDeclined = max_return >= targetReturn && current_return < targetReturn;
                
                // 손절 기준 도달 여부
                const isStopLossReached = stopLossValue && current_return <= stopLossValue;
                
                // 최고 수익률과 현재 수익률 비교
                const hasDeclinedFromPeak = max_return > current_return && max_return >= targetReturn;
                const declineFromPeak = hasDeclinedFromPeak ? (max_return - current_return) : 0;
                
                const progress = Math.min((current_return / targetReturn) * 100, 100);
                const excessReturn = isAchieved ? (current_return - targetReturn) : 0;
                
                return (
                  <div className="mt-3 pt-3 border-t border-blue-200">
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="text-gray-600">목표 수익률: {targetReturn}%</span>
                      <span className={
                        isStopLossReached ? 'text-red-600 font-semibold' :
                        wasAchievedButDeclined ? 'text-orange-600 font-semibold' :
                        isAchieved ? 'text-green-600 font-semibold' : 
                        'text-gray-500'
                      }>
                        {isStopLossReached 
                          ? `⚠️ 손절 기준 도달 (${current_return.toFixed(2)}%)`
                          : wasAchievedButDeclined
                          ? `⚠️ 목표 달성했으나 수익률 하락 (최고 ${max_return.toFixed(2)}% → 현재 ${current_return.toFixed(2)}%)`
                          : isAchieved 
                          ? `✅ 목표 달성${excessReturn > 0 ? ` (+${excessReturn.toFixed(2)}% 초과)` : ''}${hasDeclinedFromPeak ? ` (최고 ${max_return.toFixed(2)}%에서 ${declineFromPeak.toFixed(2)}% 하락)` : ''}`
                          : `목표까지 ${(targetReturn - current_return).toFixed(2)}%`}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 relative">
                      <div 
                        className={`h-2 rounded-full transition-all ${
                          isStopLossReached ? 'bg-red-500' :
                          wasAchievedButDeclined ? 'bg-orange-500' :
                          isAchieved ? 'bg-green-500' : 
                          'bg-blue-500'
                        }`}
                        style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }}
                      />
                      {isAchieved && excessReturn > 0 && !hasDeclinedFromPeak && (
                        <div className="absolute top-0 right-0 h-2 w-2 bg-yellow-400 rounded-full animate-pulse" 
                             style={{ right: `${Math.min(100 - (targetReturn / current_return * 100), 0)}%` }}
                        />
                      )}
                    </div>
                    {/* 최고 수익률 정보 (목표 달성했지만 하락한 경우) */}
                    {wasAchievedButDeclined && (
                      <div className="mt-2 text-xs text-orange-600 font-medium">
                        ⚠️ 최고 수익률 {max_return.toFixed(2)}%에서 {declineFromPeak.toFixed(2)}% 하락
                      </div>
                    )}
                    {isAchieved && excessReturn > 0 && !hasDeclinedFromPeak && (
                      <div className="mt-1 text-xs text-yellow-600 font-medium">
                        🎉 목표 대비 {((current_return / targetReturn - 1) * 100).toFixed(0)}% 초과 달성!
                      </div>
                    )}
                    {isStopLossReached && stopLossValue && (
                      <div className="mt-2 text-xs text-red-600 font-medium">
                        🛑 손절 기준({stopLossValue}%) 도달 - 매도 고려 권장
                      </div>
                    )}
                  </div>
                );
              })()
            )}
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


