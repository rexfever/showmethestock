import React, { useState } from 'react';
import Head from 'next/head';
import MarketGuide from '../components/MarketGuide';

const MarketGuideTest = () => {
  const [selectedScenario, setSelectedScenario] = useState('bull');

  // 목업 데이터 시나리오들
  const mockScenarios = {
    bull: {
      name: '강세장',
      market_guide: {
        market_condition: '강세',
        guide_message: '🚀 강세장입니다. 적극적인 매수 기회를 활용하세요.',
        investment_strategy: '즉시 매수 후 단기 수익 실현 전략',
        risk_level: '낮음',
        timing_advice: '장 시작 직후 또는 상승 모멘텀 확인 시 매수'
      },
      stocks: [
        { name: '삼성전자', ticker: '005930', change_rate: 3.2, score: 9.1 },
        { name: 'SK하이닉스', ticker: '000660', change_rate: 2.8, score: 8.7 },
        { name: 'NAVER', ticker: '035420', change_rate: 4.1, score: 8.3 }
      ]
    },
    bear: {
      name: '약세장',
      market_guide: {
        market_condition: '약세',
        guide_message: '⚠️ 약세장입니다. 매수보다는 관망을 권장합니다.',
        investment_strategy: '관심종목 등록 후 추가 하락 시 매수 기회 포착',
        risk_level: '높음',
        timing_advice: '당일 매수 지양, 익일 시초가 확인 후 판단'
      },
      stocks: [
        { name: '휴온스글로벌', ticker: '084110', change_rate: -4.2, score: 8.0 },
        { name: '씨젠', ticker: '096530', change_rate: -2.1, score: 6.0 }
      ]
    },
    neutral: {
      name: '중립장',
      market_guide: {
        market_condition: '중립',
        guide_message: '⚖️ 중립적 시장입니다. 신중한 접근이 필요합니다.',
        investment_strategy: '관망 또는 소량 분할 매수',
        risk_level: '보통',
        timing_advice: '하락 시 매수, 상승 확인 후 추가 매수'
      },
      stocks: [
        { name: '삼성전자', ticker: '005930', change_rate: 0.8, score: 7.2 },
        { name: 'LG화학', ticker: '051910', change_rate: -0.5, score: 6.8 },
        { name: '카카오', ticker: '035720', change_rate: 1.2, score: 6.5 }
      ]
    },
    noresult: {
      name: '추천종목 없음',
      market_guide: {
        market_condition: '급락',
        guide_message: '☕ 장이 좋지 않아 추천 종목이 없습니다. 투자에도 휴식이 필요합니다.',
        investment_strategy: '현금 보유, 다음 기회 대기',
        risk_level: '매우 높음',
        timing_advice: '시장 개선 시까지 관망'
      },
      stocks: []
    }
  };

  const currentScenario = mockScenarios[selectedScenario];

  return (
    <>
      <Head>
        <title>Market Guide 테스트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-800 mb-6 text-center">
            📊 Market Guide 화면 테스트
          </h1>

          {/* 시나리오 선택 버튼들 */}
          <div className="flex flex-wrap gap-2 mb-6 justify-center">
            {Object.entries(mockScenarios).map(([key, scenario]) => (
              <button
                key={key}
                onClick={() => setSelectedScenario(key)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  selectedScenario === key
                    ? 'bg-blue-500 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
              >
                {scenario.name}
              </button>
            ))}
          </div>

          {/* Market Guide 컴포넌트 */}
          <MarketGuide marketGuide={currentScenario.market_guide} />

          {/* 종목 목록 (참고용) */}
          <div className="bg-white rounded-lg shadow-sm border p-4">
            <h3 className="text-lg font-semibold mb-3">
              📈 {currentScenario.name} - 추천 종목 ({currentScenario.stocks.length}개)
            </h3>
            
            {currentScenario.stocks.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-6xl mb-4">😔</div>
                <p className="text-gray-500">추천 종목이 없습니다</p>
              </div>
            ) : (
              <div className="space-y-3">
                {currentScenario.stocks.map((stock, index) => (
                  <div key={stock.ticker} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <div>
                      <span className="font-medium">{stock.name}</span>
                      <span className="text-gray-500 ml-2">({stock.ticker})</span>
                      <span className="ml-2 text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">
                        점수: {stock.score}
                      </span>
                    </div>
                    <div className={`font-bold ${
                      stock.change_rate > 0 ? 'text-red-500' : 
                      stock.change_rate < 0 ? 'text-blue-500' : 'text-gray-500'
                    }`}>
                      {stock.change_rate > 0 ? '+' : ''}{stock.change_rate}%
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 시나리오 설명 */}
          <div className="mt-6 bg-white rounded-lg shadow-sm border p-4">
            <h3 className="text-lg font-semibold mb-2">📋 시나리오 설명</h3>
            <div className="text-sm text-gray-600 space-y-1">
              <p><strong>강세장:</strong> 많은 종목 매칭, 높은 RSI, 대부분 상승</p>
              <p><strong>약세장:</strong> 적은 종목 매칭, 낮은 RSI, 대부분 하락</p>
              <p><strong>중립장:</strong> 보통 종목 매칭, 보통 RSI, 혼재 상황</p>
              <p><strong>추천종목 없음:</strong> 매칭 종목 없음, 매우 낮은 RSI</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default MarketGuideTest;