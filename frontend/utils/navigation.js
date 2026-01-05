/**
 * 네비게이션 유틸리티
 * 동적 스캐너 링크를 가져오는 함수
 */
import getConfig from '../config';

/**
 * 스캐너 링크를 동적으로 가져오는 함수
 * @returns {Promise<string>} 스캐너 링크 URL
 */
export const getScannerLink = async () => {
  try {
    const config = getConfig();
    const base = config?.backendUrl || 'http://localhost:8010';
    const response = await fetch(`${base}/bottom-nav-link`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      mode: 'cors',
      cache: 'no-cache',
    });
    
    if (response.ok) {
      const data = await response.json();
      const linkUrl = data.link_url || '/v2/scanner-v2';
      console.log('[getScannerLink] API 응답:', { link_url: linkUrl, link_type: data.link_type, full_data: data });
      return linkUrl;
    } else {
      console.warn('[getScannerLink] API 응답 실패:', { status: response.status, statusText: response.statusText });
    }
  } catch (error) {
    console.error('[getScannerLink] 스캐너 링크 조회 실패:', error);
  }
  // 에러 시 기본값 반환
  console.warn('[getScannerLink] fallback 사용: /v2/scanner-v2');
  return '/v2/scanner-v2';
};

