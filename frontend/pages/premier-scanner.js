import { useState, useEffect } from 'react';
import Head from 'next/head';

export default function PremierScanner({ initialData }) {
  const [scanResults, setScanResults] = useState(initialData || []);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState('score');
  const [analysisInput, setAnalysisInput] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  // 최신 스캔 결과 가져오기
  const fetchScanResults = async () => {
    setLoading(true);
    try {
      const base = (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_BACKEND_URL) || 'https://sohntech.ai.kr/backend';
      const response = await fetch(`${base}/latest-scan`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.ok && data.data) {
        setScanResults(data.data.items || []);
      } else {
        console.error('스캔 결과 조회 실패:', data.error);
        setScanResults([]);
      }
    } catch (error) {
      console.error('스캔 결과 조회 실패:', error);
      setScanResults([]);
    } finally {
      setLoading(false);
    }
  };

  // 단일 종목 분석
  const analyzeStock = async () => {
    if (!analysisInput.trim()) return;
    
    setAnalyzing(true);
    setAnalysisResult(null);
    
    try {
      const base = (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_BACKEND_URL) || 'https://sohntech.ai.kr/backend';
      const response = await fetch(`${base}/analyze?name_or_code=${encodeURIComponent(analysisInput.trim())}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.ok && data.item) {
        setAnalysisResult(data.item);
      } else {
        setAnalysisResult({ error: data.error || '분석 실패' });
      }
    } catch (error) {
      console.error('분석 실패:', error);
      setAnalysisResult({ error: '분석 중 오류가 발생했습니다.' });
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    // SSR 데이터가 있으면 클라이언트 API 호출 생략
    if (initialData && initialData.length > 0) {
      console.log('SSR 데이터 사용, 클라이언트 API 호출 생략');
      setScanResults(initialData);
      return;
    }
    
    // 초기 데이터가 없으면 API 호출
    if (!initialData || initialData.length === 0) {
      fetchScanResults();
    }
  }, [initialData]);

  // 필터링 제거 - 모든 결과 표시
  const filteredResults = scanResults.filter(item => {
    if (!item) return false;
    return true;
  });

  // 정렬
  const sortedResults = [...filteredResults].sort((a, b) => {
    if (sortBy === 'score') return (b.score || 0) - (a.score || 0);
    if (sortBy === 'name') return (a.name || '').localeCompare(b.name || '');
    return 0;
  });

  // 별점 렌더링
  const renderStars = (score) => {
    const starCount = Math.min(5, Math.max(1, Math.floor((score || 0) / 2)));
    return Array.from({ length: 5 }, (_, i) => (
      <span key={i} className={`text-lg ${i < starCount ? 'text-yellow-400' : 'text-gray-300'}`}>
        ★
      </span>
    ));
  };

  return (
    <>
      <Head>
        <title>스톡인사이트 - 프리미어 클럽</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* 상단 바 */}
        <div className="bg-white shadow-sm">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center">
              <span className="text-lg font-semibold text-gray-800">프리미어 클럽</span>
              <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">VIP</span>
            </div>
            <button 
              onClick={fetchScanResults}
              className="p-2 text-gray-600 hover:text-gray-800"
            >
              🔄
            </button>
          </div>
        </div>

        {/* 프리미어 클럽 배너 */}
        <div className="bg-gradient-to-r from-yellow-500 to-orange-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">프리미어 클럽 전용</h2>
              <p className="text-sm opacity-90">고급 분석 도구와 개인화된 서비스</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                <span className="text-3xl">👑</span>
              </div>
            </div>
          </div>
        </div>

        {/* 단일 종목 분석 섹션 */}
        <div className="bg-white p-4 border-b">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">종목 분석</h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={analysisInput}
              onChange={(e) => setAnalysisInput(e.target.value)}
              placeholder="종목명 또는 종목코드 입력 (예: 삼성전자, 005930)"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyPress={(e) => e.key === 'Enter' && analyzeStock()}
            />
            <button
              onClick={analyzeStock}
              disabled={analyzing || !analysisInput.trim()}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {analyzing ? '분석중...' : '분석'}
            </button>
          </div>
        </div>

        {/* 분석 결과 */}
        {analysisResult && (
          <div className="bg-white p-4 border-b">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">분석 결과</h3>
            {analysisResult.error ? (
              <div className="text-red-600 bg-red-50 p-3 rounded-lg">
                {analysisResult.error}
              </div>
            ) : (
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="font-semibold text-gray-800">{analysisResult.name}</h4>
                    <p className="text-sm text-gray-500">({analysisResult.ticker})</p>
                    <div className="flex items-center mt-1">
                      {renderStars(analysisResult.score)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-gray-800">
                      {analysisResult.score || '-'}
                    </div>
                    <div className="text-sm text-gray-500">
                      {analysisResult.score_label || '-'}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
                  <div>
                    <span className="text-gray-500">전략:</span>
                    <span className="ml-2 text-gray-800">{analysisResult.strategy || '-'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">매칭:</span>
                    <span className="ml-2 text-gray-800">{analysisResult.match ? '매칭' : '비매칭'}</span>
                  </div>
                </div>

                {/* 기술적 지표 */}
                {analysisResult.indicators && (
                  <div className="mt-4">
                    <h5 className="font-semibold text-gray-700 mb-2">기술적 지표</h5>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-gray-500">RSI:</span>
                        <span className="ml-2 text-gray-800">{analysisResult.indicators.RSI?.toFixed(2) || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">MACD:</span>
                        <span className="ml-2 text-gray-800">{analysisResult.indicators.MACD_OSC?.toFixed(2) || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">TEMA:</span>
                        <span className="ml-2 text-gray-800">{analysisResult.indicators.TEMA?.toFixed(0) || '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">DEMA:</span>
                        <span className="ml-2 text-gray-800">{analysisResult.indicators.DEMA?.toFixed(0) || '-'}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}


        {/* 스캔 결과 목록 */}
        <div className="p-4 space-y-3">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-gray-500 mt-2">스캔 결과를 불러오는 중...</p>
            </div>
          ) : sortedResults.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">스캔 결과가 없습니다.</p>
              <p className="text-sm text-gray-400 mt-2">자동 스캔 결과를 기다리는 중...</p>
            </div>
          ) : (
            sortedResults.map((item) => (
              <div key={item.ticker} className="bg-white rounded-lg shadow-sm border p-4">
                {/* 종목 정보 */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <h3 className="font-semibold text-gray-800">{item.name}</h3>
                      <span className="text-xs text-gray-500">({item.ticker})</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      {renderStars(item.score)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-gray-800">
                      {item.score || '-'}
                    </div>
                    <div className="text-sm text-gray-500">
                      {item.score_label || '-'}
                    </div>
                  </div>
                </div>

                {/* 스캔 정보 */}
                <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
                  <div>
                    <span className="text-gray-500">종목코드:</span>
                    <span className="ml-2 text-gray-800">{item.ticker || '-'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">평가:</span>
                    <span className="ml-2 text-gray-800">{item.score_label || '-'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">점수:</span>
                    <span className="ml-2 text-gray-800">{item.score || '-'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">시장:</span>
                    <span className="ml-2 text-gray-800">{item.ticker && item.ticker.length === 6 ? (item.ticker.startsWith('0') ? '코스닥' : '코스피') : '-'}</span>
                  </div>
                </div>

                {/* 액션 버튼 */}
                <div className="flex items-center justify-between pt-3 border-t">
                  <div className="flex space-x-4 text-sm">
                    <button 
                      onClick={() => {
                        setAnalysisInput(item.name);
                        setTimeout(() => analyzeStock(), 100);
                      }}
                      className="text-blue-500 hover:text-blue-700"
                    >
                      상세분석
                    </button>
                    <button className="text-blue-500 hover:text-blue-700">투자등록</button>
                    <button className="text-blue-500 hover:text-blue-700">차트</button>
                  </div>
                  <button className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600">
                    매수
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* 하단 네비게이션 */}
        <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
          <div className="flex items-center justify-around py-2">
            {['메뉴', '홈', '통합검색', '관심종목', '주식현재가', '주식주문'].map((item) => (
              <button key={item} className="flex flex-col items-center py-2">
                <span className="text-xs">{item}</span>
              </button>
            ))}
          </div>
        </div>

        {/* 하단 네비게이션 공간 확보 */}
        <div className="h-20"></div>
      </div>
    </>
  );
}

export async function getServerSideProps() {
  try {
    const base = 'http://localhost:8000';
    const response = await fetch(`${base}/latest-scan`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.ok && data.data) {
      return {
        props: {
          initialData: data.data.items || []
        }
      };
    } else {
      return {
        props: {
          initialData: []
        }
      };
    }
  } catch (error) {
    console.error('SSR 데이터 로드 실패:', error);
    return {
      props: {
        initialData: []
      }
    };
  }
}
