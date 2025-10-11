import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import { fetchPortfolio } from '../services/portfolioService';
import { calculateHoldingPeriod, formatDate, formatCurrency, formatPercentage } from '../utils/portfolioUtils';
import { handleError } from '../utils/errorHandler';

export default function Portfolio() {
  const router = useRouter();
  const { isAuthenticated, user, loading: authLoading, authChecked, logout } = useAuth();
  const [portfolio, setPortfolio] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authChecked && !authLoading && isAuthenticated()) {
      loadPortfolio();
    }
  }, [authChecked, authLoading, isAuthenticated]);

  const loadPortfolio = async () => {
    try {
      setLoading(true);
      const data = await fetchPortfolio();
      setPortfolio(data);
    } catch (error) {
      handleError(error, '포트폴리오 로드');
      setPortfolio([]);
    } finally {
      setLoading(false);
    }
  };

  if (!authChecked || authLoading) {
    return (
      <>
        <Head>
          <title>나의투자종목 - Stock Insight</title>
        </Head>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">로딩 중...</p>
          </div>
        </div>
      </>
    );
  }

  if (!isAuthenticated()) {
    return (
      <>
        <Head>
          <title>나의투자종목 - Stock Insight</title>
        </Head>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">로그인이 필요합니다</h2>
            <p className="text-gray-600 mb-6">나의투자종목을 관리하려면 로그인해주세요.</p>
            <a href="/login" className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600">
              로그인하기
            </a>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Head>
        <title>나의투자종목 - Stock Insight</title>
      </Head>
      
      <div className="min-h-screen bg-gray-50">
        {/* 상단 헤더 */}
        <div className="bg-white shadow-sm border-b">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center">
              <button 
                onClick={() => router.push('/')}
                className="text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors"
              >
                Stock Insight
              </button>
            </div>
            <div className="flex items-center space-x-4">
              {user ? (
                <span className="text-sm text-gray-600">
                  {user.name}님 ({user.provider})
                </span>
              ) : (
                <span className="text-sm text-gray-500">게스트 사용자</span>
              )}
            </div>
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="p-4">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-600">포트폴리오를 불러오는 중...</p>
            </div>
          ) : portfolio.length > 0 ? (
            <div className="space-y-4">
              {portfolio.map((item) => (
                <div key={item.id} className="bg-white rounded-lg shadow-sm border p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <div className="font-semibold text-gray-800">
                        {item.name}
                        <span className="text-xs text-gray-500 ml-2">({item.ticker})</span>
                      </div>
                      <div className="text-sm text-gray-600">
                        현재가: {formatCurrency(item.current_price)}원
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-gray-500">매수가:</span>
                      <span className="ml-2 text-gray-800">{formatCurrency(item.entry_price)}원</span>
                    </div>
                    <div>
                      <span className="text-gray-500">수량:</span>
                      <span className="ml-2 text-gray-800">{item.quantity || '-'}주</span>
                    </div>
                    <div>
                      <span className="text-gray-500">손익:</span>
                      <span className={`ml-2 ${item.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(item.profit_loss)}원
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">수익률:</span>
                      <span className={`ml-2 ${item.profit_loss_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatPercentage(item.profit_loss_pct)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-gray-500">매수일:</span>
                        <span className="ml-2 text-gray-800">{formatDate(item.entry_date)}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">보유기간:</span>
                        <span className="ml-2 text-gray-800 font-medium">{calculateHoldingPeriod(item.entry_date)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">📊</div>
              <h3 className="text-lg font-medium text-gray-800 mb-2">나의투자종목이 비어있습니다</h3>
              <p className="text-gray-600 mb-6">스캐너에서 관심있는 종목을 투자등록해보세요.</p>
              <a 
                href="/customer-scanner" 
                className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600"
              >
                스캐너에서 종목 찾기
              </a>
            </div>
          )}
        </div>

        {/* 하단 네비게이션 */}
        <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
          <div className="flex justify-around items-center py-2">
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => router.push('/customer-scanner')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="text-xs">홈</span>
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
              className="flex flex-col items-center py-2 bg-gray-700"
              onClick={() => router.push('/portfolio')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              <span className="text-xs">나의투자종목</span>
            </button>
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={async () => {
                if (user && logout) {
                  try {
                    await logout();
                    router.push('/customer-scanner');
                  } catch (error) {
                    console.error('로그아웃 중 오류:', error);
                    // 오류가 발생해도 고객스캔 페이지로 이동
                    router.push('/customer-scanner');
                  }
                } else {
                  router.push('/login');
                }
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              <span className="text-xs">{user ? '로그아웃' : '로그인'}</span>
            </button>
          </div>
        </div>

        {/* 하단 네비게이션 공간 확보 */}
        <div className="h-20"></div>
      </div>
    </>
  );
}