/**
 * BROKEN 상태 전용 추천 카드 컴포넌트
 * 
 * 규칙:
 * - BROKEN 상태만 처리
 * - 손익률, 추천일, 경과일 표시
 * - CTA 금지
 * - 정보성만 표시
 */

import { useRouter } from 'next/router';
import { STATUS_COLOR_CLASSES, BACKEND_STATUS, STATUS_TO_UX, getTerminationReasonText } from '../../utils/v3StatusMapping';
import { StrategyLabel } from '../../utils/strategyLabelUtils';

export default function BrokenRecommendationCard({ item }) {
  const router = useRouter();
  
  // 디버깅: 조건 확인
  if (process.env.NODE_ENV === 'development') {
    if (!item) {
      console.warn('[BrokenRecommendationCard] item이 없습니다');
    } else if (!item.status) {
      console.warn('[BrokenRecommendationCard] item.status가 없습니다:', item);
    } else if (item.status !== BACKEND_STATUS.BROKEN) {
      console.warn('[BrokenRecommendationCard] status가 BROKEN이 아닙니다:', {
        status: item.status,
        statusType: typeof item.status,
        BACKEND_STATUS_BROKEN: BACKEND_STATUS.BROKEN,
        equals: item.status === BACKEND_STATUS.BROKEN
      });
    }
  }
  
  if (!item || !item.status || item.status !== BACKEND_STATUS.BROKEN) {
    return null;
  }

  const { ticker, name, recommendation_id, id, reason, broken_return_pct, strategy } = item;
  const recId = recommendation_id || id;
  
  // 수익률 계산: 종료 시점 고정 수익률 (broken_return_pct)
  let brokenReturnRate = null;
  if (broken_return_pct !== undefined && broken_return_pct !== null && !isNaN(broken_return_pct)) {
    brokenReturnRate = broken_return_pct;
  }
  
  // 종료 사유 문구 가져오기 (추가 정보 없이)
  const reasonText = getTerminationReasonText(reason);
  
  const colors = STATUS_COLOR_CLASSES[BACKEND_STATUS.BROKEN];
  
  // 종목명 폴백 처리
  const displayName = name || (ticker ? `${ticker} (종목 정보 불러오는 중)` : '종목 정보 없음');
  
  // 클릭 핸들러: 상세 화면으로 이동 (정보 확인용)
  const handleClick = () => {
    if (ticker) {
      const params = new URLSearchParams({
        ticker,
        from: 'v3'
      });
      if (recId) {
        params.append('rec_id', recId);
      }
      router.push(`/stock-analysis?${params.toString()}`);
    }
  };

  // 문구 테이블에서 가져오기
  const uxConfig = STATUS_TO_UX[BACKEND_STATUS.BROKEN];
  const summaryText = uxConfig.summary;

  return (
    <div
      data-ticker={ticker}
      onClick={handleClick}
      className={`${colors.cardBg} ${colors.cardBorder} border-2 rounded-lg p-4 cursor-pointer hover:shadow-md transition-shadow`}
    >
      {/* 전략 라벨 (본문 위) */}
      <StrategyLabel strategy={strategy} />
      
      {/* 상단: 종목명 + 현재 손익률 */}
      <div className="flex items-start justify-between mb-3">
        {/* 종목명 */}
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-gray-900 truncate">
            {displayName}
          </h3>
          {ticker && (
            <div className="mt-1">
              <span className="text-xs text-gray-500 font-mono">
                {ticker}
              </span>
            </div>
          )}
        </div>
        
        {/* 수익률 (상단 우측) */}
        <div className="text-right ml-4 flex-shrink-0">
          {brokenReturnRate !== null && brokenReturnRate !== undefined && !isNaN(brokenReturnRate) ? (
            <>
              <div className="text-xs text-gray-500 mb-0.5">수익률</div>
              <span className={`text-sm font-medium ${brokenReturnRate > 0 ? 'text-red-500' : brokenReturnRate < 0 ? 'text-blue-500' : colors.bodyText}`}>
                {brokenReturnRate > 0 ? '+' : ''}{brokenReturnRate.toFixed(2)}%
              </span>
            </>
          ) : (
            <>
              <div className="text-xs text-gray-500 mb-0.5">수익률</div>
              <span className={`text-sm ${colors.bodyText} opacity-50`}>
                —
              </span>
            </>
          )}
        </div>
      </div>
      
      {/* 본문 - 고정 (2줄) */}
      <div className="mt-3 pt-3 border-t border-gray-200">
        <p className={`text-sm font-medium ${colors.bodyText}`}>
          {summaryText}
        </p>
        <p className={`text-sm ${colors.bodyText} mt-1`}>
          사유: {reasonText || '관리 기간 종료'}
        </p>
      </div>
    </div>
  );
}


