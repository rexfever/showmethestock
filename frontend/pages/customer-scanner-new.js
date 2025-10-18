import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useRouter } from 'next/router';
import getConfig from '../config';

export default function CustomerScannerNew({ initialData = [] }) {
  const { user, loading: authLoading, authChecked, isAuthenticated, logout, token } = useAuth();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // 스캔 결과 상태
  const [scanResults, setScanResults] = useState(initialData || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 포트폴리오 상태
  const [portfolioData, setPortfolioData] = useState([]);
  const [portfolioLoading, setPortfolioLoading] = useState(false);

  // 재등장 종목 상태
  const [recurringStocks, setRecurringStocks] = useState([]);
  const [recurringLoading, setRecurringLoading] = useState(false);

  // 투자 모달 상태
  const [showInvestmentModal, setShowInvestmentModal] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [investmentLoading, setInvestmentLoading] = useState(false);

  // 모바일 감지
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // 컴포넌트 마운트 상태
  useEffect(() => {
    setMounted(true);
  }, []);

  // 포트폴리오 조회
  const fetchPortfolio = useCallback(async () => {
    if (!token || !isAuthenticated() || !user) return;
    
    setPortfolioLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/portfolio`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setPortfolioData(data.items || []);
      }
    } catch (error) {
      console.error('포트폴리오 조회 실패:', error);
    } finally {
      setPortfolioLoading(false);
    }
  }, [token, isAuthenticated, user]);

  // 재등장 종목 조회
  const fetchRecurringStocks = useCallback(async () => {
    setRecurringLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/recurring-stocks?days=7&min_appearances=2`);
      const data = await response.json();
      
      if (data.ok && data.data && data.data.recurring_stocks) {
        const stocks = Object.entries(data.data.recurring_stocks).map(([ticker, stockData]) => ({
          ticker,
          ...stockData
        }));
        setRecurringStocks(stocks);
      } else {
        setRecurringStocks([]);
      }
    } catch (error) {
      console.error('재등장 종목 조회 실패:', error);
      setRecurringStocks([]);
    } finally {
      setRecurringLoading(false);
    }
  }, []);

  // 최신 스캔 결과 조회
  const fetchLatestScan = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/latest-scan`);
      const data = await response.json();
      
      if (data.ok && data.data && data.data.items) {
        setScanResults(data.data.items);
      } else {
        setError(data.error || '스캔 결과를 가져올 수 없습니다.');
        setScanResults([]);
      }
    } catch (error) {
      console.error('스캔 결과 조회 실패:', error);
      setError('스캔 결과를 가져올 수 없습니다.');
      setScanResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 초기 데이터 로드
  useEffect(() => {
    if (authChecked) {
      if (isAuthenticated() && user) {
        fetchPortfolio();
      }
      fetchRecurringStocks();
      
      // SSR 데이터가 없으면 API 호출
      if (!initialData || initialData.length === 0) {
        fetchLatestScan();
      }
    }
  }, [authChecked, isAuthenticated, user, fetchPortfolio, fetchRecurringStocks, fetchLatestScan, initialData]);

  // 투자 모달 열기
  const openInvestmentModal = (stock) => {
    setSelectedStock(stock);
    setShowInvestmentModal(true);
  };

  // 투자 모달 닫기
  const closeInvestmentModal = () => {
    setSelectedStock(null);
    setShowInvestmentModal(false);
  };

  // 투자 등록
  const handleInvestmentRegistration = async (stock, entryPrice, quantity) => {
    if (!isAuthenticated() || !user) {
      alert('로그인이 필요합니다.');
      return;
    }

    setInvestmentLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/portfolio/add`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ticker: stock.ticker,
          name: stock.name,
          entry_price: parseFloat(entryPrice),
          quantity: parseInt(quantity),
          source: 'recommended'
        })
      });

      if (response.ok) {
        alert('투자 등록이 완료되었습니다.');
        closeInvestmentModal();
        fetchPortfolio(); // 포트폴리오 새로고침
      } else {
        const errorData = await response.json();
        alert(`투자 등록 실패: ${errorData.error || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('투자 등록 실패:', error);
      alert('투자 등록 중 오류가 발생했습니다.');
    } finally {
      setInvestmentLoading(false);
    }
  };

  // 로그아웃
  const handleLogout = async () => {
    try {
      await logout();
      router.push('/customer-scanner');
    } catch (error) {
      console.error('로그아웃 실패:', error);
    }
  };

  // 로딩 중이거나 마운트되지 않은 경우
  if (!mounted || authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">오늘의 추천 종목</h1>
              <span className="ml-3 px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                {scanResults.length}개 종목
              </span>
            </div>
            
            <div className="flex items-center space-x-4">
              {isAuthenticated() && user ? (
                <>
                  <button
                    onClick={() => router.push('/portfolio')}
                    className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    나의 투자종목
                  </button>
                  <span className="text-sm text-gray-600">{user.email}</span>
                  <button
                    onClick={handleLogout}
                    className="bg-red-500 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-red-600"
                  >
                    로그아웃
                  </button>
                </>
              ) : (
                <button
                  onClick={() => router.push('/login')}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
                >
                  로그인
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 오늘의 추천 종목 */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">오늘의 추천 종목</h2>
            <button
              onClick={fetchLatestScan}
              disabled={loading}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            >
              {loading ? '새로고침 중...' : '새로고침'}
            </button>
          </div>

          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="mt-4 text-gray-600">스캔 결과를 불러오는 중...</p>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <div className="text-red-500 mb-4">⚠️ {error}</div>
              <button
                onClick={fetchLatestScan}
                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                다시 시도
              </button>
            </div>
          ) : scanResults.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">오늘의 추천 종목이 없습니다.</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {scanResults.map((item) => (
                <div key={item.ticker} className="bg-white rounded-lg shadow-sm border p-4 space-y-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-lg font-bold text-gray-900 truncate">
                        {item.name}
                      </h3>
                      {item.is_recurring && (
                        <div className="flex flex-col space-y-1">
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                            🔄 재스캔 {item.recurring_count}회
                          </span>
                          {item.latest_recurring_date && (
                            <span className="text-xs text-gray-500">
                              최근: {item.latest_recurring_date}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-xs text-gray-500 font-mono">
                        {item.ticker}
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        {item.market || (item.ticker && item.ticker.length === 6 ? 
                          (item.ticker.startsWith('0') ? '코스닥' : '코스피') : '')}
                      </span>
                    </div>
                    {/* 거래량과 거래대금 */}
                    <div className="text-xs text-gray-600 mt-1">
                      거래량: {item.volume > 0 ? `${(item.volume / 1000).toFixed(0)}K` : '데이터 없음'}
                      {item.volume > 0 && item.current_price > 0 && (
                        <span className="ml-4">거래대금: {Math.round(item.volume * item.current_price / 100000000).toLocaleString()}억</span>
                      )}
                    </div>
                    {/* 과거 등장일 표시 */}
                    {item.is_recurring && item.recurring_dates && item.recurring_dates.length > 0 && (
                      <div className="text-xs text-orange-600 mt-1">
                        과거 등장일: {item.recurring_dates.slice(0, 3).map(date => date.replace(/-/g, '/')).join(', ')}
                        {item.recurring_dates.length > 3 && ` 외 ${item.recurring_dates.length - 3}일`}
                      </div>
                    )}
                  </div>
                  <div className="text-right ml-4">
                    <div className="text-2xl font-bold text-gray-900">
                      {item.current_price > 0 ? `${item.current_price.toLocaleString()}원` : '데이터 없음'}
                    </div>
                    <div className={`text-sm font-semibold ${item.change_rate > 0 ? 'text-red-500' : item.change_rate < 0 ? 'text-blue-500' : 'text-gray-500'}`}>
                      {item.change_rate > 0 ? '+' : ''}{item.change_rate}%
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {item.score_label} ({item.score}점)
                    </div>
                  </div>
                  <div className="flex space-x-2 pt-2">
                    <button
                      onClick={() => window.open(`https://finance.naver.com/item/main.naver?code=${item.ticker}`, '_blank')}
                      className="flex-1 px-3 py-2 bg-gray-100 text-gray-700 rounded text-sm font-medium hover:bg-gray-200"
                    >
                      차트 & 기업정보
                    </button>
                    <button
                      onClick={() => openInvestmentModal(item)}
                      className="flex-1 px-3 py-2 bg-blue-500 text-white rounded text-sm font-medium hover:bg-blue-600"
                    >
                      투자등록
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>

      {/* 투자 등록 모달 */}
      {showInvestmentModal && selectedStock && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-bold text-gray-900 mb-4">투자 등록</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">종목명</label>
                <div className="text-sm text-gray-900">{selectedStock.name} ({selectedStock.ticker})</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">매수가</label>
                <input
                  type="number"
                  defaultValue={selectedStock.current_price || 0}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="매수가를 입력하세요"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">수량</label>
                <input
                  type="number"
                  defaultValue="1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="수량을 입력하세요"
                />
              </div>
            </div>
            <div className="flex space-x-3 mt-6">
              <button
                onClick={closeInvestmentModal}
                className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
              >
                취소
              </button>
              <button
                onClick={() => {
                  const entryPrice = document.querySelector('input[type="number"]:first-of-type').value;
                  const quantity = document.querySelector('input[type="number"]:last-of-type').value;
                  handleInvestmentRegistration(selectedStock, entryPrice, quantity);
                }}
                disabled={investmentLoading}
                className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                {investmentLoading ? '등록 중...' : '등록'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export async function getServerSideProps(context) {
  try {
    const config = getConfig();
    const base = config.backendUrl;
    
    const response = await fetch(`${base}/latest-scan`);
    
    if (response.ok) {
      const data = await response.json();
      return {
        props: {
          initialData: data.data?.items || []
        }
      };
    } else {
      return {
        props: {
          initialData: []
        }
      };
    }
  } catch (error) {
    return {
      props: {
        initialData: []
      }
    };
  }
}


