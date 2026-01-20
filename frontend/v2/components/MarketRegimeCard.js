/**
 * Scanner V2용 시장 레짐 카드 컴포넌트 (Regime v4 기반)
 * 시장 상황과 투자 조언을 간단하게 표시합니다.
 */
export default function MarketRegimeCard({ marketCondition }) {
  if (!marketCondition) {
    return null;
  }

  // Regime v4의 midterm_regime을 기본으로 사용 (fallback: final_regime → market_sentiment)
  const midtermRegime = marketCondition.midterm_regime || 
                        marketCondition.final_regime || 
                        marketCondition.market_sentiment || 
                        'neutral';
  
  const shortTermRisk = marketCondition.short_term_risk_score ?? null;

  // 중기 장세별 설정
  const regimeConfig = {
    bull: {
      icon: '🟢',
      text: '상승',
      fullText: '중기적으로 상승 추세',
      color: 'green',
      advice: '적극적 투자 권장',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      textColor: 'text-green-800'
    },
    neutral: {
      icon: '🟡',
      text: '중립',
      fullText: '중기 흐름은 중립',
      color: 'yellow',
      advice: '신중한 투자, 분할 매수 권장',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      textColor: 'text-yellow-800'
    },
    bear: {
      icon: '🔴',
      text: '하락',
      fullText: '중기적으로 하락 압력',
      color: 'red',
      advice: '보수적 투자, 소액 분할 매수',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-800'
    },
    crash: {
      icon: '⚠️',
      text: '급락',
      fullText: '중기적으로도 급락 국면',
      color: 'orange',
      advice: '투자 중단 권장',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
      textColor: 'text-orange-800'
    }
  };

  // 단기 변동성 텍스트
  const getShortTermRiskText = (risk) => {
    if (risk === null || risk === undefined) return '낮음';
    if (risk === 0) return '낮음';
    if (risk === 1) return '보통';
    if (risk === 2) return '높음';
    if (risk >= 3) return '매우 높음';
    return '낮음';
  };

  const getShortTermRiskColor = (risk) => {
    if (risk === null || risk === undefined) return 'text-green-600';
    if (risk === 0) return 'text-green-600';
    if (risk === 1) return 'text-yellow-600';
    if (risk === 2) return 'text-orange-600';
    if (risk >= 3) return 'text-red-600';
    return 'text-green-600';
  };

  const config = regimeConfig[midtermRegime] || regimeConfig.neutral;
  const riskText = getShortTermRiskText(shortTermRisk);
  const riskColor = getShortTermRiskColor(shortTermRisk);

  return (
    <div className={`${config.bgColor} border ${config.borderColor} rounded-lg p-4 mb-4`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">{config.icon}</span>
          <div>
            <h3 className={`text-lg font-semibold ${config.textColor}`}>
              중기 장세: {config.text}
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              {config.fullText}
            </p>
          </div>
        </div>
      </div>
      
      {/* 단기 변동성 표시 */}
      <div className="mb-3 pb-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-sm">⚡</span>
          <span className="text-sm text-gray-600">단기 변동성:</span>
          <span className={`text-sm font-semibold ${riskColor}`}>
            {riskText}
          </span>
        </div>
      </div>

      {/* 투자 조언 */}
      <div className="mt-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">💡</span>
          <span className={`text-sm font-medium ${config.textColor}`}>
            오늘의 투자 전략
          </span>
        </div>
        <p className={`text-sm mt-1 ${config.textColor}`}>
          {config.advice}
        </p>
      </div>
    </div>
  );
}
