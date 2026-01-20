/**
 * 전략 라벨 유틸리티
 * 
 * 전략 라벨 정의:
 * - Midterm → "중기 전략"
 * - V2 lite → "단기 전략"
 */

/**
 * 전략 라벨 텍스트 반환
 * @param {string} strategy - 전략명 ('midterm' 또는 'v2_lite')
 * @returns {string|null} - 전략 라벨 텍스트 또는 null
 */
export function getStrategyLabel(strategy) {
  if (!strategy) {
    return null;
  }
  
  const strategyLower = strategy.toLowerCase();
  
  if (strategyLower === 'midterm') {
    return '중기 전략';
  } else if (strategyLower === 'v2_lite' || strategyLower === 'v2lite') {
    return '단기 전략';
  }
  
  return null;
}

/**
 * 전략 라벨 컴포넌트 (JSX)
 * @param {string} strategy - 전략명
 * @returns {JSX.Element|null} - 전략 라벨 JSX 또는 null
 */
export function StrategyLabel({ strategy }) {
  const labelText = getStrategyLabel(strategy);
  
  if (!labelText) {
    return null;
  }
  
  return (
    <div className="mb-3">
      <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium text-gray-600 bg-gray-100">
        {labelText}
      </span>
    </div>
  );
}

