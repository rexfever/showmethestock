// Scanner V2 전용 화면 - 인피니티 스크롤 버전
import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
// config는 동적 import로 처리
const getConfig = () => {
  if (typeof window !== 'undefined') {
    // 클라이언트 사이드 - 개발 환경에서는 항상 로컬 백엔드 사용
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    return {
      backendUrl: isLocal 
        ? 'http://localhost:8010'
        : (process.env.NODE_ENV === 'production' ? 'https://sohntech.ai.kr/api' : 'http://localhost:8010')
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
  const [activeEngine, setActiveEngine] = useState(null);

  // active_engine 확인 (v3인지 확인) - mounted 후에만 실행하여 초기 로딩 지연 방지
  useEffect(() => {
    if (!mounted) return;
    
    const checkActiveEngine = async () => {
      try {
        const config = getConfig();
        const base = config.backendUrl;
        
        // 인증 토큰 가져오기 (사용자별 설정을 위해 필요)
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
        
        const headers = {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        };
        
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000); // 2초로 단축
        
        const response = await fetch(`${base}/bottom-nav-link`, {
          method: 'GET',
          headers: headers,
          mode: 'cors',
          cache: 'no-cache',
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
          const data = await response.json();
          if (data.link_type === 'v3') {
            setActiveEngine('v3');
            setScannerVersion('v3');
          } else if (data.link_type === 'v2') {
            setActiveEngine('v2');
            setScannerVersion('v2');
          } else {
            setActiveEngine('v1');
            setScannerVersion('v1');
          }
        }
      } catch (error) {
        // 에러 시 기본값 사용 (조용히 처리)
        setActiveEngine('v2');
        setScannerVersion('v2');
      }
    };
    
    checkActiveEngine();
  }, [mounted]);

  // 최신 스캔 결과 가져오기
  // 특정 날짜의 스캔 결과 가져오기
  const fetchScanByDate = useCallback(async (date) => {
    if (!date) return;
    
    setLoadingMore(true);
    
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      // active_engine에 따라 scanner_version 결정
      const version = activeEngine === 'v3' ? 'v3' : 'v2';
      const response = await fetch(`${base}/scan-by-date/${date}?scanner_version=${version}`, {
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
        
        // 실제 추천 종목이 있는지 확인
        const hasActualStocks = items.some(item => item && item.ticker && item.ticker !== 'NORESULT');
        
        console.log(`fetchScanByDate ${date}:`, { itemsCount: items.length, hasActualStocks });
        
        // NORESULT만 있는 경우는 fetchLatestScan에서만 처리 (무한 루프 방지)
        // hasMore는 handleLoadMore에서 이전 거래일이 없을 때만 false로 설정
      } else {
        // 해당 날짜에 데이터가 없어도 이전 거래일이 있을 수 있으므로
        // hasMore는 handleLoadMore에서 처리
        // 단, 빈 날짜도 표시하기 위해 저장
        console.log(`fetchScanByDate ${date}: 데이터 없음 (ok=false 또는 data 없음)`);
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
      
      // 연속으로 여러 번 실패하면 hasMore를 false로 설정 (최대 3번 실패 시)
      // 단, 네트워크 오류는 제외
      if (!error.message.includes('Failed to fetch') && !error.message.includes('network')) {
        // 실패 카운트는 별도로 관리하지 않고, 단순히 다음 시도는 계속 진행
      }
    } finally {
      setLoadingMore(false);
    }
  }, [activeEngine]);

  // 최신 스캔 결과 가져오기
  const fetchLatestScan = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      // active_engine에 따라 scanner_version 결정
      const version = activeEngine === 'v3' ? 'v3' : (activeEngine === 'v2' ? 'v2' : 'v2');
      // 타임아웃 설정 (5초로 단축)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      const response = await fetch(`${base}/latest-scan?scanner_version=${version}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        mode: 'cors',
        cache: 'no-cache',
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
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
          setDateSections(prev => {
            const updated = {
              ...prev,
              [scanDate]: {
                stocks: items,
                marketCondition: marketCondition,
                loaded: true
              }
            };
            
            // 초기 로드 후 자동으로 이전 날짜 2개 미리 로드 (인피니티 스크롤 개선)
            const hasActualStocks = items.some(item => item && item.ticker && item.ticker !== 'NORESULT');
            if (hasActualStocks && items.length > 0) {
              // 실제 데이터가 있으면 이전 날짜 2개를 미리 로드
              let currentDate = scanDate;
              const datesToPreload = [];
              for (let i = 0; i < 2; i++) {
                const prevDate = getPreviousTradingDate(currentDate);
                if (prevDate && !updated[prevDate]) {
                  datesToPreload.push(prevDate);
                  currentDate = prevDate;
                } else {
                  break;
                }
              }
              
              // 약간의 지연 후 순차적으로 로드 (초기 렌더링 후)
              if (datesToPreload.length > 0) {
                setTimeout(() => {
                  datesToPreload.forEach((date, index) => {
                    setTimeout(() => {
                      fetchScanByDate(date);
                    }, index * 500); // 500ms 간격
                  });
                }, 1000); // 초기 렌더링 후 1초 대기
              }
            }
            
            return updated;
          });
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
  }, [activeEngine, fetchScanByDate]);

  // 더 많은 데이터 로드 (인피니티 스크롤)
  const handleLoadMore = useCallback(() => {
    if (loadingMore || !hasMore) {
      console.log('handleLoadMore: 스킵', { loadingMore, hasMore });
      return;
    }
    
    // 가장 오래된 날짜 찾기
    const dates = Object.keys(dateSections).sort((a, b) => b.localeCompare(a));
    if (dates.length === 0) {
      console.log('handleLoadMore: 날짜 없음');
      return;
    }
    
    // 빈 데이터(로드되었지만 실제 데이터가 없는 날짜)를 건너뛰고 실제 데이터가 있는 날짜 찾기
    let oldestDate = dates[dates.length - 1];
    let oldestSection = dateSections[oldestDate];
    
    // 빈 데이터만 있는 날짜는 건너뛰기 (최대 5개까지)
    let skipCount = 0;
    while (oldestSection && oldestSection.loaded && 
           (!oldestSection.stocks || oldestSection.stocks.length === 0 || 
            (oldestSection.stocks.length === 1 && oldestSection.stocks[0]?.ticker === 'NORESULT')) &&
           skipCount < 5) {
      const prevDate = getPreviousTradingDate(oldestDate);
      if (!prevDate) break;
      
      // 이전 날짜가 이미 로드되어 있는지 확인
      if (dateSections[prevDate]) {
        oldestDate = prevDate;
        oldestSection = dateSections[prevDate];
        skipCount++;
      } else {
        // 아직 로드하지 않은 날짜를 찾았으면 그 날짜를 로드
        console.log('handleLoadMore: 빈 데이터 건너뛰고 다음 날짜 로드', { skipped: skipCount, targetDate: prevDate });
        fetchScanByDate(prevDate);
        return;
      }
    }
    
    // 실제 데이터가 있는 가장 오래된 날짜의 이전 날짜 찾기
    const previousDate = getPreviousTradingDate(oldestDate);
    
    console.log('handleLoadMore:', { oldestDate, previousDate, hasData: previousDate && !dateSections[previousDate] });
    
    if (previousDate && !dateSections[previousDate]) {
      // 이전 날짜가 있고 아직 로드하지 않았으면 로드
      fetchScanByDate(previousDate);
    } else if (!previousDate) {
      // 이전 거래일이 없으면 더 이상 데이터가 없음
      console.log('handleLoadMore: 더 이상 이전 거래일 없음');
      setHasMore(false);
    }
    // previousDate가 있지만 이미 로드된 경우는 다음 스크롤에서 처리됨
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
  // SSR에서 이미 데이터를 받았으므로 클라이언트에서 추가 호출하지 않음
  useEffect(() => {
    // SSR 데이터가 있으면 클라이언트에서 추가 호출하지 않음
    if (mounted && Object.keys(dateSections).length === 0 && !initialData) {
      fetchLatestScan();
    }
  }, [mounted, dateSections, fetchLatestScan, initialData]);
  
  // 초기 데이터(SSR)가 NORESULT만 있으면 이전 날짜 자동 로드
  useEffect(() => {
    if (!mounted || loading || loadingMore) return;
    
    const dates = Object.keys(dateSections).sort((a, b) => b.localeCompare(a));
    if (dates.length === 0) return;
    
    const newestDate = dates[0];
    const section = dateSections[newestDate];
    if (section && section.stocks && section.loaded) {
      const hasActualStocks = section.stocks.some(item => item && item.ticker && item.ticker !== 'NORESULT');
      // NORESULT만 있고 아직 다른 날짜를 로드하지 않았으면 이전 날짜 로드 (최대 3일 전까지)
      if (!hasActualStocks && section.stocks.length > 0) {
        // 이미 로드 시도 중이 아닌 경우만
        const isAlreadyLoading = dates.some(d => {
          const s = dateSections[d];
          return s && !s.loaded;
        });
        
        if (!isAlreadyLoading) {
          let currentDate = newestDate;
          let datesToLoad = [];
          
          // 최대 3일 전까지 확인
          for (let i = 0; i < 3; i++) {
            const previousDate = getPreviousTradingDate(currentDate);
            if (previousDate && !dateSections[previousDate]) {
              datesToLoad.push(previousDate);
              currentDate = previousDate;
            } else {
              break;
            }
          }
          
          // 여러 날짜를 순차적으로 로드
          if (datesToLoad.length > 0) {
            datesToLoad.forEach((date, index) => {
              setTimeout(() => {
                fetchScanByDate(date);
              }, index * 300); // 300ms 간격으로 로드
            });
          }
        }
      }
    }
  }, [mounted, dateSections, loading, loadingMore, fetchScanByDate]);

  // 날짜별로 정렬 (최신순)
  const sortedDates = Object.keys(dateSections).sort((a, b) => b.localeCompare(a));
  
  // 디버깅: 상태 로그 (개발 환경에서만)
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('ScannerV2 상태:', {
        dateSectionsCount: sortedDates.length,
        hasMore,
        loading,
        loadingMore,
        activeEngine,
        scannerVersion
      });
    }
  }, [sortedDates.length, hasMore, loading, loadingMore, activeEngine, scannerVersion]);

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
                추천 종목
              </h2>
              <p className="text-sm opacity-90">
                고급 분석 알고리즘으로 찾아낸 추천 종목
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
    
    // V2 페이지는 항상 V2 데이터만 요청
    // 타임아웃 설정 (5초로 단축 - 성능 개선)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(`${base}/latest-scan?scanner_version=v2`, {
      headers: {
        'Accept': 'application/json',
      },
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);

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
