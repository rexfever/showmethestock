// 전략 설명 목록 페이지
import { useRouter } from 'next/router';
import Head from 'next/head';
import Layout from '../../layouts/v2/Layout';

export default function StrategyDescription() {
  const router = useRouter();

  const strategies = [
    { 
      id: 'midterm', 
      label: '중기 전략', 
      path: '/more/strategy-description/midterm',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
      gradient: 'from-indigo-500 to-purple-500',
      bgGradient: 'from-indigo-50 to-purple-50',
      description: '25거래일 관찰 기간의 중기 투자 전략'
    },
    { 
      id: 'v2lite', 
      label: '단기 전략', 
      path: '/more/strategy-description/v2lite',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      gradient: 'from-blue-500 to-cyan-500',
      bgGradient: 'from-blue-50 to-cyan-50',
      description: '15거래일 관찰 기간의 단기 투자 전략'
    },
  ];

  return (
    <>
      <Head>
        <title>전략 설명 - 스톡인사이트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <Layout headerTitle="스톡인사이트">
        {/* 정보 배너 - 개선된 그라데이션 */}
        <div className="relative bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 text-white overflow-hidden">
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
                  전략 설명
                </h2>
                <p className="text-sm opacity-90">
                  사용 중인 투자 전략에 대한 상세 설명
                </p>
              </div>
              <div className="hidden sm:block">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
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

            <div className="space-y-4">
              {strategies.map((strategy, index) => (
                <button
                  key={strategy.id}
                  onClick={() => router.push(strategy.path)}
                  className="group relative w-full text-left bg-white rounded-2xl shadow-lg hover:shadow-2xl border border-gray-100 overflow-hidden transition-all duration-300 transform hover:-translate-y-1"
                  style={{
                    animationDelay: `${index * 100}ms`
                  }}
                >
                  {/* 그라데이션 배경 */}
                  <div className={`absolute inset-0 bg-gradient-to-br ${strategy.bgGradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}></div>
                  
                  {/* 아이콘 배경 원형 그라데이션 */}
                  <div className={`absolute top-4 right-4 w-16 h-16 rounded-full bg-gradient-to-br ${strategy.gradient} opacity-10 group-hover:opacity-20 transition-opacity duration-300 blur-xl`}></div>
                  
                  <div className="relative p-6 flex items-center space-x-4">
                    {/* 아이콘 */}
                    <div className={`flex-shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br ${strategy.gradient} flex items-center justify-center text-white shadow-lg transform group-hover:scale-110 group-hover:rotate-3 transition-all duration-300`}>
                      {strategy.icon}
                    </div>
                    
                    {/* 텍스트 */}
                    <div className="flex-1 min-w-0">
                      <h3 className="text-gray-900 text-lg font-semibold group-hover:text-gray-800 transition-colors mb-1">
                        {strategy.label}
                      </h3>
                      <p className="text-gray-500 text-sm">
                        {strategy.description}
                      </p>
                    </div>
                    
                    {/* 화살표 아이콘 */}
                    <div className="flex-shrink-0 text-gray-400 group-hover:text-gray-600 transform group-hover:translate-x-1 transition-all duration-300">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                  
                  {/* 하단 그라데이션 라인 */}
                  <div className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r ${strategy.gradient} transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left`}></div>
                </button>
              ))}
            </div>
            
            {/* 하단 여백 */}
            <div className="h-8"></div>
          </div>
        </div>
      </Layout>
    </>
  );
}

