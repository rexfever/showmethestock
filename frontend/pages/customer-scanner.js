import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';

export default function CustomerScanner({ initialData, initialScanFile }) {
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated, logout } = useAuth();
  
  const [scanResults, setScanResults] = useState(initialData || []);
  const [scanFile, setScanFile] = useState(initialScanFile || '');
  const [scanDate, setScanDate] = useState('');
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('score');
  const [filterBy, setFilterBy] = useState('전체종목');
  const [mounted, setMounted] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [hasSSRData, setHasSSRData] = useState(initialData && initialData.length > 0);
  const [showGuide, setShowGuide] = useState(false);
  const [showUpcomingFeatures, setShowUpcomingFeatures] = useState(false);

  // 인증 체크 (임시 비활성화 - 인증 구현 전까지)
  // useEffect(() => {
  //   if (!authLoading && !isAuthenticated()) {
  //     router.push('/login');
  //   }
  // }, [authLoading, isAuthenticated, router]);

  // 사용 가능한 스캔 날짜 목록 가져오기
  const fetchAvailableDates = useCallback(async () => {
    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';
      
      const response = await fetch(`${base}/available-scan-dates`);
      const data = await response.json();
      
      if (data.ok && data.dates) {
        setAvailableDates(data.dates);
        // 기본값을 최신 날짜로 설정
        if (data.dates.length > 0 && !selectedDate) {
          setSelectedDate(data.dates[0]);
        }
      }
    } catch (error) {
      console.error('사용 가능한 날짜 조회 실패:', error);
    }
  }, [selectedDate]);

  // 특정 날짜의 스캔 결과 가져오기
  const fetchScanByDate = useCallback(async (date) => {
    if (!date) return;
    
    setLoading(true);
    setError(null);
    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';
      
      const response = await fetch(`${base}/scan-by-date/${date}`);
      const data = await response.json();
      
      if (data.ok && data.data) {
        const items = data.data.items || data.data.rank || [];
        setScanResults(items);
        setScanFile(data.file || '');
        setScanDate(data.data.scan_date || '');
        setError(null);
      } else {
        const errorMsg = data.error || '스캔 결과 조회 실패';
        setError(errorMsg);
        setScanResults([]);
      }
    } catch (error) {
      console.error('스캔 결과 조회 실패:', error);
      setError('스캔 결과 조회 중 오류가 발생했습니다.');
      setScanResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 최신 스캔 결과 가져오기
  const fetchScanResults = useCallback(async () => {
    // 모바일에서 네트워크 상태 확인
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      setError('네트워크 연결을 확인해주세요.');
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';
      console.log('API 호출 URL:', `${base}/latest-scan`);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10초 타임아웃
      
      const response = await fetch(`${base}/latest-scan`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        mode: 'cors',
        cache: 'no-cache',
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('최신 스캔 결과:', data);
      console.log('data.file 값:', data.file);
      console.log('data.ok 값:', data.ok);
      console.log('data.data 값:', data.data);
      
      if (data.ok && data.data) {
        // items 또는 rank 필드 처리
        const items = data.data.items || data.data.rank || [];
        console.log('설정할 scanFile 값:', data.file);
        setScanResults(items);
        setScanFile(data.file || '');
        setScanDate(data.data.scan_date || '');
        setError(null);
      } else {
        const errorMsg = data.error || '스캔 결과 조회 실패';
        console.error('스캔 결과 조회 실패:', errorMsg);
        setError(errorMsg);
        setScanResults([]);
      }
    } catch (error) {
      console.error('스캔 결과 조회 실패:', error);
      if (error.name === 'AbortError') {
        setError('요청 시간이 초과되었습니다. 다시 시도해주세요.');
      } else if (error.message.includes('Failed to fetch')) {
        setError('네트워크 연결을 확인해주세요.');
      } else {
        setError(`데이터 불러오는 중 오류가 발생했습니다: ${error.message}`);
      }
      setScanResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setMounted(true);
    
    // 모바일 감지
    if (typeof window !== 'undefined') {
      const userAgent = navigator.userAgent;
      const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
      setIsMobile(isMobileDevice);
    }
    
    // 사용 가능한 날짜 목록 가져오기
    fetchAvailableDates();
    
    // SSR 데이터가 있으면 클라이언트 API 호출 완전 비활성화
    if (hasSSRData) {
      console.log('SSR 데이터 사용, 클라이언트 API 호출 생략');
      console.log('SSR scanFile:', initialScanFile);
      setScanResults(initialData);
      setScanFile(initialScanFile || '');
      setError(null);
      setLoading(false);
      return;
    }
    
    // 초기 데이터가 없으면 API 호출
    if (!hasSSRData) {
      fetchScanResults();
    }
    
    // 5분마다 자동 새로고침 (SSR 데이터가 있을 때는 비활성화)
    const interval = setInterval(() => {
      if (!hasSSRData) {
        fetchScanResults();
      }
    }, 5 * 60 * 1000);
    
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [hasSSRData, initialData]);

  // 필터링 (시장별 필터 제거)
  const filteredResults = scanResults.filter(item => {
    if (!item) return false;
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

  // 상태 정보 표시 (일반인 친화적 용어)
  const getStatusAndInterest = (item) => {
    const strategy = item.strategy;
    if (!strategy) return '-';
    
    // 상태 관련 키워드를 일반인이 이해하기 쉬운 용어로 변환
    if (strategy.includes('거래확대')) return '관심증가';
    if (strategy.includes('상승추세 정착')) return '상승중(안정)';
    if (strategy.includes('상승추세')) return '상승중';
    if (strategy.includes('하락추세')) return '하락중';
    if (strategy.includes('횡보')) return '횡보';
    if (strategy.includes('양전환')) return '반등';
    if (strategy.includes('음전환')) return '하락전환';
    
    // 기본적으로 전략의 첫 번째 부분을 상태로 표시
    return strategy.split(' / ')[0] || strategy;
  };

  // 거래대금 기반 시장관심도 표시
  const getSimpleStrategy = (item) => {
    if (!item.volume || !item.current_price) return '-';
    
    const tradingAmount = item.volume * item.current_price / 100000000; // 억원 단위
    
    if (tradingAmount > 1000) return '매우높음';      // 1,000억원 이상
    else if (tradingAmount > 500) return '높음';      // 500억원 이상
    else if (tradingAmount > 100) return '보통';      // 100억원 이상
    else return '낮음';                               // 100억원 미만
  };

  // 매매전략 정보 표시 (백엔드에서 이미 사용자 친화적으로 변환됨)
  const getStrategyInfo = (item) => {
    const strategy = item.strategy;
    if (!strategy) return '-';
    
    // 백엔드에서 이미 사용자 친화적 용어로 변환되어 있으므로 그대로 사용
    // 상승신호, 상승시작, 관심증가, 상승추세정착, 관심
    return strategy.split(' / ')[0] || strategy;
  };

  // 전략기반 액션 생성 (관리자용과 동일한 로직)
  const getStrategyActions = (strategy) => {
    if (!strategy) return '';
    const labels = String(strategy)
      .split('/')
      .map(s => s.trim())
      .map(s => s.replace(/\s+/g, '')); // 공백 제거해 라벨 표준화
    const actions = [];
    
    // 백엔드의 새로운 사용자 친화적 전략 용어와 매칭
    if (labels.includes('상승신호')) {
      actions.push('돌파하면 매수, 단기 이동평균 아래로 떨어지면 정리');
    }
    if (labels.includes('상승시작')) {
      actions.push('오늘 최고가 돌파 시 매수, 상승세가 꺾이면 비중 줄이기');
    }
    if (labels.includes('관심증가')) {
      actions.push('거래량이 5일평균↑이면 비중 늘리기, 다음 날 거래량 줄면 일부 청산');
    }
    if (labels.includes('상승추세정착')) {
      actions.push('추세 지속 시 비중 유지, 추세 전환 시 정리');
    }
    if (labels.includes('관심') || actions.length === 0) {
      actions.push('아직 기다리기 (신호 2개 이상 뜨면 매수)');
    }
    
    // 기존 용어도 호환성을 위해 유지
    if (labels.includes('골든크로스형성')) {
      actions.push('돌파하면 매수, 단기 이동평균 아래로 떨어지면 정리');
    }
    if (labels.includes('모멘텀양전환')) {
      actions.push('오늘 최고가 돌파 시 매수, 상승세가 꺾이면 비중 줄이기');
    }
    if (labels.includes('거래확대')) {
      actions.push('거래량이 5일평균↑이면 비중 늘리기, 다음 날 거래량 줄면 일부 청산');
    }
    if (labels.includes('관망')) {
      actions.push('아직 기다리기 (신호 2개 이상 뜨면 매수)');
    }
    
    return actions.join(' · ');
  };

  // 평가 라벨 변환 함수 (관리자 화면과 동일)
  const getLabelMeta = (label) => {
    const v = String(label || '').trim();
    if (v === '강한 매수') {
      return {
        text: '매수 후보(강)',
        hint: '신호 충족도 높음. 오늘 최고가 돌파 시 분할 매수 고려, 단기 이동평균 하회 시 정리.',
        cls: 'bg-emerald-100 text-emerald-800',
      };
    }
    if (v === '매수 후보') {
      return {
        text: '매수 후보',
        hint: '신호 충족도 양호. 오늘 최고가 돌파 시 매수 고려, 추세 전환 시 정리.',
        cls: 'bg-blue-100 text-blue-800',
      };
    }
    if (v === '관심') {
      return {
        text: '관심',
        hint: '신호 일부 충족. 거래량 증가·상승세 확인 후 매수 판단.',
        cls: 'bg-amber-100 text-amber-800',
      };
    }
    if (v === '관망') {
      return {
        text: '관망',
        hint: '신호 부족. 추가 신호 대기 후 매수 판단.',
        cls: 'bg-yellow-100 text-yellow-800',
      };
    }
    return {
      text: '제외',
      hint: '조건 미충족. 대기.',
      cls: 'bg-slate-100 text-slate-700',
    };
  };

  // mounted 체크 제거 - SSR 데이터가 있으므로 바로 렌더링

  return (
    <>
      <Head>
        <title>스톡인사이트 - 주식 스캐너</title>
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
              {user ? (
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">
                    {user.name}님 ({user.provider})
                  </span>
                  <button 
                    onClick={() => {
                      logout();
                      router.push('/login');
                    }}
                    className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700 border border-gray-300 rounded"
                  >
                    로그아웃
                  </button>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-500">게스트 사용자</span>
                  <button 
                    onClick={() => router.push('/login')}
                    className="px-2 py-1 text-xs text-blue-600 hover:text-blue-700 border border-blue-300 rounded"
                  >
                    로그인
                  </button>
                </div>
              )}
              <button 
                onClick={() => alert('준비중입니다.')}
                className="px-3 py-1 bg-gradient-to-r from-yellow-400 to-yellow-500 text-gray-800 text-xs font-semibold rounded-full shadow-sm hover:shadow-md transition-all duration-200"
              >
                👑 프리미어
              </button>
              <button 
                className="p-2 text-gray-600 hover:text-gray-800"
                onClick={() => alert('준비중입니다.')}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
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
              <p className="text-sm opacity-90">AI가 찾아낸 주도주를 지금 확인하세요!</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                <span className="text-3xl">💰</span>
              </div>
            </div>
          </div>
        </div>


        {/* 투자 활용법 가이드 */}
        <div className="bg-white border-b">
          <button
            onClick={() => setShowGuide(!showGuide)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center space-x-2">
              <span className="text-lg">📊</span>
              <span className="font-medium text-gray-800">투자 활용법</span>
            </div>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform ${showGuide ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {showGuide && (
            <div className="px-4 pb-4 border-t bg-gray-50">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-xl">🔍</span>
                    <h3 className="font-semibold text-gray-800">선별 기준</h3>
                  </div>
                  <p className="text-sm text-gray-600">상승 신호, 과매도 탈출, 거래량 급증 등</p>
                  <p className="text-xs text-gray-500 mt-1">AI가 여러 조건을 종합해서 선별</p>
                  <p className="text-xs text-blue-600 mt-1 font-medium">※ 여러 조건 만족 = 강력한 신호 (우선 검토)</p>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-xl">⚡</span>
                    <h3 className="font-semibold text-gray-800">투자 방법</h3>
                  </div>
                  <p className="text-sm text-gray-600">3-10일 정도 보유하는 단기 투자</p>
                  <p className="text-xs text-gray-500 mt-1">참고 수익률: 3-5% (개인 판단 필요)</p>
                  <p className="text-xs text-red-500 mt-1 font-medium">※ 실제 매매는 증권사에서 진행하세요</p>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-xl">📈</span>
                    <h3 className="font-semibold text-gray-800">투자 주의사항</h3>
                  </div>
                  <p className="text-sm text-gray-600">차트 분석 기반, 손실 시 빠른 매도</p>
                  <p className="text-xs text-gray-500 mt-1">투자 결정은 신중히 하시기 바랍니다.</p>
                </div>
              </div>
              
              {/* 상세 매매 전략 설명 */}
              <div className="mt-6 bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-3">📋 상세 매매 전략</h4>
                <div className="mb-4 p-3 bg-yellow-50 border-l-4 border-yellow-400 rounded">
                  <p className="text-sm text-yellow-800">
                    <strong>💡 점수 시스템 해석:</strong> 8개 조건을 종합해서 점수를 부여합니다. (만점 15점)
                    <br/>• <strong>10점 이상</strong>: 강한 매수 (우선 검토)
                    <br/>• <strong>8-9점</strong>: 매수 후보/관심 (신중한 검토)
                    <br/>• <strong>6-7점</strong>: 관망 (추가 분석 필요)
                    <br/>• <strong>6점 미만</strong>: 제외 (투자 부적합)
                  </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <h5 className="font-medium text-blue-700 mb-2">🎯 매매 방식</h5>
                    <ul className="space-y-1 text-blue-600">
                      <li>• <strong>단기 투자</strong>: 3-10일 보유 (추천)</li>
                      <li>• <strong>단타 매매</strong>: 개인 판단 (고위험)</li>
                      <li>• <strong>장기 투자</strong>: 개인 판단 (별도 분석 필요)</li>
                    </ul>
                  </div>
                  <div>
                    <h5 className="font-medium text-blue-700 mb-2">💰 수익률 목표</h5>
                    <ul className="space-y-1 text-blue-600">
                      <li>• <strong>단기</strong>: 3-5% (추천 수익률)</li>
                      <li>• <strong>단타</strong>: 개인 판단 (고위험)</li>
                      <li>• <strong>장기</strong>: 개인 판단 (별도 분석 필요)</li>
                    </ul>
                  </div>
                  <div>
                    <h5 className="font-medium text-blue-700 mb-2">🛡️ 리스크 관리</h5>
                    <ul className="space-y-1 text-blue-600">
                      <li>• <strong>손절매</strong>: -3~5% 도달 시</li>
                      <li>• <strong>분할 매수</strong>: 2-3회에 나누어</li>
                      <li>• <strong>포지션 크기</strong>: 자금의 10-20%</li>
                    </ul>
                  </div>
                  <div>
                    <h5 className="font-medium text-blue-700 mb-2">📊 진입/청산 기준</h5>
                    <ul className="space-y-1 text-blue-600">
                      <li>• <strong>진입</strong>: 스캔 결과 + 추가 분석</li>
                      <li>• <strong>청산</strong>: 목표가 도달 또는 손절</li>
                      <li>• <strong>관리</strong>: 일일 모니터링 필수</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 준비중인 기능 안내 */}
        <div className="bg-white border-b">
          <button
            onClick={() => setShowUpcomingFeatures(!showUpcomingFeatures)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center space-x-2">
              <span className="text-lg">🚧</span>
              <span className="font-medium text-gray-800">준비중인 기능</span>
            </div>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform ${showUpcomingFeatures ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {showUpcomingFeatures && (
            <div className="px-4 pb-4 border-t bg-gray-50">
              <div className="bg-orange-50 rounded-lg p-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <h5 className="font-medium text-orange-700 mb-2">📱 알림 서비스</h5>
                    <ul className="space-y-1 text-orange-600">
                      <li>• <strong>카카오톡 알림톡</strong>: 스캔 결과 자동 알림</li>
                      <li>• <strong>푸시 알림</strong>: 모바일 앱 알림</li>
                      <li>• <strong>이메일 알림</strong>: 상세 분석 리포트</li>
                    </ul>
                  </div>
                  <div>
                    <h5 className="font-medium text-orange-700 mb-2">💼 관심종목 관리</h5>
                    <ul className="space-y-1 text-orange-600">
                      <li>• <strong>관심종목 등록</strong>: 스캔 결과에서 바로 등록</li>
                      <li>• <strong>관심종목 목록</strong>: 등록한 종목 관리</li>
                      <li>• <strong>알림 설정</strong>: 관심종목 변동 알림</li>
                    </ul>
                  </div>
                  <div>
                    <h5 className="font-medium text-orange-700 mb-2">📊 고급 분석</h5>
                    <ul className="space-y-1 text-orange-600">
                      <li>• <strong>상세 차트</strong>: 기술적 분석 도구</li>
                      <li>• <strong>기업정보</strong>: 재무제표 및 뉴스</li>
                      <li>• <strong>통합검색</strong>: 종목 검색 기능</li>
                    </ul>
                  </div>
                </div>
                <div className="mt-4 p-3 bg-orange-100 rounded-lg">
                  <p className="text-sm text-orange-700">
                    <strong>💡 안내:</strong> 모든 기능은 순차적으로 출시될 예정입니다. 
                    먼저 기본 스캔 서비스를 이용해보시고, 추가 기능 출시 소식을 기다려주세요!
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 필터 및 정렬 */}
        <div className="bg-white p-4 border-b">
          <div className="flex space-x-3">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="flex-1 p-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="score">점수순</option>
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

        {/* 통합된 스캔 정보 */}
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 mx-4 mb-4">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-3">
              <div className="text-blue-800">
                <span className="font-medium">📅 스캔 날짜:</span>
              </div>
              <select 
                value={selectedDate} 
                onChange={(e) => {
                  setSelectedDate(e.target.value);
                  fetchScanByDate(e.target.value);
                }}
                className="px-2 py-1 border border-blue-300 rounded text-sm bg-white"
              >
                {availableDates.map(date => (
                  <option key={date} value={date}>
                    {date.slice(0,4)}-{date.slice(4,6)}-{date.slice(6,8)}
                  </option>
                ))}
              </select>
            </div>
            <div className="text-blue-600">
              <span className="font-medium">매칭종목:</span> {scanResults.length}개
            </div>
          </div>
        </div>

        {/* 스캔 결과 목록 */}
        <div className="p-4 space-y-3">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-gray-500 mt-2">스캔 결과를 불러오는 중...</p>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <div className="text-red-500 text-lg mb-2">⚠️</div>
              <p className="text-red-600 font-medium">{error}</p>
              <button 
                onClick={() => {
                  setHasSSRData(false);
                  fetchScanResults();
                }}
                className="mt-3 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                다시 시도
              </button>
            </div>
          ) : (
            <div>
              {/* 스캔 결과가 없을 때 메시지 */}
              {sortedResults.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">선택한 날짜에 스캔 결과가 없습니다.</p>
                  <p className="text-sm text-gray-400 mt-2">
                    다른 날짜를 선택하거나 최신 스캔을 확인해보세요.
                  </p>
                </div>
              ) : (
                sortedResults.map((item) => (
              <div key={item.ticker} className="bg-white rounded-lg shadow-sm border p-4">
              {/* 상단: 종목명 + 종목코드 + 시장 + 현재가 + 변동률 */}
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="font-semibold text-gray-800">
                    {item.name}
                    <span className="text-xs text-gray-500 ml-2">({item.ticker})</span>
                    <span className="text-xs text-blue-600 ml-2">
                      {item.market || (item.ticker && item.ticker.length === 6 ? 
                        (item.ticker.startsWith('0') ? '코스닥' : '코스피') : '')}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    {item.current_price > 0 ? `${item.current_price.toLocaleString()}원` : '데이터 없음'}
                    <span className={`ml-2 ${getReturnColor(item.change_rate)}`}>
                      {item.change_rate !== 0 ? `${item.change_rate > 0 ? '+' : ''}${item.change_rate}%` : ''}
                    </span>
                  </div>
                </div>
                <div className="flex items-center space-x-1">
                  {renderStars(item.score)}
                </div>
              </div>

                {/* 하단: 추가 정보 */}
                <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                  <div>
                    <span className="text-gray-500">거래량:</span>
                    <span className="ml-2 text-gray-800">
                      {item.volume > 0 ? `${(item.volume / 1000).toFixed(0)}K` : '데이터 없음'}
                    </span>
                    {item.volume > 0 && item.current_price > 0 && (
                      <span className="ml-1 text-xs text-gray-500">
                        ({Math.round(item.volume * item.current_price / 100000000).toLocaleString()}억원)
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-gray-500">시장관심도:</span>
                    <span className="ml-2 text-gray-800 text-xs">
                      {item.market_interest || getSimpleStrategy(item)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">상태:</span>
                    <span className="ml-2 text-gray-800 text-xs">
                      {item.strategy || getStrategyInfo(item)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">점수:</span>
                    <span className="ml-2 text-gray-800">
                      {item.score ? `${item.score}/15` : '-'}
                    </span>
                  </div>
                </div>

                {/* 평가 정보 */}
                {item.score_label && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-xs text-gray-600 font-medium">📊 투자 평가</div>
                  <div 
                    className="px-2 py-1 rounded-full text-xs font-medium"
                    style={{
                      backgroundColor: getLabelMeta(item.score_label).cls.includes('emerald') ? '#d1fae5' : 
                                     getLabelMeta(item.score_label).cls.includes('blue') ? '#dbeafe' :
                                     getLabelMeta(item.score_label).cls.includes('amber') ? '#fef3c7' :
                                     getLabelMeta(item.score_label).cls.includes('yellow') ? '#fef3c7' : '#f1f5f9',
                      color: getLabelMeta(item.score_label).cls.includes('emerald') ? '#065f46' : 
                            getLabelMeta(item.score_label).cls.includes('blue') ? '#1e40af' :
                            getLabelMeta(item.score_label).cls.includes('amber') ? '#92400e' :
                            getLabelMeta(item.score_label).cls.includes('yellow') ? '#92400e' : '#374151'
                    }}
                  >
                    {getLabelMeta(item.score_label).text}
                  </div>
                    </div>
                    <div className="text-xs text-gray-700 leading-relaxed">
                      {getLabelMeta(item.score_label).hint}
                    </div>
                    {item.evaluation && item.evaluation.total_score && (
                      <div className="mt-2 text-xs text-gray-600">
                        종합 점수: <span className="font-semibold">{item.evaluation.total_score}점</span>
                      </div>
                    )}
                  </div>
                )}

                {/* 전략기반 액션 */}
                {item.strategy && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
                    <div className="text-xs text-blue-600 font-medium mb-1">📋 매매 가이드</div>
                    <div className="text-xs text-blue-800 leading-relaxed">
                      {getStrategyActions(item.strategy)}
                    </div>
                  </div>
                )}

                {/* 액션 버튼 */}
                <div className="flex items-center justify-between pt-3 border-t">
                  <div className="flex space-x-4 text-sm">
                    <button 
                      className="text-blue-500 hover:text-blue-700"
                      onClick={() => alert('준비중입니다.')}
                    >
                      관심등록
                    </button>
                    <button 
                      className="text-blue-500 hover:text-blue-700"
                      onClick={() => alert('준비중입니다.')}
                    >
                      차트
                    </button>
                    <button 
                      className="text-blue-500 hover:text-blue-700"
                      onClick={() => alert('준비중입니다.')}
                    >
                      기업정보
                    </button>
                  </div>
                  <button 
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600"
                    onClick={() => alert('준비중입니다.')}
                  >
                    관심등록
                  </button>
                </div>
              </div>
            ))
              )}
            </div>
          )}
        </div>

        {/* 하단 네비게이션 */}
        <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
          <div className="flex items-center justify-around py-2">
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => alert('준비중입니다.')}
            >
              <svg className="w-5 h-5 mb-1" fill="currentColor" viewBox="0 0 24 24">
                <path d="M3 12h2l3-9 3 9h2l-3 9-3-9z"/>
              </svg>
              <span className="text-xs">메뉴</span>
            </button>
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => alert('준비중입니다.')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="text-xs">홈</span>
            </button>
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => alert('준비중입니다.')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span className="text-xs">통합검색</span>
            </button>
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => alert('준비중입니다.')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              <span className="text-xs">관심종목</span>
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
    const base = 'http://localhost:8010';
    const response = await fetch(`${base}/latest-scan`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.ok && data.data) {
      // items 또는 rank 필드 처리
      const items = data.data.items || data.data.rank || [];
      return {
        props: {
          initialData: items,
          initialScanFile: data.file || ''
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
