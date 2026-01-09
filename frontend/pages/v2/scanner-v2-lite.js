// Scanner V2-Lite 전용 화면
// 기존 scanner-v2.js를 기반으로 v2-lite 전용으로 수정
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
import Layout from '../../layouts/v2/Layout';
import DateSection from '../../components/v2/DateSection';
import InfiniteScrollContainer from '../../components/v2/InfiniteScrollContainer';

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

export default function ScannerV2Lite({ initialData, initialScanDate, initialScannerVersion }) {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  
  // 날짜별 데이터 구조: { 'YYYYMMDD': { stocks: [], marketCondition: null, loaded: boolean } }
  // v2-lite는 market_condition을 사용하지 않으므로 항상 null
  const [dateSections, setDateSections] = useState(() => {
    const initial = {};
    if (initialScanDate && initialData) {
      initial[initialScanDate] = {
        stocks: initialData,
        marketCondition: null,  // v2-lite는 레짐 분석 미사용
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
  const [scannerVersion, setScannerVersion] = useState(initialScannerVersion || 'v2-lite');

  // 특정 날짜의 스캔 결과 가져오기
  const fetchScanByDate = useCallback(async (date) => {
    if (!date) return;
    
    setLoadingMore(true);
    
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      // V2-Lite 페이지는 항상 v2-lite 데이터만 요청
      const response = await fetch(`${base}/scan-by-date/${date}?scanner_version=v2-lite`, {
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
        // v2-lite는 market_condition을 사용하지 않음
        const marketCondition = null;
        
        // 날짜별 데이터 구조로 저장
        setDateSections(prev => ({
          ...prev,
          [date]: {
            stocks: items,
            marketCondition: marketCondition,
            loaded: true
          }
        }));
      } else {
        // 해당 날짜에 데이터가 없어도 이전 거래일이 있을 수 있으므로
        // hasMore는 handleLoadMore에서 처리
        // 단, 빈 날짜도 표시하기 위해 저장
        setDateSections(prev => ({
          ...prev,
          [date]: {
            stocks: [],
            marketCondition: null,
            loaded: true
          }
        }));
      }
    } catch (error) {
      console.error(`날짜 ${date} 스캔 결과 조회 실패:`, error);
      // 에러가 발생해도 이전 거래일이 있을 수 있으므로 hasMore는 유지
      // 단, 빈 날짜로 표시
      setDateSections(prev => ({
        ...prev,
        [date]: {
          stocks: [],
          marketCondition: null,
          loaded: true
        }
      }));
    } finally {
      setLoadingMore(false);
    }
  }, []);

  // 최신 스캔 결과 가져오기
  const fetchLatestScan = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      // V2-Lite 페이지는 항상 v2-lite 데이터만 요청
      const response = await fetch(`${base}/latest-scan?scanner_version=v2-lite`, {
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
        const detectedVersion = data.data.scanner_version || 'v2-lite';
        // v2-lite는 market_condition을 사용하지 않음
        const marketCondition = null;
        
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
  }, [fetchScanByDate]);

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
    } else if (!previousDate) {
      // 이전 거래일이 없으면 더 이상 데이터가 없음
      setHasMore(false);
    }
    // previousDate가 있지만 이미 로드된 경우는 아무것도 하지 않음 (hasMore 유지)
  }, [dateSections, loadingMore, hasMore, fetchScanByDate]);

  // 차트 보기 핸들러
  const handleViewChart = useCallback((ticker) => {
    router.push(`/stock-analysis?code=${ticker}`);
  }, [router]);

  // 마운트 후 최신 스캔 결과 가져오기
  useEffect(() => {
    setMounted(true);
    if (Object.keys(dateSections).length === 0) {
      fetchLatestScan();
    }
  }, []);

  // 날짜 정렬 (최신순)
  const sortedDates = Object.keys(dateSections).sort((a, b) => b.localeCompare(a));

  return (
    <>
      <Head>
        <title>스톡인사이트 - 눌림목 전략 스캐너 (V2-Lite)</title>
        <meta name="description" content="눌림목 전략 V2-Lite - 단순화된 스캐너" />
      </Head>
      <Layout>
        {/* 헤더 */}
        <div className="bg-white border-b border-gray-200 px-4 py-4 sticky top-0 z-20">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">눌림목 전략 스캐너</h1>
              <p className="text-sm text-gray-600 mt-1">V2-Lite (레짐 분석/점수 계산 미사용)</p>
            </div>
            <button
              onClick={fetchLatestScan}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
            >
              새로고침
            </button>
          </div>
        </div>

        {/* V2-Lite 안내 */}
        <div className="mx-4 mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-800">
            <strong>V2-Lite 특징:</strong> 눌림목 전략 전용 (2주 이내 +5% 단기 스윙), 레짐 분석 미사용, 점수 계산 미사용, True/False 판단만 수행
          </p>
        </div>

        {/* 에러 메시지 */}
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
    
    // V2-Lite 페이지는 항상 v2-lite 데이터만 요청
    const response = await fetch(`${base}/latest-scan?scanner_version=v2-lite`, {
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
      // v2-lite는 market_condition을 사용하지 않음
      const detectedVersion = data.data.scanner_version || 'v2-lite';

      return {
        props: {
          initialData: items,
          initialScanDate: scanDate,
          initialScannerVersion: detectedVersion,
        },
      };
    } else {
      return {
        props: {
          initialData: [],
          initialScanDate: '',
          initialScannerVersion: 'v2-lite',
        },
      };
    }
  } catch (error) {
    console.error('V2-Lite 스캔 결과 조회 실패:', error);
    return {
      props: {
        initialData: [],
        initialScanDate: '',
        initialScannerVersion: 'v2-lite',
      },
    };
  }
}
























