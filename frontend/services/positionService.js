/**
 * 개인 매수가 서비스 레이어
 * 
 * API 스펙 (TODO: 백엔드 구현 필요 시):
 * - GET  /me/positions/{ticker}  -> { avg_buy_price } 또는 null
 * - PUT  /me/positions/{ticker}  body { avg_buy_price }
 * - DELETE /me/positions/{ticker}
 */

import getConfig from '../config';

/**
 * 개인 매수가 조회
 * @param {string} ticker - 종목 코드
 * @returns {Promise<{avg_buy_price: number | null}>}
 */
export async function getPersonalBuyPrice(ticker) {
  try {
    const config = getConfig();
    const base = config.backendUrl;
    
    // TODO: 백엔드 API 구현 후 활성화
    // const response = await fetch(`${base}/me/positions/${ticker}`, {
    //   method: 'GET',
    //   headers: {
    //     'Content-Type': 'application/json',
    //     'Accept': 'application/json',
    //   },
    //   credentials: 'include',
    // });
    
    // if (!response.ok) {
    //   if (response.status === 404) {
    //     return { avg_buy_price: null };
    //   }
    //   throw new Error(`HTTP error! status: ${response.status}`);
    // }
    
    // const data = await response.json();
    // return { avg_buy_price: data.avg_buy_price || null };
    
    // 임시: API가 없으면 null 반환
    return { avg_buy_price: null };
  } catch (error) {
    console.error('[positionService] getPersonalBuyPrice error:', error);
    return { avg_buy_price: null };
  }
}

/**
 * 개인 매수가 저장/수정
 * @param {string} ticker - 종목 코드
 * @param {number} avgBuyPrice - 평균 매수가
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function savePersonalBuyPrice(ticker, avgBuyPrice) {
  try {
    const config = getConfig();
    const base = config.backendUrl;
    
    // TODO: 백엔드 API 구현 후 활성화
    // const response = await fetch(`${base}/me/positions/${ticker}`, {
    //   method: 'PUT',
    //   headers: {
    //     'Content-Type': 'application/json',
    //     'Accept': 'application/json',
    //   },
    //   credentials: 'include',
    //   body: JSON.stringify({ avg_buy_price: avgBuyPrice }),
    // });
    
    // if (!response.ok) {
    //   const errorData = await response.json().catch(() => ({}));
    //   throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    // }
    
    // return { success: true };
    
    // 임시: API가 없으면 성공으로 처리 (로컬 상태만 저장)
    console.warn('[positionService] savePersonalBuyPrice: API not implemented, using local storage');
    if (typeof window !== 'undefined') {
      localStorage.setItem(`position_${ticker}`, String(avgBuyPrice));
    }
    return { success: true };
  } catch (error) {
    console.error('[positionService] savePersonalBuyPrice error:', error);
    return { success: false, error: error.message || '저장에 실패했습니다.' };
  }
}

/**
 * 개인 매수가 삭제
 * @param {string} ticker - 종목 코드
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function deletePersonalBuyPrice(ticker) {
  try {
    const config = getConfig();
    const base = config.backendUrl;
    
    // TODO: 백엔드 API 구현 후 활성화
    // const response = await fetch(`${base}/me/positions/${ticker}`, {
    //   method: 'DELETE',
    //   headers: {
    //     'Content-Type': 'application/json',
    //     'Accept': 'application/json',
    //   },
    //   credentials: 'include',
    // });
    
    // if (!response.ok) {
    //   const errorData = await response.json().catch(() => ({}));
    //   throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    // }
    
    // return { success: true };
    
    // 임시: API가 없으면 성공으로 처리 (로컬 스토리지만 삭제)
    console.warn('[positionService] deletePersonalBuyPrice: API not implemented, using local storage');
    if (typeof window !== 'undefined') {
      localStorage.removeItem(`position_${ticker}`);
    }
    return { success: true };
  } catch (error) {
    console.error('[positionService] deletePersonalBuyPrice error:', error);
    return { success: false, error: error.message || '삭제에 실패했습니다.' };
  }
}



