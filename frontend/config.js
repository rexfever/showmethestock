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
  const env = process.env.NODE_ENV || 'development';
  return config[env];
};

export default getConfig;
