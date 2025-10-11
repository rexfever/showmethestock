import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import getConfig from '../config';

export default function AdminDashboard() {
  const router = useRouter();
  const { isAuthenticated, user, token } = useAuth();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    
    // 관리자 권한 확인
    if (!user?.is_admin) {
      alert('관리자 권한이 필요합니다.');
      router.push('/customer-scanner');
      return;
    }
    
    // URL 파라미터에서 analyze 값 확인
    if (router.query.analyze) {
      performAnalysis(router.query.analyze);
    } else {
      fetchAdminData();
    }
  }, [isAuthenticated, user, router, router.query.analyze]);

  const performAnalysis = async (ticker) => {
    setAnalysisLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/analyze?name_or_code=${encodeURIComponent(ticker)}`);
      const data = await response.json();
      
      if (data.ok) {
        setAnalysisResult(data);
      } else {
        alert(`분석 실패: ${data.error}`);
      }
    } catch (error) {
      console.error('분석 오류:', error);
      alert('분석 중 오류가 발생했습니다.');
    } finally {
      setAnalysisLoading(false);
    }
  };

  const fetchAdminData = async () => {
    try {
      const config = getConfig();
      const base = config.backendUrl;

      const [statsResponse, usersResponse] = await Promise.all([
        fetch(`${base}/admin/stats`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }),
        fetch(`${base}/admin/users`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      ]);

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }

      if (usersResponse.ok) {
        const usersData = await usersResponse.json();
        setUsers(usersData.users);
      }
    } catch (error) {
      console.error('관리자 데이터 조회 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUserEdit = (user) => {
    setEditingUser({ ...user });
    setShowUserModal(true);
  };

  const handleUserUpdate = async () => {
    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';

      const response = await fetch(`${base}/admin/users/${editingUser.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: editingUser.id,
          membership_tier: editingUser.membership_tier,
          subscription_status: editingUser.subscription_status,
          is_admin: editingUser.is_admin
        })
      });

      if (response.ok) {
        alert('사용자 정보가 업데이트되었습니다.');
        setShowUserModal(false);
        fetchAdminData(); // 데이터 새로고침
      } else {
        const errorData = await response.json();
        alert(`업데이트 실패: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('사용자 업데이트 오류:', error);
      alert('사용자 업데이트 중 오류가 발생했습니다.');
    }
  };

  const handleUserDelete = async (userId) => {
    if (!confirm('정말 이 사용자를 삭제하시겠습니까?')) {
      return;
    }

    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';

      const response = await fetch(`${base}/admin/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: userId,
          confirm: true
        })
      });

      if (response.ok) {
        alert('사용자가 삭제되었습니다.');
        fetchAdminData(); // 데이터 새로고침
      } else {
        const errorData = await response.json();
        alert(`삭제 실패: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('사용자 삭제 오류:', error);
      alert('사용자 삭제 중 오류가 발생했습니다.');
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('ko-KR').format(price);
  };

  const getTierColor = (tier) => {
    switch (tier) {
      case 'free': return 'bg-gray-100 text-gray-800';
      case 'premium': return 'bg-blue-100 text-blue-800';
      case 'vip': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTierName = (tier) => {
    switch (tier) {
      case 'free': return '무료';
      case 'premium': return '프리미엄';
      case 'vip': return 'VIP';
      default: return '무료';
    }
  };

  if (loading || analysisLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">
            {analysisLoading ? '종목 분석 중...' : '관리자 데이터를 불러오는 중...'}
          </p>
        </div>
      </div>
    );
  }

  // 분석 결과가 있으면 분석 화면 표시
  if (analysisResult) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Head>
          <title>종목 분석 결과 - Stock Insight</title>
        </Head>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* 헤더 */}
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">종목 분석 결과</h1>
              <p className="mt-2 text-gray-600">{analysisResult.item?.name} ({analysisResult.item?.ticker})</p>
            </div>
            <button
              onClick={() => {
                setAnalysisResult(null);
                router.push('/admin');
              }}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-700 border border-gray-300 rounded-md"
            >
              관리자 대시보드로 돌아가기
            </button>
          </div>

          {/* 분석 결과 카드 */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* 기본 정보 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">기본 정보</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">종목명:</span>
                    <span className="font-medium">{analysisResult.item?.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">종목코드:</span>
                    <span className="font-medium">{analysisResult.item?.ticker}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">현재가:</span>
                    <span className="font-medium">{analysisResult.item?.indicators?.close?.toLocaleString()}원</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">거래량:</span>
                    <span className="font-medium">{analysisResult.item?.indicators?.VOL?.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* 분석 결과 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">분석 결과</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">매칭 여부:</span>
                    <span className={`font-medium ${analysisResult.item?.match ? 'text-green-600' : 'text-red-600'}`}>
                      {analysisResult.item?.match ? '매칭' : '비매칭'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">점수:</span>
                    <span className="font-medium">{analysisResult.item?.score}점</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">전략:</span>
                    <span className="font-medium">{analysisResult.item?.strategy}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">시장:</span>
                    <span className="font-medium">{analysisResult.item?.market}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 기술적 지표 */}
            {analysisResult.item?.indicators && (
              <div className="mt-8">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">기술적 지표</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm text-gray-600">TEMA(20)</div>
                    <div className="font-medium">{analysisResult.item.indicators.TEMA?.toFixed(2)}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm text-gray-600">DEMA(10)</div>
                    <div className="font-medium">{analysisResult.item.indicators.DEMA?.toFixed(2)}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm text-gray-600">RSI(14)</div>
                    <div className="font-medium">{analysisResult.item.indicators.RSI?.toFixed(2)}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm text-gray-600">MACD</div>
                    <div className="font-medium">{analysisResult.item.indicators.MACD?.toFixed(2)}</div>
                  </div>
                </div>
              </div>
            )}

            {/* 액션 버튼 */}
            <div className="mt-8 flex justify-center space-x-4">
              <button
                onClick={() => {
                  const naverUrl = `https://finance.naver.com/item/main.naver?code=${analysisResult.item?.ticker}`;
                  window.open(naverUrl, '_blank');
                }}
                className="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                네이버 금융에서 보기
              </button>
              <button
                onClick={() => {
                  const newTicker = prompt('다른 종목을 분석하시겠습니까? 종목 코드 또는 종목명을 입력하세요:');
                  if (newTicker) {
                    performAnalysis(newTicker);
                  }
                }}
                className="px-6 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600"
              >
                다른 종목 분석
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>관리자 대시보드 - Stock Insight</title>
      </Head>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 헤더 */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">관리자 대시보드</h1>
            <p className="mt-2 text-gray-600">사용자 관리 및 시스템 통계</p>
          </div>
          <button
            onClick={() => router.push('/customer-scanner')}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-700 border border-gray-300 rounded-md"
          >
            메인으로 돌아가기
          </button>
        </div>

        {/* 통계 카드 */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">총 사용자</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.total_users}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 rounded-lg">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">활성 구독</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.active_subscriptions}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-yellow-100 rounded-lg">
                  <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">총 수익</p>
                  <p className="text-2xl font-semibold text-gray-900">{formatPrice(stats.total_revenue)}원</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">VIP 사용자</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.vip_users}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 사용자 목록 */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">사용자 관리</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">사용자</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">등급</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">가입일</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">관리자</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">작업</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">{user.name || '이름 없음'}</div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                        <div className="text-xs text-gray-400">{user.provider}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getTierColor(user.membership_tier)}`}>
                        {getTierName(user.membership_tier)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {user.subscription_status}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(user.created_at).toLocaleDateString('ko-KR')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {user.is_admin ? (
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                          관리자
                        </span>
                      ) : (
                        <span className="text-sm text-gray-500">일반</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => handleUserEdit(user)}
                        className="text-blue-600 hover:text-blue-900 mr-3"
                      >
                        수정
                      </button>
                      <button
                        onClick={() => handleUserDelete(user.id)}
                        className="text-red-600 hover:text-red-900"
                        disabled={user.id === user.id} // 자기 자신 삭제 방지
                      >
                        삭제
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 사용자 수정 모달 */}
        {showUserModal && editingUser && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
              <div className="mt-3">
                <h3 className="text-lg font-medium text-gray-900 mb-4">사용자 정보 수정</h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">이름</label>
                    <input
                      type="text"
                      value={editingUser.name || ''}
                      onChange={(e) => setEditingUser({...editingUser, name: e.target.value})}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">회원 등급</label>
                    <select
                      value={editingUser.membership_tier}
                      onChange={(e) => setEditingUser({...editingUser, membership_tier: e.target.value})}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="free">무료</option>
                      <option value="premium">프리미엄</option>
                      <option value="vip">VIP</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">구독 상태</label>
                    <select
                      value={editingUser.subscription_status}
                      onChange={(e) => setEditingUser({...editingUser, subscription_status: e.target.value})}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="active">활성</option>
                      <option value="expired">만료</option>
                      <option value="cancelled">취소</option>
                    </select>
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="is_admin"
                      checked={editingUser.is_admin}
                      onChange={(e) => setEditingUser({...editingUser, is_admin: e.target.checked})}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="is_admin" className="ml-2 block text-sm text-gray-900">
                      관리자 권한
                    </label>
                  </div>
                </div>
                
                <div className="flex justify-end space-x-3 mt-6">
                  <button
                    onClick={() => setShowUserModal(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                  >
                    취소
                  </button>
                  <button
                    onClick={handleUserUpdate}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md"
                  >
                    저장
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
