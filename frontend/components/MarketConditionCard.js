// 사용자 친화적 장세 분석 카드
import { useState } from 'react';

export default function MarketConditionCard({ marketCondition }) {
  if (!marketCondition) {
    return null;
  }

  const sentiment = marketCondition.market_sentiment || 'neutral';
  const kospiReturn = marketCondition.kospi_return || 0;

  // 시장 상황별 이모지와 메시지
  const marketInfo = {
    'bull': {
      emoji: '📈',
      title: '오늘은 상승장이에요',
      message: '시장이 활발하게 움직이고 있어요',
      color: 'bg-green-50 border-green-200',
      textColor: 'text-green-700',
      advice: '추천 종목에 적극적으로 투자해보세요'
    },
    'neutral': {
      emoji: '📊',
      title: '오늘은 보합장이에요',
      message: '시장이 안정적으로 움직이고 있어요',
      color: 'bg-blue-50 border-blue-200',
      textColor: 'text-blue-700',
      advice: '추천 종목에 투자하되 분할 매수하세요'
    },
    'bear': {
      emoji: '📉',
      title: '오늘은 하락장이에요',
      message: '시장이 조정을 받고 있어요',
      color: 'bg-orange-50 border-orange-200',
      textColor: 'text-orange-700',
      advice: '소액으로 분할 매수를 고려하세요'
    },
    'crash': {
      emoji: '⚠️',
      title: '오늘은 급락장이에요',
      message: '시장이 크게 하락하고 있어요',
      color: 'bg-red-50 border-red-200',
      textColor: 'text-red-700',
      advice: '오늘은 투자를 쉬는 것을 권장합니다'
    }
  };

  const info = marketInfo[sentiment] || marketInfo['neutral'];

  return (
    <div className={`rounded-lg shadow-sm border-2 ${info.color} p-4 mb-4`}>
      {/* 메인 메시지 */}
      <div className="flex items-start gap-3 mb-3">
        <span className="text-3xl">{info.emoji}</span>
        <div className="flex-1">
          <h3 className={`text-lg font-bold ${info.textColor} mb-1`}>
            {info.title}
          </h3>
          <p className="text-sm text-gray-600 mb-2">
            {info.message}
          </p>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span>코스피</span>
            <span className={`font-semibold ${kospiReturn >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
              {kospiReturn >= 0 ? '+' : ''}{(kospiReturn * 100).toFixed(2)}%
            </span>
          </div>
        </div>
      </div>

      {/* 투자 조언 */}
      <div className="bg-white bg-opacity-50 rounded-lg p-3 border border-gray-200">
        <div className="flex items-start gap-2">
          <span className="text-lg">💡</span>
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-700 mb-1">
              오늘의 투자 전략
            </p>
            <p className="text-sm text-gray-600">
              {info.advice}
            </p>
            {sentiment === 'bear' && (
              <p className="text-xs text-orange-600 mt-2 font-medium">
                ⚠️ 약세장에서는 보수적으로 1~3개 종목만 추천합니다
              </p>
            )}
            {sentiment === 'crash' && (
              <p className="text-xs text-red-600 mt-2">
                ⚠️ 오늘은 추천 종목이 제공되지 않습니다
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
