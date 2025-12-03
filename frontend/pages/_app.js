import '../styles/globals.css';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import { useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/router';
import { isKakaoTalkBrowser, autoLoginWithKakaoTalk, autoLoginWithKakaoSession, isKakaoSDKReady } from '../utils/kakaoAuth';
import getConfig from '../config';
import Cookies from 'js-cookie';

// localStorage 키를 사용하여 중복 로그인 시도 방지
const AUTO_LOGIN_ATTEMPT_KEY = 'kakao_auto_login_attempt';
const AUTO_LOGIN_ATTEMPT_TIMEOUT = 5000; // 5초

// 카카오 SDK 로드 및 초기화
const loadKakaoSDK = () => {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('서버 사이드에서는 실행할 수 없습니다.'));
  }
  
  // 이미 로드되어 있으면 스킵
  if (window.Kakao && window.Kakao.isInitialized()) {
    return Promise.resolve();
  }
  
  return new Promise((resolve, reject) => {
    // 이미 스크립트가 있으면 스킵
    if (document.querySelector('script[src*="kakao.min.js"]')) {
      // 스크립트가 로드될 때까지 대기
      let checkInterval = setInterval(() => {
        if (window.Kakao && window.Kakao.isInitialized()) {
          clearInterval(checkInterval);
          resolve();
        }
      }, 100);
      
      const timeout = setTimeout(() => {
        clearInterval(checkInterval);
        if (window.Kakao && window.Kakao.isInitialized()) {
          resolve();
        } else {
          reject(new Error('카카오 SDK 로드 타임아웃'));
        }
      }, 5000);
      
      // Promise가 resolve/reject되면 자동으로 cleanup되므로 별도 처리 불필요
    }
    
    const script = document.createElement('script');
    script.src = 'https://t1.kakaocdn.net/kakao_js_sdk/2.6.0/kakao.min.js';
    script.async = false;
    
    let initTimeout;
    
    script.onload = () => {
      if (window.Kakao) {
        try {
          window.Kakao.init('4eb579e52709ea64e8b941b9c95d20da');
          initTimeout = setTimeout(() => resolve(), 100);
        } catch (error) {
          if (initTimeout) clearTimeout(initTimeout);
          reject(error);
        }
      } else {
        if (initTimeout) clearTimeout(initTimeout);
        reject(new Error('카카오 SDK 로드 실패'));
      }
    };
    
    script.onerror = () => {
      if (initTimeout) clearTimeout(initTimeout);
      reject(new Error('카카오 SDK 스크립트 로드 실패'));
    };
    
    document.head.appendChild(script);
  });
};

function AutoKakaoLoginHandler() {
  const router = useRouter();
  const { isAuthenticated, authChecked, setUser, setToken } = useAuth();
  const isAttemptingRef = useRef(false);
  const timeoutRef = useRef(null);
  const intervalRef = useRef(null);
  
  // 카카오 로그인 성공 처리 함수
  const handleKakaoLoginSuccess = useCallback(async (kakaoUserInfo) => {
    try {
      // 다시 한번 로그인 상태 확인 (경쟁 조건 방지)
      const existingToken = localStorage.getItem('token') || Cookies.get('auth_token');
      if (existingToken) {
        console.log('이미 로그인되어 있습니다. 중복 로그인 시도 방지');
        isAttemptingRef.current = false;
        return;
      }
      
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
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: '로그인 실패' }));
        const errorMessage = errorData.detail || '로그인 실패';
        
        // 401 에러는 토큰 만료 또는 인증 실패
        if (response.status === 401) {
          console.warn('카카오 토큰이 만료되었거나 유효하지 않습니다:', errorMessage);
        } else {
          console.error('자동 로그인 API 호출 실패:', errorMessage);
        }
        
        throw new Error(errorMessage);
      }
      
      const data = await response.json();
      
      // AuthContext 상태 업데이트 (동기화 보장)
      setToken(data.access_token);
      setUser(data.user);
      
      // localStorage와 쿠키에 저장 (AuthContext와 동기화)
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      Cookies.set('auth_token', data.access_token, { expires: 7 });
      
      console.log('자동 로그인 완료');
      // 성공 시 localStorage 플래그 제거
      localStorage.removeItem(AUTO_LOGIN_ATTEMPT_KEY);
    } catch (error) {
      console.error('자동 로그인 API 호출 실패:', error);
      // 에러 발생 시에도 플래그 해제하여 재시도 가능하도록 함
      localStorage.removeItem(AUTO_LOGIN_ATTEMPT_KEY);
    } finally {
      isAttemptingRef.current = false;
    }
  }, [setUser, setToken]);
  
  useEffect(() => {
    // cleanup 함수
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);
  
  useEffect(() => {
    // AuthContext 초기화 대기
    if (!authChecked) {
      return;
    }
    
    // 이미 로그인되어 있으면 스킵 (토큰과 사용자 정보 모두 확인)
    const token = localStorage.getItem('token') || Cookies.get('auth_token');
    const user = localStorage.getItem('user');
    if (token && user && isAuthenticated()) {
      return;
    }
    
    // 이미 자동 로그인 시도 중이면 스킵
    if (isAttemptingRef.current) {
      return;
    }
    
    // localStorage를 사용한 중복 시도 방지 (다른 탭에서 시도 중인 경우)
    const lastAttempt = localStorage.getItem(AUTO_LOGIN_ATTEMPT_KEY);
    if (lastAttempt) {
      const lastAttemptTime = parseInt(lastAttempt, 10);
      const now = Date.now();
      if (now - lastAttemptTime < AUTO_LOGIN_ATTEMPT_TIMEOUT) {
        console.log('최근 자동 로그인 시도가 있었습니다. 잠시 대기합니다.');
        return;
      }
    }
    
    // 로그인 페이지나 콜백 페이지에서는 자동 로그인 시도하지 않음
    if (router.pathname === '/login' || router.pathname === '/kakao-callback' || router.pathname === '/signup') {
      return;
    }
    
    // 자동 로그인 시도 플래그 설정
    isAttemptingRef.current = true;
    localStorage.setItem(AUTO_LOGIN_ATTEMPT_KEY, Date.now().toString());
    
    // 카카오 SDK 로드 및 자동 로그인 시도
    loadKakaoSDK()
      .then(() => {
        // SDK 로드 후 약간의 지연을 두고 자동 로그인 시도
        timeoutRef.current = setTimeout(() => {
          // 다시 한번 로그인 상태 확인 (경쟁 조건 방지)
          const currentToken = localStorage.getItem('token') || Cookies.get('auth_token');
          const currentUser = localStorage.getItem('user');
          if (currentToken && currentUser) {
            console.log('이미 로그인되어 있습니다. 자동 로그인 스킵');
            isAttemptingRef.current = false;
            return;
          }
          
          if (isKakaoSDKReady()) {
            // 카카오톡 인앱 브라우저인 경우
            if (isKakaoTalkBrowser()) {
              autoLoginWithKakaoTalk()
                .then(handleKakaoLoginSuccess)
                .catch((error) => {
                  // 자동 로그인 실패는 정상 (사용자가 카카오톡에 로그인하지 않았거나 취소한 경우)
                  console.log('카카오톡 자동 로그인 실패 (정상):', error.message);
                  localStorage.removeItem(AUTO_LOGIN_ATTEMPT_KEY);
                  isAttemptingRef.current = false;
                });
            } else {
              // 일반 브라우저인 경우 - 카카오 세션 확인
              autoLoginWithKakaoSession()
                .then((kakaoUserInfo) => {
                  if (kakaoUserInfo) {
                    console.log('카카오 세션 자동 로그인 성공:', kakaoUserInfo);
                    handleKakaoLoginSuccess(kakaoUserInfo);
                  } else {
                    // 세션이 없으면 정상 (사용자가 카카오에 로그인하지 않음)
                    console.log('카카오 세션이 없습니다. (정상)');
                    localStorage.removeItem(AUTO_LOGIN_ATTEMPT_KEY);
                    isAttemptingRef.current = false;
                  }
                })
                .catch((error) => {
                  console.error('카카오 세션 확인 실패:', error);
                  localStorage.removeItem(AUTO_LOGIN_ATTEMPT_KEY);
                  isAttemptingRef.current = false;
                });
            }
          } else {
            console.warn('카카오 SDK가 준비되지 않았습니다.');
            localStorage.removeItem(AUTO_LOGIN_ATTEMPT_KEY);
            isAttemptingRef.current = false;
          }
        }, 500);
      })
      .catch((error) => {
        console.error('카카오 SDK 로드 실패:', error);
        localStorage.removeItem(AUTO_LOGIN_ATTEMPT_KEY);
        isAttemptingRef.current = false;
      });
  }, [router.pathname, authChecked, setUser, setToken, handleKakaoLoginSuccess]);
  
  return null;
}

export default function MyApp({ Component, pageProps }) {
  return (
    <>
      <Head>
        <title>Stock Insight</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      
      <AuthProvider>
        <AutoKakaoLoginHandler />
        <Component {...pageProps} />
      </AuthProvider>
    </>
  );
}


