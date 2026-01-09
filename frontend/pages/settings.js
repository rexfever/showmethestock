// 개인설정 페이지
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Layout from '../layouts/v2/Layout';
import getConfig from '../config';
import { useAuth } from '../contexts/AuthContext';

export default function Settings() {
  const router = useRouter();
  const { isAuthenticated, user, loading: authLoading, authChecked, logout } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [currentType, setCurrentType] = useState(null); // 'daily' 또는 'conditional'
  const [selectedType, setSelectedType] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  // 인증 체크
  useEffect(() => {
    if (authChecked && !authLoading && !isAuthenticated()) {
      router.push('/login');
    }
  }, [authChecked, authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!authChecked || authLoading) {
      return;
    }
    
    if (!isAuthenticated()) {
      return;
    }
    
    setMounted(true);
    fetchCurrentSettings();
  }, [authChecked, authLoading, isAuthenticated]);

  const fetchCurrentSettings = async () => {
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      if (!token) {
        // 토큰이 없으면 기본값 사용
        setCurrentType('daily');
        setSelectedType('daily');
        setLoading(false);
        return;
      }

      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      };

      // 사용자별 추천 방식 조회 API 호출
      const response = await fetch(`${base}/user/preferences`, {
        method: 'GET',
        headers: headers,
        mode: 'cors',
        cache: 'no-cache',
      });

      if (response.ok) {
        const data = await response.json();
        if (data.ok && data.data) {
          const type = data.data.recommendation_type; // 'daily' 또는 'conditional'
          setCurrentType(type);
          setSelectedType(type);
        } else {
          // 기본값: 일일 추천
          setCurrentType('daily');
          setSelectedType('daily');
        }
      } else {
        // 기본값: 일일 추천
        setCurrentType('daily');
        setSelectedType('daily');
      }
    } catch (error) {
      console.error('설정 조회 실패:', error);
      // 기본값: 일일 추천
      setCurrentType('daily');
      setSelectedType('daily');
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    setShowConfirmDialog(true);
  };

  const handleConfirmApply = async () => {
    setSaving(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      if (!token) {
        alert('로그인이 필요합니다.');
        router.push('/login');
        return;
      }

      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      };

      // 사용자별 추천 방식 저장 API 호출
      const response = await fetch(`${base}/user/preferences`, {
        method: 'POST',
        headers: headers,
        mode: 'cors',
        cache: 'no-cache',
        body: JSON.stringify({
          recommendation_type: selectedType
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.ok) {
          setCurrentType(selectedType);
          setShowConfirmDialog(false);
          
          // 설정 변경 이벤트 발생 (바텀 네비게이션이 다시 API를 호출하도록)
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('userPreferencesChanged'));
          }
          
          alert('추천 방식이 변경되었습니다.');
        } else {
          throw new Error(data.error || '설정 저장에 실패했습니다.');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || '설정 저장에 실패했습니다.');
      }
    } catch (error) {
      console.error('설정 저장 실패:', error);
      alert(`설정 저장에 실패했습니다: ${error.message || '알 수 없는 오류'}`);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelDialog = () => {
    setShowConfirmDialog(false);
  };

  if (!mounted) {
    return null;
  }

  const recommendationTypes = [
    {
      id: 'daily',
      label: '일일 추천',
      description: '매 거래일마다 추천 종목을 제공합니다.'
    },
    {
      id: 'conditional',
      label: '조건 추천',
      description: '정해진 조건이 충족되었을 때만 추천 종목을 제공합니다.'
    }
  ];

  const currentTypeLabel = currentType === 'daily' ? '일일 추천' : '조건 추천';
  const hasChanges = selectedType !== currentType;

  return (
    <>
      <Head>
        <title>개인설정 - 스톡인사이트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <Layout headerTitle="스톡인사이트">
        {/* 정보 배너 */}
        <div className="relative bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 text-white overflow-hidden">
          {/* 배경 패턴 */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute inset-0" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }}></div>
          </div>
          
          <div className="relative p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold mb-1">
                  개인설정
                </h2>
                <p className="text-sm opacity-90">
                  추천 방식을 선택하고 변경할 수 있습니다
                </p>
              </div>
              <div className="hidden sm:block">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 메인 컨텐츠 */}
        <div className="bg-gradient-to-b from-gray-50 via-gray-50 to-white min-h-screen">
          <div className="px-4 py-6">
            {/* 뒤로가기 버튼 */}
            <button
              onClick={() => router.back()}
              className="mb-6 flex items-center text-gray-600 hover:text-gray-900 transition-colors group"
            >
              <svg
                className="w-5 h-5 mr-2 transform group-hover:-translate-x-1 transition-transform"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="text-sm font-medium">뒤로가기</span>
            </button>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
              </div>
            ) : (
              <>
                {/* 섹션 제목 */}
                <h3 className="text-xl font-bold text-gray-900 mb-6">
                  추천 방식
                </h3>

                {/* 선택 UI */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 mb-6">
                  <div className="space-y-4">
                    {recommendationTypes.map((type) => (
                      <label
                        key={type.id}
                        className="flex items-start cursor-pointer group"
                      >
                        <div className="flex-shrink-0 mt-1">
                          <input
                            type="radio"
                            name="recommendationType"
                            value={type.id}
                            checked={selectedType === type.id}
                            onChange={() => setSelectedType(type.id)}
                            className="w-5 h-5 text-purple-600 focus:ring-purple-500 focus:ring-2 border-gray-300"
                          />
                        </div>
                        <div className="ml-3 flex-1">
                          <div className="text-gray-900 font-semibold text-base mb-1">
                            {type.label}
                          </div>
                          <div className="text-gray-600 text-sm">
                            {type.description}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {/* 현재 상태 표시 */}
                {currentType && (
                  <div className="mb-4 px-2">
                    <p className="text-sm text-gray-600">
                      현재 사용 중: <span className="font-semibold text-gray-900">{currentTypeLabel}</span>
                    </p>
                  </div>
                )}

                {/* 변경 안내 문구 */}
                <div className="mb-6 px-2">
                  <p className="text-xs text-gray-500">
                    추천 방식 변경은 이후 제공되는 추천부터 적용됩니다.
                  </p>
                </div>

                {/* 적용 버튼 */}
                <button
                  onClick={handleApply}
                  disabled={!hasChanges || saving}
                  className={`w-full py-4 rounded-2xl font-semibold text-base transition-all duration-300 ${
                    hasChanges && !saving
                      ? 'bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-lg hover:shadow-xl transform hover:-translate-y-0.5'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  {saving ? '적용 중...' : '적용'}
                </button>

                {/* 로그아웃 버튼 */}
                <div className="mt-8 pt-6 border-t border-gray-200">
                  <button
                    onClick={async () => {
                      if (confirm('로그아웃하시겠습니까?')) {
                        await logout();
                        router.push('/login');
                      }
                    }}
                    className="w-full py-3 rounded-xl border-2 border-red-300 text-red-600 font-semibold hover:bg-red-50 transition-colors"
                  >
                    로그아웃
                  </button>
                </div>
              </>
            )}
          </div>
          
          {/* 하단 여백 */}
          <div className="h-8"></div>
        </div>

        {/* 확인 다이얼로그 */}
        {showConfirmDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">
                추천 방식을 변경하시겠습니까?
              </h3>
              <p className="text-sm text-gray-600 mb-6 leading-relaxed">
                변경된 추천 방식은<br />
                이후 제공되는 추천부터 적용됩니다.
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={handleCancelDialog}
                  className="flex-1 py-3 rounded-xl border-2 border-gray-300 text-gray-700 font-semibold hover:bg-gray-50 transition-colors"
                >
                  취소
                </button>
                <button
                  onClick={handleConfirmApply}
                  disabled={saving}
                  className="flex-1 py-3 rounded-xl bg-gradient-to-r from-purple-500 to-pink-600 text-white font-semibold hover:shadow-lg transition-all disabled:opacity-50"
                >
                  {saving ? '적용 중...' : '변경하기'}
                </button>
              </div>
            </div>
          </div>
        )}
      </Layout>
    </>
  );
}

