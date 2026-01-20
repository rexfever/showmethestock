/**
 * Scanner V2용 종목 카드 컴포넌트
 * 일반 투자자에게 실용적이고 이해하기 쉬운 정보를 제공합니다.
 */
import { memo } from 'react';

function StockCardV2({ item, onViewChart }) {
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
    returns = {},
    recurrence = {}
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
  // v3의 경우 strategy에 따라 기본값 설정 (백엔드에서 전달되지 않은 경우 대비)
  let targetProfit = null;
  let stopLoss = null;
  let holdingPeriod = null;
  
  // flags에서 target_profit 추출 (소수 형태로 저장되어 있음)
  if (flags.target_profit !== undefined && flags.target_profit !== null) {
    targetProfit = (parseFloat(flags.target_profit) * 100).toFixed(1);
  }
  if (flags.stop_loss !== undefined && flags.stop_loss !== null) {
    stopLoss = (parseFloat(flags.stop_loss) * 100).toFixed(1);
  }
  if (flags.holding_period !== undefined && flags.holding_period !== null) {
    holdingPeriod = flags.holding_period;
  }
  
  // target_profit이 없으면 strategy에 따라 기본값 설정
  if (!targetProfit && strategy) {
    if (strategy === "v2_lite" || strategy === "눌림목") {
      targetProfit = "5.0";  // 5%
      stopLoss = stopLoss || "2.0";  // 2%
      holdingPeriod = holdingPeriod || 14;  // 2주
    } else if (strategy === "midterm") {
      targetProfit = "10.0";  // 10%
      stopLoss = stopLoss || "7.0";  // 7%
      holdingPeriod = holdingPeriod || 15;  // 15일
    }
  }

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

  // 날짜 포맷팅 헬퍼 함수
  const formatDate = (dateStr) => {
    if (!dateStr || dateStr.length !== 8) return '-';
    return `${dateStr.slice(0,4)}년 ${dateStr.slice(4,6)}월 ${dateStr.slice(6,8)}일`;
  };

  // 달성률 계산 및 상태 판단 함수
  const calculateProgressMetrics = (targetProfitStr, currentReturn, maxReturn, stopLossStr) => {
    if (!targetProfitStr || typeof currentReturn !== 'number' || isNaN(currentReturn)) {
      return null;
    }
    
    const targetReturn = parseFloat(targetProfitStr);
    if (isNaN(targetReturn) || targetReturn <= 0) {
      return null;
    }
    
    const stopLossValue = stopLossStr ? parseFloat(stopLossStr) : null;
    
    // 상태 판단
    const isAchieved = currentReturn >= targetReturn;
    const wasAchievedButDeclined = maxReturn >= targetReturn && currentReturn < targetReturn;
    const isStopLossReached = stopLossValue !== null && currentReturn <= stopLossValue;
    const hasDeclinedFromPeak = maxReturn > currentReturn && maxReturn >= targetReturn;
    
    // 계산
    const progress = Math.max(0, Math.min((currentReturn / targetReturn) * 100, 100));
    const excessReturn = isAchieved ? (currentReturn - targetReturn) : 0;
    const declineFromPeak = hasDeclinedFromPeak ? (maxReturn - currentReturn) : 0;
    const maxProgress = Math.min((maxReturn / targetReturn) * 100, 100);
    const remainingToTarget = targetReturn - currentReturn;
    
    return {
      targetReturn,
      stopLossValue,
      progress,
      excessReturn,
      declineFromPeak,
      maxProgress,
      remainingToTarget,
      isAchieved,
      wasAchievedButDeclined,
      isStopLossReached,
      hasDeclinedFromPeak
    };
  };

  // 수익률 카드 렌더링 조건 확인
  const shouldShowReturnCard = recommended_date && recommended_price && 
    typeof current_return === 'number' && !isNaN(current_return);
  
  // 달성률 메트릭 계산
  const progressMetrics = shouldShowReturnCard && targetProfit 
    ? calculateProgressMetrics(targetProfit, current_return, max_return, stopLoss)
    : null;

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

      {/* 재등장 정보 카드 */}
      {recurrence?.appeared_before && (
        <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">🔄</span>
            <h4 className="font-semibold text-purple-900">재등장 정보</h4>
            {recurrence.days_since_last && recurrence.days_since_last <= 3 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700 ml-auto">
                ⚡ {recurrence.days_since_last}일 만에 재등장
              </span>
            )}
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">재등장 횟수:</span>
              <span className="font-bold text-purple-700">{recurrence.appear_count || 0}회</span>
            </div>
            {recurrence.first_as_of && (
              <div className="flex justify-between">
                <span className="text-gray-600">첫 등장:</span>
                <span className="font-medium text-gray-800">
                  {recurrence.first_as_of.slice(0,4)}년 {recurrence.first_as_of.slice(4,6)}월 {recurrence.first_as_of.slice(6,8)}일
                </span>
              </div>
            )}
            {recurrence.last_as_of && (
              <div className="flex justify-between">
                <span className="text-gray-600">마지막 등장:</span>
                <span className="font-medium text-gray-800">
                  {recurrence.last_as_of.slice(0,4)}년 {recurrence.last_as_of.slice(4,6)}월 {recurrence.last_as_of.slice(6,8)}일
                </span>
              </div>
            )}
            {recurrence.days_since_last !== null && recurrence.days_since_last !== undefined && (
              <div className="flex justify-between pt-2 border-t border-purple-200">
                <span className="text-gray-600 font-semibold">등장 간격:</span>
                <span className="font-bold text-purple-700">{recurrence.days_since_last}일</span>
              </div>
            )}
          </div>
        </div>
      )}

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
      {shouldShowReturnCard && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">📊</span>
            <h4 className="font-semibold text-blue-900">추천일 대비 수익률</h4>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">추천일:</span>
              <span className="font-medium text-gray-800">
                {formatDate(recommended_date)}
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
              <span className={`text-lg font-bold ${
                current_return > 0 ? 'text-red-500' : 
                current_return < 0 ? 'text-blue-500' : 
                'text-gray-500'
              }`}>
                {current_return > 0 ? '+' : ''}{current_return.toFixed(2)}%
                {current_return > 0 ? ' 📈' : current_return < 0 ? ' 📉' : ''}
              </span>
            </div>
            
            {/* 목표 달성 여부 및 손절 기준 표시 */}
            {progressMetrics && (
              <div className={`mt-3 pt-3 border-t ${
                progressMetrics.wasAchievedButDeclined 
                  ? 'border-orange-200 bg-orange-50 rounded-lg p-3 -mt-3 -pt-3' 
                  : 'border-blue-200'
              }`}>
                <div className="flex items-center justify-between text-xs mb-2">
                  <div className="flex flex-col">
                    <span className="text-gray-600">목표 수익률: {progressMetrics.targetReturn}%</span>
                    <span className="text-gray-500 text-xs mt-0.5">
                      달성률: {progressMetrics.progress.toFixed(1)}%
                    </span>
                  </div>
                  <span className={
                    progressMetrics.isStopLossReached ? 'text-red-600 font-semibold' :
                    progressMetrics.wasAchievedButDeclined ? 'text-orange-600 font-semibold' :
                    progressMetrics.isAchieved ? 'text-green-600 font-semibold' : 
                    'text-gray-500'
                  }>
                    {progressMetrics.isStopLossReached 
                      ? `⚠️ 손절 기준 도달 (${current_return.toFixed(2)}%)`
                      : progressMetrics.wasAchievedButDeclined
                      ? `📉 목표 달성했으나 하락 (최고 ${max_return.toFixed(2)}% → 현재 ${current_return.toFixed(2)}%)`
                      : progressMetrics.isAchieved 
                      ? `✅ 목표 달성${progressMetrics.excessReturn > 0 ? ` (+${progressMetrics.excessReturn.toFixed(2)}% 초과)` : ''}${progressMetrics.hasDeclinedFromPeak ? ` (최고 ${max_return.toFixed(2)}%에서 ${progressMetrics.declineFromPeak.toFixed(2)}% 하락)` : ''}`
                      : `목표까지 ${progressMetrics.remainingToTarget.toFixed(2)}%`}
                  </span>
                </div>
                
                {/* 진행률 바 */}
                <div className="w-full bg-gray-200 rounded-full h-2 relative">
                  <div 
                    className={`h-2 rounded-full transition-all ${
                      progressMetrics.isStopLossReached ? 'bg-red-500' :
                      progressMetrics.wasAchievedButDeclined ? 'bg-gradient-to-r from-orange-400 via-orange-500 to-red-500' :
                      progressMetrics.isAchieved ? 'bg-green-500' : 
                      'bg-blue-500'
                    }`}
                    style={{ width: `${Math.max(0, Math.min(progressMetrics.progress, 100))}%` }}
                  />
                  {/* 최고 수익률 마커 (목표 달성했지만 하락한 경우) */}
                  {progressMetrics.wasAchievedButDeclined && progressMetrics.maxProgress > progressMetrics.progress && (
                    <div 
                      className="absolute top-0 h-2 flex items-center justify-center"
                      style={{ left: `${Math.min(progressMetrics.maxProgress, 100)}%`, transform: 'translateX(-50%)' }}
                    >
                      <div 
                        className="w-3 h-3 bg-yellow-400 transform rotate-45 border border-yellow-500 shadow-sm" 
                        title={`최고 수익률: ${max_return.toFixed(2)}%`}
                      />
                    </div>
                  )}
                </div>
                
                {/* 추가 정보 메시지 */}
                {progressMetrics.wasAchievedButDeclined && (
                  <div className="mt-2 text-xs text-orange-700 font-medium bg-orange-100 rounded px-2 py-1">
                    📉 최고 수익률 {max_return.toFixed(2)}%에서 {progressMetrics.declineFromPeak.toFixed(2)}% 하락 (현재: {current_return.toFixed(2)}%)
                  </div>
                )}
                {progressMetrics.isAchieved && progressMetrics.excessReturn > 0 && !progressMetrics.hasDeclinedFromPeak && (
                  <div className="mt-1 text-xs text-yellow-600 font-medium">
                    🎉 목표 대비 {((current_return / progressMetrics.targetReturn - 1) * 100).toFixed(0)}% 초과 달성!
                  </div>
                )}
                {progressMetrics.isStopLossReached && progressMetrics.stopLossValue !== null && (
                  <div className="mt-2 text-xs text-red-600 font-medium">
                    🛑 손절 기준({progressMetrics.stopLossValue}%) 도달 - 매도 고려 권장
                  </div>
                )}
              </div>
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

export default memo(StockCardV2, (prevProps, nextProps) => {
  // props 비교 최적화: ticker가 같고 주요 데이터가 변경되지 않으면 리렌더링 방지
  if (prevProps.item?.ticker !== nextProps.item?.ticker) return false;
  if (prevProps.item?.current_price !== nextProps.item?.current_price) return false;
  if (prevProps.item?.current_return !== nextProps.item?.current_return) return false;
  if (prevProps.item?.change_rate !== nextProps.item?.change_rate) return false;
  if (prevProps.onViewChart !== nextProps.onViewChart) return false;
  return true; // 변경 없음
});


