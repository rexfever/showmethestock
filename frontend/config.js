// 환경별 설정 - 간단하고 명확한 구조
const config = {
  development: {
    domain: 'http://localhost:3000',
    backendUrl: 'http://localhost:8000'
  },
  production: {
    domain: 'https://sohntech.ai.kr',
    backendUrl: 'https://sohntech.ai.kr/api'
  }
};

// 현재 환경에 맞는 설정 반환
const getConfig = () => {
  // NODE_ENV로 환경 판단 (간단하고 명확)
  const env = process.env.NODE_ENV || 'development';
  return config[env];
};

export default getConfig;
