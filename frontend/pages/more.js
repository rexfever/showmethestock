import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import Header from '../components/Header';

export default function More() {
  const router = useRouter();
  const { isAuthenticated, user, loading: authLoading, authChecked, logout } = useAuth();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogout = async () => {
    if (user && logout) {
      try {
        await logout();
        router.push('/customer-scanner');
      } catch (error) {
        console.error('로그아웃 중 오류:', error);
        router.push('/customer-scanner');
      }
    }
  };

  if (!mounted) {
    return null;
  }

  return (
    <>
      <Head>
        <title>더보기 - 스톡인사이트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        <Header />

        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">더보기</h2>
              <p className="text-sm opacity-90">다양한 서비스와 설정을 확인하세요</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <span className="text-2xl">⚙️</span>
            </div>
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="p-4">
          {/* 사용자 정보 카드 */}
          {!authLoading && authChecked && user ? (
            <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-xl">👤</span>
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-gray-900">{user.name}님</div>
                  <div className="text-sm text-gray-600">
                    {user.is_admin ? '🔧 관리자' : 
                     user.membership_tier === 'premium' ? '👑 프리미엄 회원' : '일반 회원'} ({user.provider})
                  </div>
                  {/* 디버깅 정보 */}
                  <div className="text-xs text-gray-400 mt-1">
                    Debug: is_admin={String(user.is_admin)} ({typeof user.is_admin}), tier={user.membership_tier}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-500">포인트</div>
                  <div className="font-semibold text-blue-600">0P</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-xl">👤</span>
                </div>
                <div className="font-semibold text-gray-900 mb-2">게스트 사용자</div>
                <button 
                  onClick={() => router.push('/login')}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
                >
                  로그인하기
                </button>
              </div>
            </div>
          )}




          {/* 투자 활용법 가이드 */}
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <h3 className="font-semibold text-gray-900 mb-4">투자 활용법</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xl">🔍</span>
                  <h4 className="font-semibold text-gray-800">어떤 종목을 찾나요?</h4>
                </div>
                <p className="text-sm text-gray-600 font-medium">📈 상승 초입 단계의 종목들</p>
                <p className="text-xs text-gray-500 mt-1">• 하락이 끝나고 막 오르기 시작하는 종목</p>
                <p className="text-xs text-gray-500">• 거래량이 늘어나며 관심받기 시작하는 종목</p>
                <p className="text-xs text-blue-600 mt-2 font-medium">💡 상승 초기에 발견해서 수익 기회 제공</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xl">💰</span>
                  <h4 className="font-semibold text-gray-800">어떻게 투자하나요?</h4>
                </div>
                <p className="text-sm text-gray-600 font-medium">🎯 단기 스윙 투자 (1주일 내외)</p>
                <p className="text-xs text-gray-500 mt-1">• 상승 초입에서 매수 → 상승 후 매도</p>
                <p className="text-xs text-gray-500">• 목표: 5~10% 수익, 손절: -5% 이하</p>
                <p className="text-xs text-gray-500">• 욕심내지 말고 적당한 수익에서 매도</p>
                <div className="mt-2 p-2 bg-green-100 rounded">
                  <p className="text-xs text-green-700 font-medium">💡 핵심: 상승 파도를 타고 적당히 내리기</p>
                </div>
                <p className="text-xs text-red-500 mt-2 font-medium">⚠️ 투자는 본인 책임, 신중한 판단 필요</p>
              </div>
            </div>
          </div>

          {/* 준비중인 기능 */}
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <h3 className="font-semibold text-gray-900 mb-4">준비중인 기능</h3>
            <div className="bg-orange-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <h5 className="font-medium text-orange-700 mb-2">📱 알림 서비스</h5>
                  <ul className="space-y-1 text-orange-600">
                    <li>• <strong>카카오톡 알림톡</strong>: 스캔 결과 자동 알림</li>
                    <li>• <strong>푸시 알림</strong>: 모바일 앱 알림</li>
                    <li>• <strong>이메일 알림</strong>: 상세 분석 리포트</li>
                  </ul>
                </div>
                <div>
                  <h5 className="font-medium text-orange-700 mb-2">💼 관심종목 관리</h5>
                  <ul className="space-y-1 text-orange-600">
                    <li>• <strong>관심종목 등록</strong>: 스캔 결과에서 바로 등록</li>
                    <li>• <strong>관심종목 목록</strong>: 등록한 종목 관리</li>
                    <li>• <strong>알림 설정</strong>: 관심종목 변동 알림</li>
                  </ul>
                </div>
                <div>
                  <h5 className="font-medium text-orange-700 mb-2">📊 고급 분석</h5>
                  <ul className="space-y-1 text-orange-600">
                    <li>• <strong>상세 차트</strong>: 기술적 분석 도구</li>
                    <li>• <strong>기업정보</strong>: 재무제표 및 뉴스</li>
                    <li>• <strong>종목분석</strong>: 단일 종목 상세 분석</li>
                  </ul>
                </div>
              </div>
              <div className="mt-4 p-3 bg-orange-100 rounded-lg">
                <p className="text-sm text-orange-700">
                  <strong>💡 안내:</strong> 모든 기능은 순차적으로 출시될 예정입니다. 
                  먼저 기본 스캔 서비스를 이용해보시고, 추가 기능 출시 소식을 기다려주세요!
                </p>
              </div>
            </div>
          </div>

          {/* 계정 관리 */}
          {!authLoading && authChecked && user && (
            <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
              <h3 className="font-semibold text-gray-900 mb-4">계정 관리</h3>
              <div className="space-y-3">
                <button 
                  onClick={handleLogout}
                  className="w-full flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                      <span className="text-sm">🚪</span>
                    </div>
                    <span className="text-gray-700">로그아웃</span>
                  </div>
                  <span className="text-gray-400">›</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 하단 네비게이션 */}
        <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
          <div className="flex items-center justify-around py-2">
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => router.push('/customer-scanner')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="text-xs">추천종목</span>
            </button>
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => router.push('/stock-analysis')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span className="text-xs">종목분석</span>
            </button>
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => router.push('/portfolio')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              <span className="text-xs">나의투자종목</span>
            </button>
            {user?.is_admin && (
              <button 
                className="flex flex-col items-center py-2 hover:bg-gray-800"
                onClick={() => router.push('/admin')}
              >
                <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span className="text-xs">관리자</span>
              </button>
            )}
            <button 
              className="flex flex-col items-center py-2 bg-gray-700"
              onClick={() => router.push('/more')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
              <span className="text-xs">더보기</span>
            </button>
          </div>
        </div>

        {/* 하단 네비게이션 공간 확보 */}
        <div className="h-20"></div>
      </div>
    </>
  );
}
