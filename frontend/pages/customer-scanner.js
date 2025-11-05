// CACHE BUST: 2025-10-26-20-25-v3
import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import getConfig from '../config';
import Header from '../components/Header';
import BottomNavigation from '../components/BottomNavigation';
import PopupNotice from '../components/PopupNotice';
import MarketGuide from '../components/MarketGuide';

export default function CustomerScanner({ initialData, initialScanFile, initialScanDate }) {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  
  const [scanResults, setScanResults] = useState(initialData || []);
  const [scanFile, setScanFile] = useState(initialScanFile || '');
  const [scanDate, setScanDate] = useState(initialScanDate || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mounted, setMounted] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [hasSSRData, setHasSSRData] = useState(initialData && initialData.length > 0);
  const [recurringStocks, setRecurringStocks] = useState({});
  const [showInvestmentModal, setShowInvestmentModal] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [investmentLoading, setInvestmentLoading] = useState(false);
  const [marketGuide, setMarketGuide] = useState(null);
  const [maintenanceStatus, setMaintenanceStatus] = useState({
    is_enabled: false,
    end_date: null,
    message: '서비스 점검 중입니다.'
  });

  // 메인트넌스 상태 확인
  useEffect(() => {
    const checkMaintenanceStatus = async () => {
      try {
        const config = getConfig();
        const base = config.backendUrl;
        const response = await fetch(`${base}/maintenance/status`);
        const data = await response.json();
        
        if (data.is_enabled) {
          setMaintenanceStatus(data);
        }
      } catch (error) {
        console.error('메인트넌스 상태 확인 실패:', error);
      }
    };

    checkMaintenanceStatus();
  }, []);

  const openInvestmentModal = (stock) => {
    setSelectedStock(stock);
    setShowInvestmentModal(true);
  };

  const closeInvestmentModal = () => {
    setSelectedStock(null);
    setShowInvestmentModal(false);
  };
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

  const loadTestScenario = useCallback(async (scenario) => {
    setLoading(true);
    setError(null);
    
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/test-scan/${scenario}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data) {
        const items = data.items || [];
        // market_guide를 첫 번째 아이템에 추가
        if (items.length > 0 && data.market_guide) {
          items[0].market_guide = data.market_guide;
        }
        setScanResults(items);
        setScanFile(`test-${scenario}`);
        setScanDate(data.as_of || '');
        setError(null);
      }
    } catch (error) {
      setError(`테스트 시나리오 로드 실패: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchScanResults = useCallback(async () => {
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
      
      console.log('API 응답 데이터:', data);
      console.log('items 배열:', data.data?.items);
      console.log('items 개수:', data.data?.items?.length);
      
      if (data.ok && data.data) {
        // items 또는 rank 필드 처리
        const items = data.data.items || data.data.rank || [];
        const scanDate = data.data.as_of || data.data.scan_date || '';
        
        // market_guide를 별도 state로 관리
        if (data.data.market_guide) {
          setMarketGuide(data.data.market_guide);
        }
        
        // market_guide를 첫 번째 아이템에 추가 (호환성)
        if (items.length > 0 && data.data.market_guide) {
          items[0].market_guide = data.data.market_guide;
        }
        
        console.log('API 응답 전체:', data);
        console.log('설정할 items:', items);
        console.log('설정할 scanDate:', scanDate);
        console.log('market_guide:', data.data.market_guide);
        setScanResults(items);
        setScanFile(data.file || '');
        setScanDate(scanDate);
        setError(null);
      } else {
        const errorMsg = data.error || '스캔 결과 조회 실패';
        setError(errorMsg);
        setScanResults([]);
        setMarketGuide(null);
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
    
    // 재등장 종목 조회
    fetchRecurringStocks();
  }, [fetchRecurringStocks]);

  useEffect(() => {
    if (initialData && initialData.length > 0) {
      setScanResults(initialData);
      setScanFile(initialScanFile || '');
      setScanDate(initialScanDate || '');
      // SSR 데이터에서 market_guide 추출
      if (initialData[0] && initialData[0].market_guide) {
        setMarketGuide(initialData[0].market_guide);
      }
      setHasSSRData(true);
      setError(null);
      setLoading(false);
    }
  }, [initialData, initialScanFile, initialScanDate]);
  
  useEffect(() => {
    if (!initialData && scanResults.length === 0 && !loading && !error) {
      setLoading(true);
      fetchScanResults();
    }
  }, [scanResults.length, loading, error, fetchScanResults, initialData]);

  const filteredResults = scanResults.filter(item => item !== null && item !== undefined);
  const sortedResults = filteredResults;

  if (maintenanceStatus.is_enabled) {
    return (
      <>
        <Head>
          <title>스톡인사이트 - 서비스 점검 중</title>
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <meta name="format-detection" content="telephone=no" />
          <meta name="mobile-web-app-capable" content="yes" />
        </Head>

        <div className="min-h-screen bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center">
          <div className="bg-white rounded-2xl shadow-2xl p-8 mx-4 max-w-md w-full text-center">
            {/* 공사 아이콘 */}
            <div className="text-6xl mb-6">🚧</div>
            
            {/* 제목 */}
            <h1 className="text-2xl font-bold text-gray-800 mb-4">
              서비스 점검 중
            </h1>
            
            {/* 메시지 */}
            <div className="text-gray-600 mb-6 space-y-2">
              <p className="text-lg font-medium">
                {maintenanceStatus.message}
              </p>
              {maintenanceStatus.end_date && (
                <p className="text-lg font-bold text-red-600">
                  {maintenanceStatus.end_date}까지
                </p>
              )}
              <p className="text-sm text-gray-500 mt-4">
                이용에 불편을 드려 죄송합니다.
              </p>
            </div>
            
            {/* 수동 이동 버튼 */}
            <button
              onClick={() => router.push('/')}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 px-6 rounded-lg transition-colors duration-200"
            >
              메인 페이지로 이동
            </button>
          </div>
        </div>
      </>
    );
  }


  return (
    <>
      <Head>
        <title>스톡인사이트 - 주식 스캐너</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        <PopupNotice />
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
                  {(() => {
                    console.log('날짜 렌더링 - mounted:', mounted, 'scanDate:', scanDate);
                    
                    if (!mounted) {
                      return '로딩 중...';
                    }
                    
                    if (!scanDate || scanDate === '') {
                      return '날짜 정보 없음';
                    }
                    
                    try {
                      let date;
                      if (scanDate.length === 8 && /^\d{8}$/.test(scanDate)) {
                        // YYYYMMDD 형식 (기본)
                        const year = scanDate.substring(0, 4);
                        const month = parseInt(scanDate.substring(4, 6));
                        const day = parseInt(scanDate.substring(6, 8));
                        date = new Date(year, month - 1, day);
                      } else if (scanDate.includes('-')) {
                        // YYYY-MM-DD 형식 (호환성)
                        date = new Date(scanDate);
                      } else {
                        return `잘못된 날짜 형식: ${scanDate}`;
                      }
                      
                      if (isNaN(date.getTime())) {
                        return `유효하지 않은 날짜: ${scanDate}`;
                      }
                      
                      return date.toLocaleDateString('ko-KR', { 
                        year: 'numeric', 
                        month: 'long', 
                        day: 'numeric',
                        weekday: 'short'
                      });
                    } catch (error) {
                      console.error('날짜 파싱 오류:', error, 'scanDate:', scanDate);
                      return `날짜 파싱 오류: ${scanDate}`;
                    }
                  })()}
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span className="text-gray-600 font-medium">매칭종목</span>
                  <span className="text-blue-600 font-bold text-lg">
                    {scanResults.length > 0 && scanResults[0].ticker === 'NORESULT' ? 0 : scanResults.length}
                  </span>
                  <span className="text-gray-500 text-sm">개</span>
                </div>
              </div>
              
              {/* 오른쪽: 버튼 */}
              <button
                onClick={() => {
                  if (!isAuthenticated()) {
                    router.push('/login');
                    return;
                  }
                  router.push('/performance-report');
                }}
                className="relative bg-gradient-to-br from-yellow-500 via-yellow-600 to-yellow-700 hover:from-yellow-600 hover:via-yellow-700 hover:to-yellow-800 text-white px-5 py-2 rounded-lg font-medium transition-all duration-300 shadow-lg hover:shadow-xl transform hover:scale-105 hover:-translate-y-1 active:scale-95 overflow-hidden group"
              >
                {/* 배경 애니메이션 효과 */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-20 group-hover:translate-x-full transition-all duration-700"></div>
                
                <div className="relative flex flex-col items-center justify-center space-y-1">
                  <div className="w-4 h-4 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
                    <span className="text-xs">📋</span>
                  </div>
                  <div className="text-xs font-bold tracking-wide text-center leading-tight">
                    추천종목<br />성과보고서
                  </div>
                </div>
                
                {/* 하단 글로우 효과 */}
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-60 transition-opacity duration-300"></div>
              </button>
            </div>
          </div>
        </div>

        {/* 테스트 시나리오 선택 (관리자만) */}
        {user && user.is_admin && (
          <div className="mx-4 mb-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h3 className="text-sm font-bold text-yellow-800 mb-2">🧪 테스트 시나리오</h3>
            <div className="flex flex-wrap gap-2">
              {['bull', 'bear', 'neutral', 'noresult'].map(scenario => (
                <button
                  key={scenario}
                  onClick={() => loadTestScenario(scenario)}
                  className="px-3 py-1 bg-yellow-200 hover:bg-yellow-300 text-yellow-800 rounded text-xs font-medium"
                >
                  {scenario === 'bull' ? '강세장' :
                   scenario === 'bear' ? '약세장' :
                   scenario === 'neutral' ? '중립장' : '추천없음'}
                </button>
              ))}
              <button
                onClick={() => fetchScanResults()}
                className="px-3 py-1 bg-blue-200 hover:bg-blue-300 text-blue-800 rounded text-xs font-medium"
              >
                실제 데이터
              </button>
            </div>
          </div>
        )}

        {/* 스캔 결과 목록 */}
        <div className="p-4 space-y-3">
          {/* Market Guide 섹션 - 항상 표시 */}
          {marketGuide && (
            <MarketGuide marketGuide={marketGuide} />
          )}
          {/* NORESULT인 경우 가이드 표시 */}
          {!marketGuide && scanResults.length > 0 && scanResults[0].ticker === 'NORESULT' && (
            <MarketGuide marketGuide={{
              market_condition: '급락',
              guide_message: '😔 장이 좋지 않아 추천 종목이 없습니다. 투자에도 휴식이 필요합니다.',
              investment_strategy: '전면 관망, 투자 휴식',
              risk_level: '매우 높음',
              timing_advice: '시장 회복 신호까지 대기'
            }} />
          )}
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-gray-500 mt-2">스캔 결과를 불러오는 중...</p>
            </div>
          ) : error && scanResults.length === 0 ? (
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
              ) : sortedResults.length === 1 && sortedResults[0].ticker === 'NORESULT' ? (
                <div className="bg-white rounded-lg shadow-sm border p-6 text-center">
                  <div className="text-6xl mb-4">😔</div>
                  <p className="text-lg text-gray-700 mb-2">
                    장이 좋지 않아 추천된 종목이 없어요.
                  </p>
                  <p className="text-md text-gray-600">
                    ☕ 투자에도 휴식이 필요합니다.
                  </p>
                </div>
              ) : (
                sortedResults.filter(item => item.ticker !== 'NORESULT').map((item) => (
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
    
    console.log('SSR: Fetching from', `${base}/latest-scan`);
    
    // Next.js 서버 측 fetch는 timeout 옵션을 지원하지 않으므로 제거
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10초 타임아웃
    
    const response = await fetch(`${base}/latest-scan`, {
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      console.error('SSR: HTTP error! status:', response.status);
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('SSR: Response data:', data.ok, data.data ? 'has data' : 'no data');
    
    if (data.ok && data.data) {
      // items 또는 rank 필드 처리
      const items = data.data.items || data.data.rank || [];
      const scanDate = data.data.as_of || data.data.scan_date || '';
      console.log('SSR: Returning', items.length, 'items');
      console.log('SSR: scanDate:', scanDate);
      console.log('SSR: data.data.as_of:', data.data.as_of);
      console.log('SSR: data.data.scan_date:', data.data.scan_date);
      return {
        props: {
          initialData: items,
          initialScanFile: data.file || '',
          initialScanDate: scanDate
        }
      };
    } else {
      console.log('SSR: Data not ok or no data');
    }
  } catch (error) {
    console.error('SSR: Error fetching scan data:', error.message);
    // 에러 발생 시에도 빈 데이터로 반환하여 페이지는 정상 렌더링되도록 함
  }
  
  console.log('SSR: Returning empty data');
  return {
    props: {
      initialData: [],
      initialScanFile: '',
      initialScanDate: ''
    }
  };
}
