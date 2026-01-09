/**
 * 추천 없는 날 안내 카드 컴포넌트
 * 
 * 규칙:
 * - 중립 색상(회색/블루)
 * - CTA 버튼 없음
 * - 스캔 결과, 후보 종목 노출 금지
 * - 투자 조언 표현 금지
 */

import { EMPTY_STATE_MESSAGES } from '../../utils/v3StatusMapping';

export default function NoRecommendationsCard() {
  const messages = EMPTY_STATE_MESSAGES.NO_RECOMMENDATIONS;

  return (
    <div className={`bg-white rounded-lg border-2 ${messages.colorClass} p-6`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="w-6 h-6 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <div className="ml-4 flex-1">
          <h3 className={`text-lg font-bold ${messages.headerColorClass}`}>
            {messages.header}
          </h3>
          <div className="mt-3 space-y-2">
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



