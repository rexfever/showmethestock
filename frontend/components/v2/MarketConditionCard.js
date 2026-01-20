// Regime v4 기반 장세 분석 카드
import { useState } from 'react';

export default function MarketConditionCard({ marketCondition }) {
  if (!marketCondition) {
    return null;
  }

  // Regime v4의 midterm_regime을 기본으로 사용 (fallback: final_regime → market_sentiment)
  const midtermRegime = marketCondition.midterm_regime || 
                        marketCondition.final_regime || 
                        marketCondition.market_sentiment || 
                        'neutral';
  
  const shortTermRisk = marketCondition.short_term_risk_score ?? null;
  const kospiReturn = marketCondition.kospi_return || 0;

  // 중기 장세별 메시지 (midterm_regime 기반)
  const midtermRegimeInfo = {
    'bull': {
      emoji: '📈',
      title: '중기적으로 상승 추세입니다',
      message: '시장이 중기적으로 상승 흐름을 보이고 있어요',
      color: 'bg-green-50 border-green-200',
      textColor: 'text-green-700',
      advice: '추천 종목에 적극적으로 투자해보세요'
    },
    'neutral': {
      emoji: '📊',
      title: '중기 흐름은 중립입니다',
      message: '시장이 중기적으로 안정적인 흐름을 보이고 있어요',
      color: 'bg-blue-50 border-blue-200',
      textColor: 'text-blue-700',
      advice: '추천 종목에 투자하되 분할 매수하세요'
    },
    'bear': {
      emoji: '📉',
      title: '중기적으로 하락 압력이 있는 구간입니다',
      message: '시장이 중기적으로 하락 압력을 받고 있어요',
      color: 'bg-orange-50 border-orange-200',
      textColor: 'text-orange-700',
      advice: '소액으로 분할 매수를 고려하세요'
    },
    'crash': {
      emoji: '⚠️',
      title: '중기적으로도 급락 국면입니다',
      message: '시장이 중기적으로도 급락 국면에 있어요',
      color: 'bg-red-50 border-red-200',
      textColor: 'text-red-700',
      advice: '오늘은 투자를 쉬는 것을 권장합니다'
    }
  };

  // 단기 변동성 메시지 (short_term_risk_score 기반)
  const shortTermRiskInfo = {
    0: {
      text: '단기 변동성은 낮은 편입니다',
      color: 'text-green-600',
      bgColor: 'bg-green-50'
    },
    1: {
      text: '단기 변동성이 다소 있습니다',
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50'
    },
    2: {
      text: '단기 변동성이 높으니 보수적인 접근이 필요합니다',
      color: 'text-orange-600',
      bgColor: 'bg-orange-50'
    },
    3: {
      text: '단기 리스크가 매우 높습니다. 비중 관리에 특히 유의해야 합니다',
      color: 'text-red-600',
      bgColor: 'bg-red-50'
    }
  };

  const midtermInfo = midtermRegimeInfo[midtermRegime] || midtermRegimeInfo['neutral'];
  const riskInfo = shortTermRisk !== null && shortTermRisk >= 0 && shortTermRisk <= 3 
    ? shortTermRiskInfo[shortTermRisk] 
    : shortTermRiskInfo[0];

  return (
    <div className={`rounded-lg shadow-sm border-2 ${midtermInfo.color} p-4 mb-4`}>
      {/* 메인 메시지 - 중기 장세 */}
      <div className="flex items-start gap-3 mb-3">
        <span className="text-3xl">{midtermInfo.emoji}</span>
        <div className="flex-1">
          <h3 className={`text-lg font-bold ${midtermInfo.textColor} mb-1`}>
            {midtermInfo.title}
          </h3>
          <p className="text-sm text-gray-600 mb-2">
            {midtermInfo.message}
          </p>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span>코스피</span>
            <span className={`font-semibold ${kospiReturn >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
              {kospiReturn >= 0 ? '+' : ''}{(kospiReturn * 100).toFixed(2)}%
            </span>
          </div>
        </div>
      </div>

      {/* 단기 변동성 정보 */}
      {shortTermRisk !== null && (
        <div className={`${riskInfo.bgColor} rounded-lg p-2 mb-3 border border-gray-200`}>
          <div className="flex items-center gap-2">
            <span className="text-sm">⚡</span>
            <p className={`text-sm font-medium ${riskInfo.color}`}>
              {riskInfo.text}
            </p>
          </div>
        </div>
      )}

      {/* 투자 조언 */}
      <div className="bg-white bg-opacity-50 rounded-lg p-3 border border-gray-200">
        <div className="flex items-start gap-2">
          <span className="text-lg">💡</span>
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-700 mb-1">
              오늘의 투자 전략
            </p>
            <p className="text-sm text-gray-600">
              {midtermInfo.advice}
            </p>
            {midtermRegime === 'bear' && (
              <p className="text-xs text-orange-600 mt-2 font-medium">
                ⚠️ 약세장에서는 보수적으로 1~3개 종목만 추천합니다
              </p>
            )}
            {midtermRegime === 'crash' && (
              <p className="text-xs text-red-600 mt-2">
                ⚠️ 급락장에서는 장기 투자만 조건부 허용됩니다
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 추가 정보 (legacy market_sentiment) - 작은 텍스트로 표시 */}
      {marketCondition.market_sentiment && 
       marketCondition.market_sentiment !== midtermRegime && (
        <div className="mt-2 text-xs text-gray-400 text-right">
          참고: 일일 장세 ({marketCondition.market_sentiment})
        </div>
      )}
    </div>
  );
}
