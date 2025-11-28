/**
 * 공지사항 관리 유틸리티
 */

const NOTICE_KEY_PREFIX = 'stock-insight-notice-';

/**
 * 공지사항을 표시해야 하는지 확인하는 함수
 * @param {string} noticeId - 공지사항 ID (예: '2025-10-11')
 * @param {number} hideDays - 숨김 기간 (일 단위, 기본값: 3)
 * @returns {boolean} 공지사항을 표시해야 하는지 여부
 */
export const shouldShowNotice = (noticeId, hideDays = 3) => {
  const noticeKey = `${NOTICE_KEY_PREFIX}${noticeId}`;
  const lastShown = localStorage.getItem(noticeKey);
  
  if (!lastShown) {
    return true; // 처음 방문
  }
  
  const now = new Date().getTime();
  const hideDuration = hideDays * 24 * 60 * 60 * 1000; // 밀리초로 변환
  
  return (now - parseInt(lastShown)) > hideDuration;
};

/**
 * 공지사항을 숨김 처리하는 함수
 * @param {string} noticeId - 공지사항 ID
 */
export const hideNotice = (noticeId) => {
  const noticeKey = `${NOTICE_KEY_PREFIX}${noticeId}`;
  localStorage.setItem(noticeKey, new Date().getTime().toString());
};

/**
 * 공지사항 숨김을 해제하는 함수 (테스트용)
 * @param {string} noticeId - 공지사항 ID
 */
export const clearNoticeHide = (noticeId) => {
  const noticeKey = `${NOTICE_KEY_PREFIX}${noticeId}`;
  localStorage.removeItem(noticeKey);
};

/**
 * 모든 공지사항 숨김을 해제하는 함수 (테스트용)
 */
export const clearAllNoticeHides = () => {
  const keys = Object.keys(localStorage);
  keys.forEach(key => {
    if (key.startsWith(NOTICE_KEY_PREFIX)) {
      localStorage.removeItem(key);
    }
  });
};

/**
 * 공지사항 목록 관리
 */
export const NOTICE_LIST = {
  '2025-10-11': {
    id: '2025-10-11',
    title: '🎉 새로운 기능 업데이트!',
    date: '2025년 10월 11일',
    version: 'v2.1.0',
    features: [
      '투자등록 기능 추가',
      '나의투자종목 관리 개선',
      'UI/UX 개선',
      '성능 및 안정성 향상'
    ]
  }
};

/**
 * 특정 공지사항 정보를 가져오는 함수
 * @param {string} noticeId - 공지사항 ID
 * @returns {Object|null} 공지사항 정보
 */
export const getNoticeInfo = (noticeId) => {
  return NOTICE_LIST[noticeId] || null;
};
