/**
 * v3 ARCHIVED 추천 카드 컴포넌트
 * 
 * 규칙:
 * - ARCHIVED는 "관리 종료" 기록으로만 표시
 * - 성과/행동 유도 완전 제거
 * - 중립 색상, CTA 없음
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { getTradingDaysElapsed, getTradingDaysBetween, formatDateForDisplay } from '../../utils/tradingDaysUtils';
import { getTerminationReasonText } from '../../utils/v3StatusMapping';

export default function ArchivedCardV3({ item }) {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [tradingDays, setTradingDays] = useState(0);
  const [formattedDate, setFormattedDate] = useState('');
  
  useEffect(() => {
    setMounted(true);
  }, []);
  
  if (!item || !item.status || item.status !== 'ARCHIVED') {
    return null;
  }

  const { ticker, name, recommendation_id, id, anchor_date, created_at, current_return, updated_at, archived_at, observation_period_days, archive_return_pct, archive_reason } = item;
  const recId = recommendation_id || id;
  
  // 수익률 계산 (ARCHIVED 스냅샷 우선, 없으면 current_return)
  // archive_return_pct가 있으면 사용 (ARCHIVED 전환 시점의 수익률 - 종료 시점 고정)
  let returnRate = null;
  if (archive_return_pct !== undefined && archive_return_pct !== null && !isNaN(archive_return_pct)) {
    returnRate = archive_return_pct;
  } else if (current_return !== undefined && current_return !== null && !isNaN(current_return)) {
    returnRate = current_return;
  }
  
  // 디버깅: 수익률 확인
  if (process.env.NODE_ENV === 'development') {
    if (returnRate === null) {
      console.warn('[ArchivedCardV3] 수익률이 없습니다:', {
        ticker,
        archive_return_pct,
        current_return
      });
    }
  }
  
  // 종료 사유 문구 가져오기 (추가 정보 없이)
  const reasonText = getTerminationReasonText(archive_reason);
  
  // 추천일 및 관찰 기간 계산
  const recommendationDate = anchor_date || created_at;
  
  useEffect(() => {
    if (mounted && recommendationDate) {
      // observation_period_days가 있으면 사용
      if (observation_period_days !== undefined && observation_period_days !== null) {
        setTradingDays(observation_period_days);
      } else if (archived_at) {
        // archived_at이 있으면 anchor_date부터 archived_at까지의 거래일 계산
        try {
          const tradingDays = getTradingDaysBetween(recommendationDate, archived_at);
          setTradingDays(tradingDays);
        } catch (e) {
          console.error('[ArchivedCardV3] 거래일 계산 오류:', e);
          // 계산 실패 시 현재까지 계산
          setTradingDays(getTradingDaysElapsed(recommendationDate));
        }
      } else {
        // 종료 시점이 없으면 현재까지 계산
        setTradingDays(getTradingDaysElapsed(recommendationDate));
      }
      setFormattedDate(formatDateForDisplay(recommendationDate));
    }
  }, [mounted, recommendationDate, observation_period_days, archived_at]);

  // 종목명 폴백 처리
  const displayName = name || (ticker ? `${ticker} (종목 정보 불러오는 중)` : '종목 정보 없음');

  // 클릭 핸들러: 상세 화면으로 이동 (정보 확인용)
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

  // 새로운 본문 문구 만들지 않음 (스펙에 따라)

  return (
    <div
      onClick={handleClick}
      className="bg-gray-50 border-2 border-gray-200 rounded-lg p-4 cursor-pointer hover:shadow-md transition-shadow"
    >
      {/* 상단: 상태 배지 + 메타 정보 */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          {/* 메타 정보: 추천일 + 기간 */}
          {mounted && formattedDate && (
            <p className="text-xs text-gray-600 opacity-70 font-medium">
              추천일 {formattedDate} · {tradingDays}거래일
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
      
      {/* 종료 사유 (BROKEN의 종료 사유만 표시) */}
      <div className="mt-3 pt-3 border-t border-gray-200">
        <p className="text-sm text-gray-700">
          사유: {reasonText || '관리 기간 종료'}
        </p>
      </div>
    </div>
  );
}

