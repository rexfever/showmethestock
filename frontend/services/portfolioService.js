/**
 * 포트폴리오 관련 API 서비스
 */
import getConfig from '../config';
import { getAuthToken } from '../utils/portfolioUtils';

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

  const response = await fetch(`${base}/portfolio/add`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      ticker: investmentData.ticker,
      name: investmentData.name,
      entry_price: parseFloat(investmentData.entry_price),
      quantity: parseInt(investmentData.quantity),
      entry_date: investmentData.entry_date,
      status: 'holding'
    })
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

  const response = await fetch(`${base}/portfolio/${ticker}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
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







