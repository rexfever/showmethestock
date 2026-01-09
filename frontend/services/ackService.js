/**
 * 추천 인스턴스 확인(ack) 서비스
 */

import getConfig from '../config';

/**
 * 추천 인스턴스 확인(ack) 처리
 * @param {string} recDate - 추천 날짜 (YYYYMMDD 또는 YYYY-MM-DD)
 * @param {string} recCode - 종목 코드
 * @param {string} recScannerVersion - 스캐너 버전 (기본값: v3)
 * @param {string} ackType - 확인 타입 (기본값: BROKEN_VIEWED)
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function ackRecommendation(recDate, recCode, recScannerVersion = 'v3', ackType = 'BROKEN_VIEWED') {
  try {
    const config = getConfig();
    const base = config.backendUrl;
    
    // 날짜 정규화 (YYYYMMDD 형식으로)
    const normalizedDate = String(recDate).replace(/-/g, '').slice(0, 8);
    
    const response = await fetch(`${base}/api/v3/recommendations/${normalizedDate}/${recCode}/${recScannerVersion}/ack?ack_type=${ackType}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return { success: data.ok || true };
  } catch (error) {
    console.error('[ackService] ackRecommendation error:', error);
    return { success: false, error: error.message || '확인 처리 중 오류가 발생했습니다.' };
  }
}



