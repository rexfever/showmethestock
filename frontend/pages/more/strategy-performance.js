// 전략 성과 페이지
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Layout from '../../layouts/v2/Layout';

const getConfig = () => {
  if (typeof window !== 'undefined') {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const backendUrl = isLocal 
      ? 'http://localhost:8010'
      : (process.env.NEXT_PUBLIC_BACKEND_URL || (process.env.NODE_ENV === 'production' ? 'https://sohntech.ai.kr/api' : 'http://localhost:8010'));
    return { backendUrl };
  } else {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8010';
    return { backendUrl };
  }
};

export default function StrategyPerformance() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [isActive, setIsActive] = useState(false);

  useEffect(() => {
    setMounted(true);
    // 전략 성과 기능 활성화 여부 확인 (현재는 비활성)
    setIsActive(false);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <>
      <Head>
        <title>전략 성과 - 스톡인사이트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <Layout headerTitle="스톡인사이트">
        {/* 정보 배너 - 개선된 그라데이션 */}
        <div className="relative bg-gradient-to-br from-green-600 via-emerald-600 to-teal-600 text-white overflow-hidden">
          {/* 배경 패턴 */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute inset-0" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }}></div>
          </div>
          
          <div className="relative p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold mb-1">
                  전략 성과
                </h2>
                <p className="text-sm opacity-90">
                  전략별 수익률 통계 및 성과 분석
                </p>
              </div>
              <div className="hidden sm:block">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 메인 컨텐츠 */}
        <div className="bg-gradient-to-b from-gray-50 via-gray-50 to-white min-h-screen">
          <div className="px-4 py-6">
            {/* 뒤로가기 버튼 */}
            <button
              onClick={() => router.push('/more')}
              className="mb-6 flex items-center text-gray-600 hover:text-gray-900 transition-colors group"
            >
              <svg
                className="w-5 h-5 mr-2 transform group-hover:-translate-x-1 transition-transform"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="text-sm font-medium">뒤로가기</span>
            </button>
            
            {isActive ? (
              <div className="space-y-4">
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-shadow">
                  <div className="text-gray-900 font-semibold text-lg mb-2">중기 전략</div>
                  <div className="text-gray-600 text-sm">성과 데이터 준비 중...</div>
                </div>
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-shadow">
                  <div className="text-gray-900 font-semibold text-lg mb-2">단기 전략</div>
                  <div className="text-gray-600 text-sm">성과 데이터 준비 중...</div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                {/* 상단 그라데이션 */}
                <div className="h-2 bg-gradient-to-r from-green-500 to-emerald-500"></div>
                
                <div className="p-8 text-center">
                  {/* 아이콘 */}
                  <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-green-100 to-emerald-100 flex items-center justify-center">
                    <svg className="w-10 h-10 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  
                  <h3 className="text-xl font-bold text-gray-900 mb-2">
                    준비 중입니다
                  </h3>
                  <p className="text-gray-600 text-base leading-relaxed">
                    전략 성과 분석 기능은 현재 개발 중입니다.
                    <br />
                    곧 만나보실 수 있습니다.
                  </p>
                  
                  {/* 장식 요소 */}
                  <div className="mt-6 flex justify-center space-x-2">
                    <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                </div>
              </div>
            )}
            
            {/* 하단 여백 */}
            <div className="h-8"></div>
          </div>
        </div>
      </Layout>
    </>
  );
}

