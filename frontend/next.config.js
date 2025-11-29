/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  // experimental 설정 제거 (Next.js 13.5.6에서 불필요)
  // Node.js 18+ 호환성
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }
    return config;
  },
  // 리다이렉트 설정
  async redirects() {
    return [
      {
        source: '/customer-scanner',
        destination: '/v2/scanner-v2',
        permanent: false, // 307 리다이렉트 (임시 리다이렉트)
      },
    ];
  },
};

module.exports = nextConfig;


