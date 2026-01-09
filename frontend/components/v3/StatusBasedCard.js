/**
 * 상태 기반 임시 카드 컴포넌트 (숫자 노출 금지)
 * 
 * 이 단계에서는 최소한의 정보만 표시:
 * - 종목명/티커
 * - 상태 라벨 (ACTIVE, BROKEN)
 * 
 * 가격/수익률/등락 등 숫자 필드는 절대 렌더하지 않음
 */

export default function StatusBasedCard({ item }) {
  if (!item) {
    return null;
  }

  const { ticker, name, status } = item;

  // 상태 라벨 텍스트
  const getStatusLabel = (status) => {
    switch (status) {
      case 'ACTIVE':
        return '유효한 추천';
      case 'BROKEN':
        return '관리 필요';
      case 'ARCHIVED':
        return '아카이브됨';
      default:
        return status || '알 수 없음';
    }
  };

  // 상태별 색상
  const getStatusColor = (status) => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-green-50 border-green-200 text-green-700';
      case 'BROKEN':
        return 'bg-red-50 border-red-200 text-red-700';
      case 'ARCHIVED':
        return 'bg-gray-50 border-gray-200 text-gray-700';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-700';
    }
  };

  const statusLabel = getStatusLabel(status);
  const statusColor = getStatusColor(status);

  return (
    <div className={`bg-white rounded-lg shadow-sm border-2 ${statusColor} p-4`}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-gray-900 truncate">
            {name || '종목명 없음'}
          </h3>
          <div className="flex items-center space-x-2 mt-1">
            <span className="text-xs text-gray-500 font-mono">
              {ticker || '코드 없음'}
            </span>
          </div>
        </div>
        <div className="ml-4">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${statusColor}`}>
            {statusLabel}
          </span>
        </div>
      </div>
    </div>
  );
}



