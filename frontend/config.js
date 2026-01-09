// 환경별 설정 - 간단하고 명확한 구조
const config = {
  development: {
    domain: 'http://localhost:3000',
    backendUrl: 'http://localhost:8010'
  },
  production: {
    domain: 'https://sohntech.ai.kr',
    backendUrl: 'https://sohntech.ai.kr/api'
  }
};

// 현재 환경에 맞는 설정 반환
const getConfig = () => {
  // 클라이언트 사이드에서는 hostname으로 로컬 환경 감지
  if (typeof window !== 'undefined') {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocal) {
      return config.development;
    }
  }
  
  // NODE_ENV로 환경 판단 (서버 사이드 또는 프로덕션)
  const env = process.env.NODE_ENV || 'development';
  const result = config[env] || config.development; // fallback to development
  
  // 디버깅용 (개발 환경에서만)
  if (typeof window !== 'undefined' && env === 'development') {
    console.log('[Config] 환경:', env, 'backendUrl:', result.backendUrl);
  }
  
  return result;
};

export default getConfig;
