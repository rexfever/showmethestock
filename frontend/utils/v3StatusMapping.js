/**
 * v3 추천 시스템 - 백엔드 상태 → UX 매핑
 * 
 * 규칙:
 * - 백엔드 상태를 1:1로 번역만 수행
 * - 판단/해석 금지
 * - 숫자, 점수, 엔진명, 추천 횟수 노출 금지
 */

/**
 * 백엔드 상태 타입
 */
export const BACKEND_STATUS = {
  ACTIVE: 'ACTIVE',
  WEAK_WARNING: 'WEAK_WARNING',
  BROKEN: 'BROKEN',
  ARCHIVED: 'ARCHIVED',
  REPLACED: 'REPLACED'
};

/**
 * 백엔드 상태 → UX 매핑
 */
export const STATUS_TO_UX = {
  [BACKEND_STATUS.ACTIVE]: {
    // 카드 헤더 (배지용) - 배지 제거로 미사용
    header: '추천 유효',
    // 상태 요약 (최종 확정 문구)
    summary: '현재 추천은 변경 없이 유지되고 있습니다',
    // 행동 가이드 (행동 유도 금지)
    actionGuide: null,
    // 보조 설명 (선택) - 제거
    helperText: null,
    // UX 규칙
    colorScheme: 'green', // 초록 계열
    allowEntryCTA: false, // 행동 유도 금지 (CTA 제거)
    renderInMainSection: true, // 메인 추천 영역에 렌더링
    maxPerTicker: 1 // ticker당 최대 1개만 렌더링
  },
  [BACKEND_STATUS.WEAK_WARNING]: {
    header: '흐름 약화',
    // 상태 요약 (최종 확정 문구)
    summary: '추천 이후 이전과 다른 움직임이 감지되었습니다',
    actionGuide: null,
    helperText: null,
    colorScheme: 'yellow', // 노랑/주황 계열
    allowEntryCTA: true, // 신규 진입 CTA 유지
    renderInMainSection: true, // 메인 추천 영역에 렌더링
    maxPerTicker: 1
  },
  [BACKEND_STATUS.BROKEN]: {
    header: null, // 헤더 사용 안 함
    // 상태 요약 (최종 확정 문구)
    summary: '추천 관리가 종료되었습니다',
    actionGuide: null,
    helperText: null,
    colorScheme: 'red', // 빨강/주황 계열
    allowEntryCTA: false, // 신규 진입 CTA 금지
    renderInMainSection: false, // 추천 영역과 분리된 섹션에 렌더링
    maxPerTicker: 1
  },
  [BACKEND_STATUS.ARCHIVED]: {
    header: null, // 헤더 사용 안 함
    summary: null, // 새로운 본문 문구 만들지 않음
    actionGuide: null,
    helperText: null, // 새로운 본문 문구 만들지 않음
    colorScheme: 'gray',
    allowEntryCTA: false,
    renderInMainSection: false, // 별도 섹션으로만 노출
    renderInHistory: true // 히스토리/상세 화면에서도 접근 가능
  },
  [BACKEND_STATUS.REPLACED]: {
    header: null, // UX 노출 금지
    summary: null,
    actionGuide: null,
    helperText: null,
    colorScheme: null,
    allowEntryCTA: false,
    renderInMainSection: false, // 내부 상태로만 사용
    renderInHistory: false // 사용자는 항상 최신 추천만 보도록 처리
  }
};

/**
 * 상태별 색상 클래스 매핑
 */
export const STATUS_COLOR_CLASSES = {
  [BACKEND_STATUS.ACTIVE]: {
    cardBg: 'bg-green-50',
    cardBorder: 'border-green-200',
    headerText: 'text-green-800',
    bodyText: 'text-gray-700',
    badgeBg: 'bg-green-100',
    badgeText: 'text-green-800'
  },
  [BACKEND_STATUS.WEAK_WARNING]: {
    cardBg: 'bg-orange-50',
    cardBorder: 'border-orange-300',
    headerText: 'text-orange-800',
    bodyText: 'text-gray-700',
    badgeBg: 'bg-orange-100',
    badgeText: 'text-orange-800'
  },
  [BACKEND_STATUS.BROKEN]: {
    cardBg: 'bg-red-50',
    cardBorder: 'border-red-200',
    headerText: 'text-red-800',
    bodyText: 'text-gray-700',
    badgeBg: 'bg-red-100',
    badgeText: 'text-red-800'
  },
  [BACKEND_STATUS.ARCHIVED]: {
    cardBg: 'bg-gray-50',
    cardBorder: 'border-gray-200',
    headerText: 'text-gray-700',
    bodyText: 'text-gray-600',
    badgeBg: 'bg-gray-100',
    badgeText: 'text-gray-700'
  }
};

/**
 * 상태별 렌더링 가능 여부 확인
 * @param {string} status - 백엔드 상태
 * @param {boolean} isHistoryView - 히스토리 화면 여부
 * @returns {boolean} 렌더링 가능 여부
 */
export function shouldRenderStatus(status, isHistoryView = false) {
  const ux = STATUS_TO_UX[status];
  if (!ux) return false;
  
  // REPLACED는 절대 노출하지 않음
  if (status === BACKEND_STATUS.REPLACED) return false;
  
  // ARCHIVED는 히스토리 화면에서만 노출
  if (status === BACKEND_STATUS.ARCHIVED) {
    return isHistoryView && ux.renderInHistory;
  }
  
  // BROKEN은 별도 "관리 필요" 섹션에 렌더링되므로 항상 true 반환
  if (status === BACKEND_STATUS.BROKEN) {
    return true;
  }
  
  // ACTIVE, WEAK_WARNING은 메인 화면에서 노출
  return ux.renderInMainSection || (!isHistoryView && ux.renderInHistory);
}

/**
 * 상태별 섹션 분류
 * @param {string} status - 백엔드 상태
 * @returns {string} 섹션 타입 ('active' | 'needs-attention' | 'hidden')
 */
export function getSectionType(status) {
  if (status === BACKEND_STATUS.ACTIVE || status === BACKEND_STATUS.WEAK_WARNING) {
    return 'active';
  }
  if (status === BACKEND_STATUS.BROKEN) {
    return 'needs-attention';
  }
  return 'hidden';
}

/**
 * 휴장일/추천 없음 UX 문구 상수
 */
export const EMPTY_STATE_MESSAGES = {
  NO_RECOMMENDATIONS: {
    header: '오늘은 새로운 추천이 없습니다',
    summary: '현재 시장에서는 추가 확인이 더 필요한 상황입니다',
    helperText: '조건이 충족되면 추천으로 안내드립니다',
    colorClass: 'bg-gray-50 border-gray-200',
    headerColorClass: 'text-gray-800',
    bodyColorClass: 'text-gray-700'
  },
  MARKET_HOLIDAY: {
    header: '오늘은 시장 휴장일입니다',
    summary: '시장 휴장으로 추천 변경이 없습니다',
    helperText: '다음 거래일에 다시 확인해 주세요',
    colorClass: 'bg-blue-50 border-blue-200',
    headerColorClass: 'text-blue-800',
    bodyColorClass: 'text-blue-700'
  }
};

/**
 * 종료 사유 코드 → 사용자 문구 매핑
 */
export const TERMINATION_REASON_MAP = {
  TTL_EXPIRED: '관리 기간 종료',
  NO_MOMENTUM: '이전 흐름 유지 실패',
  MANUAL_ARCHIVE: '운영자 종료'
};

/**
 * 종료 사유 코드를 사용자 문구로 변환
 * @param {string} reasonCode - 종료 사유 코드 (TTL_EXPIRED, NO_MOMENTUM, MANUAL_ARCHIVE)
 * @param {object} options - 추가 정보 (사용하지 않음, 스펙에 따라 추가 정보 표시 금지)
 * @returns {string} 사용자 문구
 */
export function getTerminationReasonText(reasonCode, options = {}) {
  // reasonCode가 없으면 기본값 반환
  if (!reasonCode) {
    return '관리 기간 종료';
  }
  
  const baseText = TERMINATION_REASON_MAP[reasonCode];
  if (!baseText) {
    // 알 수 없는 reasonCode인 경우 기본값 반환
    return '관리 기간 종료';
  }
  
  // 괄호 설명, 수익률, 기간, 수치 추가 금지
  return baseText;
}

/**
 * 일일 추천 상태 배너 문구 상수
 * 기준 시각: 매 거래일 15:35 (추천 확정 시각)
 */
export const DAY_STATUS_BANNER_MESSAGES = {
  NEW_RECOMMENDATIONS_AFTER_1535: {
    header: '오늘 새로운 추천이 추가되었습니다',
    helperText: null,
    colorClass: 'bg-green-50 border-green-200',
    headerColorClass: 'text-green-800',
    bodyColorClass: 'text-green-700'
  },
  MAINTAINED_AFTER_1535: {
    header: '오늘 새로운 추천은 추가되지 않았습니다',
    helperText: null,
    colorClass: 'bg-blue-50 border-blue-200',
    headerColorClass: 'text-blue-800',
    bodyColorClass: 'text-blue-700'
  },
  NO_RECOMMENDATIONS_AFTER_1535: {
    header: '오늘 새로운 추천은 추가되지 않았습니다',
    helperText: null,
    colorClass: 'bg-gray-50 border-gray-200',
    headerColorClass: 'text-gray-800',
    bodyColorClass: 'text-gray-700'
  },
  BEFORE_1535: {
    header: '오늘 새로운 추천은 추가되지 않았습니다',
    helperText: null,
    colorClass: 'bg-blue-50 border-blue-200',
    headerColorClass: 'text-blue-800',
    bodyColorClass: 'text-blue-700'
  },
  MARKET_HOLIDAY: {
    header: '오늘은 시장 휴장일입니다',
    helperText: null,
    colorClass: 'bg-blue-50 border-blue-200',
    headerColorClass: 'text-blue-800',
    bodyColorClass: 'text-blue-700'
  }
};

