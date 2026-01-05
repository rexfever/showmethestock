/**
 * ACTIVE 카드 컴포넌트 (v3 홈 화면)
 * 
 * 필수 표시:
 * - 종목명(티커 포함 가능)
 * - 상태 배지: "유효"
 * - 조건부 배지: "신규" (오늘 생성된 ACTIVE일 때만)
 * - 1줄 고정 문구: 신규일 때 "새로운 기회로 포착되었습니다", 유지일 때 "추천 가정이 유지되고 있습니다"
 * 
 * 금지:
 * - 가격/수익률/등락/손익/목표가/손절가 등 숫자 전부
 * - 매수/매도/추가매수/익절 등 매매 지시/암시
 * - 재진입/재추천 암시
 * 
 * 클릭: 상세 화면으로 이동
 */

import { useRouter } from 'next/router';

export default function ActiveStockCardV3({ item, isNew = false }) {
  const router = useRouter();
  
  if (!item) {
    return null;
  }

  const { ticker, name } = item;

  // 클릭 핸들러: 상세 화면으로 이동 (v3 플래그 추가)
  const handleClick = () => {
    if (ticker) {
      router.push(`/stock-analysis?ticker=${ticker}&from=v3`);
    }
  };

  // 고정 문구: 신규일 때와 유지일 때
  const message = isNew 
    ? '새로운 기회로 포착되었습니다'
    : '추천 가정이 유지되고 있습니다';

  return (
    <div
      onClick={handleClick}
      className="bg-white rounded-lg border-2 border-green-200 p-4 cursor-pointer hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-gray-900 truncate">
            {name || '종목명 없음'}
          </h3>
          {ticker && (
            <div className="mt-1">
              <span className="text-xs text-gray-500 font-mono">
                {ticker}
              </span>
            </div>
          )}
        </div>
        <div className="ml-4 flex items-start space-x-2">
          {/* 상태 배지: "유효" */}
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 whitespace-nowrap">
            유효
          </span>
          {/* 조건부 배지: "신규" */}
          {isNew && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 whitespace-nowrap">
              신규
            </span>
          )}
        </div>
      </div>
      
      {/* 고정 문구 1줄 */}
      <div className="mt-3 pt-3 border-t border-green-100">
        <p className="text-sm text-gray-700">
          {message}
        </p>
      </div>
    </div>
  );
}

