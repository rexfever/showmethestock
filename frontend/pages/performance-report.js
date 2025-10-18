import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import getConfig from '../config';
import Header from '../components/Header';

export default function PerformanceReport() {
  const router = useRouter();
  const { isAuthenticated, user, loading: authLoading, authChecked } = useAuth();
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('weekly');
  const [selectedYear, setSelectedYear] = useState(2025);
  const [selectedMonth, setSelectedMonth] = useState(8);
  const [selectedWeek, setSelectedWeek] = useState(1);
  const [selectedQuarter, setSelectedQuarter] = useState(1);
  const [availableReports, setAvailableReports] = useState({});
  const [isMounted, setIsMounted] = useState(true);

  // 컴포넌트 마운트 상태 관리
  useEffect(() => {
    setIsMounted(true);
    return () => {
      setIsMounted(false);
    };
  }, []);

  // 로그인 체크
  useEffect(() => {
    if (authChecked && !authLoading && !isAuthenticated()) {
      router.push('/login');
    }
  }, [authChecked, authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (authChecked && !authLoading) {
      const abortController = new AbortController();
      
      const loadAvailableReportsWithAbort = async () => {
        try {
          await loadAvailableReports(abortController.signal);
        } catch (error) {
          if (error.name !== 'AbortError') {
            console.error('사용 가능한 보고서 목록 로드 실패:', error);
          }
        }
      };
      
      loadAvailableReportsWithAbort();
      
      return () => {
        abortController.abort();
      };
    }
  }, [authChecked, authLoading]);

  useEffect(() => {
    const abortController = new AbortController();
    
    // 기존 데이터 초기화
    setReportData(null);
    setError(null);
    
    const loadReportWithAbort = async () => {
      try {
        await loadReport(abortController.signal);
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('보고서 로드 오류:', error);
        }
      }
    };
    
    loadReportWithAbort();
    
    return () => {
      abortController.abort();
    };
  }, [activeTab, selectedYear, selectedMonth, selectedWeek, selectedQuarter]);

  const loadAvailableReports = async (signal) => {
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const [weeklyRes, monthlyRes, quarterlyRes, yearlyRes] = await Promise.all([
        fetch(`${base}/reports/available/weekly`, { signal }),
        fetch(`${base}/reports/available/monthly`, { signal }),
        fetch(`${base}/reports/available/quarterly`, { signal }),
        fetch(`${base}/reports/available/yearly`, { signal })
      ]);
      
      if (signal?.aborted) {
        throw new Error('AbortError');
      }
      
      const [weeklyData, monthlyData, quarterlyData, yearlyData] = await Promise.all([
        weeklyRes.json(),
        monthlyRes.json(),
        quarterlyRes.json(),
        yearlyRes.json()
      ]);
      
      if (signal?.aborted) {
        throw new Error('AbortError');
      }
      
      if (isMounted) {
        setAvailableReports({
          weekly: weeklyData.ok ? weeklyData.data : [],
          monthly: monthlyData.ok ? monthlyData.data : [],
          quarterly: quarterlyData.ok ? quarterlyData.data : [],
          yearly: yearlyData.ok ? yearlyData.data : []
        });
      }
    } catch (error) {
      if (error.name === 'AbortError' || error.message === 'AbortError') {
        // 요청이 취소된 경우는 에러로 처리하지 않음
        return;
      }
      console.error('사용 가능한 보고서 목록 로드 실패:', error);
    }
  };

  const loadReport = async (signal) => {
    try {
      if (isMounted) {
        setLoading(true);
        setError(null);
      }
      
      const config = getConfig();
      const base = config.backendUrl;
      
      let url = '';
      if (activeTab === 'weekly') {
        url = `${base}/reports/weekly/${selectedYear}/${selectedMonth}/${selectedWeek}`;
      } else if (activeTab === 'monthly') {
        url = `${base}/reports/monthly/${selectedYear}/${selectedMonth}`;
      } else if (activeTab === 'quarterly') {
        url = `${base}/reports/quarterly/${selectedYear}/${selectedQuarter}`;
      } else if (activeTab === 'yearly') {
        url = `${base}/reports/yearly/${selectedYear}`;
      }
      
      const response = await fetch(url, { signal });
      
      if (signal?.aborted) {
        throw new Error('AbortError');
      }
      
      const data = await response.json();
      
      if (signal?.aborted) {
        throw new Error('AbortError');
      }
      
      if (isMounted) {
        if (data.ok) {
          setReportData(data.data);
          setError(null); // 성공 시 에러 초기화
        } else {
          setError(data.error || '보고서 데이터를 불러올 수 없습니다.');
          setReportData(null); // 에러 시 데이터 초기화
        }
      }
    } catch (error) {
      if (error.name === 'AbortError' || error.message === 'AbortError') {
        // 요청이 취소된 경우는 에러로 처리하지 않음
        return;
      }
      if (isMounted) {
        setError('네트워크 오류가 발생했습니다.');
        setReportData(null); // 네트워크 오류 시 데이터 초기화
      }
    } finally {
      if (!signal?.aborted && isMounted) {
        setLoading(false);
      }
    }
  };


  if (!authChecked || authLoading) {
    return (
      <>
        <Head>
          <title>성과 보고서 - 스톡인사이트</title>
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


  // 로딩 중이거나 인증되지 않은 경우
  if (authLoading || !authChecked) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated()) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">로그인이 필요합니다.</p>
          <button
            onClick={() => router.push('/login')}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
          >
            로그인하기
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>성과 보고서 - 스톡인사이트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        <Header />

        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">추천종목 성과 보고서</h2>
              <p className="text-sm opacity-90">추천 종목의 성과 분석 및 투자 결과 리포트</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <span className="text-2xl">📈</span>
            </div>
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="p-4">
          <div className="max-w-6xl mx-auto">

            {/* 탭 메뉴 */}
            <div className="bg-white rounded-lg shadow-sm mb-6">
              <div className="flex border-b">
                {[
                  { key: 'weekly', label: '주간' },
                  { key: 'monthly', label: '월간' },
                  { key: 'quarterly', label: '분기' },
                  { key: 'yearly', label: '연간' }
                ].map(tab => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab.key
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 컨트롤 */}
            <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
              <div className="flex flex-wrap items-center gap-4 mb-4">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-gray-700">연도</label>
                  <select 
                    value={selectedYear}
                    onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                    className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="2025">2025</option>
                    <option value="2024">2024</option>
                    <option value="2023">2023</option>
                  </select>
                </div>
              </div>
              
              {/* 주간 탭 */}
              {activeTab === 'weekly' && (
                <>
                  <div className="flex items-center gap-2 mb-2">
                    <label className="text-sm font-medium text-gray-700">월</label>
                  </div>
                  <div className="grid grid-cols-6 md:grid-cols-12 gap-2 mb-4">
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(month => (
                      <button
                        key={month}
                        onClick={() => setSelectedMonth(month)}
                        className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                          selectedMonth === month
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {month}월
                      </button>
                    ))}
                  </div>
                  
                  <div className="flex items-center gap-2 mb-2">
                    <label className="text-sm font-medium text-gray-700">주차</label>
                  </div>
                  <div className="grid grid-cols-5 gap-2">
                    {[1, 2, 3, 4, 5].map(week => (
                      <button
                        key={week}
                        onClick={() => setSelectedWeek(week)}
                        className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                          selectedWeek === week
                            ? 'bg-green-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {week}주차
                      </button>
                    ))}
                  </div>
                </>
              )}
              
              {/* 월간 탭 */}
              {activeTab === 'monthly' && (
                <>
                  <div className="flex items-center gap-2 mb-2">
                    <label className="text-sm font-medium text-gray-700">월</label>
                  </div>
                  <div className="grid grid-cols-6 md:grid-cols-12 gap-2">
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(month => (
                      <button
                        key={month}
                        onClick={() => setSelectedMonth(month)}
                        className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                          selectedMonth === month
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {month}월
                      </button>
                    ))}
                  </div>
                </>
              )}
              
              {/* 분기 탭 */}
              {activeTab === 'quarterly' && (
                <>
                  <div className="flex items-center gap-2 mb-2">
                    <label className="text-sm font-medium text-gray-700">분기</label>
                  </div>
                  <div className="grid grid-cols-4 gap-2">
                    {[1, 2, 3, 4].map(quarter => (
                      <button
                        key={quarter}
                        onClick={() => setSelectedQuarter(quarter)}
                        className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                          selectedQuarter === quarter
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {quarter}분기
                      </button>
                    ))}
                  </div>
                </>
              )}
              
              {/* 연간 탭 */}
              {activeTab === 'yearly' && (
                <div className="text-center py-4">
                  <p className="text-gray-600">선택된 연도의 연간 보고서를 조회합니다.</p>
                </div>
              )}
            </div>

            {/* 에러 메시지 */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
                <p className="text-red-600">{error}</p>
              </div>
            )}

            {/* 로딩 */}
            {loading && (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                <p className="text-gray-500 mt-2">데이터를 불러오는 중...</p>
              </div>
            )}

            {/* 보고서 데이터 */}
            {reportData && !loading && !error && (
              <div className="space-y-6">
                {/* 요약 정보 - 한 줄 표시 */}
                <div className="bg-white rounded-lg shadow-sm p-6">
                    <div className="flex flex-wrap items-center justify-between gap-6">
                    <div className="flex items-center gap-3">
                      <span className="text-base font-medium text-gray-600">총 추천 종목:</span>
                      <span className="text-lg font-bold text-gray-900">{reportData.statistics.total_stocks}개</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-base font-medium text-gray-600">평균 수익률:</span>
                      <span className={`text-lg font-bold ${reportData.statistics.avg_return >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
                        {reportData.statistics.avg_return >= 0 ? '+' : ''}{reportData.statistics.avg_return}%
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-base font-medium text-gray-600">수익 종목 비율:</span>
                      <div className="flex flex-col items-center">
                        <span className="text-lg font-bold text-gray-900">
                          {reportData.statistics.positive_rate}%
                        </span>
                        <div className="flex gap-1 mt-2">
                          <div className={`w-4 h-4 rounded-full ${
                            reportData.statistics.positive_rate < 50 ? 'bg-red-500' : 'bg-red-100'
                          }`}></div>
                          <div className={`w-4 h-4 rounded-full ${
                            reportData.statistics.positive_rate >= 50 && reportData.statistics.positive_rate < 70 ? 'bg-yellow-300' : 'bg-yellow-100'
                          }`}></div>
                          <div className={`w-4 h-4 rounded-full ${
                            reportData.statistics.positive_rate >= 70 ? 'bg-green-500' : 'bg-green-100'
                          }`}></div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-base font-medium text-gray-600">추천 기간:</span>
                      <span className="text-lg font-bold text-gray-900">{reportData.dates.length}일</span>
                    </div>
                  </div>
                </div>

                {/* 최고/최저 성과 - 한 줄 표시 */}
                {reportData.statistics.best_stock && reportData.statistics.worst_stock && (
                  <div className="bg-white rounded-lg shadow-sm p-6">
                    <div className="flex flex-wrap items-center justify-between gap-6">
                      <div className="flex items-center gap-3">
                        <span className="text-base font-medium text-gray-600">최고 성과:</span>
                        <span className="text-base font-semibold text-gray-900">{reportData.statistics.best_stock.name}</span>
                        <span className={`text-base font-bold ${reportData.statistics.best_stock.max_return >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
                          {reportData.statistics.best_stock.max_return >= 0 ? '+' : ''}{reportData.statistics.best_stock.max_return}%
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-base font-medium text-gray-600">최저 성과:</span>
                        <span className="text-base font-semibold text-gray-900">{reportData.statistics.worst_stock.name}</span>
                        <span className={`text-base font-bold ${reportData.statistics.worst_stock.max_return >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
                          {reportData.statistics.worst_stock.max_return >= 0 ? '+' : ''}{reportData.statistics.worst_stock.max_return}%
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* 종목 리스트 */}
                {reportData.stocks && reportData.stocks.length > 0 && (
                  <div className="bg-white rounded-lg shadow-sm">
                    <div className="p-6 border-b">
                      <h3 className="text-xl font-bold text-gray-900">
                        {activeTab === 'weekly' && '주간 추천 종목 리스트'}
                        {activeTab === 'monthly' && '월간 추천 종목 리스트'}
                        {activeTab === 'quarterly' && '분기 추천 종목 리스트'}
                        {activeTab === 'yearly' && '연간 추천 종목 리스트'}
                      </h3>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">종목명</th>
                            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">추천가</th>
                            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">추천일</th>
                            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">현재수익률</th>
                            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">최고수익률</th>
                            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">최저수익률</th>
                            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">경과일</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {reportData.stocks
                            .sort((a, b) => b.current_return - a.current_return)
                            .map((stock, index) => (
                            <tr key={index}>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm font-semibold text-gray-900">{stock.name}</div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {stock.scan_price.toLocaleString()}원
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {stock.scan_date}
                              </td>
                              <td className={`px-6 py-4 whitespace-nowrap text-sm font-semibold ${
                                stock.current_return >= 0 ? 'text-red-600' : 'text-blue-600'
                              }`}>
                                {stock.current_return >= 0 ? '+' : ''}{stock.current_return}%
                              </td>
                              <td className={`px-6 py-4 whitespace-nowrap text-sm font-semibold ${
                                stock.max_return >= 0 ? 'text-red-600' : 'text-blue-600'
                              }`}>
                                {stock.max_return >= 0 ? '+' : ''}{stock.max_return}%
                              </td>
                              <td className={`px-6 py-4 whitespace-nowrap text-sm font-semibold ${
                                stock.min_return >= 0 ? 'text-red-600' : 'text-blue-600'
                              }`}>
                                {stock.min_return >= 0 ? '+' : ''}{stock.min_return}%
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {stock.days_elapsed}일
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
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
              className="flex flex-col items-center py-2 hover:bg-gray-800"
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
