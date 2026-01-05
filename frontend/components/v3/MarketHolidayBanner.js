/**
 * 휴장일 안내 배너 컴포넌트
 * 
 * 규칙:
 * - 메인 추천 영역 상단 고정 안내 배너
 * - 기존 추천 카드 상태 유지
 * - 휴장일임을 명확히 알리는 아이콘/톤 사용
 */

import { EMPTY_STATE_MESSAGES } from '../../utils/v3StatusMapping';

export default function MarketHolidayBanner() {
  const messages = EMPTY_STATE_MESSAGES.MARKET_HOLIDAY;

  return (
    <div className={`bg-white border-b-2 ${messages.colorClass} px-4 py-3`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="w-5 h-5 text-blue-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className={`text-base font-semibold ${messages.headerColorClass}`}>
            {messages.header}
          </h3>
          <div className="mt-1 space-y-1">
            <p className={`text-sm ${messages.bodyColorClass}`}>
              {messages.summary}
            </p>
            {messages.helperText && (
              <p className={`text-xs ${messages.bodyColorClass} opacity-75`}>
                {messages.helperText}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


