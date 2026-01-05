/**
 * ACTIVE 상태 전용 추천 카드 컴포넌트
 * 
 * 규칙:
 * - ACTIVE 상태만 처리
 * - 수익률 표시 (보조 정보로만, 강조 금지)
 * - 행동 유도 문구 금지
 * - 추천일 + 경과 거래일 표시
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { STATUS_COLOR_CLASSES, BACKEND_STATUS, STATUS_TO_UX } from '../../utils/v3StatusMapping';
import { getTradingDaysElapsed, formatDateForDisplay } from '../../utils/tradingDaysUtils';

export default function ActiveRecommendationCard({ item, isNew = false }) {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [tradingDays, setTradingDays] = useState(0);
  const [formattedDate, setFormattedDate] = useState('');
  
  useEffect(() => {
    setMounted(true);
  }, []);
  
  if (!item || !item.status || item.status !== BACKEND_STATUS.ACTIVE) {
    return null;
  }

  const { ticker, name, recommendation_id, id, anchor_date, created_at, current_return, return_pct, returns } = item;
  const recId = recommendation_id || id;
  
  // 수익률 계산 (보조 정보로만 표시)
  // 우선순위: current_return > returns.current_return > return_pct
  let returnRate = null;
  if (current_return !== undefined && current_return !== null && !isNaN(current_return)) {
    returnRate = current_return;
  } else if (returns && returns.current_return !== undefined && returns.current_return !== null && !isNaN(returns.current_return)) {
    returnRate = returns.current_return;
  } else if (return_pct !== undefined && return_pct !== null && !isNaN(return_pct)) {
    returnRate = return_pct;
  }
  
  // 디버깅 (개발 환경에서만)
  if (process.env.NODE_ENV === 'development') {
    console.log('[ActiveRecommendationCard] 손익률 데이터:', {
      ticker,
      current_return,
      return_pct,
      returns_current_return: returns?.current_return,
      returnRate,
      mounted,
      anchor_close: item.anchor_close
    });
  }
  
  // 추천일 및 경과 거래일 계산
  const recommendationDate = anchor_date || created_at;
  
  // 경과 거래일 즉시 계산 (useEffect 전에 계산하여 메시지 선택에 사용)
  const elapsedTradingDays = recommendationDate ? getTradingDaysElapsed(recommendationDate) : 0;
  
  useEffect(() => {
    if (mounted && recommendationDate) {
      setTradingDays(elapsedTradingDays);
      setFormattedDate(formatDateForDisplay(recommendationDate));
    }
  }, [mounted, recommendationDate, elapsedTradingDays]);

  const colors = STATUS_COLOR_CLASSES[BACKEND_STATUS.ACTIVE];
  
  // 종목명 폴백 처리
  const displayName = name || (ticker ? `${ticker} (종목 정보 불러오는 중)` : '종목 정보 없음');
  
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

  // 문구 테이블에서 가져오기
  const uxConfig = STATUS_TO_UX[BACKEND_STATUS.ACTIVE];
  const summaryText = uxConfig.summary;

  return (
    <div
      onClick={handleClick}
      className={`${colors.cardBg} ${colors.cardBorder} border-2 rounded-lg p-4 cursor-pointer hover:shadow-md transition-shadow`}
    >
      {/* 상단: 종목명 + 현재 손익률 */}
      <div className="flex items-start justify-between mb-3">
        {/* 종목명 */}
        <div className="flex-1 min-w-0">
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
        
        {/* 추천 후 손익 (상단 우측) */}
        <div className="text-right ml-4 flex-shrink-0">
          <div className="text-xs text-gray-500 mb-0.5">추천 후 손익</div>
          {returnRate !== null && returnRate !== undefined && !isNaN(returnRate) ? (
            <span className={`text-sm font-medium ${returnRate > 0 ? 'text-red-500' : returnRate < 0 ? 'text-blue-500' : colors.bodyText}`}>
              {returnRate > 0 ? '+' : ''}{returnRate.toFixed(2)}%
            </span>
          ) : (
            <span className={`text-sm ${colors.bodyText} opacity-50`}>
              —
            </span>
          )}
        </div>
      </div>
      
      {/* 상태 설명 문구 1줄만 */}
      <div className="mt-3 pt-3 border-t border-gray-200">
        <p className={`text-sm font-medium ${colors.bodyText}`}>
          {summaryText}
        </p>
      </div>
      
      {/* 메타 정보: 추천일 + 경과 거래일 (카드 하단) */}
      {mounted && formattedDate && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className={`text-xs ${colors.bodyText} opacity-70`}>
            추천일 {formattedDate} · {elapsedTradingDays}거래일 경과
          </p>
        </div>
      )}
    </div>
  );
}


