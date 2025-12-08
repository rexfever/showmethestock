// Scanner V2 전용 화면 - 인피니티 스크롤 버전
import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
// config는 동적 import로 처리
const getConfig = () => {
  if (typeof window !== 'undefined') {
    // 클라이언트 사이드
    return {
      backendUrl: process.env.NODE_ENV === 'production' 
        ? 'https://sohntech.ai.kr/api' 
        : 'http://localhost:8010'
    };
  } else {
    // 서버 사이드
    return {
      backendUrl: process.env.BACKEND_URL || 'http://localhost:8010'
    };
  }
};
import Layout from '../layouts/Layout';
import DateSection from '../components/DateSection';
import InfiniteScrollContainer from '../components/InfiniteScrollContainer';

// 날짜 계산 헬퍼 함수
const formatDate = (dateStr) => {
  if (!dateStr || dateStr.length !== 8) return dateStr;
  try {
    const year = dateStr.slice(0, 4);
    const month = dateStr.slice(4, 6);
    const day = dateStr.slice(6, 8);
    const dateObj = new Date(`${year}-${month}-${day}`);
    const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
    const weekday = weekdays[dateObj.getDay()];
    return `${year}년 ${parseInt(month)}월 ${parseInt(day)}일 (${weekday})`;
  } catch (e) {
    return dateStr;
  }
};

// 이전 거래일 계산 (주말/공휴일 제외)
const getPreviousTradingDate = (dateStr) => {
  if (!dateStr || dateStr.length !== 8) return null;
  try {
    const year = parseInt(dateStr.slice(0, 4));
    const month = parseInt(dateStr.slice(4, 6)) - 1;
    const day = parseInt(dateStr.slice(6, 8));
    let date = new Date(year, month, day);
    
    // 최대 10일 전까지 확인
    for (let i = 0; i < 10; i++) {
      date.setDate(date.getDate() - 1);
      const weekday = date.getDay();
      // 주말 제외 (토요일=6, 일요일=0)
      if (weekday !== 0 && weekday !== 6) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}${month}${day}`;
      }
    }
    return null;
  } catch (e) {
    return null;
  }
};

export default function ScannerV2({ initialData, initialScanDate, initialMarketCondition, initialScannerVersion }) {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  
  // 날짜별 데이터 구조: { 'YYYYMMDD': { stocks: [], marketCondition: {}, loaded: boolean } }
  const [dateSections, setDateSections] = useState(() => {
    const initial = {};
    if (initialScanDate && initialData) {
      initial[initialScanDate] = {
        stocks: initialData,
        marketCondition: initialMarketCondition,
        loaded: true
      };
    }
    return initial;
  });
  
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [mounted, setMounted] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [scannerVersion, setScannerVersion] = useState(initialScannerVersion || 'v1');

  // 최신 스캔 결과 가져오기
  const fetchLatestScan = useCallback(async () => {
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
        const items = data.data.items || [];
        const scanDate = data.data.as_of || data.data.scan_date || '';
        const detectedVersion = data.data.scanner_version || 'v1';
        const marketCondition = data.data.market_condition || null;
        
        setScannerVersion(detectedVersion);
        
        // 날짜별 데이터 구조로 저장
        if (scanDate) {
          setDateSections(prev => ({
            ...prev,
            [scanDate]: {
              stocks: items,
              marketCondition: marketCondition,
              loaded: true
            }
          }));
        }
        
        setError(null);
      } else {
        const errorMsg = data.error || '스캔 결과 조회 실패';
        setError(errorMsg);
      }
    } catch (error) {
      if (error.message.includes('Failed to fetch')) {
        setError('네트워크 연결을 확인해주세요.');
      } else {
        setError(`데이터 불러오는 중 오류가 발생했습니다: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // 특정 날짜의 스캔 결과 가져오기
  const fetchScanByDate = useCallback(async (date) => {
    if (!date) return;
    
    setLoadingMore(true);
    
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/scan-by-date/${date}`, {
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
        const items = data.data.items || [];
        const marketCondition = data.data.market_condition || null;
        
        // 날짜별 데이터 구조로 저장
        setDateSections(prev => ({
          ...prev,
          [date]: {
            stocks: items,
            marketCondition: marketCondition,
            loaded: true
          }
        }));
        
        // 더 이상 데이터가 없으면 hasMore를 false로
        if (items.length === 0 && !marketCondition) {
          setHasMore(false);
        }
      } else {
        // 해당 날짜에 데이터가 없으면 더 이상 로드하지 않음
        setHasMore(false);
      }
    } catch (error) {
      console.error(`날짜 ${date} 스캔 결과 조회 실패:`, error);
      setHasMore(false);
    } finally {
      setLoadingMore(false);
    }
  }, []);

  // 더 많은 데이터 로드 (인피니티 스크롤)
  const handleLoadMore = useCallback(() => {
    if (loadingMore || !hasMore) return;
    
    // 가장 오래된 날짜 찾기
    const dates = Object.keys(dateSections).sort((a, b) => b.localeCompare(a));
    if (dates.length === 0) return;
    
    const oldestDate = dates[dates.length - 1];
    const previousDate = getPreviousTradingDate(oldestDate);
    
    if (previousDate && !dateSections[previousDate]) {
      fetchScanByDate(previousDate);
    } else {
      setHasMore(false);
    }
  }, [dateSections, loadingMore, hasMore, fetchScanByDate]);

  // 차트 보기 핸들러
  const handleViewChart = useCallback((ticker) => {
    // 네이버 금융 차트 & 기업정보 링크 열기
    const naverInfoUrl = `https://finance.naver.com/item/main.naver?code=${ticker}`;
    window.open(naverInfoUrl, '_blank');
  }, []);

  useEffect(() => {
    setMounted(true);
  }, []);

  // 초기 데이터가 없으면 최신 스캔 결과 가져오기
  useEffect(() => {
    if (mounted && Object.keys(dateSections).length === 0) {
      fetchLatestScan();
    }
  }, [mounted, dateSections, fetchLatestScan]);

  // 날짜별로 정렬 (최신순)
  const sortedDates = Object.keys(dateSections).sort((a, b) => b.localeCompare(a));

  return (
    <>
      <Head>
        <title>Scanner V2 - Stock Insight</title>
        <meta name="description" content="고급 분석 알고리즘으로 찾아낸 추천 종목" />
      </Head>
      <Layout headerTitle="스톡인사이트">
        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">
                추천 종목 {scannerVersion === 'v2' && '(Scanner V2)'}
              </h2>
              <p className="text-sm opacity-90">
                {scannerVersion === 'v2' 
                  ? '고급 분석 알고리즘으로 찾아낸 추천 종목' 
                  : 'AI가 찾아낸 추천 종목을 지금 확인하세요!'}
              </p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* 에러 표시 */}
        {error && (
          <div className="mx-4 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{error}</p>
            <button
              onClick={fetchLatestScan}
              className="mt-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm"
            >
              다시 시도
            </button>
          </div>
        )}

        {/* 초기 로딩 */}
        {loading && sortedDates.length === 0 && (
          <div className="p-4 text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
            <p className="text-gray-500 mt-2">스캔 결과를 불러오는 중...</p>
          </div>
        )}

        {/* 날짜별 스캔 결과 */}
        {sortedDates.length > 0 && (
          <InfiniteScrollContainer
            onLoadMore={handleLoadMore}
            hasMore={hasMore}
            isLoading={loadingMore}
          >
            {sortedDates.map((date) => {
              const section = dateSections[date];
              return (
                <DateSection
                  key={date}
                  date={date}
                  stocks={section.stocks}
                  marketCondition={section.marketCondition}
                  isLoading={false}
                  onViewChart={handleViewChart}
                />
              );
            })}
          </InfiniteScrollContainer>
        )}

        {/* 데이터가 없는 경우 */}
        {!loading && sortedDates.length === 0 && !error && (
          <div className="p-4 text-center py-8">
            <p className="text-gray-500 text-lg mb-2">스캔 결과가 없습니다.</p>
            <p className="text-gray-400 text-sm">
              아직 스캔이 실행되지 않았거나 데이터가 없습니다.
            </p>
          </div>
        )}
      </Layout>
    </>
  );
}

export async function getServerSideProps() {
  try {
    // 서버 사이드에서는 환경 변수 직접 사용
    const base = process.env.BACKEND_URL || (process.env.NODE_ENV === 'production' 
      ? 'https://sohntech.ai.kr/api' 
      : 'http://localhost:8010');
    
    // 최신 스캔 결과 가져오기
    const response = await fetch(`${base}/latest-scan`, {
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (data.ok && data.data) {
      const items = data.data.items || [];
      const scanDate = data.data.as_of || data.data.scan_date || '';
      const marketCondition = data.data.market_condition || null;
      const detectedVersion = data.data.scanner_version || 'v1';

      return {
        props: {
          initialData: items,
          initialScanDate: scanDate,
          initialMarketCondition: marketCondition,
          initialScannerVersion: detectedVersion,
        },
      };
    } else {
      return {
        props: {
          initialData: [],
          initialScanDate: '',
          initialMarketCondition: null,
          initialScannerVersion: 'v1',
        },
      };
    }
  } catch (error) {
    console.error('SSR 오류:', error);
    return {
      props: {
        initialData: [],
        initialScanDate: '',
        initialMarketCondition: null,
        initialScannerVersion: 'v1',
      },
    };
  }
}
