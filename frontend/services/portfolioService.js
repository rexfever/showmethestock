/**
 * 포트폴리오 관련 API 서비스
 */
import getConfig from '../config';
import { getAuthToken } from '../utils/portfolioUtils';
import { generateCSRFToken, sanitizeInput, validatePortfolioInput } from '../utils/security';

/**
 * 포트폴리오 목록을 가져오는 함수
 * @returns {Promise<Object>} 포트폴리오 데이터
 */
export const fetchPortfolio = async () => {
  const config = getConfig();
  const base = config.backendUrl;
  const token = getAuthToken();

  if (!token) {
    throw new Error('인증 토큰이 없습니다.');
  }

  const response = await fetch(`${base}/portfolio`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('인증이 필요합니다. 다시 로그인해주세요.');
    }
    throw new Error('포트폴리오를 불러오는데 실패했습니다.');
  }

  const data = await response.json();
  return data.items || [];
};

/**
 * 포트폴리오에 종목을 추가하는 함수
 * @param {Object} investmentData - 투자 데이터
 * @returns {Promise<Object>} 추가된 포트폴리오 아이템
 */
export const addToPortfolio = async (investmentData) => {
  const config = getConfig();
  const base = config.backendUrl;
  const token = getAuthToken();

  if (!token) {
    throw new Error('인증 토큰이 없습니다.');
  }
  
  // 입력 검증
  const validationErrors = validatePortfolioInput(investmentData);
  if (validationErrors.length > 0) {
    throw new Error(validationErrors.join(', '));
  }
  
  // 입력 데이터 정제
  const sanitizedData = {
    ticker: sanitizeInput(investmentData.ticker),
    name: sanitizeInput(investmentData.name),
    entry_price: parseFloat(investmentData.entry_price),
    quantity: parseInt(investmentData.quantity),
    entry_date: investmentData.entry_date,
    status: 'holding'
  };
  
  // CSRF 토큰 생성
  const csrfToken = await generateCSRFToken();

  const response = await fetch(`${base}/portfolio/add`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken
    },
    body: JSON.stringify(sanitizedData)
  });

  if (!response.ok) {
    const errorData = await response.json();
    if (response.status === 401) {
      throw new Error('인증이 필요합니다. 다시 로그인해주세요.');
    }
    throw new Error(errorData.detail || '투자등록에 실패했습니다.');
  }

  return await response.json();
};

/**
 * 포트폴리오에서 종목을 제거하는 함수
 * @param {string} ticker - 종목 코드
 * @returns {Promise<Object>} 삭제 결과
 */
export const removeFromPortfolio = async (ticker) => {
  const config = getConfig();
  const base = config.backendUrl;
  const token = getAuthToken();

  if (!token) {
    throw new Error('인증 토큰이 없습니다.');
  }
  
  // 입력 검증
  if (!ticker || typeof ticker !== 'string') {
    throw new Error('유효한 종목 코드가 필요합니다');
  }
  
  const sanitizedTicker = sanitizeInput(ticker);
  const csrfToken = await generateCSRFToken();

  const response = await fetch(`${base}/portfolio/${sanitizedTicker}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-CSRF-Token': csrfToken
    },
  });

  if (!response.ok) {
    const errorData = await response.json();
    if (response.status === 401) {
      throw new Error('인증이 필요합니다. 다시 로그인해주세요.');
    }
    throw new Error(errorData.detail || '종목 삭제에 실패했습니다.');
  }

  return await response.json();
};











