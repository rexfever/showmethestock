// 더보기 메인 페이지 (재구성)
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Layout from '../layouts/v2/Layout';

export default function More() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [faqOpen, setFaqOpen] = useState(false);
  const faqRef = useRef(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  const handleCardClick = (path) => {
    if (path) {
      router.push(path);
    }
  };

  const handleFaqToggle = () => {
    setFaqOpen(!faqOpen);
    if (!faqOpen && faqRef.current) {
      setTimeout(() => {
        faqRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  };

  return (
    <>
      <Head>
        <title>더보기 - 스톡인사이트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <Layout headerTitle="스톡인사이트">
        {/* 정보 배너 */}
        <div className="relative bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 text-white overflow-hidden">
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
                  더보기
                </h2>
                <p className="text-sm opacity-90">
                  서비스 정보 및 설정을 확인하세요
                </p>
              </div>
              <div className="hidden sm:block">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 메인 컨텐츠 */}
        <div className="bg-gradient-to-b from-gray-50 via-gray-50 to-white min-h-screen">
          <div className="px-4 py-6 space-y-8">
            
            {/* 블록 1: 일일 추천 */}
            <div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">일일 추천</h3>
              
              {/* 1) 기본 설명 (정적) */}
              <div className="mb-4">
                <p className="text-gray-700 text-base">
                  매 거래일마다 추천 종목을 제공합니다.
                </p>
              </div>

              {/* 2) 전략 설명 (카드) */}
              <button
                onClick={() => handleCardClick('/more/strategy-description/v2')}
                className="group relative w-full text-left bg-white rounded-2xl shadow-lg hover:shadow-2xl border border-gray-100 overflow-hidden transition-all duration-300 transform hover:-translate-y-1 mb-4"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-cyan-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="absolute top-4 right-4 w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 opacity-10 group-hover:opacity-20 transition-opacity duration-300 blur-xl"></div>
                
                <div className="relative p-6 flex items-center space-x-4">
                  <div className="flex-shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white shadow-lg transform group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="text-gray-900 text-lg font-semibold group-hover:text-gray-800 transition-colors">
                      일일 추천 전략 설명
                    </h4>
                    <p className="text-gray-500 text-sm mt-1">
                      전략 구성과 추천 방식 안내
                    </p>
                  </div>
                  
                  <div className="flex-shrink-0 text-gray-400 group-hover:text-gray-600 transform group-hover:translate-x-1 transition-all duration-300">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
                
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-cyan-500 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left"></div>
              </button>

              {/* 3) 기록 확인 - 성과 */}
              <button
                onClick={() => handleCardClick('/more/strategy-performance?scanner_version=v2')}
                className="group relative w-full text-left bg-white rounded-2xl shadow-lg hover:shadow-2xl border border-gray-100 overflow-hidden transition-all duration-300 transform hover:-translate-y-1"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-green-50 to-emerald-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="absolute top-4 right-4 w-16 h-16 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 opacity-10 group-hover:opacity-20 transition-opacity duration-300 blur-xl"></div>
                
                <div className="relative p-6 flex items-center space-x-4">
                  <div className="flex-shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center text-white shadow-lg transform group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="text-gray-900 text-lg font-semibold group-hover:text-gray-800 transition-colors">
                      일일 추천 성과
                    </h4>
                    <p className="text-gray-500 text-sm mt-1">
                      전략 요약 통계
                    </p>
                  </div>
                  
                  <div className="flex-shrink-0 text-gray-400 group-hover:text-gray-600 transform group-hover:translate-x-1 transition-all duration-300">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
                
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-green-500 to-emerald-500 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left"></div>
              </button>
            </div>

            {/* 블록 2: 조건 추천 */}
            <div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">조건 추천</h3>
              
              {/* 1) 기본 설명 (정적) */}
              <div className="mb-4">
                <p className="text-gray-700 text-base">
                  정해진 조건이 충족되었을 때만 추천 종목을 제공합니다.
                </p>
              </div>

              {/* 2) 전략 설명 (카드) */}
              <button
                onClick={() => handleCardClick('/more/strategy-description/v3')}
                className="group relative w-full text-left bg-white rounded-2xl shadow-lg hover:shadow-2xl border border-gray-100 overflow-hidden transition-all duration-300 transform hover:-translate-y-1 mb-4"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-cyan-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="absolute top-4 right-4 w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 opacity-10 group-hover:opacity-20 transition-opacity duration-300 blur-xl"></div>
                
                <div className="relative p-6 flex items-center space-x-4">
                  <div className="flex-shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white shadow-lg transform group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="text-gray-900 text-lg font-semibold group-hover:text-gray-800 transition-colors">
                      조건 추천 전략 설명
                    </h4>
                    <p className="text-gray-500 text-sm mt-1">
                      추천 생성 및 관리 방식 안내
                    </p>
                  </div>
                  
                  <div className="flex-shrink-0 text-gray-400 group-hover:text-gray-600 transform group-hover:translate-x-1 transition-all duration-300">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
                
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-cyan-500 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left"></div>
              </button>

              {/* 3) 기록 확인 - ARCHIVED */}
              <button
                onClick={() => handleCardClick('/more/archived-history?scanner_version=v3')}
                className="group relative w-full text-left bg-white rounded-2xl shadow-lg hover:shadow-2xl border border-gray-100 overflow-hidden transition-all duration-300 transform hover:-translate-y-1 mb-4"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-purple-50 to-indigo-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="absolute top-4 right-4 w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-indigo-500 opacity-10 group-hover:opacity-20 transition-opacity duration-300 blur-xl"></div>
                
                <div className="relative p-6 flex items-center space-x-4">
                  <div className="flex-shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center text-white shadow-lg transform group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="text-gray-900 text-lg font-semibold group-hover:text-gray-800 transition-colors">
                      조건 추천 이력
                    </h4>
                    <p className="text-gray-500 text-sm mt-1">
                      종료된 추천 종목 기록
                    </p>
                  </div>
                  
                  <div className="flex-shrink-0 text-gray-400 group-hover:text-gray-600 transform group-hover:translate-x-1 transition-all duration-300">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
                
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 to-indigo-500 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left"></div>
              </button>

              {/* 4) 기록 확인 - 성과 */}
              <button
                onClick={() => handleCardClick('/more/strategy-performance?scanner_version=v3')}
                className="group relative w-full text-left bg-white rounded-2xl shadow-lg hover:shadow-2xl border border-gray-100 overflow-hidden transition-all duration-300 transform hover:-translate-y-1"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-green-50 to-emerald-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="absolute top-4 right-4 w-16 h-16 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 opacity-10 group-hover:opacity-20 transition-opacity duration-300 blur-xl"></div>
                
                <div className="relative p-6 flex items-center space-x-4">
                  <div className="flex-shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center text-white shadow-lg transform group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="text-gray-900 text-lg font-semibold group-hover:text-gray-800 transition-colors">
                      조건 추천 성과
                    </h4>
                    <p className="text-gray-500 text-sm mt-1">
                      전략 요약 통계
                    </p>
                  </div>
                  
                  <div className="flex-shrink-0 text-gray-400 group-hover:text-gray-600 transform group-hover:translate-x-1 transition-all duration-300">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
                
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-green-500 to-emerald-500 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left"></div>
              </button>
            </div>

            {/* 블록 3: 서비스 공통 안내 */}
            <div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">서비스 공통 안내</h3>
              <button
                onClick={() => handleCardClick('/more/service-guide')}
                className="group relative w-full text-left bg-white rounded-2xl shadow-lg hover:shadow-2xl border border-gray-100 overflow-hidden transition-all duration-300 transform hover:-translate-y-1"
              >
                <div className="absolute inset-0 bg-gray-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                
                <div className="relative p-6 flex items-center space-x-4">
                  <div className="flex-shrink-0 w-14 h-14 rounded-xl flex items-center justify-center transform group-hover:scale-105 transition-all duration-300" style={{ backgroundColor: '#E2E8F0' }}>
                    <svg className="w-6 h-6" fill="none" stroke="#334155" viewBox="0 0 24 24" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                    </svg>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="text-gray-900 text-lg font-semibold group-hover:text-gray-800 transition-colors">
                      서비스 안내
                    </h4>
                    <p className="text-gray-500 text-sm mt-1">
                      서비스 이용 가이드
                    </p>
                  </div>
                  
                  <div className="flex-shrink-0 text-gray-400 group-hover:text-gray-600 transform group-hover:translate-x-1 transition-all duration-300">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
                
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-[#475569] opacity-20 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left"></div>
              </button>
            </div>

            {/* 블록 4: FAQ */}
            <div ref={faqRef}>
              <button
                onClick={handleFaqToggle}
                className="w-full text-left bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden mb-4"
              >
                <div className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                  <h3 className="text-xl font-bold text-gray-900">
                    자주 묻는 질문
                  </h3>
                  <svg
                    className={`w-5 h-5 text-gray-500 transform transition-transform ${faqOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {faqOpen && (
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                  <div className="px-6 pb-6 space-y-4">
                    <div className="pb-4 border-b border-gray-100">
                      <h4 className="text-gray-900 font-semibold text-base mb-2">
                        추천 종목은 언제 추가되나요?
                      </h4>
                      <p className="text-gray-600 text-sm leading-relaxed">
                        일정 조건이 충족되었을 때만 추천 종목이 표시됩니다. 조건이 맞지 않으면 새 추천이 없을 수도 있습니다.
                      </p>
                    </div>
                    <div className="pb-4 border-b border-gray-100">
                      <h4 className="text-gray-900 font-semibold text-base mb-2">
                        추천이 없어지거나 바뀔 수도 있나요?
                      </h4>
                      <p className="text-gray-600 text-sm leading-relaxed">
                        상황 변화에 따라 추천이 종료되거나 관리 대상에서 제외될 수 있습니다.
                      </p>
                    </div>
                    <div>
                      <h4 className="text-gray-900 font-semibold text-base mb-2">
                        이 추천대로 꼭 투자해야 하나요?
                      </h4>
                      <p className="text-gray-600 text-sm leading-relaxed">
                        추천은 참고용이며, 투자 판단은 사용자가 직접 결정합니다.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

          </div>
          
          {/* 하단 여백 */}
          <div className="h-8"></div>
        </div>
      </Layout>
    </>
  );
}
