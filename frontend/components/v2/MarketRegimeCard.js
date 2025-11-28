/**
 * Scanner V2용 시장 레짐 카드 컴포넌트
 * 시장 상황과 투자 조언을 간단하게 표시합니다.
 */
export default function MarketRegimeCard({ marketCondition }) {
  if (!marketCondition) {
    return null;
  }

  // 레짐 타입 (final_regime 또는 market_sentiment)
  const regime = marketCondition.final_regime || marketCondition.market_sentiment || 'neutral';

  // 레짐별 설정
  const regimeConfig = {
    bull: {
      icon: '🟢',
      text: '강세장',
      color: 'green',
      advice: '적극적 투자 권장',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      textColor: 'text-green-800'
    },
    neutral: {
      icon: '🟡',
      text: '중립장',
      color: 'yellow',
      advice: '신중한 투자, 분할 매수 권장',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      textColor: 'text-yellow-800'
    },
    bear: {
      icon: '🔴',
      text: '약세장',
      color: 'red',
      advice: '보수적 투자, 소액 분할 매수',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-800'
    },
    crash: {
      icon: '⚠️',
      text: '급락장',
      color: 'orange',
      advice: '투자 중단 권장',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
      textColor: 'text-orange-800'
    }
  };

  const config = regimeConfig[regime] || regimeConfig.neutral;

  return (
    <div className={`${config.bgColor} border ${config.borderColor} rounded-lg p-4 mb-4`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">{config.icon}</span>
          <h3 className={`text-lg font-semibold ${config.textColor}`}>
            시장 상황: {config.text}
          </h3>
        </div>
      </div>
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


