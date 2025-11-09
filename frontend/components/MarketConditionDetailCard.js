// 관리자용 상세 장세 분석 카드
import { useState } from 'react';

export default function MarketConditionDetailCard({ marketCondition }) {
  const [showDetails, setShowDetails] = useState(false);

  if (!marketCondition) {
    return null;
  }

  // 시장 심리 한글 변환
  const sentimentLabels = {
    'bull': '강세장',
    'neutral': '중립장',
    'bear': '약세장',
    'crash': '급락장'
  };

  // 섹터 로테이션 한글 변환
  const sectorLabels = {
    'tech': '기술주 강세',
    'value': '가치주 강세',
    'mixed': '혼재'
  };

  // 외국인 수급 한글 변환
  const flowLabels = {
    'buy': '순매수',
    'sell': '순매도',
    'neutral': '중립'
  };

  // 거래량 추세 한글 변환
  const volumeLabels = {
    'high': '높음',
    'normal': '보통',
    'low': '낮음'
  };

  // 시장 심리에 따른 색상
  const sentimentColors = {
    'bull': 'text-green-600 bg-green-50',
    'neutral': 'text-blue-600 bg-blue-50',
    'bear': 'text-orange-600 bg-orange-50',
    'crash': 'text-red-600 bg-red-50'
  };

  const sentimentBorderColors = {
    'bull': 'border-green-200',
    'neutral': 'border-blue-200',
    'bear': 'border-orange-200',
    'crash': 'border-red-200'
  };

  const sentiment = marketCondition.market_sentiment || 'neutral';
  const colorClass = sentimentColors[sentiment] || sentimentColors['neutral'];
  const borderClass = sentimentBorderColors[sentiment] || sentimentBorderColors['neutral'];

  return (
    <div className={`bg-white rounded-lg shadow-sm border-2 ${borderClass} p-4 mb-4`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">📊</span>
          <h3 className="text-lg font-bold text-gray-800">장세 분석 (관리자)</h3>
        </div>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
        >
          {showDetails ? '간단히 보기' : '자세히 보기'}
        </button>
      </div>

      {/* 주요 지표 */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        {/* 시장 심리 */}
        <div className={`${colorClass} rounded-lg p-3`}>
          <div className="text-xs text-gray-600 mb-1">시장 심리</div>
          <div className="text-lg font-bold">{sentimentLabels[sentiment]}</div>
          {marketCondition.kospi_return !== undefined && (
            <div className="text-xs mt-1">
              KOSPI {(marketCondition.kospi_return * 100).toFixed(2)}%
            </div>
          )}
        </div>

        {/* RSI 임계값 */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-xs text-gray-600 mb-1">RSI 기준</div>
          <div className="text-lg font-bold text-gray-800">
            {marketCondition.rsi_threshold?.toFixed(1) || '58.0'}
          </div>
          <div className="text-xs text-gray-500 mt-1">스캔 기준값</div>
        </div>
      </div>

      {/* 상세 정보 (토글) */}
      {showDetails && (
        <div className="border-t pt-3 mt-3 space-y-2">
          {/* 섹터 로테이션 */}
          <div className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded">
            <span className="text-sm text-gray-600">섹터 로테이션</span>
            <span className="text-sm font-medium text-gray-800">
              {sectorLabels[marketCondition.sector_rotation] || '혼재'}
            </span>
          </div>

          {/* 외국인 수급 */}
          <div className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded">
            <span className="text-sm text-gray-600">외국인 수급</span>
            <span className={`text-sm font-medium ${
              marketCondition.foreign_flow === 'buy' ? 'text-red-600' :
              marketCondition.foreign_flow === 'sell' ? 'text-blue-600' :
              'text-gray-600'
            }`}>
              {flowLabels[marketCondition.foreign_flow] || '중립'}
            </span>
          </div>

          {/* 거래량 추세 */}
          <div className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded">
            <span className="text-sm text-gray-600">거래량 추세</span>
            <span className={`text-sm font-medium ${
              marketCondition.volume_trend === 'high' ? 'text-green-600' :
              marketCondition.volume_trend === 'low' ? 'text-gray-500' :
              'text-gray-600'
            }`}>
              {volumeLabels[marketCondition.volume_trend] || '보통'}
            </span>
          </div>

          {/* 변동성 */}
          {marketCondition.volatility !== undefined && (
            <div className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded">
              <span className="text-sm text-gray-600">시장 변동성</span>
              <span className="text-sm font-medium text-gray-800">
                {(marketCondition.volatility * 100).toFixed(2)}%
              </span>
            </div>
          )}

          {/* 스캔 파라미터 */}
          <div className="mt-3 p-3 bg-gray-50 rounded">
            <div className="text-xs font-medium text-gray-700 mb-2">스캔 파라미터</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>min_signals: {marketCondition.min_signals}</div>
              <div>macd_osc_min: {marketCondition.macd_osc_min}</div>
              <div>vol_ma5_mult: {marketCondition.vol_ma5_mult}</div>
              <div>gap_max: {marketCondition.gap_max}</div>
              <div>ext_from_tema20_max: {marketCondition.ext_from_tema20_max}</div>
            </div>
          </div>

          {/* 분석 노트 */}
          {marketCondition.analysis_notes && (
            <div className="mt-3 p-3 bg-blue-50 rounded text-xs text-gray-600">
              <div className="font-medium text-gray-700 mb-1">📝 분석 메모</div>
              {marketCondition.analysis_notes}
            </div>
          )}
        </div>
      )}

      {/* 투자 가이드 */}
      <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded text-xs">
        <div className="flex items-start gap-2">
          <span>💡</span>
          <div>
            <div className="font-medium text-gray-700 mb-1">투자 전략</div>
            <div className="text-gray-600">
              {sentiment === 'bull' && '강세장: 높은 RSI 허용으로 상승 추세 포착'}
              {sentiment === 'neutral' && '중립장: 균형잡힌 조건으로 안정적 선별'}
              {sentiment === 'bear' && '약세장: 엄격한 조건으로 리스크 관리'}
              {sentiment === 'crash' && '급락장: 추천 종목 없음, 투자 휴식 권장'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

