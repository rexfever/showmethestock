import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import getConfig from '../config';
import { addToPortfolio } from '../services/portfolioService';
import { validateInvestmentForm } from '../utils/portfolioUtils';
import { handleError } from '../utils/errorHandler';
import NoticePopup from '../components/NoticePopup';

export default function CustomerScanner({ initialData, initialScanFile }) {
  const router = useRouter();
  const { user, loading: authLoading, authChecked, isAuthenticated, logout } = useAuth();
  
  const [scanResults, setScanResults] = useState(initialData || []);
  const [scanFile, setScanFile] = useState(initialScanFile || '');
  const [scanDate, setScanDate] = useState('');
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('price');
  const [filterBy, setFilterBy] = useState('전체종목');
  const [mounted, setMounted] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [hasSSRData, setHasSSRData] = useState(initialData && initialData.length > 0);
  const [showGuide, setShowGuide] = useState(false);
  const [showUpcomingFeatures, setShowUpcomingFeatures] = useState(false);
  const [portfolioItems, setPortfolioItems] = useState(new Set());
  const [recurringStocks, setRecurringStocks] = useState([]);
  const [recurringLoading, setRecurringLoading] = useState(false);
  
  // 투자등록 모달 상태
  const [showInvestmentModal, setShowInvestmentModal] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [investmentForm, setInvestmentForm] = useState({
    entry_price: '',
    quantity: '',
    entry_date: ''
  });
  const [investmentLoading, setInvestmentLoading] = useState(false);

  // 인증 체크 (선택적 - 로그인하지 않아도 스캐너 사용 가능)
  // useEffect(() => {
  //   if (!authLoading && !isAuthenticated()) {
  //     // router.push('/login'); // 주석 처리 - 게스트 사용자도 접근 가능
  //   }
  // }, [authLoading, isAuthenticated, router]);


  // 포트폴리오 조회
  const fetchPortfolio = useCallback(async () => {
    if (!isAuthenticated()) return;
    
    try {
      const token = localStorage.getItem('token') || document.cookie
        .split('; ')
        .find(row => row.startsWith('auth_token='))
        ?.split('=')[1];
      
      if (!token) {
        console.log('토큰이 없어서 포트폴리오 조회를 건너뜁니다.');
        return;
      }
      
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
        const tickers = new Set(data.items.map(item => item.ticker));
        setPortfolioItems(tickers);
      } else if (response.status === 401) {
        console.log('인증 실패 - 포트폴리오 조회를 건너뜁니다.');
        // 401 오류 시 자동 로그아웃 처리하지 않고 조용히 건너뜀
      }
    } catch (error) {
      console.error('포트폴리오 조회 실패:', error);
    }
  }, [isAuthenticated]);

  // 포트폴리오에 종목 추가
  const addToPortfolio = async (ticker, name) => {
    if (!isAuthenticated()) {
      alert('관심종목 기능을 사용하려면 로그인이 필요합니다.');
      router.push('/login');
      return;
    }
    alert('준비중입니다.');
    return;
  };

  // 포트폴리오에서 종목 제거
  const removeFromPortfolio = async (ticker) => {
    alert('준비중입니다.');
    return;
  };

  // 투자등록 모달 열기
  const openInvestmentModal = (stock) => {
    if (!isAuthenticated()) {
      alert('투자등록을 하려면 로그인이 필요합니다.');
      router.push('/login');
      return;
    }
    
    setSelectedStock(stock);
    setInvestmentForm({
      entry_price: stock.current_price?.toString() || stock.details?.close?.toString() || '',
      quantity: '',
      entry_date: new Date().toISOString().split('T')[0] // 오늘 날짜
    });
    setShowInvestmentModal(true);
  };

  // 투자등록 모달 닫기
  const closeInvestmentModal = () => {
    setShowInvestmentModal(false);
    setSelectedStock(null);
    setInvestmentForm({
      entry_price: '',
      quantity: '',
      entry_date: ''
    });
  };

  // 투자등록 실행
  const handleInvestmentRegistration = async () => {
    if (!selectedStock) return;
    
    // 폼 데이터 검증
    const validation = validateInvestmentForm(investmentForm);
    if (!validation.isValid) {
      alert(validation.errors.join('\n'));
      return;
    }

    setInvestmentLoading(true);
    try {
      await addToPortfolio({
        ticker: selectedStock.ticker,
        name: selectedStock.name,
        ...investmentForm
      });

      alert(`${selectedStock.name}이(가) 투자종목에 등록되었습니다.`);
      closeInvestmentModal();
      // 포트폴리오 목록 새로고침
      fetchPortfolio();
    } catch (error) {
      handleError(error, '투자등록', alert);
    } finally {
      setInvestmentLoading(false);
    }
  };

  // 재등장 종목 조회
  const fetchRecurringStocks = useCallback(async () => {
    setRecurringLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/recurring-stocks?days=7&min_appearances=2`);
      const data = await response.json();
      
      if (data.ok && data.data && data.data.recurring_stocks) {
        const stocks = Object.values(data.data.recurring_stocks);
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

  // 사용 가능한 스캔 날짜 목록 가져오기
  const fetchAvailableDates = useCallback(async () => {
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/available-scan-dates`);
      const data = await response.json();
      
      if (data.ok && data.dates) {
        setAvailableDates(data.dates);
        // 기본값을 최신 날짜로 설정
        if (data.dates.length > 0 && !selectedDate) {
          setSelectedDate(data.dates[0]);
        }
      }
    } catch (error) {
      console.error('사용 가능한 날짜 조회 실패:', error);
    }
  }, [selectedDate]);

  // 특정 날짜의 스캔 결과 가져오기
  const fetchScanByDate = useCallback(async (date) => {
    if (!date) return;
    
    setLoading(true);
    setError(null);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/scan-by-date/${date}`);
      const data = await response.json();
      
      if (data.ok && data.data) {
        const items = data.data.items || data.data.rank || [];
        setScanResults(items);
        setScanFile(data.file || '');
        setScanDate(data.data.scan_date || '');
        setError(null);
      } else {
        const errorMsg = data.error || '스캔 결과 조회 실패';
        setError(errorMsg);
        setScanResults([]);
      }
    } catch (error) {
      console.error('스캔 결과 조회 실패:', error);
      setError('스캔 결과 조회 중 오류가 발생했습니다.');
      setScanResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 최신 스캔 결과 가져오기
  const fetchScanResults = useCallback(async () => {
    // 모바일에서 네트워크 상태 확인
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      setError('네트워크 연결을 확인해주세요.');
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      console.log('API 호출 URL:', `${base}/latest-scan`);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10초 타임아웃
      
      const response = await fetch(`${base}/latest-scan`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        mode: 'cors',
        cache: 'no-cache',
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('최신 스캔 결과:', data);
      console.log('data.file 값:', data.file);
      console.log('data.ok 값:', data.ok);
      console.log('data.data 값:', data.data);
      
      if (data.ok && data.data) {
        // items 또는 rank 필드 처리
        const items = data.data.items || data.data.rank || [];
        console.log('설정할 scanFile 값:', data.file);
        setScanResults(items);
        setScanFile(data.file || '');
        setScanDate(data.data.scan_date || '');
        setError(null);
      } else {
        const errorMsg = data.error || '스캔 결과 조회 실패';
        console.error('스캔 결과 조회 실패:', errorMsg);
        setError(errorMsg);
        setScanResults([]);
      }
    } catch (error) {
      console.error('스캔 결과 조회 실패:', error);
      if (error.name === 'AbortError') {
        setError('요청 시간이 초과되었습니다. 다시 시도해주세요.');
      } else if (error.message.includes('Failed to fetch')) {
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
    
    // 사용 가능한 날짜 목록 가져오기
    fetchAvailableDates();
    
    // 포트폴리오 조회
    fetchPortfolio();
    
    // 재등장 종목 조회
    fetchRecurringStocks();
    
    // SSR 데이터가 있으면 클라이언트 API 호출 완전 비활성화
    if (hasSSRData) {
      console.log('SSR 데이터 사용, 클라이언트 API 호출 생략');
      console.log('SSR scanFile:', initialScanFile);
      setScanResults(initialData);
      setScanFile(initialScanFile || '');
      setError(null);
      setLoading(false);
      return;
    }
    
    // 초기 데이터가 없으면 API 호출
    if (!hasSSRData) {
      fetchScanResults();
    }
    
    // 5분마다 자동 새로고침 (SSR 데이터가 있을 때는 비활성화)
    const interval = setInterval(() => {
      if (!hasSSRData) {
        fetchScanResults();
      }
    }, 5 * 60 * 1000);
    
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [hasSSRData, initialData]);

  // 필터링 (시장별 필터 제거)
  const filteredResults = scanResults.filter(item => {
    if (!item) return false;
    
    
    return true;
  });

  // 정렬
  const sortedResults = [...filteredResults].sort((a, b) => {
    if (sortBy === 'price') return (b.details?.close || 0) - (a.details?.close || 0);
    if (sortBy === 'change') return (b.change_rate || 0) - (a.change_rate || 0);
    return 0;
  });


  // 수익률 색상
  const getReturnColor = (returnRate) => {
    if (returnRate > 0) return 'text-red-500';
    if (returnRate < 0) return 'text-blue-500';
    return 'text-gray-500';
  };




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

        {/* 상단 바 */}
        <div className="bg-white shadow-sm">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center">
              <button 
                onClick={() => router.push('/')}
                className="text-lg font-semibold text-gray-800 hover:text-blue-600 transition-colors"
              >
                스톡인사이트
              </button>
            </div>
            <div className="flex items-center space-x-3">
              {!authLoading && authChecked && user ? (
                <span className="text-sm text-gray-600">
                  {user.name}님 ({user.provider})
                </span>
              ) : !authLoading && authChecked ? (
                <span className="text-sm text-gray-500">게스트 사용자</span>
              ) : (
                <span className="text-sm text-gray-400">로딩 중...</span>
              )}
              <button 
                onClick={() => router.push('/subscription')}
                className="px-3 py-1 bg-gradient-to-r from-yellow-400 to-yellow-500 text-gray-800 text-xs font-semibold rounded-full shadow-sm hover:shadow-md transition-all duration-200"
              >
                👑 프리미어
              </button>
            </div>
          </div>
        </div>

        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">시장의 주도주 정보</h2>
              <p className="text-sm opacity-90">AI가 찾아낸 주도주를 지금 확인하세요!</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                <span className="text-3xl">💰</span>
              </div>
            </div>
          </div>
        </div>


        {/* 투자 활용법 가이드 */}
        <div className="bg-white border-b">
          <button
            onClick={() => setShowGuide(!showGuide)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center space-x-2">
              <span className="text-lg">📊</span>
              <span className="font-medium text-gray-800">투자 활용법</span>
            </div>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform ${showGuide ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {showGuide && (
            <div className="px-4 pb-4 border-t bg-gray-50">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-xl">🔍</span>
                    <h3 className="font-semibold text-gray-800">선별 기준</h3>
                  </div>
                  <p className="text-sm text-gray-600">상승 신호, 과매도 탈출, 거래량 급증 등</p>
                  <p className="text-xs text-gray-500 mt-1">AI가 여러 조건을 종합해서 선별</p>
                  <p className="text-xs text-blue-600 mt-1 font-medium">※ 여러 조건 만족 = 강력한 신호 (우선 검토)</p>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-xl">📈</span>
                    <h3 className="font-semibold text-gray-800">투자 방법</h3>
                  </div>
                  <p className="text-sm text-gray-600">3~10일 정도 보유 단기 투자, 3~5% 수익 실현</p>
                  <p className="text-sm text-gray-600 mt-1">-3~5% 손실 시 즉시 매도(손절)</p>
                  <p className="text-xs text-red-500 mt-2 font-medium">※ 실제 매매는 증권사에서 진행하세요</p>
                  <p className="text-xs text-gray-500 mt-1">※ 투자는 개인의 책임이며, 투자 결정은 신중히 하시기 바랍니다.</p>
                </div>
              </div>
              
            </div>
          )}
        </div>

        {/* 준비중인 기능 안내 */}
        <div className="bg-white border-b">
          <button
            onClick={() => setShowUpcomingFeatures(!showUpcomingFeatures)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center space-x-2">
              <span className="text-lg">🚧</span>
              <span className="font-medium text-gray-800">준비중인 기능</span>
            </div>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform ${showUpcomingFeatures ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {showUpcomingFeatures && (
            <div className="px-4 pb-4 border-t bg-gray-50">
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
          )}
        </div>

        {/* 필터 및 정렬 */}
        <div className="bg-white p-4 border-b">
          <div className="flex space-x-3">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="flex-1 p-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="price">현재가순</option>
              <option value="change">변동률순</option>
            </select>
            <select
              value={filterBy}
              onChange={(e) => setFilterBy(e.target.value)}
              className="flex-1 p-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="전체종목">전체종목</option>
              <option value="관심종목">관심종목</option>
              <option value="보유종목">보유종목</option>
            </select>
          </div>
          <div className="mt-3">
          </div>
        </div>

        {/* 통합된 스캔 정보 */}
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 mx-4 mb-4">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-3">
              <div className="text-blue-800">
                <span className="font-medium">📅 추천 날짜:</span>
              </div>
              <select 
                value={selectedDate} 
                onChange={(e) => {
                  setSelectedDate(e.target.value);
                  fetchScanByDate(e.target.value);
                }}
                className="px-2 py-1 border border-blue-300 rounded text-sm bg-white"
              >
                {availableDates.map(date => (
                  <option key={date} value={date}>
                    {date.slice(0,4)}-{date.slice(4,6)}-{date.slice(6,8)}
                  </option>
                ))}
              </select>
            </div>
            <div className="text-blue-600">
              <span className="font-medium">매칭종목:</span> {scanResults.length}개
            </div>
          </div>
          
          {/* 수익률 정보 설명 (과거 날짜에서만 표시) */}
          {selectedDate && selectedDate !== new Date().toISOString().slice(0, 10).replace(/-/g, '') && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="text-xs text-gray-600">
                <div className="font-medium mb-1 text-gray-800">💡 수익률 정보</div>
                <div className="text-xs leading-relaxed">
                  추천한 날짜의 종가로 매수하여 현재까지 보유했을 때의 수익률입니다.
                </div>
              </div>
            </div>
          )}
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
                      {item.recurrence?.appeared_before && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          🔄 {item.recurrence.appear_count}회 등장
                        </span>
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
                    <div className={`text-sm font-semibold ${getReturnColor(item.change_rate)}`}>
                      {item.change_rate !== 0 ? `${item.change_rate > 0 ? '+' : ''}${item.change_rate}%` : ''}
                    </div>
                  </div>
                </div>


                {/* 수익률 정보 (과거 스캔 결과인 경우) */}
                {item.returns && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-2 mb-3">
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-xs text-gray-700 font-medium">📈 수익률</div>
                      <div className="text-xs text-gray-500">
                        {item.returns.days_elapsed ? `${item.returns.days_elapsed}일 경과` : ''}
                      </div>
                    </div>
                    <div className="flex justify-between text-sm">
                      <div className="text-center">
                        <div className="text-xs text-gray-500">현재</div>
                        <div className={`font-semibold ${item.returns.current_return > 0 ? 'text-red-500' : item.returns.current_return < 0 ? 'text-blue-500' : 'text-gray-500'}`}>
                          {item.returns.current_return > 0 ? '+' : ''}{item.returns.current_return}%
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-gray-500">최고</div>
                        <div className="font-semibold text-red-500">
                          +{item.returns.max_return}%
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-gray-500">최저</div>
                        <div className="font-semibold text-blue-500">
                          {item.returns.min_return}%
                        </div>
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
                    className="px-3 py-1 bg-blue-500 text-white rounded text-xs font-medium hover:bg-blue-600"
                    onClick={() => openInvestmentModal(item)}
                  >
                    투자등록
                  </button>
                </div>
              </div>
            ))
              )}
            </div>
          )}
        </div>

        {/* 재등장 종목 섹션 */}
        {recurringStocks.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <div className="flex items-center mb-3">
              <div className="w-8 h-8 bg-yellow-500 rounded-full flex items-center justify-center mr-3">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-yellow-800">🔄 재등장 종목</h3>
            </div>
            <p className="text-sm text-yellow-700 mb-4">
              최근 7일간 여러 번 추천된 종목들입니다. 지속적인 관심이 필요한 종목일 수 있습니다.
            </p>
            
            {recurringLoading ? (
              <div className="text-center py-4">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-yellow-600 mx-auto"></div>
                <p className="text-sm text-yellow-600 mt-2">재등장 종목을 불러오는 중...</p>
              </div>
            ) : (
              <div className="grid gap-3">
                {recurringStocks.map((stock, index) => (
                  <div key={index} className="bg-white rounded-lg p-3 border border-yellow-200">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center">
                          <h4 className="font-semibold text-gray-900">{stock.name}</h4>
                          <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                            {stock.appear_count}회 등장
                          </span>
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          최근 등장일: {stock.latest_date} | 최신 점수: {stock.latest_score}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold text-yellow-700">
                          {stock.latest_score}점
                        </div>
                        <div className="text-xs text-gray-500">
                          {stock.appearances.length}일간 추천
                        </div>
                      </div>
                    </div>
                    {/* 재등장 종목 액션 버튼 */}
                    <div className="flex justify-between items-center mt-2 pt-2 border-t border-yellow-100">
                      <div className="flex space-x-2">
                        <button 
                          className="text-xs text-blue-500 hover:text-blue-700"
                          onClick={() => {
                            const naverInfoUrl = `https://finance.naver.com/item/main.naver?code=${stock.code || stock.ticker}`;
                            window.open(naverInfoUrl, '_blank');
                          }}
                        >
                          차트 & 기업정보
                        </button>
                      </div>
                      <button 
                        className="px-2 py-1 bg-blue-500 text-white rounded text-xs font-medium hover:bg-blue-600"
                        onClick={() => openInvestmentModal({
                          ticker: stock.code || stock.ticker,
                          name: stock.name,
                          current_price: stock.latest_score
                        })}
                      >
                        투자등록
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

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
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={async () => {
                if (user) {
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

      {/* 투자등록 모달 */}
      {showInvestmentModal && selectedStock && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800">투자등록</h3>
              <button 
                onClick={closeInvestmentModal}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="mb-4">
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="font-medium text-gray-800">{selectedStock.name}</div>
                <div className="text-sm text-gray-600">({selectedStock.ticker})</div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  매수가격 (원)
                </label>
                <input
                  type="number"
                  value={investmentForm.entry_price}
                  onChange={(e) => setInvestmentForm({...investmentForm, entry_price: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="매수가격을 입력하세요"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  수량 (주)
                </label>
                <input
                  type="number"
                  value={investmentForm.quantity}
                  onChange={(e) => setInvestmentForm({...investmentForm, quantity: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="수량을 입력하세요"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  매수일
                </label>
                <input
                  type="date"
                  value={investmentForm.entry_date}
                  onChange={(e) => setInvestmentForm({...investmentForm, entry_date: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex space-x-3 mt-6">
              <button
                onClick={closeInvestmentModal}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                취소
              </button>
              <button
                onClick={handleInvestmentRegistration}
                disabled={investmentLoading}
                className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {investmentLoading ? '등록 중...' : '투자등록'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 공지사항 팝업 */}
      <NoticePopup />
    </>
  );
}

export async function getServerSideProps() {
  try {
    // 서버에서 백엔드 API 호출
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
      return {
        props: {
          initialData: items,
          initialScanFile: data.file || ''
        }
      };
    }
  } catch (error) {
    console.error('서버에서 스캔 결과 조회 실패:', error);
  }
  
  return {
    props: {
      initialData: []
    }
  };
}
