/**
 * v3 추천 카드 컴포넌트 (백엔드 상태 1:1 매핑)
 * 
 * 규칙:
 * - 백엔드 상태를 정확히 번역만 수행
 * - 판단/해석 금지
 * - 숫자, 점수, 엔진명, 추천 횟수 노출 금지
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { STATUS_TO_UX, STATUS_COLOR_CLASSES, BACKEND_STATUS } from '../../utils/v3StatusMapping';
import { getTradingDaysElapsed, formatDateForDisplay } from '../../utils/tradingDaysUtils';

export default function RecommendationCardV3({ item, isNew = false }) {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [tradingDays, setTradingDays] = useState(0);
  const [formattedDate, setFormattedDate] = useState('');
  
  useEffect(() => {
    setMounted(true);
  }, []);
  
  if (!item || !item.status) {
    return null;
  }

  const { ticker, name, status, recommendation_id, id, anchor_date, created_at, current_return, return_pct } = item;
  // 백엔드가 id를 반환하는 경우 recommendation_id로 매핑
  const recId = recommendation_id || id;
  
  // 수익률 계산 (current_return 또는 return_pct 사용)
  const returnRate = current_return !== undefined && current_return !== null 
    ? current_return 
    : (return_pct !== undefined && return_pct !== null ? return_pct : null);
  
  // 추천일 및 경과 거래일 계산 (ACTIVE/WEAK_WARNING만 표시)
  // Hydration 오류 방지를 위해 클라이언트에서만 계산
  const recommendationDate = anchor_date || created_at;
  
  useEffect(() => {
    if (mounted && recommendationDate) {
      setTradingDays(getTradingDaysElapsed(recommendationDate));
      setFormattedDate(formatDateForDisplay(recommendationDate));
    }
  }, [mounted, recommendationDate]);
  
  // REPLACED는 렌더링하지 않음
  if (status === BACKEND_STATUS.REPLACED) {
    return null;
  }
  
  // ARCHIVED는 기본 화면에 노출하지 않음
  if (status === BACKEND_STATUS.ARCHIVED) {
    return null;
  }

  const ux = STATUS_TO_UX[status];
  const colors = STATUS_COLOR_CLASSES[status];
  
  if (!ux || !colors) {
    console.warn(`[RecommendationCardV3] 알 수 없는 상태: ${status}`);
    return null;
  }

  // 종목명 폴백 처리
  const displayName = name || (ticker ? `${ticker} (종목 정보 불러오는 중)` : '종목 정보 없음');
  
  // name이 없으면 에러 로그
  if (!name && ticker && process.env.NODE_ENV === 'development') {
    console.warn(`[RecommendationCardV3] 종목명 누락: ticker=${ticker}, recommendation_id=${recId}`);
  }
  
  // 신규 뱃지 표시 여부: ACTIVE/WEAK_WARNING만 표시, BROKEN에는 표시하지 않음
  const showNewBadge = isNew && (status === BACKEND_STATUS.ACTIVE || status === BACKEND_STATUS.WEAK_WARNING);

  // 클릭 핸들러: 상세 화면으로 이동
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

  return (
    <div
      onClick={handleClick}
      className={`${colors.cardBg} ${colors.cardBorder} border-2 rounded-lg p-4 cursor-pointer hover:shadow-md transition-shadow`}
    >
      {/* 상단: 상태 배지 + 메타 정보 (우선순위 1) */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          {/* 상태 배지 */}
          <div className="flex items-center space-x-2 mb-2">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${colors.badgeBg} ${colors.badgeText} whitespace-nowrap`}>
              {ux.header}
            </span>
            {/* 신규 뱃지 (ACTIVE/WEAK_WARNING만, 15:35 이전에 오늘 생성된 경우만) */}
            {showNewBadge && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 whitespace-nowrap">
                신규
              </span>
            )}
          </div>
          
          {/* 메타 정보: 추천일 + 경과 거래일 + ARCHIVED 전이까지 남은 거래일 (상태 배지 바로 아래, 우선순위 2) */}
          {mounted && (status === BACKEND_STATUS.ACTIVE || status === BACKEND_STATUS.WEAK_WARNING) && formattedDate && (
            <p className={`text-xs ${colors.bodyText} opacity-70 font-medium`}>
              추천일 {formattedDate} · 경과 {tradingDays}거래일
              {item.days_until_archive !== null && item.days_until_archive !== undefined && (
                <span className="ml-2">
                  · ARCHIVED 전이까지 {item.days_until_archive}일 남음
                </span>
              )}
            </p>
          )}
        </div>
      </div>
      
      {/* 종목명 */}
      <div className="mb-3">
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
      
      {/* 상태 요약 및 가이드 */}
      <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
        <p className={`text-sm font-medium ${colors.bodyText}`}>
          {ux.summary}
        </p>
        
        {/* 행동 가이드 */}
        {ux.actionGuide && (
          <p className={`text-sm ${colors.bodyText}`}>
            {ux.actionGuide}
          </p>
        )}
        
        {/* 수익률 표시 (낮은 시각적 우선순위, 하단 배치) */}
        {mounted && (status === BACKEND_STATUS.ACTIVE || status === BACKEND_STATUS.WEAK_WARNING) && returnRate !== null && returnRate !== undefined && !isNaN(returnRate) && (
          <p className="text-xs text-gray-400 opacity-60 mt-2">
            {returnRate > 0 ? '+' : ''}{returnRate.toFixed(2)}%
          </p>
        )}
        
        {/* 보조 설명 (선택) */}
        {ux.helperText && (
          <p className={`text-xs ${colors.bodyText} opacity-75`}>
            {ux.helperText}
          </p>
        )}
      </div>

      {/* 신규 진입 CTA 버튼 (ACTIVE/WEAK_WARNING만 허용, BROKEN 금지) */}
      {ux.allowEntryCTA && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={(e) => {
              e.stopPropagation(); // 카드 클릭 이벤트 방지
              handleClick();
            }}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            차트 보기
          </button>
        </div>
      )}
    </div>
  );
}

