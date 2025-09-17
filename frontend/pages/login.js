import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const router = useRouter();
  const { login, isAuthenticated, loading } = useAuth();
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState('');

  // 이미 로그인된 사용자는 메인 페이지로 리다이렉트 (임시 비활성화)
  // useEffect(() => {
  //   if (!loading && isAuthenticated()) {
  //     router.push('/customer-scanner');
  //   }
  // }, [loading, isAuthenticated, router]);

  const handleSocialLogin = async (provider) => {
    setIsLoggingIn(true);
    setError('');

    try {
      // 실제 소셜 로그인 구현을 위해서는 각 플랫폼의 SDK를 사용해야 합니다
      // 여기서는 데모용으로 가짜 토큰을 사용합니다
      const mockToken = `mock_${provider}_token_${Date.now()}`;
      
      const result = await login(provider, mockToken);
      
      if (result.success) {
        router.push('/customer-scanner');
      } else {
        setError(result.error || '로그인에 실패했습니다.');
      }
    } catch (error) {
      setError('로그인 중 오류가 발생했습니다.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-16 w-16 bg-blue-600 rounded-full flex items-center justify-center">
            <span className="text-2xl">💰</span>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            스톡인사이트 로그인
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            AI가 찾아낸 주도주 정보를 확인하세요
          </p>
        </div>

        <div className="mt-8 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <button
              onClick={() => handleSocialLogin('kakao')}
              disabled={isLoggingIn}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-yellow-400 hover:bg-yellow-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                <span className="text-lg">💬</span>
              </span>
              {isLoggingIn ? '로그인 중...' : '카카오로 로그인'}
            </button>

            <button
              onClick={() => handleSocialLogin('naver')}
              disabled={isLoggingIn}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-green-500 hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                <span className="text-lg">N</span>
              </span>
              {isLoggingIn ? '로그인 중...' : '네이버로 로그인'}
            </button>

            <button
              onClick={() => handleSocialLogin('toss')}
              disabled={isLoggingIn}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                <span className="text-lg">💳</span>
              </span>
              {isLoggingIn ? '로그인 중...' : '토스로 로그인'}
            </button>
          </div>

          <div className="text-center">
            <p className="text-xs text-gray-500">
              로그인 시 서비스 이용약관 및 개인정보처리방침에 동의하는 것으로 간주됩니다.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
