/**
 * 에러 처리 유틸리티
 */

/**
 * 에러 메시지를 사용자 친화적으로 변환하는 함수
 * @param {Error} error - 에러 객체
 * @returns {string} 사용자 친화적인 에러 메시지
 */
export const getErrorMessage = (error) => {
  if (error.message.includes('인증')) {
    return '로그인이 필요합니다. 다시 로그인해주세요.';
  }
  
  if (error.message.includes('네트워크') || error.message.includes('fetch')) {
    return '네트워크 연결을 확인해주세요.';
  }
  
  if (error.message.includes('서버')) {
    return '서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.';
  }
  
  return error.message || '알 수 없는 오류가 발생했습니다.';
};

/**
 * 에러를 콘솔에 로깅하고 사용자에게 알림을 표시하는 함수
 * @param {Error} error - 에러 객체
 * @param {string} context - 에러가 발생한 컨텍스트
 * @param {Function} showAlert - 알림 표시 함수 (선택사항)
 */
export const handleError = (error, context, showAlert = null) => {
  console.error(`${context} 오류:`, error);
  
  if (showAlert) {
    const message = getErrorMessage(error);
    showAlert(message);
  }
};

/**
 * API 응답을 처리하는 함수
 * @param {Response} response - fetch 응답 객체
 * @returns {Promise<Object>} JSON 데이터
 * @throws {Error} 응답이 실패한 경우
 */
export const handleApiResponse = async (response) => {
  if (!response.ok) {
    let errorMessage = '요청 처리에 실패했습니다.';
    
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {
      // JSON 파싱 실패 시 기본 메시지 사용
    }
    
    if (response.status === 401) {
      errorMessage = '인증이 필요합니다. 다시 로그인해주세요.';
    } else if (response.status >= 500) {
      errorMessage = '서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.';
    }
    
    throw new Error(errorMessage);
  }
  
  return await response.json();
};




