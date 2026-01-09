// 서비스 안내 페이지
import { useRouter } from 'next/router';
import Head from 'next/head';
import Layout from '../../layouts/v2/Layout';

export default function ServiceGuide() {
  const router = useRouter();

  const guideItems = [
    {
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="#334155" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      ),
      title: '추천 방식',
      description: '스톡인사이트는 특정 조건이 충족되었을 때만 추천 종목을 보여줍니다.'
    },
    {
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="#334155" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      title: '추천이 나오는 시점',
      description: '조건에 맞았다고 바로 표시하지 않고, 기준이 명확해졌을 때만 추천을 보여줍니다.'
    },
    {
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="#334155" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
        </svg>
      ),
      title: '이 서비스에서 하지 않는 일',
      description: '종목에 대한 해석이나 투자 조언은 제공하지 않습니다.'
    },
    {
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="#334155" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      title: '이용 안내',
      description: '제공되는 정보는 참고용이며, 투자 판단은 사용자가 직접 결정합니다.'
    },
  ];


  return (
    <>
      <Head>
        <title>서비스 안내 - 스톡인사이트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <Layout headerTitle="스톡인사이트">
        {/* 정보 배너 */}
        <div className="relative overflow-hidden" style={{ backgroundColor: '#E5EAF3' }}>
          {/* 배경 패턴 */}
          <div className="absolute inset-0 opacity-5">
            <div className="absolute inset-0" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }}></div>
          </div>
          
          <div className="relative p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold mb-1" style={{ color: '#1F2937' }}>
                  서비스 안내
                </h2>
                <p className="text-sm" style={{ color: '#1F2937', opacity: 0.7 }}>
                  서비스 성격 및 유의 사항 안내
                </p>
              </div>
              <div className="hidden sm:block">
                <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ backgroundColor: 'rgba(31, 41, 55, 0.1)' }}>
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ color: '#1F2937', opacity: 0.6 }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
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
              {guideItems.map((item, index) => (
                <div
                  key={index}
                  className="group relative bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden transition-all duration-300"
                  style={{
                    animationDelay: `${index * 100}ms`
                  }}
                >
                  <div className="relative p-6 flex items-center space-x-4">
                    {/* 아이콘 */}
                    <div 
                      className="flex-shrink-0 w-14 h-14 rounded-xl flex items-center justify-center"
                      style={{ backgroundColor: '#E2E8F0' }}
                    >
                      {item.icon}
                    </div>
                    
                    {/* 텍스트 */}
                    <div className="flex-1 min-w-0">
                      <h3 className="text-gray-900 text-lg font-semibold mb-1">
                        {item.title}
                      </h3>
                      <p className="text-gray-500 text-sm">
                        {item.description}
                      </p>
                    </div>
                  </div>
                </div>
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

