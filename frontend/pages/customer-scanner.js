import { useState, useEffect } from 'react';
import Head from 'next/head';

export default function CustomerScanner({ initialData }) {
  const [scanResults, setScanResults] = useState(initialData || []);
  const [loading, setLoading] = useState(false);
  const [selectedMarket, setSelectedMarket] = useState('전체');
  const [sortBy, setSortBy] = useState('score');
  const [filterBy, setFilterBy] = useState('전체종목');

  // 최신 스캔 결과 가져오기
  const fetchScanResults = async () => {
    setLoading(true);
    try {
      const response = await fetch('/backend/latest-scan');
      const data = await response.json();
      console.log('최신 스캔 결과:', data);
      
      if (data.ok && data.data) {
        setScanResults(data.data.rank || []);
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

  useEffect(() => {
    // 초기 데이터가 없으면 API 호출
    if (!initialData || initialData.length === 0) {
      fetchScanResults();
    }
    
    // 5분마다 자동 새로고침
    const interval = setInterval(fetchScanResults, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, [initialData]);

  // 시장별 필터링
  const filteredResults = scanResults.filter(item => {
    if (selectedMarket === '전체') return true;
    if (selectedMarket === '코스피') return item.market === 'KOSPI';
    if (selectedMarket === '코스닥') return item.market === 'KOSDAQ';
    return true;
  });

  // 정렬
  const sortedResults = [...filteredResults].sort((a, b) => {
    if (sortBy === 'score') return (b.score || 0) - (a.score || 0);
    if (sortBy === 'price') return (b.details?.close || 0) - (a.details?.close || 0);
    if (sortBy === 'change') return (b.score || 0) - (a.score || 0); // 점수로 정렬
    return 0;
  });

  // 별점 렌더링
  const renderStars = (score) => {
    const stars = [];
    const starCount = Math.min(5, Math.max(1, Math.floor((score || 0) / 2)));
    
    for (let i = 0; i < 5; i++) {
      stars.push(
        <span key={i} className={`text-lg ${i < starCount ? 'text-yellow-400' : 'text-gray-300'}`}>
          ★
        </span>
      );
    }
    return stars;
  };

  // 수익률 색상
  const getReturnColor = (returnRate) => {
    if (returnRate > 0) return 'text-red-500';
    if (returnRate < 0) return 'text-blue-500';
    return 'text-gray-500';
  };

  return (
    <>
      <Head>
        <title>스타매니지먼트 - 주식 스캐너</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* 상단 바 */}
        <div className="bg-white shadow-sm">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center">
              <span className="text-lg font-semibold text-gray-800">스타매니지먼트</span>
            </div>
            <div className="flex items-center space-x-3">
              <button className="p-2 text-gray-600">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5-5-5h5v-5a7.5 7.5 0 1 0-15 0v5h5l-5 5-5-5h5v-5a7.5 7.5 0 1 1 15 0v5z" />
                </svg>
              </button>
              <button className="p-2 text-gray-600">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                </svg>
              </button>
              <button className="p-2 text-gray-600">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">시장의 주도주 정보</h2>
              <p className="text-sm opacity-90">PRIME CLUB에서 확인!</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full"></div>
              </div>
            </div>
          </div>
        </div>

        {/* 시장 선택 탭 */}
        <div className="bg-white border-b">
          <div className="flex">
            {['전체', '코스피', '코스닥'].map((market) => (
              <button
                key={market}
                onClick={() => setSelectedMarket(market)}
                className={`flex-1 py-3 px-4 text-center font-medium ${
                  selectedMarket === market
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {market}
              </button>
            ))}
          </div>
        </div>

        {/* 필터 및 정렬 */}
        <div className="bg-white p-4 border-b">
          <div className="flex space-x-3">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="flex-1 p-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="score">스타레이팅종합</option>
              <option value="price">현재가순</option>
              <option value="change">변동률순</option>
            </select>
            <select
              value={filterBy}
              onChange={(e) => setFilterBy(e.target.value)}
              className="flex-1 p-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="전체종목">전체종목</option>
              <option value="관심종목">관심종목</option>
              <option value="보유종목">보유종목</option>
            </select>
          </div>
        </div>

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
                    <span className="text-gray-500">상태:</span>
                    <span className="ml-2 text-gray-800">스캔완료</span>
                  </div>
                </div>

                {/* 액션 버튼 */}
                <div className="flex items-center justify-between pt-3 border-t">
                  <div className="flex space-x-4 text-sm">
                    <button className="text-blue-500 hover:text-blue-700">관심등록</button>
                    <button className="text-blue-500 hover:text-blue-700">차트</button>
                    <button className="text-blue-500 hover:text-blue-700">기업정보</button>
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
            <button className="flex flex-col items-center py-2">
              <svg className="w-5 h-5 mb-1" fill="currentColor" viewBox="0 0 24 24">
                <path d="M3 12h2l3-9 3 9h2l-3 9-3-9z"/>
              </svg>
              <span className="text-xs">메뉴</span>
            </button>
            <button className="flex flex-col items-center py-2">
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="text-xs">홈</span>
            </button>
            <button className="flex flex-col items-center py-2">
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span className="text-xs">통합검색</span>
            </button>
            <button className="flex flex-col items-center py-2">
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              <span className="text-xs">관심종목</span>
            </button>
            <button className="flex flex-col items-center py-2">
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span className="text-xs">주식현재가</span>
            </button>
            <button className="flex flex-col items-center py-2">
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
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
    // 서버에서 백엔드 API 호출
    const response = await fetch('http://localhost:8010/latest-scan');
    const data = await response.json();
    
    if (data.ok && data.data) {
      return {
        props: {
          initialData: data.data.rank || []
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
