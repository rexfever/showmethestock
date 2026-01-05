/**
 * 시장 관련 유틸리티 함수
 * 
 * 규칙:
 * - Asia/Seoul 타임존 기준
 * - 주말(토/일)을 휴장일로 판단
 * - 공휴일은 백엔드에서 처리 (추후 확장 가능)
 */

/**
 * 휴장일 여부 판단 (Asia/Seoul 기준)
 * @param {Date} date - 확인할 날짜 (선택, 없으면 오늘)
 * @returns {boolean} 휴장일이면 true
 */
export function isMarketHoliday(date = null) {
  const checkDate = date || new Date();
  // Asia/Seoul 타임존으로 변환
  const seoulTime = new Date(checkDate.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  const dayOfWeek = seoulTime.getDay(); // 0 = 일요일, 6 = 토요일
  return dayOfWeek === 0 || dayOfWeek === 6;
}

/**
 * 오늘이 휴장일인지 확인
 * @returns {boolean} 오늘이 휴장일이면 true
 */
export function isMarketHolidayToday() {
  return isMarketHoliday();
}

/**
 * 거래일 여부 판단 (휴장일의 반대)
 * @param {Date} date - 확인할 날짜 (선택, 없으면 오늘)
 * @returns {boolean} 거래일이면 true
 */
export function isTradingDay(date = null) {
  return !isMarketHoliday(date);
}

/**
 * 오늘이 거래일인지 확인
 * @returns {boolean} 오늘이 거래일이면 true
 */
export function isTradingDayToday() {
  return isTradingDay();
}


