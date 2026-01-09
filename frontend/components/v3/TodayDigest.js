/**
 * Today Digest 컴포넌트
 * 
 * 명세:
 * - 레이어 ①: 신규 추천 요약 (항상 1줄)
 * - 레이어 ②: 추천 변화 이벤트 목록 (조건부)
 */

export default function TodayDigest({ dailyDigest }) {
  if (!dailyDigest) {
    return null;
  }

  // 명세에 맞게 데이터 변환
  const has_new_recommendations = (dailyDigest.new_recommendations || 0) > 0;
  const has_changes = dailyDigest.has_changes || false;
  
  // change_items 생성: broken_items와 weak_warning_items를 하나의 배열로 합침
  const change_items = [];
  
  // BROKEN 항목 추가
  if (dailyDigest.broken_items && Array.isArray(dailyDigest.broken_items)) {
    dailyDigest.broken_items.forEach(item => {
      const name = item.name || item.ticker;
      if (name) {
        change_items.push({
          type: 'BROKEN',
          name: name
        });
      }
    });
  }
  
  // WEAK_WARNING 항목 추가
  if (dailyDigest.weak_warning_items && Array.isArray(dailyDigest.weak_warning_items)) {
    dailyDigest.weak_warning_items.forEach(item => {
      const name = item.name || item.ticker;
      if (name) {
        change_items.push({
          type: 'WEAK_WARNING',
          name: name
        });
      }
    });
  }

  // 레이어 ② 표시 조건: has_changes == true && change_items.length > 0
  const showEventList = has_changes && change_items.length > 0;

  return (
    <div className="bg-white border-b border-gray-200">
      <div className="px-4 py-3">
        {/* 레이어 ①: 신규 추천 요약 (항상 1줄) */}
        <div className="mb-2">
          <p className="text-sm text-gray-700">
            {has_new_recommendations
              ? "오늘 새로운 추천이 추가되었습니다"
              : "오늘은 새로운 추천이 없습니다"}
          </p>
        </div>

        {/* 레이어 ②: 추천 변화 이벤트 목록 (조건부) */}
        {showEventList && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            {change_items.map((item, idx) => {
              // 허용되지 않은 타입은 노출하지 않음
              if (item.type !== 'BROKEN' && item.type !== 'WEAK_WARNING') {
                return null;
              }
              
              // 종목명이 없으면 노출하지 않음
              if (!item.name) {
                return null;
              }

              // 출력 형식 결정
              let eventText = '';
              if (item.type === 'BROKEN') {
                eventText = `${item.name} – 추천 관리 종료`;
              } else if (item.type === 'WEAK_WARNING') {
                eventText = `${item.name} – 이전과 다른 움직임 감지`;
              }

              if (!eventText) {
                return null;
              }

              return (
                <p key={idx} className="text-sm text-gray-700 mt-1 first:mt-0">
                  {eventText}
                </p>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}


