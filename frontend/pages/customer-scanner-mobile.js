import { useState, useEffect } from 'react';
import Head from 'next/head';

export default function CustomerScannerMobile({ initialData }) {
  const [scanResults, setScanResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState('score');
  const [error, setError] = useState(null);

  // 안전한 API 호출 함수
  const fetchScanResults = async () => {
    if (loading) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const base = 'https://sohntech.ai.kr/backend';
      const response = await fetch(`${base}/latest-scan`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();

      if (data && data.ok && data.data) {
        const items = data.data.items || data.data.rank || [];
        setScanResults(items);
      } else {
        setScanResults([]);
      }
    } catch (err) {
      console.error('API 호출 오류:', err);
      setError('데이터를 불러오는 중 오류가 발생했습니다.');
      setScanResults([]);
    } finally {
      setLoading(false);
    }
  };

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    if (initialData && initialData.length > 0) {
      setScanResults(initialData);
    } else {
      fetchScanResults();
    }
  }, []);

  // 필터링 제거 - 모든 결과 표시
  const filteredResults = scanResults.filter(item => {
    if (!item) return false;
    return true;
  });

  // 정렬
  const sortedResults = [...filteredResults].sort((a, b) => {
    if (!a || !b) return 0;
    if (sortBy === 'score') return (b.score || 0) - (a.score || 0);
    if (sortBy === 'change') return (b.change_rate || 0) - (a.change_rate || 0);
    return 0;
  });

  // 별점 렌더링
  const renderStars = (score) => {
    if (!score) return null;
    const stars = [];
    const starCount = Math.min(5, Math.max(1, Math.floor(score / 2)));
    
    for (let i = 0; i < 5; i++) {
      stars.push(
        <span key={i} className={`text-lg ${i < starCount ? 'text-yellow-400' : 'text-gray-300'}`}>
          ★
        </span>
      );
    }
    return stars;
  };


  const handleSortChange = (sort) => {
    try {
      setSortBy(sort);
    } catch (err) {
      console.error('Sort change error:', err);
    }
  };

  return (
    <>
      <Head>
        <title>스톡인사이트 - 주식 스캐너</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* 상단 바 */}
        <div className="bg-white shadow-sm">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center">
              <span className="text-lg font-semibold text-gray-800">스톡인사이트</span>
            </div>
            <div className="flex items-center space-x-3">
              <button 
                className="p-2 text-gray-600"
                onClick={() => window.location.reload()}
              >
                🔄
              </button>
            </div>
          </div>
        </div>

        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">시장의 주도주 정보</h2>
              <p className="text-sm opacity-90">프리미어 클럽에서 확인!</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                <div className="relative flex items-center justify-center">
                  <span className="text-3xl">🔮</span>
                  <span className="absolute text-lg top-0 left-2 text-green-500">📈</span>
                </div>
              </div>
            </div>
          </div>
        </div>


        {/* 필터 및 정렬 */}
        <div className="bg-white p-4 border-b">
          <div className="flex space-x-3">
            <select
              value={sortBy}
              onChange={(e) => handleSortChange(e.target.value)}
              className="flex-1 p-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="score">스타레이팅종합</option>
              <option value="change">변동률순</option>
            </select>
          </div>
        </div>

        {/* 오류 메시지 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded p-4 m-4">
            <p className="text-red-600 text-sm">{error}</p>
            <button 
              onClick={fetchScanResults}
              className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-sm"
            >
              다시 시도
            </button>
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
              <button 
                onClick={fetchScanResults}
                className="mt-2 px-4 py-2 bg-blue-600 text-white rounded"
              >
                새로고침
              </button>
            </div>
          ) : (
            sortedResults.map((item, index) => {
              if (!item) return null;
              
              return (
                <div key={item.ticker || index} className="bg-white rounded-lg shadow-sm border p-4">
                  {/* 종목 정보 */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h3 className="font-semibold text-gray-800">{item.name || 'N/A'}</h3>
                        <span className="text-xs text-gray-500">({item.ticker || 'N/A'})</span>
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
                      <button className="text-blue-500">투자등록</button>
                      <button className="text-blue-500">차트</button>
                      <button className="text-blue-500">기업정보</button>
                    </div>
                    <button 
                      className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium"
                      style={{ touchAction: 'manipulation' }}
                    >
                      매수
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* 하단 네비게이션 */}
        <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
          <div className="flex items-center justify-around py-2">
            <button className="flex flex-col items-center py-2">
              <span className="text-xs">메뉴</span>
            </button>
            <button className="flex flex-col items-center py-2">
              <span className="text-xs">홈</span>
            </button>
            <button className="flex flex-col items-center py-2">
              <span className="text-xs">통합검색</span>
            </button>
            <button className="flex flex-col items-center py-2">
              <span className="text-xs">나의투자종목</span>
            </button>
            <button className="flex flex-col items-center py-2">
              <span className="text-xs">주식현재가</span>
            </button>
            <button className="flex flex-col items-center py-2">
              <span className="text-xs">주식주문</span>
            </button>
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
    const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8010';
    const response = await fetch(`${base}/latest-scan`);
    const data = await response.json();
    
    if (data && data.ok && data.data && data.data.rank) {
      return {
        props: {
          initialData: data.data.rank
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
