// CACHE BUST: 2025-12-02-v1
// 미국 주식 스캐너 페이지
import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import getConfig from '../../config';
import Layout from '../layouts/Layout';
import StockCardV2 from '../components/StockCardV2';
import MarketGuide from '../../components/MarketGuide';
import MarketConditionCard from '../../components/MarketConditionCard';

export default function USStocksScanner({ initialData, initialScanDate, initialMarketCondition }) {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  
  const [scanResults, setScanResults] = useState(initialData || []);
  const [scanDate, setScanDate] = useState(initialScanDate || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mounted, setMounted] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [hasSSRData, setHasSSRData] = useState(initialData && initialData.length > 0);
  const [marketGuide, setMarketGuide] = useState(null);
  const [marketCondition, setMarketCondition] = useState(initialMarketCondition || null);
  const [universeType, setUniverseType] = useState('sp500'); // sp500, nasdaq100, combined
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

  // 모바일 감지
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // 마운트 확인
  useEffect(() => {
    setMounted(true);
  }, []);

  // 스캔 결과 가져오기
  const fetchScanResults = useCallback(async (universe = universeType) => {
    setLoading(true);
    setError(null);
    
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/scan/us-stocks?universe_type=${universe}&limit=100`, {
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
      
      console.log('미국 주식 스캔 API 응답 데이터:', data);
      console.log('items 배열:', data.items);
      console.log('items 개수:', data.items?.length);
      
      if (data && data.items) {
        const items = data.items || [];
        const scanDate = data.as_of || '';
        
        setScanResults(items);
        setScanDate(scanDate);
        setMarketGuide(data.market_guide || null);
        setMarketCondition(data.market_condition || null);
        setHasSSRData(false);
      } else {
        setScanResults([]);
        setScanDate('');
      }
    } catch (err) {
      console.error('스캔 결과 가져오기 실패:', err);
      setError(err.message || '스캔 결과를 가져오는 중 오류가 발생했습니다.');
      setScanResults([]);
    } finally {
      setLoading(false);
    }
  }, [universeType]);

  // 유니버스 타입 변경 시 재스캔
  useEffect(() => {
    if (mounted && !hasSSRData) {
      fetchScanResults(universeType);
    }
  }, [universeType, mounted, hasSSRData, fetchScanResults]);

  // 수동 새로고침
  const handleRefresh = () => {
    setHasSSRData(false);
    fetchScanResults(universeType);
  };

  // 차트 보기
  const handleViewChart = (ticker) => {
    // 미국 주식 차트 링크 (예: Yahoo Finance)
    window.open(`https://finance.yahoo.com/quote/${ticker}`, '_blank');
  };

  // 날짜 포맷팅
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch (e) {
      return dateStr;
    }
  };

  // 유니버스 타입 표시명
  const getUniverseTypeName = (type) => {
    const names = {
      'sp500': 'S&P 500',
      'nasdaq100': 'NASDAQ 100',
      'combined': 'S&P 500 + NASDAQ 100'
    };
    return names[type] || type;
  };

  return (
    <>
      <Head>
        <title>미국 주식 스캐너 | 스톡인사이트</title>
        <meta name="description" content="AI 기반 미국 주식 스캐너 - S&P 500, NASDAQ 100 종목 분석" />
      </Head>

      <Layout>
        {/* 메인트넌스 배너 */}
        {maintenanceStatus.is_enabled && (
          <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-500" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium">{maintenanceStatus.message}</p>
                {maintenanceStatus.end_date && (
                  <p className="text-xs mt-1">점검 종료 예정: {formatDate(maintenanceStatus.end_date)}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 헤더 */}
        <div className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">🇺🇸 미국 주식 스캐너</h1>
              <p className="text-gray-600">S&P 500, NASDAQ 100 종목 실시간 분석</p>
            </div>
            <div className="mt-4 sm:mt-0 flex items-center gap-2">
              <button
                onClick={handleRefresh}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>스캔 중...</span>
                  </>
                ) : (
                  <>
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>새로고침</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* 유니버스 타입 선택 */}
          <div className="flex flex-wrap gap-2 mb-4">
            <button
              onClick={() => setUniverseType('sp500')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                universeType === 'sp500'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              S&P 500
            </button>
            <button
              onClick={() => setUniverseType('nasdaq100')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                universeType === 'nasdaq100'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              NASDAQ 100
            </button>
            <button
              onClick={() => setUniverseType('combined')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                universeType === 'combined'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              통합 (S&P 500 + NASDAQ 100)
            </button>
          </div>

          {/* 스캔 날짜 */}
          {scanDate && (
            <div className="text-sm text-gray-500 mb-4">
              스캔 날짜: {formatDate(scanDate)} ({getUniverseTypeName(universeType)})
            </div>
          )}
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4">
            <p className="font-medium">오류 발생</p>
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* 시장 가이드 */}
        {marketGuide && (
          <div className="mb-6">
            <MarketGuide guide={marketGuide} />
          </div>
        )}

        {/* 시장 조건 카드 */}
        {marketCondition && (
          <div className="mb-6">
            <MarketConditionCard condition={marketCondition} />
          </div>
        )}

        {/* 스캔 결과 */}
        {loading && !hasSSRData ? (
          <div className="text-center py-12">
            <svg className="animate-spin h-12 w-12 text-blue-600 mx-auto mb-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-gray-600">미국 주식을 스캔하는 중...</p>
          </div>
        ) : scanResults.length > 0 ? (
          <div className="space-y-4">
            <div className="text-sm text-gray-600 mb-4">
              총 {scanResults.length}개 종목 발견
            </div>
            {scanResults.map((item, index) => (
              <StockCardV2
                key={`${item.ticker}-${index}`}
                item={item}
                onViewChart={handleViewChart}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-gray-50 rounded-lg">
            <svg className="h-16 w-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-gray-600 text-lg mb-2">스캔 결과가 없습니다</p>
            <p className="text-gray-500 text-sm">새로고침 버튼을 눌러 다시 스캔해보세요.</p>
          </div>
        )}

      </Layout>
    </>
  );
}

export async function getServerSideProps() {
  try {
    // 서버에서 백엔드 API 호출
    const config = getConfig();
    const base = config.backendUrl;
    
    console.log('SSR: Fetching US stocks from', `${base}/scan/us-stocks`);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15초 타임아웃 (미국 주식 스캔은 시간이 더 걸릴 수 있음)
    
    const response = await fetch(`${base}/scan/us-stocks?universe_type=sp500&limit=100`, {
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
    console.log('SSR: Response data:', data.ok !== undefined ? 'has data' : 'no data');
    
    if (data && data.items) {
      const items = data.items || [];
      const scanDate = data.as_of || '';
      
      return {
        props: {
          initialData: items,
          initialScanDate: scanDate,
          initialMarketCondition: data.market_condition || null
        }
      };
    } else {
      console.log('SSR: Data not ok or no data');
    }
  } catch (error) {
    console.error('SSR: Error fetching US stocks scan data:', error);
  }
  
  return {
    props: {
      initialData: [],
      initialScanDate: '',
      initialMarketCondition: null
    }
  };
}

