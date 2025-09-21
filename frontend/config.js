// 환경별 설정
const config = {
  development: {
    domain: 'http://localhost:3000',
    backendUrl: 'http://localhost:8010'
  },
  production: {
    domain: 'https://sohntech.ai.kr',
    backendUrl: 'https://sohntech.ai.kr/backend'
  }
};

// 현재 환경에 맞는 설정 반환
const getConfig = () => {
  // 환경 변수가 있으면 우선 사용
  if (process.env.NEXT_PUBLIC_DOMAIN) {
    return {
      domain: process.env.NEXT_PUBLIC_DOMAIN,
      backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL || config.production.backendUrl
    };
  }
  
  // 환경 변수가 없으면 기본 설정 사용
  const env = process.env.NODE_ENV || 'development';
  return config[env];
};

export default getConfig;
