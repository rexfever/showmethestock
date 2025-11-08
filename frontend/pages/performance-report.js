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
                {/* 핵심 지표 대시보드 */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg p-6 text-white">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-blue-100 text-sm">총 추천 종목</p>
                        <p className="text-2xl font-bold">{reportData.statistics.total_stocks}개</p>
                      </div>
                      <div className="text-3xl opacity-80">📊</div>
                    </div>
                  </div>
                  
                  <div className={`rounded-lg p-6 text-white ${
                    reportData.statistics.avg_return >= 0 
                      ? 'bg-gradient-to-r from-red-500 to-red-600' 
                      : 'bg-gradient-to-r from-blue-500 to-blue-600'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-white text-opacity-80 text-sm">평균 수익률</p>
                        <p className="text-2xl font-bold">
                        {reportData.statistics.avg_return >= 0 ? '+' : ''}{reportData.statistics.avg_return}%
                        </p>
                      </div>
                      <div className="text-3xl opacity-80">📈</div>
                    </div>
                  </div>
                  
                  <div className={`rounded-lg p-6 text-white ${
                    reportData.statistics.positive_rate >= 70 
                      ? 'bg-gradient-to-r from-green-500 to-green-600'
                      : reportData.statistics.positive_rate >= 50
                      ? 'bg-gradient-to-r from-yellow-500 to-yellow-600'
                      : 'bg-gradient-to-r from-red-500 to-red-600'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-white text-opacity-80 text-sm">승률</p>
                        <p className="text-2xl font-bold">{reportData.statistics.positive_rate}%</p>
                        <div className="w-full bg-white bg-opacity-20 rounded-full h-2 mt-2">
                          <div 
                            className="bg-white h-2 rounded-full transition-all duration-300"
                            style={{ width: `${reportData.statistics.positive_rate}%` }}
                          ></div>
                        </div>
                      </div>
                      <div className="text-3xl opacity-80">🎯</div>
                    </div>
                  </div>
                  
                  <div className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg p-6 text-white">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-purple-100 text-sm">분석 기간</p>
                        <p className="text-2xl font-bold">{reportData.dates.length}일</p>
                        {reportData.report_version && (
                          <p className="text-xs text-purple-200 mt-1">v{reportData.report_version}</p>
                        )}
                      </div>
                      <div className="text-3xl opacity-80">📅</div>
                    </div>
                  </div>
                </div>

                {/* 섹터별 성과 분석 */}
                {reportData.sector_analysis && Object.keys(reportData.sector_analysis).length > 0 && (
                  <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                      <span className="text-xl mr-2">🏢</span>
                      섹터별 성과 분석
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {Object.entries(reportData.sector_analysis).map(([sector, data], index) => (
                        <div key={index} className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                          <h4 className="font-semibold text-gray-800 mb-2 truncate">
                            {sector || '기타 섹터'}
                          </h4>
                          <div className="space-y-1">
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">종목 수</span>
                              <span className="font-medium">{data.count}개</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">평균 수익률</span>
                              <span className={`font-medium ${
                                data.avg_return >= 0 ? 'text-red-600' : 'text-blue-600'
                              }`}>
                                {data.avg_return >= 0 ? '+' : ''}{data.avg_return}%
                              </span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">승률</span>
                              <span className="font-medium text-green-600">{data.win_rate}%</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 상세 분석 섹션 */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                  {/* 최고/최저 성과 */}
                {reportData.statistics.best_stock && reportData.statistics.worst_stock && (
                    <div className="bg-white rounded-lg shadow-sm p-6">
                      <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                        <span className="text-xl mr-2">🏆</span>
                        최고/최저 성과
                      </h3>
                      <div className="space-y-4">
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm text-green-600 font-medium">최고 성과</p>
                              <p className="text-lg font-bold text-gray-900">{reportData.statistics.best_stock.name}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-2xl font-bold text-green-600">
                                +{reportData.statistics.best_stock.max_return}%
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm text-red-600 font-medium">최저 성과</p>
                              <p className="text-lg font-bold text-gray-900">{reportData.statistics.worst_stock.name}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-2xl font-bold text-red-600">
                                {reportData.statistics.worst_stock.max_return}%
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* 수익률 분포 */}
                  <div className="bg-white rounded-lg shadow-sm p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                      <span className="text-xl mr-2">📊</span>
                      최고 수익률 분포
                    </h3>
                    <div className="space-y-3">
                      {(() => {
                        const ranges = [
                          { label: '20% 이상', min: 20, color: 'bg-green-500' },
                          { label: '10~20%', min: 10, max: 20, color: 'bg-blue-500' },
                          { label: '0~10%', min: 0, max: 10, color: 'bg-yellow-500' },
                          { label: '0% 미만', max: 0, color: 'bg-red-500' }
                        ];
                        
                        return ranges.map(range => {
                          const count = reportData.stocks.filter(stock => {
                            if (range.min !== undefined && range.max !== undefined) {
                              return stock.max_return >= range.min && stock.max_return < range.max;
                            } else if (range.min !== undefined) {
                              return stock.max_return >= range.min;
                            } else {
                              return stock.max_return < range.max;
                            }
                          }).length;
                          
                          const percentage = (count / reportData.stocks.length * 100).toFixed(1);
                          
                          return (
                            <div key={range.label} className="flex items-center justify-between">
                              <div className="flex items-center">
                                <div className={`w-4 h-4 rounded ${range.color} mr-3`}></div>
                                <span className="text-sm font-medium">{range.label}</span>
                              </div>
                              <div className="flex items-center">
                                <span className="text-sm text-gray-600 mr-2">{count}개</span>
                                <span className="text-sm font-bold">{percentage}%</span>
                              </div>
                            </div>
                          );
                        });
                      })()
                      }
                    </div>
                  </div>
                </div>

                {/* 향상된 성과 지표 */}
                {reportData.enhanced_metrics && (
                  <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                      <span className="text-xl mr-2">📊</span>
                      향상된 성과 지표
                      <span className="ml-2 bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded">v2.0</span>
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-gradient-to-r from-blue-50 to-blue-100 border border-blue-200 rounded-lg p-4">
                        <h4 className="font-semibold text-blue-800 mb-3">리스크 지표</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-sm text-blue-700">샤프 비율</span>
                            <span className="text-sm font-bold text-blue-900">{reportData.enhanced_metrics.risk_metrics.sharpe_ratio}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-blue-700">최대 낙폭</span>
                            <span className="text-sm font-bold text-red-600">{reportData.enhanced_metrics.risk_metrics.max_drawdown}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-blue-700">변동성 조정 수익률</span>
                            <span className="text-sm font-bold text-blue-900">{reportData.enhanced_metrics.risk_metrics.volatility_adjusted_return}</span>
                          </div>
                        </div>
                      </div>
                      <div className="bg-gradient-to-r from-green-50 to-green-100 border border-green-200 rounded-lg p-4">
                        <h4 className="font-semibold text-green-800 mb-3">성과 지표</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-sm text-green-700">승률</span>
                            <span className="text-sm font-bold text-green-900">{reportData.enhanced_metrics.performance_metrics.win_rate}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-green-700">평균 수익</span>
                            <span className="text-sm font-bold text-green-900">{reportData.enhanced_metrics.performance_metrics.avg_win}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-green-700">손익비</span>
                            <span className="text-sm font-bold text-green-900">{reportData.enhanced_metrics.performance_metrics.profit_loss_ratio}</span>
                          </div>
                        </div>
                      </div>
                      <div className="bg-gradient-to-r from-purple-50 to-purple-100 border border-purple-200 rounded-lg p-4">
                        <h4 className="font-semibold text-purple-800 mb-3">기본 통계</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-sm text-purple-700">중간값</span>
                            <span className="text-sm font-bold text-purple-900">{reportData.enhanced_metrics.basic_stats.median_return}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-purple-700">표준편차</span>
                            <span className="text-sm font-bold text-purple-900">{reportData.enhanced_metrics.basic_stats.std_return}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-purple-700">총 종목수</span>
                            <span className="text-sm font-bold text-purple-900">{reportData.enhanced_metrics.basic_stats.total_stocks}개</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* AI 인사이트 */}
                <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                    <span className="text-xl mr-2">🤖</span>
                    AI 분석 인사이트
                  </h3>
                  {reportData.ai_insights && reportData.ai_insights.length > 0 ? (
                    <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border border-yellow-200 rounded-lg p-4">
                      <h4 className="font-semibold text-orange-800 mb-3">AI 추천 사항</h4>
                      <ul className="space-y-2">
                        {reportData.ai_insights.map((insight, index) => (
                          <li key={index} className="text-sm text-orange-700 flex items-start">
                            <span className="mr-2">•</span>
                            <span>{insight}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <h4 className="font-semibold text-blue-800 mb-2">성과 분석</h4>
                        <ul className="text-sm text-blue-700 space-y-1">
                          {reportData.statistics.avg_return > 10 && (
                            <li>• 평균 수익률 10% 초과로 우수한 성과</li>
                          )}
                          {reportData.statistics.positive_rate > 70 && (
                            <li>• 70% 이상의 높은 승률 달성</li>
                          )}
                          {reportData.statistics.positive_rate < 50 && (
                            <li>• 승률 개선을 위한 전략 점검 필요</li>
                          )}
                        </ul>
                      </div>
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <h4 className="font-semibold text-green-800 mb-2">투자 가이드</h4>
                        <ul className="text-sm text-green-700 space-y-1">
                          <li>• 상위 20% 종목 우선 검토 추천</li>
                          <li>• 리스크 관리를 위한 분산 투자</li>
                          <li>• 정기적인 수익 실현 및 손절 관리</li>
                        </ul>
                      </div>
                    </div>
                  )}
                </div>

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
                            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">추천횟수</th>
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
                                <span className="font-medium">
                                  {stock.recommendation_dates 
                                    ? stock.recommendation_dates.map(date => parseInt(date.slice(-2))).join(', ') + '일'
                                    : parseInt(stock.scan_date.slice(-2)) + '일'
                                  }
                                </span>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                <div className="flex items-center space-x-2">
                                  <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded">
                                    {stock.recommendation_count || 1}회
                                  </span>
                                  {stock.recommendation_dates && stock.recommendation_dates.length > 1 && (
                                    <span className="bg-green-100 text-green-800 text-xs font-medium px-2 py-1 rounded">
                                      연속추천
                                    </span>
                                  )}
                                </div>
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
