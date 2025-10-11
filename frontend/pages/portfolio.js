import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import getConfig from '../config';
import Head from 'next/head';

export default function Portfolio() {
  const router = useRouter();
  const { isAuthenticated, getToken, user, logout, authLoading, authChecked } = useAuth();
  const [portfolio, setPortfolio] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [editingItem, setEditingItem] = useState(null);
  const [editForm, setEditForm] = useState({
    entry_price: '',
    quantity: '',
    entry_date: '',
    status: 'watching'
  });
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    // 인증 상태 확인 후 데이터 로드
    const checkAuth = () => {
      if (isAuthenticated()) {
        fetchPortfolio();
        fetchSummary();
      }
      setAuthChecked(true);
    };
    
    checkAuth();
  }, [selectedStatus]);

  useEffect(() => {
    // 인증 상태가 변경될 때마다 데이터 다시 로드
    if (authChecked && isAuthenticated()) {
      fetchPortfolio();
      fetchSummary();
    }
  }, [isAuthenticated, authChecked]);

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      const token = getToken();
      const statusParam = selectedStatus === 'all' ? '' : `?status=${selectedStatus}`;
      
      const config = getConfig();
      const response = await fetch(`${config.backendUrl}/portfolio${statusParam}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('포트폴리오 조회에 실패했습니다');
      }

      const data = await response.json();
      setPortfolio(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const token = getToken();
      const config = getConfig();
      const response = await fetch(`${config.backendUrl}/portfolio/summary`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSummary(data);
      }
    } catch (err) {
      console.error('요약 정보 조회 실패:', err);
    }
  };

  const addToPortfolio = async (ticker, name) => {
    try {
      const token = getToken();
      const config = getConfig();
      const response = await fetch(`${config.backendUrl}/portfolio/add`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ticker,
          name,
          status: 'watching'
        })
      });

      if (response.ok) {
        fetchPortfolio();
        fetchSummary();
        alert('포트폴리오에 추가되었습니다');
      } else {
        throw new Error('포트폴리오 추가에 실패했습니다');
      }
    } catch (err) {
      alert(err.message);
    }
  };

  const updatePortfolio = async (ticker) => {
    try {
      const token = getToken();
      const config = getConfig();
      const response = await fetch(`${config.backendUrl}/portfolio/${ticker}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editForm)
      });

      if (response.ok) {
        setEditingItem(null);
        setEditForm({
          entry_price: '',
          quantity: '',
          entry_date: '',
          status: 'watching'
        });
        fetchPortfolio();
        fetchSummary();
        alert('포트폴리오가 업데이트되었습니다');
      } else {
        throw new Error('포트폴리오 업데이트에 실패했습니다');
      }
    } catch (err) {
      alert(err.message);
    }
  };

  const removeFromPortfolio = async (ticker) => {
    if (!confirm('정말로 포트폴리오에서 제거하시겠습니까?')) {
      return;
    }

    try {
      const token = getToken();
      const config = getConfig();
      const response = await fetch(`${config.backendUrl}/portfolio/${ticker}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        fetchPortfolio();
        fetchSummary();
        alert('포트폴리오에서 제거되었습니다');
      } else {
        throw new Error('포트폴리오 제거에 실패했습니다');
      }
    } catch (err) {
      alert(err.message);
    }
  };

  const startEdit = (item) => {
    setEditingItem(item.ticker);
    setEditForm({
      entry_price: item.entry_price || '',
      quantity: item.quantity || '',
      entry_date: item.entry_date || '',
      status: item.status
    });
  };

  const cancelEdit = () => {
    setEditingItem(null);
    setEditForm({
      entry_price: '',
      quantity: '',
      entry_date: '',
      status: 'watching'
    });
  };

  const formatCurrency = (amount) => {
    if (!amount) return '-';
    return new Intl.NumberFormat('ko-KR').format(Math.round(amount));
  };

  const formatPercentage = (percentage) => {
    if (!percentage) return '-';
    return `${percentage > 0 ? '+' : ''}${percentage.toFixed(2)}%`;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'watching': return 'bg-blue-100 text-blue-800';
      case 'holding': return 'bg-green-100 text-green-800';
      case 'sold': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'watching': return '관심종목';
      case 'holding': return '보유중';
      case 'sold': return '매도완료';
      default: return status;
    }
  };

  // 인증 상태 확인 중이면 로딩 표시
  if (!authChecked) {
    return (
      <>
        <Head>
          <title>나의투자종목 - Stock Insight</title>
        </Head>
        
        <div className="min-h-screen bg-gray-50">
          {/* 상단 헤더 */}
          <div className="bg-white shadow-sm border-b">
            <div className="flex items-center justify-between p-4">
              <div className="flex items-center">
                <h1 className="text-xl font-bold text-gray-900">Stock Insight</h1>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-400">로딩 중...</span>
                <button className="px-3 py-1 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600">
                  Premier
                </button>
              </div>
            </div>
          </div>

          {/* 로딩 화면 */}
          <div className="flex items-center justify-center" style={{height: 'calc(100vh - 200px)'}}>
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-600">인증 상태를 확인하는 중...</p>
            </div>
          </div>

          {/* 하단 네비게이션 */}
          <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
            <div className="flex justify-around items-center py-2">
              <button 
                className="flex flex-col items-center py-2 hover:bg-gray-800"
                onClick={() => router.push('/')}
              >
                <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span className="text-xs">홈</span>
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
                className="flex flex-col items-center py-2 bg-gray-700"
                onClick={() => router.push('/portfolio')}
              >
                <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                <span className="text-xs">나의투자종목</span>
              </button>
              <button 
                className="flex flex-col items-center py-2 hover:bg-gray-800"
                onClick={() => router.push('/login')}
              >
                <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span className="text-xs">로그인</span>
              </button>
            </div>
          </div>

          {/* 하단 네비게이션 공간 확보 */}
          <div className="h-20"></div>
        </div>
      </>
    );
  }

  if (!isAuthenticated()) {
    return (
      <>
        <Head>
          <title>나의투자종목 - Stock Insight</title>
        </Head>
        
        <div className="min-h-screen bg-gray-50">
          {/* 상단 헤더 */}
          <div className="bg-white shadow-sm border-b">
            <div className="flex items-center justify-between p-4">
              <div className="flex items-center">
                <h1 className="text-xl font-bold text-gray-900">Stock Insight</h1>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-500">게스트 사용자</span>
                <button className="px-3 py-1 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600">
                  Premier
                </button>
              </div>
            </div>
          </div>

          {/* 로그인 필요 화면 */}
          <div className="flex items-center justify-center" style={{height: 'calc(100vh - 200px)'}}>
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">로그인이 필요합니다</h2>
              <p className="text-gray-600 mb-6">포트폴리오를 관리하려면 로그인해주세요.</p>
              <a href="/login" className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600">
                로그인하기
              </a>
            </div>
          </div>

          {/* 하단 네비게이션 */}
          <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
            <div className="flex justify-around items-center py-2">
              <button 
                className="flex flex-col items-center py-2 hover:bg-gray-800"
                onClick={() => router.push('/')}
              >
                <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span className="text-xs">홈</span>
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
                className="flex flex-col items-center py-2 bg-gray-700"
                onClick={() => router.push('/portfolio')}
              >
                <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                <span className="text-xs">나의투자종목</span>
              </button>
              <button 
                className="flex flex-col items-center py-2 hover:bg-gray-800"
                onClick={() => router.push('/login')}
              >
                <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span className="text-xs">로그인</span>
              </button>
            </div>
          </div>

          {/* 하단 네비게이션 공간 확보 */}
          <div className="h-20"></div>
        </div>
      </>
    );
  }

  if (loading) {
    return (
      <>
        <Head>
          <title>나의투자종목 - Stock Insight</title>
        </Head>
        
        <div className="min-h-screen bg-gray-50">
          {/* 상단 헤더 */}
          <div className="bg-white shadow-sm border-b">
            <div className="flex items-center justify-between p-4">
              <div className="flex items-center">
                <h1 className="text-xl font-bold text-gray-900">Stock Insight</h1>
              </div>
              <div className="flex items-center space-x-4">
                {!authLoading && authChecked && user ? (
                  <span className="text-sm text-gray-600">
                    {user.name}님 ({user.provider})
                  </span>
                ) : !authLoading && authChecked ? (
                  <span className="text-sm text-gray-500">게스트 사용자</span>
                ) : (
                  <span className="text-sm text-gray-400">로딩 중...</span>
                )}
                <button className="px-3 py-1 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600">
                  Premier
                </button>
              </div>
            </div>
          </div>

          {/* 로딩 화면 */}
          <div className="flex items-center justify-center" style={{height: 'calc(100vh - 200px)'}}>
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-600">포트폴리오를 불러오는 중...</p>
            </div>
          </div>

          {/* 하단 네비게이션 */}
          <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
            <div className="flex justify-around items-center py-2">
              <button 
                className="flex flex-col items-center py-2 hover:bg-gray-800"
                onClick={() => router.push('/')}
              >
                <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span className="text-xs">홈</span>
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
                className="flex flex-col items-center py-2 bg-gray-700"
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
                onClick={async () => {
                  if (user) {
                    try {
                      await logout();
                      router.push('/login');
                    } catch (error) {
                      console.error('로그아웃 중 오류:', error);
                      // 오류가 발생해도 로그인 페이지로 이동
                      router.push('/login');
                    }
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

          {/* 하단 네비게이션 공간 확보 */}
          <div className="h-20"></div>
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Head>
          <title>나의투자종목 - Stock Insight</title>
        </Head>
        
        <div className="min-h-screen bg-gray-50">
          {/* 상단 헤더 */}
          <div className="bg-white shadow-sm border-b">
            <div className="flex items-center justify-between p-4">
              <div className="flex items-center">
                <h1 className="text-xl font-bold text-gray-900">Stock Insight</h1>
              </div>
              <div className="flex items-center space-x-4">
                {!authLoading && authChecked && user ? (
                  <span className="text-sm text-gray-600">
                    {user.name}님 ({user.provider})
                  </span>
                ) : !authLoading && authChecked ? (
                  <span className="text-sm text-gray-500">게스트 사용자</span>
                ) : (
                  <span className="text-sm text-gray-400">로딩 중...</span>
                )}
                <button className="px-3 py-1 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600">
                  Premier
                </button>
              </div>
            </div>
          </div>

          {/* 에러 화면 */}
          <div className="flex items-center justify-center" style={{height: 'calc(100vh - 200px)'}}>
            <div className="text-center">
              <h2 className="text-2xl font-bold text-red-600 mb-4">오류가 발생했습니다</h2>
              <p className="text-gray-600 mb-6">{error}</p>
              <button 
                onClick={() => window.location.reload()} 
                className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600"
              >
                다시 시도
              </button>
            </div>
          </div>

          {/* 하단 네비게이션 */}
          <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
            <div className="flex justify-around items-center py-2">
              <button 
                className="flex flex-col items-center py-2 hover:bg-gray-800"
                onClick={() => router.push('/')}
              >
                <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span className="text-xs">홈</span>
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
                className="flex flex-col items-center py-2 bg-gray-700"
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
                onClick={async () => {
                  if (user) {
                    try {
                      await logout();
                      router.push('/login');
                    } catch (error) {
                      console.error('로그아웃 중 오류:', error);
                      // 오류가 발생해도 로그인 페이지로 이동
                      router.push('/login');
                    }
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

          {/* 하단 네비게이션 공간 확보 */}
          <div className="h-20"></div>
        </div>
      </>
    );
  }

  return (
    <>
      <Head>
        <title>나의투자종목 - Stock Insight</title>
      </Head>
      
      <div className="min-h-screen bg-gray-50">
        {/* 상단 헤더 */}
        <div className="bg-white shadow-sm border-b">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">Stock Insight</h1>
            </div>
            <div className="flex items-center space-x-4">
              {!authLoading && authChecked && user ? (
                <span className="text-sm text-gray-600">
                  {user.name}님 ({user.provider})
                </span>
              ) : !authLoading && authChecked ? (
                <span className="text-sm text-gray-500">게스트 사용자</span>
              ) : (
                <span className="text-sm text-gray-400">로딩 중...</span>
              )}
              <button className="px-3 py-1 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600">
                Premier
              </button>
            </div>
          </div>
        </div>

        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">나의투자종목</h2>
              <p className="text-sm opacity-90">투자 종목의 수익률을 추적하고 관리하세요</p>
            </div>
            <div className="text-2xl">📊</div>
          </div>
        </div>

      {/* 요약 정보 */}
      {summary && (
        <div className="bg-white border-b p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{summary.total_items}</div>
              <div className="text-sm text-gray-600">총 종목</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{summary.holding_count}</div>
              <div className="text-sm text-gray-600">보유중</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{summary.watching_count}</div>
              <div className="text-sm text-gray-600">관심종목</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${summary.total_profit_loss_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPercentage(summary.total_profit_loss_pct)}
              </div>
              <div className="text-sm text-gray-600">총 수익률</div>
            </div>
          </div>
        </div>
      )}

      {/* 필터 */}
      <div className="bg-white border-b p-4">
        <div className="flex space-x-2">
          <button
            onClick={() => setSelectedStatus('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              selectedStatus === 'all' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            전체
          </button>
          <button
            onClick={() => setSelectedStatus('watching')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              selectedStatus === 'watching' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            관심종목
          </button>
          <button
            onClick={() => setSelectedStatus('holding')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              selectedStatus === 'holding' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            보유중
          </button>
          <button
            onClick={() => setSelectedStatus('sold')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              selectedStatus === 'sold' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            매도완료
          </button>
        </div>
      </div>

      {/* 포트폴리오 목록 */}
      <div className="p-4 space-y-4">
        {portfolio && portfolio.items.length > 0 ? (
          portfolio.items.map((item) => (
            <div key={item.id} className="bg-white rounded-lg shadow-sm border p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="font-semibold text-gray-800">
                    {item.name}
                    <span className="text-xs text-gray-500 ml-2">({item.ticker})</span>
                  </div>
                  <div className="text-sm text-gray-600">
                    현재가: {formatCurrency(item.current_price)}원
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                    {getStatusText(item.status)}
                  </span>
                  <button
                    onClick={() => removeFromPortfolio(item.ticker)}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    삭제
                  </button>
                </div>
              </div>

              {editingItem === item.ticker ? (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-3">
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">매수가</label>
                      <input
                        type="number"
                        value={editForm.entry_price}
                        onChange={(e) => setEditForm({...editForm, entry_price: e.target.value})}
                        className="w-full p-2 border border-gray-300 rounded text-sm"
                        placeholder="매수가 입력"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">수량</label>
                      <input
                        type="number"
                        value={editForm.quantity}
                        onChange={(e) => setEditForm({...editForm, quantity: e.target.value})}
                        className="w-full p-2 border border-gray-300 rounded text-sm"
                        placeholder="수량 입력"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">매수일</label>
                      <input
                        type="date"
                        value={editForm.entry_date}
                        onChange={(e) => setEditForm({...editForm, entry_date: e.target.value})}
                        className="w-full p-2 border border-gray-300 rounded text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">상태</label>
                      <select
                        value={editForm.status}
                        onChange={(e) => setEditForm({...editForm, status: e.target.value})}
                        className="w-full p-2 border border-gray-300 rounded text-sm"
                      >
                        <option value="watching">관심종목</option>
                        <option value="holding">보유중</option>
                        <option value="sold">매도완료</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => updatePortfolio(item.ticker)}
                      className="px-4 py-2 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                    >
                      저장
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded text-sm hover:bg-gray-400"
                    >
                      취소
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-3">
                  <div>
                    <span className="text-gray-500">매수가:</span>
                    <span className="ml-2 text-gray-800">{formatCurrency(item.entry_price)}원</span>
                  </div>
                  <div>
                    <span className="text-gray-500">수량:</span>
                    <span className="ml-2 text-gray-800">{item.quantity ? `${item.quantity}주` : '-'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">총 투자금:</span>
                    <span className="ml-2 text-gray-800">{formatCurrency(item.total_investment)}원</span>
                  </div>
                  <div>
                    <span className="text-gray-500">현재 평가금액:</span>
                    <span className="ml-2 text-gray-800">{formatCurrency(item.current_value)}원</span>
                  </div>
                  <div>
                    <span className="text-gray-500">손익:</span>
                    <span className={`ml-2 ${item.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(item.profit_loss)}원
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">수익률:</span>
                    <span className={`ml-2 ${item.profit_loss_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatPercentage(item.profit_loss_pct)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">매수일:</span>
                    <span className="ml-2 text-gray-800">{item.entry_date || '-'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">등록일:</span>
                    <span className="ml-2 text-gray-800">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : '-'}
                    </span>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between pt-3 border-t">
                <div className="flex space-x-4 text-sm">
                  <button className="text-blue-500 hover:text-blue-700">차트</button>
                  <button className="text-blue-500 hover:text-blue-700">기업정보</button>
                </div>
                <button
                  onClick={() => startEdit(item)}
                  className="px-4 py-2 bg-gray-500 text-white rounded-lg text-sm font-medium hover:bg-gray-600"
                >
                  {editingItem === item.ticker ? '편집중' : '편집'}
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-12">
            <div className="text-gray-400 text-6xl mb-4">📊</div>
            <h3 className="text-lg font-medium text-gray-800 mb-2">포트폴리오가 비어있습니다</h3>
            <p className="text-gray-600 mb-6">관심있는 종목을 포트폴리오에 추가해보세요.</p>
            <a 
              href="/customer-scanner" 
              className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600"
            >
              스캐너에서 종목 찾기
            </a>
          </div>
        )}

        {/* 하단 네비게이션 */}
        <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
          <div className="flex justify-around items-center py-2">
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => router.push('/')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="text-xs">홈</span>
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
              className="flex flex-col items-center py-2 bg-gray-700"
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
              onClick={async () => {
                if (user) {
                  try {
                    await logout();
                    router.push('/login');
                  } catch (error) {
                    console.error('로그아웃 중 오류:', error);
                    // 오류가 발생해도 로그인 페이지로 이동
                    router.push('/login');
                  }
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

        {/* 하단 네비게이션 공간 확보 */}
        <div className="h-20"></div>
      </div>
    </>
  );
}
