import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';

export default function HomePage() {
  const router = useRouter();
  const [isMobile, setIsMobile] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 디바이스 감지
    const userAgent = navigator.userAgent.toLowerCase();
    const isMobileDevice = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
    setIsMobile(isMobileDevice);
    
    // 초기화면 설정 확인 및 리다이렉트
    const initialScreen = localStorage.getItem('initialScreen') || 'korean';
    if (initialScreen === 'us') {
      router.push('/v2/us-stocks-scanner');
    } else {
      router.push('/v2/scanner-v2');
    }
    
    setLoading(false);
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
        <div className="text-white text-xl">로딩 중...</div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>스톡인사이트 - 손테크</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="description" content="AI 기반 주식 스캐너로 투자 기회를 발견하세요" />
      </Head>

      <div className="min-h-screen" style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
      }}>
        {isMobile ? (
          // 모바일 버전 - 원본과 정확히 동일
          <div>
            <div className="text-center text-white py-10 px-5">
              <h1 className="text-4xl font-bold mb-4" style={{ textShadow: '2px 2px 4px rgba(0,0,0,0.3)' }}>
                스톡인사이트
              </h1>
              <p className="text-lg mb-8 opacity-90">AI 기반 주식 스캐너</p>
              <button
                onClick={() => router.push('/v2/scanner-v2')}
                className="inline-block text-white px-8 py-3 rounded-full font-bold text-lg transition-all duration-300 hover:transform hover:-translate-y-0.5"
                style={{
                  background: '#ff6b6b',
                  boxShadow: '0 4px 15px rgba(255, 107, 107, 0.3)'
                }}
              >
                스캐너 시작
              </button>
            </div>

            <div className="px-5 my-10">
              <div className="bg-white p-6 rounded-2xl text-center mb-5 shadow-lg">
                <div className="text-4xl mb-4">📊</div>
                <h3 className="text-xl font-semibold mb-3 text-gray-800">실시간 분석</h3>
                <p className="text-gray-600 text-sm leading-relaxed">실시간 주식 데이터 분석</p>
              </div>
              <div className="bg-white p-6 rounded-2xl text-center mb-5 shadow-lg">
                <div className="text-4xl mb-4">🤖</div>
                <h3 className="text-xl font-semibold mb-3 text-gray-800">AI 스캐닝</h3>
                <p className="text-gray-600 text-sm leading-relaxed">기술적 지표 종합 분석으로 매수/매도 신호 제공</p>
              </div>
              <div className="bg-white p-6 rounded-2xl text-center mb-5 shadow-lg">
                <div className="text-4xl mb-4">📱</div>
                <h3 className="text-xl font-semibold mb-3 text-gray-800">모바일 알림</h3>
                <p className="text-gray-600 text-sm leading-relaxed">카카오톡 알림톡으로 실시간 투자 기회 알림</p>
              </div>
            </div>

            <div className="mx-5 my-10 p-6 rounded-2xl text-white" style={{
              background: 'rgba(255,255,255,0.1)',
              backdropFilter: 'blur(10px)'
            }}>
              <h2 className="text-2xl font-bold mb-4">손테크</h2>
              <div className="space-y-2 text-sm">
                <p><strong>서비스:</strong> 스톡인사이트</p>
                <p><strong>주소:</strong> 서울시 송파구 올림픽로 435</p>
                <p><strong>이메일:</strong> sohnaitech@gmail.com</p>
                <p><strong>연락처:</strong> 02-501-0956</p>
              </div>
            </div>
          </div>
        ) : (
          // PC 버전 - 원본과 정확히 동일
          <div className="max-w-6xl mx-auto px-5">
            <div className="text-center text-white py-20">
              <h1 className="text-6xl font-bold mb-5" style={{ textShadow: '2px 2px 4px rgba(0,0,0,0.3)' }}>
                스톡인사이트
              </h1>
              <p className="text-xl mb-10 opacity-90">AI 기반 주식 스캐너로 투자 기회를 발견하세요</p>
              <button
                onClick={() => router.push('/v2/scanner-v2')}
                className="inline-block text-white px-10 py-4 rounded-full font-bold text-xl transition-all duration-300 hover:transform hover:-translate-y-0.5"
                style={{
                  background: '#ff6b6b',
                  boxShadow: '0 4px 15px rgba(255, 107, 107, 0.3)'
                }}
              >
                스캐너 시작하기
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-10 my-20">
              <div className="bg-white p-10 rounded-2xl text-center shadow-lg transition-transform duration-300 hover:transform hover:-translate-y-1">
                <div className="text-5xl mb-5">📊</div>
                <h3 className="text-2xl font-semibold mb-4 text-gray-800">실시간 분석</h3>
                <p className="text-gray-600 leading-relaxed">실시간 주식 데이터 분석으로 최신 시장 동향을 파악합니다.</p>
              </div>
              <div className="bg-white p-10 rounded-2xl text-center shadow-lg transition-transform duration-300 hover:transform hover:-translate-y-1">
                <div className="text-5xl mb-5">🤖</div>
                <h3 className="text-2xl font-semibold mb-4 text-gray-800">AI 스캐닝</h3>
                <p className="text-gray-600 leading-relaxed">다양한 기술적 지표를 종합하여 매수/매도 신호를 자동으로 분석하고 추천합니다.</p>
              </div>
              <div className="bg-white p-10 rounded-2xl text-center shadow-lg transition-transform duration-300 hover:transform hover:-translate-y-1">
                <div className="text-5xl mb-5">📱</div>
                <h3 className="text-2xl font-semibold mb-4 text-gray-800">모바일 알림</h3>
                <p className="text-gray-600 leading-relaxed">카카오톡 알림톡을 통해 중요한 투자 기회를 놓치지 않고 실시간으로 알려드립니다.</p>
              </div>
            </div>

            <div className="p-10 rounded-2xl text-white mt-16" style={{
              background: 'rgba(255,255,255,0.1)',
              backdropFilter: 'blur(10px)'
            }}>
              <h2 className="text-3xl font-bold mb-5">손테크</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto text-left">
                <p><strong>서비스명:</strong> 스톡인사이트</p>
                <p><strong>주소:</strong> 서울시 송파구 올림픽로 435</p>
                <p><strong>이메일:</strong> sohnaitech@gmail.com</p>
                <p><strong>연락처:</strong> 02-501-0956</p>
                <p><strong>사업자등록번호:</strong> 530-44-01163</p>
              </div>
            </div>
          </div>
        )}
        
      </div>
    </>
  );
}