/**
 * 일일 추천 상태 배너 유틸리티
 * 
 * 규칙:
 * - 추천 확정 시각: 매 거래일 15:35 (Asia/Seoul)
 * - 현재 시각과 15:35를 비교하여 배너 상태 결정
 */

/**
 * 현재 시각이 15:35 이후인지 확인 (Asia/Seoul 기준)
 * @returns {boolean} 15:35 이후이면 true
 */
export function isAfterRecommendationTime() {
  if (typeof window === 'undefined') {
    return false; // 서버 사이드에서는 false
  }
  
  const now = new Date();
  // Asia/Seoul 타임존으로 변환
  const seoulTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  const hours = seoulTime.getHours();
  const minutes = seoulTime.getMinutes();
  
  // 15:35 이후인지 확인
  return hours > 15 || (hours === 15 && minutes >= 35);
}

/**
 * 오늘 날짜 (Asia/Seoul 기준, YYYY-MM-DD 형식)
 * @returns {string} 오늘 날짜
 */
export function getTodayDate() {
  const now = new Date();
  const seoulTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  const year = seoulTime.getFullYear();
  const month = String(seoulTime.getMonth() + 1).padStart(2, '0');
  const day = String(seoulTime.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * 날짜 문자열이 오늘인지 확인
 * @param {string} dateStr - YYYY-MM-DD 형식 날짜
 * @returns {boolean} 오늘이면 true
 */
export function isToday(dateStr) {
  if (!dateStr) return false;
  return dateStr === getTodayDate();
}

/**
 * 현재 시각이 15:35 이전인지 확인 (Asia/Seoul 기준)
 * @returns {boolean} 15:35 이전이면 true
 */
export function isBeforeRecommendationTime() {
  if (typeof window === 'undefined') {
    return true; // 서버 사이드에서는 true (보수적)
  }
  
  const now = new Date();
  // Asia/Seoul 타임존으로 변환
  const seoulTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  const hours = seoulTime.getHours();
  const minutes = seoulTime.getMinutes();
  
  // 15:35 이전인지 확인
  return hours < 15 || (hours === 15 && minutes < 35);
}

/**
 * 타임스탬프 문자열의 날짜가 오늘인지 확인 (KST 기준)
 * @param {string} timestampStr - ISO 8601 형식 타임스탬프 (예: "2025-12-31T10:55:03.116086+09:00")
 * @returns {boolean} 오늘이면 true
 */
export function isTimestampToday(timestampStr) {
  if (!timestampStr) return false;
  
  try {
    // 타임스탬프를 Date 객체로 변환
    const date = new Date(timestampStr);
    // KST로 변환하여 날짜 추출
    const kstDate = new Date(date.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
    const year = kstDate.getFullYear();
    const month = String(kstDate.getMonth() + 1).padStart(2, '0');
    const day = String(kstDate.getDate()).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    
    return dateStr === getTodayDate();
  } catch (e) {
    console.warn('[isTimestampToday] 날짜 파싱 오류:', timestampStr, e);
    return false;
  }
}

