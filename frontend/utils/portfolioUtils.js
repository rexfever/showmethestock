/**
 * 포트폴리오 관련 유틸리티 함수들
 */

/**
 * 토큰을 가져오는 함수
 * @returns {string|null} 토큰 또는 null
 */
export const getAuthToken = () => {
  return localStorage.getItem('token') || 
    document.cookie
      .split('; ')
      .find(row => row.startsWith('auth_token='))
      ?.split('=')[1] || 
    null;
};

/**
 * 보유기간을 계산하는 함수
 * @param {string} entryDate - 매수일 (YYYY-MM-DD 형식)
 * @returns {string} 보유기간 문자열
 */
export const calculateHoldingPeriod = (entryDate) => {
  if (!entryDate) return '-';
  
  const entry = new Date(entryDate);
  const today = new Date();
  const diffTime = Math.abs(today - entry);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return '당일';
  if (diffDays < 30) return `${diffDays}일`;
  if (diffDays < 365) {
    const months = Math.floor(diffDays / 30);
    const days = diffDays % 30;
    return days > 0 ? `${months}개월 ${days}일` : `${months}개월`;
  } else {
    const years = Math.floor(diffDays / 365);
    const months = Math.floor((diffDays % 365) / 30);
    return months > 0 ? `${years}년 ${months}개월` : `${years}년`;
  }
};

/**
 * 날짜를 한국어 형식으로 포맷팅하는 함수
 * @param {string} dateString - 날짜 문자열
 * @returns {string} 포맷팅된 날짜
 */
export const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
};

/**
 * 숫자를 천 단위 구분자와 함께 포맷팅하는 함수
 * @param {number} value - 포맷팅할 숫자
 * @returns {string} 포맷팅된 문자열
 */
export const formatCurrency = (value) => {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('ko-KR').format(Math.round(value));
};

/**
 * 퍼센트를 포맷팅하는 함수
 * @param {number} value - 퍼센트 값
 * @returns {string} 포맷팅된 퍼센트 문자열
 */
export const formatPercentage = (value) => {
  if (value === null || value === undefined) return '-';
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
};

/**
 * 투자등록 폼 데이터를 검증하는 함수
 * @param {Object} formData - 폼 데이터
 * @returns {Object} 검증 결과 {isValid: boolean, errors: string[]}
 */
export const validateInvestmentForm = (formData) => {
  const errors = [];
  
  if (!formData.entry_price || isNaN(parseFloat(formData.entry_price)) || parseFloat(formData.entry_price) <= 0) {
    errors.push('올바른 매수가격을 입력해주세요.');
  }
  
  if (!formData.quantity || isNaN(parseInt(formData.quantity)) || parseInt(formData.quantity) <= 0) {
    errors.push('올바른 수량을 입력해주세요.');
  }
  
  if (!formData.entry_date) {
    errors.push('매수일을 선택해주세요.');
  } else {
    const entryDate = new Date(formData.entry_date);
    const today = new Date();
    if (entryDate > today) {
      errors.push('매수일은 오늘 이전이어야 합니다.');
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};
