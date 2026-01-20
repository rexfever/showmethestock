/**
 * WEAK_WARNING 카드 컴포넌트 (v3)
 * 
 * 백엔드 상태 WEAK_WARNING을 정확히 번역
 */

import RecommendationCardV3 from './RecommendationCardV3';

export default function WeakWarningCardV3({ item, isNew = false }) {
  // RecommendationCardV3가 상태를 자동으로 처리하므로 재사용
  return <RecommendationCardV3 item={item} isNew={isNew} />;
}



