import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import getConfig from '../config';
import Header from '../components/Header';
import BottomNavigation from '../components/BottomNavigation';

export default function CustomerScanner({ initialData, initialScanFile, initialScanDate }) {
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated, logout } = useAuth();
  
  const [scanResults, setScanResults] = useState(initialData || []);
  const [scanFile, setScanFile] = useState(initialScanFile || '');
  const [scanDate, setScanDate] = useState(initialScanDate || '');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mounted, setMounted] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [hasSSRData, setHasSSRData] = useState(initialData && initialData.length > 0);
  // 포트폴리오 관련 상태 제거 (스캐너에서는 불필요)
  const [recurringStocks, setRecurringStocks] = useState({});

  // 투자 모달 상태
  const [showInvestmentModal, setShowInvestmentModal] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [investmentLoading, setInvestmentLoading] = useState(false);

  // 인증 체크 (선택적 - 로그인하지 않아도 스캐너 사용 가능)
  // useEffect(() => {
  //   if (!authLoading && !isAuthenticated()) {
  //     // router.push('/login'); // 주석 처리 - 게스트 사용자도 접근 가능
  //   }
  // }, [authLoading, isAuthenticated, router]);


  // 포트폴리오 조회 함수 제거 (스캐너에서는 불필요)

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
  const handleInvestmentRegistration = async (stock, entryPrice, quantity, entryDate) => {
    if (!isAuthenticated() || !user) {
      alert('로그인이 필요합니다.');
      return;
    }

    setInvestmentLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/portfolio/add', {
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
          entry_date: entryDate
        })
      });

      if (response.ok) {
        alert('투자 등록이 완료되었습니다.');
        closeInvestmentModal();
      } else {
        const error = await response.json();
        alert(`등록 실패: ${error.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      alert(`등록 실패: ${error.message}`);
    } finally {
      setInvestmentLoading(false);
    }
  };

  // 재등장 종목 조회 (종목명 표시용)
  const fetchRecurringStocks = useCallback(async () => {
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/recurring-stocks?days=14&min_appearances=2`);
      const data = await response.json();
      
      if (data.ok && data.data && data.data.recurring_stocks) {
        // 재등장 종목 데이터를 객체로 저장
        setRecurringStocks(data.data.recurring_stocks);
      } else {
        setRecurringStocks({});
      }
    } catch (error) {
      setRecurringStocks({});
    }
  }, []);

  // 최신 스캔 결과 가져오기
  // 클라이언트에서 추가 데이터 로드 (필요시에만)
  const fetchScanResults = useCallback(async () => {
    // SSR로 이미 데이터가 로드되었으므로 클라이언트에서는 추가 로드 불필요
    // 필요시에만 새로고침 기능으로 사용
    setLoading(true);
    setError(null);
    
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/latest-scan`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        mode: 'cors',
        cache: 'no-cache',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.ok && data.data) {
        // items 또는 rank 필드 처리
        const items = data.data.items || data.data.rank || [];
        setScanResults(items);
        setScanFile(data.file || '');
        setScanDate(data.data.as_of || data.data.scan_date || '');
        setError(null);
      } else {
        const errorMsg = data.error || '스캔 결과 조회 실패';
        setError(errorMsg);
        setScanResults([]);
      }
    } catch (error) {
      if (error.message.includes('Failed to fetch')) {
        setError('네트워크 연결을 확인해주세요.');
      } else {
        setError(`데이터 불러오는 중 오류가 발생했습니다: ${error.message}`);
      }
      setScanResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setMounted(true);
    
    // 모바일 감지
    if (typeof window !== 'undefined') {
      const userAgent = navigator.userAgent;
      const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
      setIsMobile(isMobileDevice);
    }
    
    // 스캐너에서는 포트폴리오 조회 생략 (성능 최적화)
    
    // 재등장 종목 조회
    fetchRecurringStocks();
    
    // SSR 데이터가 있으면 클라이언트 API 호출 완전 비활성화
    if (hasSSRData) {
      setScanResults(initialData);
      setScanFile(initialScanFile || '');
      setScanDate(initialScanDate || '');
      setError(null);
      setLoading(false);
      return;
    }
    
    // 초기 데이터가 없으면 에러 상태로 설정 (API 호출 제거)
    if (!hasSSRData) {
      setError('스캔 데이터가 없습니다.');
      setLoading(false);
    }
    
    // SSR 데이터가 있을 때는 자동 새로고침 비활성화 (성능 최적화)
    // 필요시에만 수동 새로고침 버튼으로 fetchScanResults() 호출
  }, [hasSSRData, initialData]);

  // 필터링 (시장별 필터 제거)
  const filteredResults = scanResults.filter(item => {
    if (!item) return false;
    
    
    return true;
  });

  // 정렬 없이 그대로 사용
  const sortedResults = filteredResults;






  // mounted 체크 제거 - SSR 데이터가 있으므로 바로 렌더링

  return (
    <>
      <Head>
        <title>스톡인사이트 - 주식 스캐너</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
      </Head>

      <div className="min-h-screen bg-gray-50">

        <Header title="스톡인사이트" />

        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">오늘의 추천 종목</h2>
              <p className="text-sm opacity-90">AI가 찾아낸 추천 종목을 지금 확인하세요!</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                <span className="text-3xl">💰</span>
              </div>
            </div>
          </div>
        </div>

        {/* 통합된 스캔 정보 */}
        <div className="bg-white mx-4 mb-4 rounded-lg shadow-sm border border-gray-100">
          <div className="p-4">
            <div className="flex items-center justify-between">
              {/* 왼쪽: 날짜와 매칭종목 */}
              <div className="flex flex-col space-y-1">
                <div className="text-lg font-semibold text-gray-800">
                  {mounted && scanDate ? (() => {
                    // YYYYMMDD 형식을 YYYY년 M월 D일 형식으로 변환
                    const year = scanDate.substring(0, 4);
                    const month = parseInt(scanDate.substring(4, 6));
                    const day = parseInt(scanDate.substring(6, 8));
                    const date = new Date(year, month - 1, day);
                    return date.toLocaleDateString('ko-KR', { 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric',
                      weekday: 'short'
                    });
                  })() : `로딩 중... (scanDate: ${scanDate}, mounted: ${mounted})`}
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span className="text-gray-600 font-medium">매칭종목</span>
                  <span className="text-blue-600 font-bold text-lg">{scanResults.length}</span>
                  <span className="text-gray-500 text-sm">개</span>
                </div>
              </div>
              
              {/* 오른쪽: 버튼 */}
              <button
                onClick={() => router.push('/performance-report')}
                className="relative bg-gradient-to-br from-red-500 via-rose-600 to-pink-700 hover:from-red-600 hover:via-rose-700 hover:to-pink-800 text-white px-8 py-3 rounded-2xl font-semibold transition-all duration-300 shadow-xl hover:shadow-2xl transform hover:scale-105 hover:-translate-y-1 active:scale-95 overflow-hidden group min-w-[180px]"
              >
                {/* 배경 애니메이션 효과 */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-20 group-hover:translate-x-full transition-all duration-700"></div>
                
                <div className="relative flex items-center justify-center space-x-2">
                  <div className="w-6 h-6 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
                    <span className="text-sm">📋</span>
                  </div>
                  <span className="text-sm font-bold tracking-wide whitespace-nowrap">추천 성과보고서</span>
                </div>
                
                {/* 하단 글로우 효과 */}
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-60 transition-opacity duration-300"></div>
              </button>
            </div>
          </div>
        </div>

        {/* 스캔 결과 목록 */}
        <div className="p-4 space-y-3">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-gray-500 mt-2">스캔 결과를 불러오는 중...</p>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <div className="text-red-500 text-lg mb-2">⚠️</div>
              <p className="text-red-600 font-medium">{error}</p>
              <button 
                onClick={() => {
                  setHasSSRData(false);
                  fetchScanResults();
                }}
                className="mt-3 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                다시 시도
              </button>
            </div>
          ) : (
            <div>
              {/* 스캔 결과가 없을 때 메시지 */}
              {sortedResults.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">선택한 날짜에 스캔 결과가 없습니다.</p>
                  <p className="text-sm text-gray-400 mt-2">
                    다른 날짜를 선택하거나 최신 스캔을 확인해보세요.
                  </p>
                </div>
              ) : (
                sortedResults.map((item) => (
              <div key={item.ticker} className="bg-white rounded-lg shadow-sm border p-4 space-y-3">
                {/* 종목명과 가격 */}
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-lg font-bold text-gray-900 truncate">
                        {item.name}
                      </h3>
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
                    {item.recurrence?.appeared_before && item.recurrence.days_since_last && (
                      <div className="text-xs text-green-600 mt-1">
                        마지막 등장: {item.recurrence.days_since_last}일 전
                      </div>
                    )}
                  </div>
                  <div className="text-right ml-4">
                    <div className="text-2xl font-bold text-gray-900">
                      {item.current_price > 0 ? `${item.current_price.toLocaleString()}원` : '데이터 없음'}
                    </div>
                    <div className={`text-sm font-semibold ${item.change_rate > 0 ? 'text-red-500' : item.change_rate < 0 ? 'text-blue-500' : 'text-gray-500'}`}>
                      {item.change_rate !== 0 ? `${item.change_rate > 0 ? '+' : ''}${item.change_rate}%` : '데이터 없음'}
                    </div>
                  </div>
                </div>


                {/* 재등장 정보 (재등장 종목인 경우) */}
                {recurringStocks[item.ticker] && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-2 mb-3">
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-xs text-yellow-700 font-medium">🔄 재등장 정보</div>
                      <div className="text-xs text-yellow-600">
                        최근 2주간
                      </div>
                    </div>
                    <div className="text-xs text-yellow-600">
                      <div className="mb-1">
                        <span className="font-medium">재등장 횟수:</span> {recurringStocks[item.ticker].appearances}회
                      </div>
                      <div>
                        <span className="font-medium">등장 날짜:</span> {recurringStocks[item.ticker].dates.slice(0, 3).map(date => 
                          `${date.slice(5,7)}/${date.slice(8,10)}`
                        ).join(', ')}
                        {recurringStocks[item.ticker].dates.length > 3 && '...'}
                      </div>
                    </div>
                  </div>
                )}


                {/* 액션 버튼 */}
                <div className="flex items-center justify-between pt-3 border-t">
                  <div className="flex space-x-4 text-sm">
                    <button 
                      className="text-blue-500 hover:text-blue-700"
                      onClick={() => {
                        const naverInfoUrl = `https://finance.naver.com/item/main.naver?code=${item.ticker}`;
                        window.open(naverInfoUrl, '_blank');
                      }}
                    >
                      차트 & 기업정보
                    </button>
                  </div>
                  <button 
                    className="px-3 py-1 bg-green-500 text-white rounded text-xs font-medium hover:bg-green-600"
                    onClick={() => openInvestmentModal(item)}
                  >
                    나의투자종목에 등록
                  </button>
                </div>
              </div>
            ))
              )}
            </div>
          )}
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
                    id="entryPrice"
                    defaultValue={selectedStock.current_price || 0}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="매수가를 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">수량</label>
                  <input
                    type="number"
                    id="quantity"
                    defaultValue="1"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="수량을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">매수일</label>
                  <input
                    type="date"
                    id="entryDate"
                    defaultValue={new Date().toISOString().split('T')[0]}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                    const entryPrice = document.getElementById('entryPrice').value;
                    const quantity = document.getElementById('quantity').value;
                    const entryDate = document.getElementById('entryDate').value;
                    
                    if (!entryPrice || !quantity || !entryDate) {
                      alert('모든 필드를 입력해주세요.');
                      return;
                    }
                    
                    handleInvestmentRegistration(selectedStock, entryPrice, quantity, entryDate);
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

        <BottomNavigation />
      </div>
    </>
  );
}

export async function getServerSideProps() {
  try {
    // 서버에서 백엔드 API 호출 (DB 직접 조회)
    const config = getConfig();
    const base = config.backendUrl;
    const response = await fetch(`${base}/latest-scan`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
      const data = await response.json();
      
      if (data.ok && data.data) {
        // items 또는 rank 필드 처리
        const items = data.data.items || data.data.rank || [];
        // 날짜 표시는 스캔 응답의 as_of(YYYY-MM-DD) 우선 사용하되, 표시용으로 YYYYMMDD로 변환
        const rawAsOf = data.data.as_of || '';
        const normalizedScanDate = (data.data.scan_date) || (rawAsOf ? rawAsOf.replace(/-/g, '') : '');
        return {
          props: {
            initialData: items,
            initialScanFile: data.file || '',
            initialScanDate: normalizedScanDate
          }
        };
      }
  } catch (error) {
  }
  
  return {
    props: {
      initialData: [],
      initialScanDate: ''
    }
  };
}
