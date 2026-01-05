/**
 * 일일 변화 요약 카드 컴포넌트 (NEW 요약 카드)
 * 
 * 규칙:
 * - daily_digest.has_changes = true 일 때만 노출
 * - 하루 1개만 존재
 * - 종목명 + 사건 결과 반드시 함께 나열
 * - 강조/CTA 금지
 */

import { getTerminationReasonText } from '../../utils/v3StatusMapping';

export default function DailyDigestCard({ dailyDigest }) {
  if (!dailyDigest || !dailyDigest.has_changes) {
    return null;
  }

  // 종목명 리스트 (백엔드에서 제공)
  const broken_items = dailyDigest.broken_items || [];
  const weak_warning_items = dailyDigest.weak_warning_items || [];

  // 모든 이벤트 수집
  const allEvents = [];
  
  // BROKEN 종목 (추천 관리 종료)
  broken_items.forEach(item => {
    const name = item.name || item.ticker;
    if (name) {
      const reasonText = getTerminationReasonText(item.reason);
      // 사유가 있으면 포함, 없으면 기본 문구만
      const eventText = reasonText 
        ? `추천 관리 종료 (${reasonText})`
        : '추천 관리 종료';
      allEvents.push({ name, event: eventText });
    }
  });

  // WEAK_WARNING 종목 (이전과 다른 움직임 감지)
  weak_warning_items.forEach(item => {
    const name = item.name || item.ticker;
    if (name) {
      allEvents.push({ name, event: '이전과 다른 움직임 감지' });
    }
  });

  // 종목명이 없는 경우 카드를 표시하지 않음 (요구사항: 종목명 없는 이벤트 금지)
  if (allEvents.length === 0) {
    return null;
  }

  // 축약 규칙: 2건 초과 시 첫 번째 종목 1건만 노출 + "· 외 N건"
  const displayItems = [];
  let remainingCount = 0;

  if (allEvents.length > 2) {
    // 첫 번째 종목 1건만 표시
    displayItems.push(allEvents[0]);
    remainingCount = allEvents.length - 1;
  } else {
    // 2건 이하일 경우 모두 표시
    displayItems.push(...allEvents);
  }

  return (
    <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 mb-4">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="w-5 h-5 text-blue-800"
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
          <h3 className="text-base font-semibold text-blue-800">
            오늘 추천에 변화가 있었습니다
          </h3>
          <div className="mt-2 space-y-1">
            {displayItems.map((item, idx) => (
              <p key={idx} className="text-sm text-gray-700">
                · {item.name} – {item.event}
              </p>
            ))}
            {remainingCount > 0 && (
              <p className="text-sm text-gray-700">
                · 외 {remainingCount}건
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

