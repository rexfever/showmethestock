/**
 * Scanner V3 전용 종목 카드 컴포넌트
 * 사용자 행동 안내 중심의 UX
 * 숫자, 점수, 엔진명은 기본 카드에서 숨김
 */
import { useState } from 'react';
import { CARD_COPY } from '../../utils/cardCopy';

// 상태 enum
export const STOCK_STATUS = {
  BEFORE_ENTRY: 'BEFORE_ENTRY',           // 진입 전
  OBSERVING: 'OBSERVING',                 // 관찰 (비추천 종목 전용)
  JUST_RECOMMENDED: 'JUST_RECOMMENDED',   // 추천 직후
  RECOMMENDED_PROGRESS: 'RECOMMENDED_PROGRESS',  // 추천/목표 진행 (ON_TRACK)
  WEAK_WARNING: 'WEAK_WARNING',           // 약한 경고
  STRONG_WARNING: 'STRONG_WARNING'        // 강한 경고
};

// 상태별 색상 클래스 (CARD_COPY와 분리하여 관리)
const STATUS_COLORS = {
  [STOCK_STATUS.BEFORE_ENTRY]: {
    colorClass: 'bg-gray-50 border-gray-200',
    statusColorClass: 'text-gray-700',
    actionColorClass: 'text-gray-600'
  },
  [STOCK_STATUS.OBSERVING]: {
    colorClass: 'bg-blue-50 border-blue-200',
    statusColorClass: 'text-blue-700',
    actionColorClass: 'text-blue-600'
  },
  [STOCK_STATUS.RECOMMENDED_PROGRESS]: {
    colorClass: 'bg-green-50 border-green-200',
    statusColorClass: 'text-green-700',
    actionColorClass: 'text-green-600'
  },
  [STOCK_STATUS.WEAK_WARNING]: {
    colorClass: 'bg-yellow-50 border-yellow-200',
    statusColorClass: 'text-yellow-700',
    actionColorClass: 'text-yellow-600'
  },
  [STOCK_STATUS.STRONG_WARNING]: {
    colorClass: 'bg-red-50 border-red-200',
    statusColorClass: 'text-red-700',
    actionColorClass: 'text-red-600'
  }
};

// 상태별 문구 상수 (CARD_COPY 기반, A/B 테스트 가능하도록 분리)
export const STATUS_MESSAGES = {
  [STOCK_STATUS.BEFORE_ENTRY]: {
    status: CARD_COPY.PRE_ENTRY.title,
    action: CARD_COPY.PRE_ENTRY.action,
    description: CARD_COPY.PRE_ENTRY.desc,
    ...STATUS_COLORS[STOCK_STATUS.BEFORE_ENTRY]
  },
  [STOCK_STATUS.OBSERVING]: {
    status: CARD_COPY.OBSERVING.title,
    action: CARD_COPY.OBSERVING.action,
    description: CARD_COPY.OBSERVING.desc,
    ...STATUS_COLORS[STOCK_STATUS.OBSERVING]
  },
  [STOCK_STATUS.JUST_RECOMMENDED]: {
    status: CARD_COPY.JUST_RECOMMENDED.title,
    action: CARD_COPY.JUST_RECOMMENDED.action,
    description: CARD_COPY.JUST_RECOMMENDED.desc,
    // 추천 직후는 파란색 계열 사용 (OBSERVING과 동일)
    colorClass: 'bg-blue-50 border-blue-200',
    statusColorClass: 'text-blue-700',
    actionColorClass: 'text-blue-600'
  },
  [STOCK_STATUS.RECOMMENDED_PROGRESS]: {
    status: CARD_COPY.ON_TRACK.title,
    action: CARD_COPY.ON_TRACK.action,
    description: CARD_COPY.ON_TRACK.desc,
    ...STATUS_COLORS[STOCK_STATUS.RECOMMENDED_PROGRESS]
  },
  [STOCK_STATUS.WEAK_WARNING]: {
    status: CARD_COPY.WEAK_WARNING.title,
    action: CARD_COPY.WEAK_WARNING.action,
    description: CARD_COPY.WEAK_WARNING.desc,
    ...STATUS_COLORS[STOCK_STATUS.WEAK_WARNING]
  },
  [STOCK_STATUS.STRONG_WARNING]: {
    status: CARD_COPY.STRONG_WARNING.title,
    action: CARD_COPY.STRONG_WARNING.action,
    description: CARD_COPY.STRONG_WARNING.desc,
    ...STATUS_COLORS[STOCK_STATUS.STRONG_WARNING]
  }
};

/**
 * 휴장일 여부 판단 (토/일)
 * @param {Date} date - 확인할 날짜 (선택, 없으면 오늘)
 * @returns {boolean} 휴장일이면 true
 */
function isMarketClosed(date = null) {
  const checkDate = date || new Date();
  const dayOfWeek = checkDate.getDay(); // 0 = 일요일, 6 = 토요일
  return dayOfWeek === 0 || dayOfWeek === 6;
}

/**
 * 추천일 이후 실제 거래일 수 계산 (주말 제외)
 * @param {string} recommendedDateStr - 추천일 (YYYYMMDD 또는 YYYY-MM-DD)
 * @returns {number} 실제 거래일 수
 */
function getTradingDaysElapsed(recommendedDateStr) {
  if (!recommendedDateStr) return 0;
  
  try {
    let recDate = null;
    const recDateStr = String(recommendedDateStr);
    
    // YYYYMMDD 형식
    if (recDateStr.length === 8 && /^\d+$/.test(recDateStr)) {
      const recYear = parseInt(recDateStr.slice(0, 4));
      const recMonth = parseInt(recDateStr.slice(4, 6)) - 1;
      const recDay = parseInt(recDateStr.slice(6, 8));
      recDate = new Date(recYear, recMonth, recDay);
    }
    // YYYY-MM-DD 형식
    else if (recDateStr.includes('-')) {
      recDate = new Date(recDateStr);
    }
    else {
      recDate = new Date(recDateStr);
    }
    
    if (!recDate || isNaN(recDate.getTime())) {
      return 0;
    }
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    recDate.setHours(0, 0, 0, 0);
    
    // 추천일이 오늘 이후면 0
    if (recDate > today) {
      return 0;
    }
    
    // 추천일부터 오늘까지의 실제 거래일 수 계산 (주말 제외)
    let tradingDays = 0;
    let currentDate = new Date(recDate);
    
    while (currentDate <= today) {
      const dayOfWeek = currentDate.getDay();
      // 주말이 아니면 거래일
      if (dayOfWeek !== 0 && dayOfWeek !== 6) {
        tradingDays++;
      }
      // 다음 날로 이동
      currentDate.setDate(currentDate.getDate() + 1);
    }
    
    // 추천일 당일은 0일로 계산 (첫 거래일은 다음 거래일)
    return Math.max(0, tradingDays - 1);
  } catch (e) {
    console.warn('[StockCardV3] Failed to calculate trading days:', e);
    return 0;
  }
}

/**
 * 종목 상태 판별 함수 (DEPRECATED - 서버 status 필드 사용)
 * @param {Object} item - 종목 데이터
 * @returns {string} 상태 enum 값
 * @deprecated 서버에서 내려주는 status 필드를 사용하세요. 이 함수는 더 이상 사용되지 않습니다.
 * 
 * ⚠️ 이 함수는 더 이상 호출되지 않아야 합니다.
 * 서버에서 내려주는 item.status 필드를 mapDomainStatusToUIStatus로 매핑하여 사용하세요.
 */
function determineStockStatus(item) {
  // 이 함수가 호출되면 경고 로그 출력 (회귀 방지)
  console.error('[StockCardV3] ⚠️ determineStockStatus가 호출되었습니다! 이는 버그입니다.', {
    ticker: item?.ticker,
    name: item?.name,
    stack: new Error().stack,
    message: '서버 status 필드를 사용해야 합니다. mapDomainStatusToUIStatus를 사용하세요.'
  });
  
  if (!item) {
    return STOCK_STATUS.BEFORE_ENTRY;
  }

  // flags 파싱 (문자열일 수 있음)
  let flags = item.flags || {};
  if (typeof flags === 'string') {
    try {
      flags = JSON.parse(flags);
    } catch (e) {
      console.warn('[StockCardV3] Failed to parse flags:', e);
      flags = {};
    }
  }

  // returns 파싱 (문자열일 수 있음)
  let returns = item.returns || {};
  if (typeof returns === 'string') {
    try {
      returns = JSON.parse(returns);
    } catch (e) {
      console.warn('[StockCardV3] Failed to parse returns:', e);
      returns = {};
    }
  }

  let {
    recommended_date,
    recommended_price,
    current_return: itemCurrentReturn
  } = item;

  // recommended_date를 문자열로 변환 (숫자일 수 있음)
  if (recommended_date && typeof recommended_date !== 'string') {
    recommended_date = String(recommended_date);
  }

  // recommended_price를 숫자로 변환
  if (recommended_price && typeof recommended_price !== 'number') {
    recommended_price = parseFloat(recommended_price);
  }

  // current_return은 item.current_return 또는 returns.current_return에서 가져오기
  let current_return = itemCurrentReturn;
  if ((current_return === null || current_return === undefined || isNaN(current_return)) && returns) {
    current_return = returns.current_return;
  }

  // 추천 여부 판단: recommended_date와 recommended_price가 있으면 추천된 종목
  const isRecommended = recommended_date && recommended_price && recommended_price > 0 && !isNaN(recommended_price);
  
  // 추천되지 않은 종목은 진입 전 또는 관찰 상태
  if (!isRecommended) {
    // current_return이 있으면 관찰 상태, 없으면 진입 전
    if (typeof current_return === 'number' && !isNaN(current_return)) {
      return STOCK_STATUS.OBSERVING;
    }
    return STOCK_STATUS.BEFORE_ENTRY;
  }

  // 추천일로부터 경과 일수 확인 (returns.days_elapsed 또는 계산)
  let daysElapsed = 0;
  if (returns && returns.days_elapsed !== undefined && returns.days_elapsed !== null) {
    daysElapsed = returns.days_elapsed;
  } else if (recommended_date) {
    try {
      const recDateStr = String(recommended_date);
      let recDate = null;
      
      // YYYYMMDD 형식 (예: 20251226)
      if (recDateStr.length === 8 && /^\d+$/.test(recDateStr)) {
        const recYear = parseInt(recDateStr.slice(0, 4));
        const recMonth = parseInt(recDateStr.slice(4, 6)) - 1;
        const recDay = parseInt(recDateStr.slice(6, 8));
        recDate = new Date(recYear, recMonth, recDay);
      }
      // YYYY-MM-DD 형식 (예: 2025-12-26)
      else if (recDateStr.includes('-')) {
        recDate = new Date(recDateStr);
      }
      // 그 외 형식은 Date 생성자에 직접 전달
      else {
        recDate = new Date(recDateStr);
      }
      
      if (recDate && !isNaN(recDate.getTime())) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        recDate.setHours(0, 0, 0, 0);
        daysElapsed = Math.floor((today - recDate) / (1000 * 60 * 60 * 24));
        // 음수는 0으로 처리 (미래 날짜)
        if (daysElapsed < 0) {
          daysElapsed = 0;
        }
      }
    } catch (e) {
      // 날짜 파싱 실패 시 0으로 처리
      console.warn('[StockCardV3] Failed to parse recommended_date:', recommended_date, e);
      daysElapsed = 0;
    }
  }

  // 추천 직후 초기 구간(2~3 거래일)에는 경고를 매우 보수적으로 처리
  const isInitialPeriod = daysElapsed <= 2;

  // target_profit과 stop_loss 추출
  let targetProfit = null;
  let stopLoss = null;

  if (flags.target_profit !== undefined && flags.target_profit !== null) {
    targetProfit = parseFloat(flags.target_profit) * 100; // 소수 -> 퍼센트
  }
  if (flags.stop_loss !== undefined && flags.stop_loss !== null) {
    // stop_loss는 양수로 저장되어 있으므로 음수로 변환 (예: 0.02 -> -2.0)
    stopLoss = -Math.abs(parseFloat(flags.stop_loss) * 100);
  }

  // strategy에 따라 기본값 설정 (백엔드에서 전달되지 않은 경우)
  if (!targetProfit && item.strategy) {
    if (item.strategy === 'v2_lite' || item.strategy === '눌림목') {
      targetProfit = 5.0;
      stopLoss = stopLoss || -2.0; // 음수로 저장
    } else if (item.strategy === 'midterm') {
      targetProfit = 10.0;
      stopLoss = stopLoss || -7.0; // 음수로 저장
    }
  }

  // ===== 추천된 종목의 상태 판정 (OBSERVING 절대 사용 안 함) =====
  
  // current_return이 없거나 유효하지 않으면 추천 직후로 처리
  if (typeof current_return !== 'number' || isNaN(current_return)) {
    return STOCK_STATUS.JUST_RECOMMENDED;
  }

  // 휴장일 여부 확인
  const today = new Date();
  const isClosedToday = isMarketClosed(today);
  
  // 추천일 이후 실제 거래일 수 계산 (주말 제외)
  const tradingDaysElapsed = getTradingDaysElapsed(recommended_date);
  
  // 추천 직후 판단:
  // 1. 실제 거래일이 0일이면 (첫 거래일 전) → JUST_RECOMMENDED
  // 2. 오늘이 휴장일이고 실제 거래일이 0일이면 → JUST_RECOMMENDED
  // 3. 실제 거래일이 1일 이하이면 → JUST_RECOMMENDED
  if (tradingDaysElapsed === 0 || (isClosedToday && tradingDaysElapsed <= 1)) {
    return STOCK_STATUS.JUST_RECOMMENDED;
  }
  
  // 캘린더 일수 기준으로도 체크 (하위 호환성)
  if (daysElapsed <= 1) {
    return STOCK_STATUS.JUST_RECOMMENDED;
  }

  // STRONG_WARNING: 추천 가정 붕괴 또는 손절 기준 도달
  // 명시적인 가정 붕괴 플래그가 있거나, 손절 기준을 넘어선 경우
  const assumptionBroken = flags.assumption_broken === true || 
                           flags.flow_broken === true ||
                           (stopLoss !== null && current_return <= stopLoss && !isInitialPeriod);
  
  if (assumptionBroken) {
    return STOCK_STATUS.STRONG_WARNING;
  }

  // WEAK_WARNING: 명시적인 흐름 악화 신호가 있을 때만
  // 초기 구간(2일 이내)에는 경고를 표시하지 않음
  // 양수 수익률이고 명시적 악화 신호가 없으면 경고가 나오면 안 됨
  const hasExplicitWeakSignal = flags.momentum_weak === true ||
                                 flags.flow_weak === true ||
                                 flags.trend_weak === true;
  
  // 명시적 악화 신호가 있고, 초기 구간이 아니며, 실제로 악화된 경우만 경고
  if (hasExplicitWeakSignal && !isInitialPeriod && current_return < 0) {
    return STOCK_STATUS.WEAK_WARNING;
  }

  // 목표 수익률 달성 여부 (추천/목표 진행)
  if (current_return >= targetProfit) {
    return STOCK_STATUS.RECOMMENDED_PROGRESS;
  }

  // 기본 상태: 추천 유지 (ON_TRACK)
  // 목표 미달이어도 추천된 종목이므로 "추천 이후 흐름이 유지되고 있습니다" 표시
  // target_profit이 없어도 추천된 종목이므로 ON_TRACK 반환
  return STOCK_STATUS.RECOMMENDED_PROGRESS;
}

/**
 * 서버 도메인 상태를 v3 UI 상태로 매핑
 * @param {string} domainStatus - 서버에서 내려주는 도메인 상태 (ACTIVE, BROKEN, ARCHIVED)
 * @param {Object} item - 종목 데이터
 * @returns {string} v3 UI 상태 enum 값
 */
function mapDomainStatusToUIStatus(domainStatus, item) {
  if (!domainStatus) {
    console.error('[StockCardV3] mapDomainStatusToUIStatus: domainStatus가 없습니다.', item);
    return STOCK_STATUS.OBSERVING;
  }
  
  switch (domainStatus) {
    case 'ACTIVE':
      // 유효한 추천: 추천 직후 또는 추천 진행 중
      // recommended_date와 recommended_price로 추천 직후 여부 판단
      const recommendedDate = item.recommended_date;
      const recommendedPrice = item.recommended_price;
      
      if (!recommendedDate || !recommendedPrice) {
        // 추천 정보가 없으면 관찰 상태
        return STOCK_STATUS.OBSERVING;
      }
      
      // 추천일로부터 경과 일수 확인
      const tradingDaysElapsed = getTradingDaysElapsed(recommendedDate);
      
      // 추천 직후 (1거래일 이하)
      if (tradingDaysElapsed <= 1) {
        return STOCK_STATUS.JUST_RECOMMENDED;
      }
      
      // 추천 진행 중 (목표 달성 또는 진행 중)
      return STOCK_STATUS.RECOMMENDED_PROGRESS;
      
    case 'BROKEN':
      // 관리 필요 종목: 강한 경고
      return STOCK_STATUS.STRONG_WARNING;
      
    case 'ARCHIVED':
      // 아카이브됨: 홈에서는 노출하지 않지만, 혹시 노출되면 관찰 상태로 처리
      return STOCK_STATUS.OBSERVING;
      
    default:
      console.warn('[StockCardV3] 알 수 없는 domainStatus:', domainStatus, item);
      return STOCK_STATUS.OBSERVING;
  }
}

/**
 * 휴장일 판단 함수
 * @returns {boolean} 현재가 휴장일(토/일)이면 true
 */
function isMarketClosedToday() {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0 = 일요일, 6 = 토요일
  return dayOfWeek === 0 || dayOfWeek === 6;
}

/**
 * 상세 정보 모달/드로어 컴포넌트
 */
function DetailDrawer({ item, isOpen, onClose }) {
  const [showDetailedNumbers, setShowDetailedNumbers] = useState(false);
  
  if (!isOpen || !item) return null;

  // flags 파싱 (문자열일 수 있음)
  let flags = item.flags || {};
  if (typeof flags === 'string') {
    try {
      flags = JSON.parse(flags);
    } catch (e) {
      console.warn('[StockCardV3 DetailDrawer] Failed to parse flags:', e);
      flags = {};
    }
  }

  // returns 파싱 (문자열일 수 있음)
  let returns = item.returns || {};
  if (typeof returns === 'string') {
    try {
      returns = JSON.parse(returns);
    } catch (e) {
      console.warn('[StockCardV3 DetailDrawer] Failed to parse returns:', e);
      returns = {};
    }
  }

  const {
    ticker,
    name,
    score,
    score_label,
    strategy,
    current_price,
    change_rate,
    market,
    recommended_price,
    recommended_date,
    current_return: itemCurrentReturn
  } = item;

  // current_return은 item.current_return 또는 returns.current_return에서 가져오기
  let current_return = itemCurrentReturn;
  if ((current_return === null || current_return === undefined || isNaN(current_return)) && returns) {
    current_return = returns.current_return;
  }

  const max_return = returns.max_return || (current_return > 0 ? current_return : 0);
  const min_return = returns.min_return || (current_return < 0 ? current_return : 0);
  
  // 상태 판별: 서버에서 내려주는 status 필드 사용 (카드와 동일)
  let status;
  const domainStatus = item.status;
  
  if (!domainStatus) {
    console.error('[StockCardV3 DetailDrawer] API 계약 위반: status 필드가 없습니다.', item);
    if (process.env.NODE_ENV === 'development') {
      throw new Error(`[StockCardV3 DetailDrawer] API 계약 위반: item.status가 없습니다. ticker=${item.ticker}`);
    }
    status = STOCK_STATUS.OBSERVING;
  } else {
    status = mapDomainStatusToUIStatus(domainStatus, item);
  }
  
  let messages = STATUS_MESSAGES[status];
  if (!messages) {
    messages = STATUS_MESSAGES[STOCK_STATUS.OBSERVING];
  }
  
  // target_profit, stop_loss 추출 (getExpandedInfo에서 사용하기 위해 먼저 계산)
  let targetProfit = null;
  let stopLoss = null;
  let holdingPeriod = null;

  if (flags.target_profit !== undefined && flags.target_profit !== null) {
    targetProfit = parseFloat(flags.target_profit) * 100; // 퍼센트로 변환
  }
  if (flags.stop_loss !== undefined && flags.stop_loss !== null) {
    stopLoss = parseFloat(flags.stop_loss) * 100; // 퍼센트로 변환
  }
  if (flags.holding_period !== undefined && flags.holding_period !== null) {
    holdingPeriod = flags.holding_period;
  }

  // strategy에 따라 기본값 설정
  if (!targetProfit && strategy) {
    if (strategy === 'v2_lite' || strategy === '눌림목') {
      targetProfit = 5.0;
      stopLoss = stopLoss || 2.0;
      holdingPeriod = holdingPeriod || 14;
    } else if (strategy === 'midterm') {
      targetProfit = 10.0;
      stopLoss = stopLoss || 7.0;
      holdingPeriod = holdingPeriod || 15;
    }
  }
  
  // 추천일 이후 실제 거래일 수 계산
  const tradingDaysElapsed = getTradingDaysElapsed(recommended_date);
  
  // 추천일 포맷팅
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    
    // YYYYMMDD 형식
    if (typeof dateStr === 'string' && dateStr.length === 8) {
      const year = dateStr.slice(0, 4);
      const month = dateStr.slice(4, 6);
      const day = dateStr.slice(6, 8);
      try {
        const dateObj = new Date(`${year}-${month}-${day}`);
        const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
        const weekday = weekdays[dateObj.getDay()];
        return `${year}년 ${parseInt(month)}월 ${parseInt(day)}일 (${weekday})`;
      } catch (e) {
        return `${year}년 ${parseInt(month)}월 ${parseInt(day)}일`;
      }
    }
    
    // YYYY-MM-DD 형식
    if (typeof dateStr === 'string' && dateStr.includes('-')) {
      const parts = dateStr.split('-');
      if (parts.length === 3) {
        try {
          const dateObj = new Date(dateStr);
          const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
          const weekday = weekdays[dateObj.getDay()];
          return `${parts[0]}년 ${parts[1]}월 ${parts[2]}일 (${weekday})`;
        } catch (e) {
          return `${parts[0]}년 ${parts[1]}월 ${parts[2]}일`;
        }
      }
    }
    
    return String(dateStr);
  };
  
  // 확장 정보 생성
  const getExpandedInfo = () => {
    const info = [];
    
    // 1. 추천 타임라인
    if (recommended_date) {
      const daysText = tradingDaysElapsed === 0 
        ? '첫 거래일 전' 
        : tradingDaysElapsed === 1 
        ? '1거래일 경과' 
        : `${tradingDaysElapsed}거래일 경과`;
      info.push({
        label: '추천 타임라인',
        value: `${formatDate(recommended_date)} · ${daysText}`
      });
    }
    
    // 2. 추천 이후 흐름 요약
    if (typeof current_return === 'number' && !isNaN(current_return)) {
      let flowSummary = '';
      if (status === STOCK_STATUS.JUST_RECOMMENDED) {
        flowSummary = '추천 직후 단계로, 초기 변동이 있을 수 있습니다';
      } else if (status === STOCK_STATUS.RECOMMENDED_PROGRESS) {
        if (current_return >= 0) {
          flowSummary = '추천 이후 흐름이 유지되고 있습니다';
        } else {
          flowSummary = '추천 이후 일시적 조정 중입니다';
        }
      } else if (status === STOCK_STATUS.WEAK_WARNING) {
        flowSummary = '추천 이후 흐름이 다소 약해지고 있습니다';
      } else if (status === STOCK_STATUS.STRONG_WARNING) {
        flowSummary = '추천 당시 가정이 깨졌습니다';
      }
      
      if (max_return > current_return && max_return > 0) {
        flowSummary += ` (최고 ${max_return.toFixed(1)}% 달성 후 조정)`;
      }
      
      if (flowSummary) {
        info.push({
          label: '추천 이후 흐름',
          value: flowSummary
        });
      }
    }
    
    // 3. 다음 체크 포인트
    if (status === STOCK_STATUS.JUST_RECOMMENDED) {
      info.push({
        label: '다음 체크 포인트',
        value: '다음 거래일 흐름을 먼저 확인하세요'
      });
    } else if (status === STOCK_STATUS.RECOMMENDED_PROGRESS) {
      if (typeof current_return === 'number' && current_return < 0) {
        info.push({
          label: '다음 체크 포인트',
          value: '다음 거래일에 회복 여부를 확인하세요'
        });
      } else {
        info.push({
          label: '다음 체크 포인트',
          value: '계획대로 보유 관점에서 지켜보세요'
        });
      }
    } else if (status === STOCK_STATUS.WEAK_WARNING) {
      info.push({
        label: '다음 체크 포인트',
        value: '비중을 늘리기보다는 주의 깊게 관찰하세요'
      });
    } else if (status === STOCK_STATUS.STRONG_WARNING) {
      info.push({
        label: '다음 체크 포인트',
        value: '리스크 관점에서 정리를 고려하세요'
      });
    }
    
    // 4. 리스크가 깨진 이유 유형
    if (status === STOCK_STATUS.WEAK_WARNING || status === STOCK_STATUS.STRONG_WARNING) {
      const reasons = [];
      if (flags.momentum_weak === true) reasons.push('모멘텀 약화');
      if (flags.flow_weak === true) reasons.push('흐름 약화');
      if (flags.trend_weak === true) reasons.push('추세 약화');
      if (flags.assumption_broken === true) reasons.push('가정 붕괴');
      if (flags.flow_broken === true) reasons.push('흐름 붕괴');
      
      if (reasons.length > 0) {
        info.push({
          label: '리스크 신호',
          value: reasons.join(', ')
        });
      } else if (typeof current_return === 'number' && stopLoss !== null) {
        const stopLossValue = parseFloat(stopLoss);
        if (current_return <= stopLossValue) {
          info.push({
            label: '리스크 신호',
            value: '손절 기준 도달'
          });
        }
      }
    }
    
    return info;
  };
  
  const expandedInfo = getExpandedInfo();

  return (
    <>
      {/* 오버레이 */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />
      {/* 드로어 */}
      <div className="fixed bottom-0 left-0 right-0 bg-white rounded-t-lg shadow-lg z-50 max-h-[85vh] overflow-y-auto">
        <div className="p-6">
          {/* 헤더 */}
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold text-gray-900">{name}</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>

          {/* A. 상단 요약 (카드와 동일) */}
          <div className={`border-2 ${messages.colorClass} rounded-lg p-4 mb-6`}>
            <div className={`text-base font-bold ${messages.statusColorClass} mb-2`}>
              {messages.status}
            </div>
            <div className={`text-sm ${messages.actionColorClass} font-medium mb-2`}>
              {messages.action}
            </div>
            {messages.description && (
              <div className="text-xs text-gray-600">
                {messages.description}
              </div>
            )}
          </div>

          {/* B. 확장 섹션 (카드에 없는 내용) */}
          {expandedInfo.length > 0 && (
            <div className="border-t pt-6 mb-6">
              <h4 className="font-semibold text-gray-900 mb-4">추천 흐름 상세</h4>
              <div className="space-y-4">
                {expandedInfo.map((info, index) => (
                  <div key={index} className="bg-gray-50 rounded-lg p-4">
                    <div className="text-xs text-gray-500 mb-1">{info.label}</div>
                    <div className="text-sm text-gray-900 font-medium">{info.value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* C. 상세 수치 (접기/펼치기) */}
          <div className="border-t pt-6 mb-6">
            <button
              onClick={() => setShowDetailedNumbers(!showDetailedNumbers)}
              className="w-full flex items-center justify-between py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              <span>상세 수치 보기</span>
              <span className="text-gray-400">{showDetailedNumbers ? '▲' : '▼'}</span>
            </button>
            
            {showDetailedNumbers && (
              <div className="mt-4 space-y-4 bg-gray-50 rounded-lg p-4">
                {/* 추천일 정보 */}
                {recommended_date && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">추천일:</span>
                    <span className="text-gray-900 font-medium">{formatDate(recommended_date)}</span>
                  </div>
                )}
                
                {/* 추천가 */}
                {recommended_price && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">추천가:</span>
                    <span className="text-gray-900 font-medium">
                      {recommended_price.toLocaleString()}원
                    </span>
                  </div>
                )}
                
                {/* 현재가 */}
                {current_price > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">현재가:</span>
                    <span className="text-gray-900 font-medium">
                      {current_price.toLocaleString()}원
                    </span>
                  </div>
                )}
                
                {/* 현재 수익률 */}
                {typeof current_return === 'number' && !isNaN(current_return) && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">현재 수익률:</span>
                    <span className={`font-bold ${
                      current_return > 0 ? 'text-red-500' :
                      current_return < 0 ? 'text-blue-500' :
                      'text-gray-500'
                    }`}>
                      {current_return > 0 ? '+' : ''}{current_return.toFixed(2)}%
                    </span>
                  </div>
                )}
                
                {/* 최고/최저 수익률 */}
                {typeof current_return === 'number' && !isNaN(current_return) && (
                  <>
                    {max_return > current_return && max_return > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">추천 이후 최고 수익률:</span>
                        <span className="text-green-600 font-medium">+{max_return.toFixed(2)}%</span>
                      </div>
                    )}
                    {min_return < current_return && min_return < 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">추천 이후 최저 수익률:</span>
                        <span className="text-red-600 font-medium">{min_return.toFixed(2)}%</span>
                      </div>
                    )}
                  </>
                )}
                
                {/* 매매 가이드 (접기 섹션에 포함) */}
                {targetProfit && stopLoss && holdingPeriod && (
                  <>
                    <div className="border-t pt-3 mt-3">
                      <div className="text-xs text-gray-500 mb-2">매매 가이드</div>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">목표 수익률:</span>
                          <span className="font-bold text-green-600">+{targetProfit.toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">손절 기준:</span>
                          <span className="font-bold text-red-600">-{stopLoss.toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">보유 기간:</span>
                          <span className="font-bold text-blue-600">{holdingPeriod}일</span>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* 닫기 버튼 */}
          <button
            onClick={onClose}
            className="w-full py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium"
          >
            닫기
          </button>
        </div>
      </div>
    </>
  );
}

export default function StockCardV3({ item, onViewChart, isClosedToday = false }) {
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // item이 없으면 에러 방지
  if (!item) {
    console.error('[StockCardV3] item is missing');
    return null;
  }

  // 디버깅: item 구조 확인
  if (process.env.NODE_ENV === 'development') {
    console.log('[StockCardV3] item:', item);
  }

  const {
    ticker,
    name,
    current_price,
    change_rate,
    market,
    recommended_price
  } = item;

  // 디버깅: change_rate 원본 값 확인 (항상 출력)
  if (change_rate !== null && change_rate !== undefined && !isNaN(change_rate)) {
    const rawValue = change_rate;
    const fieldName = 'change_rate';
    const formattedValue = `${rawValue > 0 ? '+' : ''}${rawValue.toFixed(2)}%`;
    
    console.log(`[StockCardV3] ${ticker || name} - 퍼센트 표시 디버깅:`, {
      raw_value: rawValue,
      field_name: fieldName,
      type: typeof rawValue,
      formatted_value: formattedValue,
      // 비정상 값 체크 (당일 등락률이 ±30% 초과면 의심)
      is_suspicious: Math.abs(rawValue) > 30,
      // 관련 필드들 확인
      current_return: item.current_return,
      returns: item.returns,
      score: item.score,
      recommended_date: item.recommended_date,
      recommended_price: item.recommended_price,
      // 전체 item 구조 확인
      item_sample: {
        ticker: item.ticker,
        name: item.name,
        change_rate: item.change_rate,
        current_return: item.current_return,
        score: item.score
      }
    });
  }

  // 상태 판별: 서버에서 내려주는 status 필드 사용 (도메인 상태)
  // 서버 status: ACTIVE, BROKEN, ARCHIVED
  // v3 UI 상태: BEFORE_ENTRY, OBSERVING, JUST_RECOMMENDED, RECOMMENDED_PROGRESS, WEAK_WARNING, STRONG_WARNING
  let status;
  
  // 서버에서 내려주는 도메인 상태 확인
  const domainStatus = item.status;
  
  if (!domainStatus) {
    // 서버가 status를 내려주지 않으면 명시적 오류
    console.error('[StockCardV3] API 계약 위반: status 필드가 없습니다.', {
      ticker: item.ticker,
      name: item.name,
      item_keys: Object.keys(item),
      message: '서버 응답에 status 필드가 포함되어야 합니다. 백엔드 API를 확인하세요.'
    });
    // 프로덕션에서는 기본 상태로 처리하되, 개발 환경에서는 명시적 오류
    if (process.env.NODE_ENV === 'development') {
      throw new Error(`[StockCardV3] API 계약 위반: item.status가 없습니다. ticker=${item.ticker}`);
    }
    // 프로덕션 fallback: OBSERVING으로 처리
    status = STOCK_STATUS.OBSERVING;
  } else {
    // 서버 도메인 상태를 v3 UI 상태로 매핑
    status = mapDomainStatusToUIStatus(domainStatus, item);
  }
  
  let messages = STATUS_MESSAGES[status];

  // messages가 없으면 기본값 사용
  if (!messages) {
    console.error('[StockCardV3] Invalid status:', status, 'Available statuses:', Object.keys(STATUS_MESSAGES));
    // 기본 상태로 fallback
    messages = STATUS_MESSAGES[STOCK_STATUS.OBSERVING];
    if (!messages) {
      console.error('[StockCardV3] Even fallback status is missing!');
      return null;
    }
  }

  // isClosedToday는 prop으로 받음 (V3DateSection에서 계산된 값 사용)
  // 휴장일에는 "당일 등락" 라벨 숨김
  
  return (
    <>
      <div className={`bg-white rounded-lg shadow-sm border-2 ${messages.colorClass} p-5 space-y-4`}>
        {/* 종목 헤더 (간소화) */}
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-bold text-gray-900 truncate">
              {name || '종목명 없음'}
            </h3>
            <div className="flex items-center space-x-2 mt-1">
              <span className="text-xs text-gray-500 font-mono">
                {ticker || '코드 없음'}
              </span>
              {market && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                  {market}
                </span>
              )}
            </div>
          </div>
          <div className="text-right ml-4">
            <div className="text-xl font-bold text-gray-900">
              {recommended_price && recommended_price > 0 ? `${recommended_price.toLocaleString()}원` : (current_price && current_price > 0 ? `${current_price.toLocaleString()}원` : '데이터 없음')}
            </div>
            {(() => {
              // 휴장일에는 "당일 등락" 표시하지 않음
              if (isClosedToday) {
                return null;
              }
              
              // change_rate 처리: 당일 등락률 표시
              // 백엔드에서 이미 퍼센트 형태로 전달됨 (예: 0.73 = 0.73%, 5.5 = 5.5%)
              let displayChangeRate = null;
              let changeRateLabel = '당일 등락';
              
              if (change_rate !== null && change_rate !== undefined && !isNaN(change_rate)) {
                const rawValue = change_rate;
                
                // 비정상 값 체크: 당일 등락률이 ±30% 초과면 데이터 오류로 간주
                if (Math.abs(rawValue) > 30) {
                  console.warn(`[StockCardV3] ${ticker || name} - 비정상 change_rate 감지:`, {
                    raw_value: rawValue,
                    field_name: 'change_rate',
                    action: 'fallback 처리 - 표시하지 않음'
                  });
                  // 비정상 값은 표시하지 않음
                  displayChangeRate = null;
                } else {
                  displayChangeRate = rawValue;
                }
              }
              
              return displayChangeRate !== null ? (
                <div className="space-y-1">
                  <div className={`text-sm font-semibold ${
                    displayChangeRate > 0 ? 'text-red-500' :
                    displayChangeRate < 0 ? 'text-blue-500' :
                    'text-gray-500'
                  }`}>
                    {displayChangeRate > 0 ? '+' : ''}{displayChangeRate.toFixed(2)}%
                  </div>
                  <div className="text-xs text-gray-400">
                    {changeRateLabel}
                  </div>
                </div>
              ) : null;
            })()}
          </div>
        </div>

        {/* 상태 헤더 (가장 중요) */}
        <div className={`pt-3 border-t ${messages.colorClass.replace('bg-', 'border-').replace('-50', '-200')}`}>
          <div className={`text-base font-bold ${messages.statusColorClass} mb-2`}>
            {messages.status}
          </div>
        </div>

        {/* 행동 가이드 */}
        <div className={`text-sm ${messages.actionColorClass} font-medium`}>
          {messages.action}
        </div>

        {/* 보조 설명 (선택) */}
        {messages.description && (
          <div className="text-xs text-gray-600">
            {messages.description}
          </div>
        )}

        {/* 추천 흐름 보기 버튼 */}
        <div className="pt-3 border-t border-gray-200">
          <button
            onClick={() => setIsDetailOpen(true)}
            className="w-full py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            추천 흐름 보기
          </button>
        </div>
      </div>

      {/* 상세 정보 드로어 */}
      <DetailDrawer
        item={item}
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
      />
    </>
  );
}

