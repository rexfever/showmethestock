/**
 * 거래일 계산 유틸리티
 * 
 * 규칙:
 * - 주말(토요일, 일요일) 제외
 * - 공휴일은 고려하지 않음 (단순화)
 */

/**
 * 추천일 이후 실제 거래일 수 계산 (주말 제외)
 * @param {string|Date} recommendedDate - 추천일 (YYYYMMDD, YYYY-MM-DD, 또는 Date 객체)
 * @returns {number} 실제 거래일 수 (추천일 당일 포함)
 */
export function getTradingDaysElapsed(recommendedDate) {
  if (!recommendedDate) return 0;
  
  try {
    let recDate = null;
    
    if (recommendedDate instanceof Date) {
      recDate = new Date(recommendedDate);
    } else {
      const recDateStr = String(recommendedDate);
      
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
    
    // 주말 제외하고 거래일 수 계산
    let tradingDays = 0;
    const current = new Date(recDate);
    
    while (current <= today) {
      const dayOfWeek = current.getDay();
      // 월요일(1) ~ 금요일(5)만 카운트
      if (dayOfWeek >= 1 && dayOfWeek <= 5) {
        tradingDays++;
      }
      current.setDate(current.getDate() + 1);
    }
    
    return tradingDays;
  } catch (error) {
    console.error('[getTradingDaysElapsed] 오류:', error);
    return 0;
  }
}

/**
 * 두 날짜 사이의 거래일 수 계산 (주말 제외)
 * @param {string|Date} startDate - 시작일 (YYYYMMDD, YYYY-MM-DD, 또는 Date 객체)
 * @param {string|Date} endDate - 종료일 (YYYYMMDD, YYYY-MM-DD, 또는 Date 객체)
 * @returns {number} 실제 거래일 수 (시작일과 종료일 포함)
 */
export function getTradingDaysBetween(startDate, endDate) {
  if (!startDate || !endDate) return 0;
  
  try {
    let start = null;
    let end = null;
    
    // startDate 파싱
    if (startDate instanceof Date) {
      start = new Date(startDate);
    } else {
      const startStr = String(startDate);
      if (startStr.length === 8 && /^\d+$/.test(startStr)) {
        const year = parseInt(startStr.slice(0, 4));
        const month = parseInt(startStr.slice(4, 6)) - 1;
        const day = parseInt(startStr.slice(6, 8));
        start = new Date(year, month, day);
      } else if (startStr.includes('-')) {
        start = new Date(startStr);
      } else {
        start = new Date(startStr);
      }
    }
    
    // endDate 파싱
    if (endDate instanceof Date) {
      end = new Date(endDate);
    } else {
      const endStr = String(endDate);
      if (endStr.length === 8 && /^\d+$/.test(endStr)) {
        const year = parseInt(endStr.slice(0, 4));
        const month = parseInt(endStr.slice(4, 6)) - 1;
        const day = parseInt(endStr.slice(6, 8));
        end = new Date(year, month, day);
      } else if (endStr.includes('-')) {
        end = new Date(endStr);
      } else {
        end = new Date(endStr);
      }
    }
    
    if (!start || !end || isNaN(start.getTime()) || isNaN(end.getTime())) {
      return 0;
    }
    
    start.setHours(0, 0, 0, 0);
    end.setHours(0, 0, 0, 0);
    
    // 시작일이 종료일 이후면 0
    if (start > end) {
      return 0;
    }
    
    // 주말 제외하고 거래일 수 계산
    let tradingDays = 0;
    const current = new Date(start);
    
    while (current <= end) {
      const dayOfWeek = current.getDay();
      // 월요일(1) ~ 금요일(5)만 카운트
      if (dayOfWeek >= 1 && dayOfWeek <= 5) {
        tradingDays++;
      }
      current.setDate(current.getDate() + 1);
    }
    
    return tradingDays;
  } catch (error) {
    console.error('[getTradingDaysBetween] 오류:', error);
    return 0;
  }
}

/**
 * 날짜를 표시용 형식으로 변환
 * @param {string|Date} date - 날짜 (YYYYMMDD, YYYY-MM-DD, 또는 Date 객체)
 * @returns {string} 표시용 날짜 문자열 (YYYY-MM-DD)
 */
export function formatDateForDisplay(date) {
  if (!date) return '';
  
  try {
    let dateObj = null;
    
    if (date instanceof Date) {
      dateObj = date;
    } else {
      const dateStr = String(date);
      if (dateStr.length === 8 && /^\d+$/.test(dateStr)) {
        const year = dateStr.slice(0, 4);
        const month = dateStr.slice(4, 6);
        const day = dateStr.slice(6, 8);
        return `${year}-${month}-${day}`;
      } else if (dateStr.includes('-')) {
        return dateStr.slice(0, 10);
      } else {
        dateObj = new Date(dateStr);
      }
    }
    
    if (dateObj && !isNaN(dateObj.getTime())) {
      const year = dateObj.getFullYear();
      const month = String(dateObj.getMonth() + 1).padStart(2, '0');
      const day = String(dateObj.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }
    
    return '';
  } catch (error) {
    console.error('[formatDateForDisplay] 오류:', error);
    return '';
  }
}
