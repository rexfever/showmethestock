import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import getConfig from '../config';
import Link from 'next/link';
import { loginWithKakao, isKakaoSDKReady } from '../utils/kakaoAuth';

export default function Login() {
  const router = useRouter();
  const { login, isAuthenticated, loading, setUser, setToken } = useAuth();
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState('');
  const [loginMethod, setLoginMethod] = useState('social'); // 'social' or 'email'
  const [emailForm, setEmailForm] = useState({
    email: '',
    password: ''
  });
  const [emailLoading, setEmailLoading] = useState(false);
  const [kakaoSDKReady, setKakaoSDKReady] = useState(false);

  // URL 파라미터에서 에러 메시지 확인
  useEffect(() => {
    const { error } = router.query;
    if (error === 'access_denied') {
      setError('카카오 로그인이 취소되었습니다.');
    } else if (error) {
      setError('로그인 중 오류가 발생했습니다.');
    }
  }, [router.query]);

  // 카카오 SDK 로드 (동기 방식)
  useEffect(() => {
    const loadKakaoSDK = () => {
      // 이미 로드되어 있는지 확인
      if (window.Kakao && window.Kakao.isInitialized()) {
        setKakaoSDKReady(true);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://t1.kakaocdn.net/kakao_js_sdk/2.6.0/kakao.min.js';
      script.async = false; // 동기 로딩으로 변경
      
      script.onload = () => {
        console.log('카카오 SDK 로드 완료');
        console.log('window.Kakao:', window.Kakao);
        console.log('window.Kakao.Auth:', window.Kakao?.Auth);
        console.log('window.Kakao.Auth.login:', typeof window.Kakao?.Auth?.login);
        
        if (window.Kakao) {
          try {
            window.Kakao.init('4eb579e52709ea64e8b941b9c95d20da');
            console.log('카카오 SDK 초기화 완료');
            
            // 초기화 후 다시 확인
            setTimeout(() => {
              console.log('초기화 후 window.Kakao.Auth.login:', typeof window.Kakao?.Auth?.login);
              setKakaoSDKReady(true);
            }, 100);
          } catch (error) {
            console.error('카카오 SDK 초기화 실패:', error);
          }
        }
      };
      
      script.onerror = () => {
        console.error('카카오 SDK 로드 실패');
      };
      
      document.head.appendChild(script);
    };

    loadKakaoSDK();
  }, []);

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
      if (provider === 'kakao') {
        // 카카오 로그인
        if (!kakaoSDKReady || !isKakaoSDKReady()) {
          setError('카카오 SDK가 아직 로드되지 않았습니다. 잠시 후 다시 시도해주세요.');
          setIsLoggingIn(false);
          return;
        }

        console.log('카카오 SDK 상태:', {
          window: typeof window !== 'undefined',
          Kakao: !!window.Kakao,
          isInitialized: window.Kakao?.isInitialized(),
          Auth: !!window.Kakao?.Auth,
          login: typeof window.Kakao?.Auth?.login,
          kakaoSDKReady: kakaoSDKReady
        });

        const kakaoUserInfo = await loginWithKakao();
        
        // 백엔드로 소셜 로그인 요청
        const config = getConfig();
        const base = config.backendUrl;

        const response = await fetch(`${base}/auth/social-login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            provider: kakaoUserInfo.provider,
            access_token: kakaoUserInfo.access_token,
            user_info: kakaoUserInfo.user_info
          }),
        });

        const data = await response.json();

        if (response.ok) {
          // 토큰 저장
          localStorage.setItem('token', data.access_token);
          localStorage.setItem('user', JSON.stringify(data.user));
          
          // 메인 페이지로 이동 (V2)
          router.push('/v2/scanner-v2');
        } else {
          setError(data.detail || '로그인에 실패했습니다.');
        }
      } else {
        // 다른 소셜 로그인 (네이버, 토스) - 아직 구현되지 않음
        setError(`${provider} 로그인은 아직 구현되지 않았습니다.`);
      }
    } catch (error) {
      console.error('로그인 에러:', error);
      setError(error.message || '로그인 중 오류가 발생했습니다.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  // 자동 카카오 로그인 실행
  useEffect(() => {
    const { auto_kakao } = router.query;
    if (auto_kakao === 'true' && kakaoSDKReady && !isLoggingIn) {
      handleSocialLogin('kakao');
    }
  }, [router.query.auto_kakao, kakaoSDKReady, isLoggingIn, handleSocialLogin]);

  const handleEmailLogin = async (e) => {
    e.preventDefault();
    setEmailLoading(true);
    setError('');

    try {
      const config = getConfig();
      const base = config.backendUrl;

      const response = await fetch(`${base}/auth/email/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: emailForm.email,
          password: emailForm.password
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // 토큰 저장
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // 메인 페이지로 이동
        router.push('/customer-scanner');
      } else {
        setError(data.detail || '로그인에 실패했습니다.');
      }
    } catch (error) {
      setError('로그인 중 오류가 발생했습니다.');
    } finally {
      setEmailLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setEmailForm(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // 개발 모드: 윤봄 계정으로 로그인
  const handleDevLogin = async () => {
    setIsLoggingIn(true);
    setError('');

    try {
      const config = getConfig();
      const base = config.backendUrl;

      // 개발 모드 로그인 엔드포인트 호출
      const response = await fetch(`${base}/auth/dev-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: 'kuksos80215@daum.net'
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // 토큰 저장
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // AuthContext 업데이트
        if (setUser && setToken) {
          setUser(data.user);
          setToken(data.access_token);
        }
        
        // 메인 페이지로 이동 (V2)
        router.push('/v2/scanner-v2');
      } else {
        setError(data.detail || '로그인에 실패했습니다.');
      }
    } catch (error) {
      console.error('개발 모드 로그인 에러:', error);
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
      <Head>
        <title>스톡인사이트 - 로그인</title>
      </Head>
      
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-16 w-16 bg-blue-600 rounded-full flex items-center justify-center">
            <span className="text-2xl">🔮</span>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            스톡인사이트 로그인
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            AI가 찾아낸 주도주 정보를 확인하세요
          </p>
        </div>

        <div className="mt-8 space-y-6">
          {/* 로그인 방법 선택 */}
          <div className="flex space-x-4">
            <button
              onClick={() => setLoginMethod('social')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium ${
                loginMethod === 'social'
                  ? 'bg-blue-100 text-blue-700 border-2 border-blue-300'
                  : 'bg-gray-100 text-gray-700 border-2 border-gray-300'
              }`}
            >
              소셜 로그인
            </button>
            <button
              onClick={() => setLoginMethod('email')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium ${
                loginMethod === 'email'
                  ? 'bg-blue-100 text-blue-700 border-2 border-blue-300'
                  : 'bg-gray-100 text-gray-700 border-2 border-gray-300'
              }`}
            >
              이메일 로그인
            </button>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
              {error}
            </div>
          )}

          {/* 소셜 로그인 */}
          {loginMethod === 'social' && (
            <div className="space-y-4">
              {/* 개발 모드: 윤봄 계정으로 로그인 (로컬 환경에서만 표시) */}
              {process.env.NODE_ENV === 'development' && (
                <button
                  onClick={handleDevLogin}
                  disabled={isLoggingIn}
                  className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-pink-500 hover:bg-pink-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-pink-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                    <span className="text-lg">✨</span>
                  </span>
                  {isLoggingIn ? '로그인 중...' : '윤봄님으로 로그인 (개발 모드)'}
                </button>
              )}
              
              <button
                onClick={() => handleSocialLogin('kakao')}
                disabled={isLoggingIn || !kakaoSDKReady}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-yellow-400 hover:bg-yellow-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                  <span className="text-lg">💬</span>
                </span>
                {!kakaoSDKReady ? 'SDK 로딩 중...' : isLoggingIn ? '로그인 중...' : '카카오로 로그인'}
              </button>

              <button
                onClick={() => alert('준비중입니다.')}
                disabled={true}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-gray-400 cursor-not-allowed"
              >
                <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                  <span className="text-lg">N</span>
                </span>
                준비중입니다
              </button>

              <button
                onClick={() => alert('준비중입니다.')}
                disabled={true}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-gray-400 cursor-not-allowed"
              >
                <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                  <span className="text-lg">💳</span>
                </span>
                준비중입니다
              </button>
            </div>
          )}

          {/* 이메일 로그인 */}
          {loginMethod === 'email' && (
            <form onSubmit={handleEmailLogin} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  이메일
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  value={emailForm.email}
                  onChange={handleInputChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="example@email.com"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                  비밀번호
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  value={emailForm.password}
                  onChange={handleInputChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="비밀번호를 입력하세요"
                />
              </div>

              <button
                type="submit"
                disabled={emailLoading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {emailLoading ? '로그인 중...' : '이메일로 로그인'}
              </button>
            </form>
          )}

          <div className="text-center">
            <p className="text-sm text-gray-600">
              계정이 없으신가요?{' '}
              <Link href="/signup" className="font-medium text-blue-600 hover:text-blue-500">
                회원가입하기
              </Link>
            </p>
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
