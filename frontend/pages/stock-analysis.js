import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import getConfig from '../config';

export default function StockAnalysis() {
  const router = useRouter();
  const { isAuthenticated, user, loading: authLoading, authChecked } = useAuth();
  const [ticker, setTicker] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // 로그인 체크
    if (authChecked && !authLoading && !isAuthenticated()) {
      alert('종목분석 기능을 사용하려면 로그인이 필요합니다.');
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
    if (!isAuthenticated()) {
      alert('종목분석 기능을 사용하려면 로그인이 필요합니다.');
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
    if (!isAuthenticated()) {
      alert('관심종목 기능을 사용하려면 로그인이 필요합니다.');
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

      <div className="min-h-screen bg-gray-50">
        {/* 상단 바 */}
        <div className="bg-white shadow-sm">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center">
              <span className="text-lg font-semibold text-gray-800">스톡인사이트</span>
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
              <h2 className="text-lg font-semibold">종목 분석</h2>
              <p className="text-sm opacity-90">개별 종목의 상세한 기술적 분석을 제공합니다</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                <span className="text-3xl">📊</span>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

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
                    {analysisResult.friendly_analysis?.simple_indicators?.current_price?.value}
                  </div>
                  <div className="text-sm text-gray-500">
                    거래량: {analysisResult.friendly_analysis?.simple_indicators?.volume?.value}
                  </div>
                </div>
              </div>
            </div>

            {/* 종합 평가 */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-center">
                <div className={`inline-flex items-center px-6 py-3 rounded-full text-lg font-bold mb-4 ${
                  analysisResult.friendly_analysis?.recommendation === '강력 추천' ? 'bg-green-100 text-green-800' :
                  analysisResult.friendly_analysis?.recommendation === '추천' ? 'bg-blue-100 text-blue-800' :
                  analysisResult.friendly_analysis?.recommendation === '관심' ? 'bg-yellow-100 text-yellow-800' :
                  analysisResult.friendly_analysis?.recommendation === '신중' ? 'bg-orange-100 text-orange-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {analysisResult.friendly_analysis?.recommendation}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {analysisResult.friendly_analysis?.summary}
                </h3>
                <p className="text-gray-600">
                  신뢰도: {analysisResult.friendly_analysis?.confidence}
                </p>
              </div>
            </div>

            {/* 상세 설명 */}
            {analysisResult.friendly_analysis?.explanations && analysisResult.friendly_analysis.explanations.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 분석 상세</h3>
                <div className="space-y-4">
                  {analysisResult.friendly_analysis.explanations.map((explanation, index) => (
                    <div key={index} className={`p-4 rounded-lg border-l-4 ${
                      explanation.impact === '긍정적' ? 'bg-green-50 border-green-400' :
                      explanation.impact === '부정적' ? 'bg-red-50 border-red-400' :
                      'bg-gray-50 border-gray-400'
                    }`}>
                      <h4 className="font-semibold text-gray-900 mb-2">
                        {explanation.title}
                      </h4>
                      <p className="text-gray-700">
                        {explanation.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 투자 조언 */}
            {analysisResult.friendly_analysis?.investment_advice && analysisResult.friendly_analysis.investment_advice.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">💡 투자 조언</h3>
                <div className="space-y-3">
                  {analysisResult.friendly_analysis.investment_advice.map((advice, index) => (
                    <div key={index} className="flex items-start space-x-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-blue-600 text-sm font-bold">{index + 1}</span>
                      </div>
                      <p className="text-gray-700">{advice}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 주의사항 */}
            {analysisResult.friendly_analysis?.warnings && analysisResult.friendly_analysis.warnings.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-yellow-800 mb-4">⚠️ 주의사항</h3>
                <div className="space-y-2">
                  {analysisResult.friendly_analysis.warnings.map((warning, index) => (
                    <p key={index} className="text-yellow-700 text-sm">
                      {warning}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* 간단한 지표 */}
            {analysisResult.friendly_analysis?.simple_indicators && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 주요 지표</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(analysisResult.friendly_analysis.simple_indicators).map(([key, indicator]) => (
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
              <p>• <strong>분석 결과</strong>: 기술적 지표와 매칭 여부를 확인할 수 있습니다</p>
            </div>
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
              className="flex flex-col items-center py-2 bg-blue-600 rounded"
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
              onClick={() => {
                if (user) {
                  logout();
                  router.push('/login');
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
        </div>
      </div>
    </>
  );
}
