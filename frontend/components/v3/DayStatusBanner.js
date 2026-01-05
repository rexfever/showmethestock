/**
 * 일일 추천 상태 배너 컴포넌트
 * 
 * 규칙:
 * - 추천 영역 최상단에 위치
 * - 항상 1개만 노출
 * - 카드가 없더라도 배너는 표시
 * - 서버 daily_digest.window 사용 (PRE_1535, POST_1535, HOLIDAY)
 * - 종목명, 개수, 후보, 스캔 언급 금지
 */

import { DAY_STATUS_BANNER_MESSAGES } from '../../utils/v3StatusMapping';

export default function DayStatusBanner({ 
  dailyDigest,
  activeItems = [], 
  todayRecommendations = [] 
}) {
  // daily_digest가 없으면 기본 배너 표시 (항상 배너는 표시되어야 함)
  const window = dailyDigest?.window;
  const new_recommendations = dailyDigest?.new_recommendations || 0;
  
  // 오늘 생성된 추천 이벤트 확인 (anchor_date가 오늘인 추천)
  const hasNewRecommendationsToday = new_recommendations > 0 || todayRecommendations.length > 0;
  
  // 기존 추천이 있는지 확인 (ACTIVE 또는 WEAK_WARNING)
  const hasExistingRecommendations = activeItems.length > 0;
  
  // 배너 상태 결정 (daily_digest.window 기반, 없으면 기본값)
  let bannerState;
  
  if (window === 'HOLIDAY') {
    // 휴장일
    bannerState = DAY_STATUS_BANNER_MESSAGES.MARKET_HOLIDAY;
  } else if (window === 'PRE_1535') {
    // 15:35 이전 (장중/장전)
    bannerState = DAY_STATUS_BANNER_MESSAGES.BEFORE_1535;
  } else if (window === 'POST_1535') {
    // 15:35 이후
    if (hasNewRecommendationsToday) {
      // 신규 추천 생성됨
      bannerState = DAY_STATUS_BANNER_MESSAGES.NEW_RECOMMENDATIONS_AFTER_1535;
    } else if (hasExistingRecommendations) {
      // 기존 추천 유지
      bannerState = DAY_STATUS_BANNER_MESSAGES.MAINTAINED_AFTER_1535;
    } else {
      // 추천 자체가 없음
      bannerState = DAY_STATUS_BANNER_MESSAGES.NO_RECOMMENDATIONS_AFTER_1535;
    }
  } else {
    // 기본값 (dailyDigest가 없거나 에러 또는 알 수 없는 상태)
    bannerState = DAY_STATUS_BANNER_MESSAGES.BEFORE_1535;
  }
  
  return (
    <div className={`bg-white border-b-2 ${bannerState.colorClass} px-4 py-3`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className={`w-5 h-5 ${bannerState.headerColorClass}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className={`text-base font-semibold ${bannerState.headerColorClass}`}>
            {bannerState.header}
          </h3>
          {bannerState.helperText && (
            <p className={`text-sm ${bannerState.bodyColorClass} mt-1`}>
              {bannerState.helperText}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

