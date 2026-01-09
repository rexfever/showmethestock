/**
 * 상태 기반 섹션 헤더 컴포넌트
 * 
 * 기능:
 * - 섹션 제목
 * - 보조 문구 (BROKEN: "추천 당시 가정이 깨진 종목입니다")
 * - 개수 배지 (BROKEN)
 * - 요약줄 (ACTIVE: "X개 (신규 Y)")
 * - 접힘/펼침 토글 버튼
 */

export default function StatusSectionHeader({
  title,
  count,
  isCollapsed,
  onToggle,
  sectionType, // 'BROKEN' | 'ACTIVE' | 'ARCHIVED'
  helperText // 보조 문구 (BROKEN 섹션용)
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200">
      <div className="flex-1">
        <div className="flex items-center space-x-2">
          <h3 className={`text-base font-semibold ${sectionType === 'BROKEN' ? 'text-red-800' : 'text-gray-900'}`}>
            {title}
            {(sectionType === 'BROKEN' || sectionType === 'ACTIVE') && count > 0 && (
              <span className="text-gray-900 font-normal"> ({count})</span>
            )}
          </h3>
        </div>
        
        {/* 보조 문구 (BROKEN 섹션용) */}
        {helperText && (
          <p className="text-xs text-gray-500 mt-1">
            {helperText}
          </p>
        )}
      </div>
      
      {/* 토글 버튼 */}
      <button
        onClick={onToggle}
        className="flex items-center justify-center w-10 h-10 rounded-lg hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 ml-4"
        aria-label={isCollapsed ? '펼치기' : '접기'}
        aria-expanded={!isCollapsed}
      >
        <svg
          className={`w-5 h-5 text-gray-600 transition-transform${isCollapsed ? '' : ' rotate-180'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    </div>
  );
}

