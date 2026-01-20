import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import getConfig from '../config';
import Layout from '../layouts/v2/Layout';
import StockDetailV3 from '../components/v3/StockDetailV3';

export default function StockAnalysis() {
  const router = useRouter();
  const { isAuthenticated, user, loading: authLoading, authChecked } = useAuth();
  const [ticker, setTicker] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // v3에서 온 경우 확인 (query parameter 또는 분석 결과에서)
  const isFromV3 = router.query.from === 'v3' || router.query.v3 === 'true';
  
  // 추천 인스턴스 정보 (query parameter에서)
  const recDateFromQuery = router.query.rec_date;
  const recVersionFromQuery = router.query.rec_version;

  useEffect(() => {
    // 로그인 체크
    if (authChecked && !authLoading && !isAuthenticated()) {
      router.push('/login');
      return;
    }
    
    // URL 파라미터에서 초기 종목 코드 확인
    if (router.query.ticker && isAuthenticated()) {
      setTicker(router.query.ticker);
      performAnalysis(router.query.ticker);
    }
  }, [router.query.ticker, authChecked, authLoading, isAuthenticated]);

  const performAnalysis = async (tickerInput) => {
    if (!authChecked || authLoading) return;
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    
    if (!tickerInput.trim()) {
      setError('종목 코드 또는 종목명을 입력해주세요.');
      return;
    }

    setLoading(true);
    setError(null);
    setAnalysisResult(null);

    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/analyze-friendly?name_or_code=${encodeURIComponent(tickerInput)}`);
      const data = await response.json();
      
      if (data.ok) {
        setAnalysisResult(data);
      } else {
        setError(data.error || '분석에 실패했습니다.');
      }
    } catch (error) {
      console.error('분석 오류:', error);
      setError('분석 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    performAnalysis(ticker);
  };

  const handleTickerChange = (e) => {
    setTicker(e.target.value);
    setError(null);
  };

  // 포트폴리오에 종목 추가
  const addToPortfolio = async (ticker, name) => {
    if (!authChecked || authLoading) return;
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    alert('준비중입니다.');
    return;
  };

  return (
    <>
      <Head>
        <title>종목 분석 - Stock Insight</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
      </Head>

      <Layout headerTitle="종목 분석">
        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">종목 분석</h2>
              <p className="text-sm opacity-90">개별 종목의 현재 상태를 객관적으로 분석합니다</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                <span className="text-3xl">📊</span>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-20">

        {/* 검색 폼 */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="ticker" className="block text-sm font-medium text-gray-700 mb-2">
                종목 코드 또는 종목명
              </label>
              <div className="flex space-x-4">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    id="ticker"
                    value={ticker}
                    onChange={handleTickerChange}
                    placeholder="예: 005930, 삼성전자"
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  {ticker && (
                    <button
                      type="button"
                      onClick={() => {
                        setTicker('');
                        setError(null);
                        setAnalysisResult(null);
                      }}
                      className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                      title="입력 내용 지우기"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={loading || !ticker.trim()}
                  className="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {loading ? '분석 중...' : '분석하기'}
                </button>
              </div>
            </div>
          </form>

          {/* 에러 메시지 */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>

        {/* 로딩 상태 */}
        {loading && (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">종목을 분석하는 중입니다...</p>
          </div>
        )}

        {/* 분석 결과 */}
        {analysisResult && !loading && (
          <div className="space-y-6">
            {/* v3 상세 화면 (v3에서 온 경우 또는 anchor 정보가 있는 경우) */}
            {(isFromV3 || analysisResult.anchor_date || analysisResult.anchor_close) && (
              <StockDetailV3 
                item={null} 
                analysisResult={analysisResult}
              />
            )}
            
            {/* 종목 기본 정보 헤더 */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">
                    {analysisResult.name}
                  </h2>
                  <p className="text-lg text-gray-600">
                    {analysisResult.ticker}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-gray-900">
                    {analysisResult.current_price?.toLocaleString()}원
                  </div>
                  <div className={`text-lg font-semibold ${
                    analysisResult.change_rate > 0 ? 'text-red-600' :
                    analysisResult.change_rate < 0 ? 'text-blue-600' :
                    'text-gray-600'
                  }`}>
                    {analysisResult.change_rate > 0 ? '+' : ''}{analysisResult.change_rate?.toFixed(2)}%
                  </div>
                </div>
              </div>
            </div>

            {/* 현재 상태 분석 */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-center">
                <div className="inline-flex items-center px-6 py-3 rounded-full text-lg font-bold mb-4 bg-blue-100 text-blue-800">
                  현재 상태 분석
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {analysisResult.analysis?.summary}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-gray-700 mb-2">현재 상태</h4>
                    <p className="text-gray-600">{analysisResult.analysis?.current_status}</p>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-gray-700 mb-2">시장 포지션</h4>
                    <p className="text-gray-600">{analysisResult.analysis?.market_position}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* 기술적 지표 상태 */}
            {analysisResult.analysis?.technical_status && analysisResult.analysis.technical_status.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 기술적 지표 상태</h3>
                <div className="space-y-3">
                  {analysisResult.analysis.technical_status.map((status, index) => (
                    <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                      <div className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full"></div>
                      <p className="text-gray-700">{status}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 현재가 및 변동률 */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">💰 가격 정보</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-gray-900 mb-1">
                    {analysisResult.current_price?.toLocaleString()}원
                  </div>
                  <div className="text-sm text-gray-600">현재가</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className={`text-2xl font-bold mb-1 ${
                    analysisResult.change_rate > 0 ? 'text-red-600' :
                    analysisResult.change_rate < 0 ? 'text-blue-600' :
                    'text-gray-900'
                  }`}>
                    {analysisResult.change_rate > 0 ? '+' : ''}{analysisResult.change_rate?.toFixed(2)}%
                  </div>
                  <div className="text-sm text-gray-600">등락률</div>
                </div>
              </div>
            </div>

            {/* 주의사항 */}
            {analysisResult.analysis?.warnings && analysisResult.analysis.warnings.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-yellow-800 mb-4">⚠️ 주의사항</h3>
                <div className="space-y-2">
                  {analysisResult.analysis.warnings.map((warning, index) => (
                    <p key={index} className="text-yellow-700 text-sm">
                      {warning}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* 간단한 지표 */}
            {analysisResult.analysis?.simple_indicators && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 주요 지표</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(analysisResult.analysis.simple_indicators).map(([key, indicator]) => (
                    <div key={key} className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-lg font-bold text-gray-900 mb-1">
                        {indicator.value}
                      </div>
                      <div className="text-xs text-gray-600">
                        {indicator.description}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 액션 버튼 */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-center space-x-4">
                <button
                  onClick={() => {
                    const naverUrl = `https://finance.naver.com/item/main.naver?code=${analysisResult.ticker}`;
                    window.open(naverUrl, '_blank');
                  }}
                  className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium"
                >
                  📊 차트 & 기업정보
                </button>
                <button
                  onClick={() => {
                    setTicker('');
                    setAnalysisResult(null);
                    setError(null);
                  }}
                  className="px-6 py-3 bg-gray-500 text-white rounded-lg hover:bg-gray-600 font-medium"
                >
                  🔄 다른 종목 분석
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 사용 가이드 */}
        {!analysisResult && !loading && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-blue-900 mb-3">💡 사용 가이드</h3>
            <div className="text-blue-800 space-y-2">
              <p>• <strong>종목 코드</strong>: 6자리 숫자 (예: 005930)</p>
              <p>• <strong>종목명</strong>: 회사명 (예: 삼성전자, SK하이닉스)</p>
              <p>• <strong>분석 결과</strong>: 종목의 현재 상태와 기술적 지표를 확인할 수 있습니다</p>
              <p>• <strong>현재 상태 분석</strong>: 스캔 조건 매칭보다는 현재 상황을 객관적으로 분석합니다</p>
            </div>
          </div>
        )}
        </div>
      </Layout>
    </>
  );
}
