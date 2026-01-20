/**
 * BROKEN 카드 컴포넌트 (v3 홈 화면)
 * 
 * 필수 표시:
 * - 종목명(티커 포함 가능, 권장)
 * - 고정 문구 2줄:
 *   1) "추천 당시 가정이 깨졌습니다"
 *   2) "리스크 관점에서 정리를 고려하세요"
 * 
 * 금지:
 * - 매도/손절 지시
 * - 재추천/재진입 암시
 * - 숫자 전부
 * 
 * 클릭: 상세 화면으로 이동
 */

import { useRouter } from 'next/router';

export default function BrokenStockCardV3({ item }) {
  const router = useRouter();
  
  if (!item) {
    return null;
  }

  const { ticker, name, recommended_date, date, scanner_version } = item;

  // 클릭 핸들러: 상세 화면으로 이동 (v3 플래그 및 추천 인스턴스 정보 추가)
  const handleClick = () => {
    if (ticker) {
      // 추천 인스턴스 정보를 query parameter로 전달
      const recDate = recommended_date || date || '';
      const recVersion = scanner_version || 'v3';
      router.push(`/stock-analysis?ticker=${ticker}&from=v3&rec_date=${recDate}&rec_version=${recVersion}`);
    }
  };

  return (
    <div
      onClick={handleClick}
      className="bg-white rounded-lg border-2 border-red-200 p-4 cursor-pointer hover:shadow-md transition-shadow"
    >
      <div className="mb-3">
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
      
      {/* 고정 문구 2줄 */}
      <div className="mt-3 pt-3 border-t border-red-100 space-y-2">
        <p className="text-sm text-gray-700 font-medium">
          추천 당시 가정이 깨졌습니다
        </p>
        <p className="text-sm text-gray-700 font-medium">
          리스크 관점에서 정리를 고려하세요
        </p>
      </div>
    </div>
  );
}

