// 미국 시장 상황 카드 컴포넌트
import { useState, useEffect } from 'react';
import getConfig from '../../config';

export default function USMarketConditionCard({ date }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchUSRegime = async () => {
      try {
        const config = getConfig();
        const url = date 
          ? `${config.backendUrl}/api/us-regime/analyze?date=${date}`
          : `${config.backendUrl}/api/us-regime/analyze`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.ok) {
          setData(result.data);
        } else {
          setError(result.error);
        }
      } catch (err) {
        setError('미국 시장 상황을 불러올 수 없습니다.');
      } finally {
        setLoading(false);
      }
    };

    fetchUSRegime();
  }, [date]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
          <div className="h-3 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return null;
  }

  // 레짐별 색상
  const getRegimeColor = (regime) => {
    switch (regime) {
      case 'bull':
        return 'bg-green-50 border-green-200 text-green-700';
      case 'neutral_bull':
        return 'bg-green-50 border-green-100 text-green-600';
      case 'bear':
        return 'bg-red-50 border-red-200 text-red-700';
      case 'neutral_bear':
        return 'bg-red-50 border-red-100 text-red-600';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-700';
    }
  };

  const regimeColor = getRegimeColor(data.regime);

  return (
    <div className={`rounded-lg border-2 p-4 mb-4 ${regimeColor}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold flex items-center">
          🇺🇸 미국 시장 상황
        </h3>
        <span className="text-sm font-medium">
          점수: {data.score} / 100
        </span>
      </div>

      <div className="mb-3">
        <div className="text-base font-semibold mb-1">
          레짐: {data.regime_kr} ({data.regime.toUpperCase()})
        </div>
      </div>

      <div className="mb-3">
        <div className="text-sm font-medium mb-2">📊 주요 지표</div>
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="bg-white bg-opacity-50 rounded p-2">
            <div className="font-medium">SPY</div>
            <div className={data.market_data.SPY.change_pct >= 0 ? 'text-red-600' : 'text-blue-600'}>
              {data.market_data.SPY.change_pct >= 0 ? '+' : ''}{data.market_data.SPY.change_pct}%
            </div>
          </div>
          <div className="bg-white bg-opacity-50 rounded p-2">
            <div className="font-medium">QQQ</div>
            <div className={data.market_data.QQQ.change_pct >= 0 ? 'text-red-600' : 'text-blue-600'}>
              {data.market_data.QQQ.change_pct >= 0 ? '+' : ''}{data.market_data.QQQ.change_pct}%
            </div>
          </div>
          <div className="bg-white bg-opacity-50 rounded p-2">
            <div className="font-medium">VIX</div>
            <div className="text-gray-700">
              {data.market_data.VIX.level}
            </div>
          </div>
        </div>
      </div>

      <div className="text-sm">
        <div className="font-medium mb-1">💡 투자 조언</div>
        <div className="text-xs leading-relaxed">
          {data.advice}
        </div>
      </div>
    </div>
  );
}
