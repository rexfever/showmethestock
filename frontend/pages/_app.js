import '../styles/globals.css';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import { useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { isKakaoTalkBrowser, autoLoginWithKakaoTalk, isKakaoSDKReady } from '../utils/kakaoAuth';
import getConfig from '../config';
import Cookies from 'js-cookie';

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
    
    // 이미 로그인되어 있으면 스킵
    if (isAuthenticated()) {
      return;
    }
    
    // 이미 자동 로그인 시도 중이면 스킵
    if (isAttemptingRef.current) {
      return;
    }
    
    // 로그인 페이지나 콜백 페이지에서는 자동 로그인 시도하지 않음
    if (router.pathname === '/login' || router.pathname === '/kakao-callback' || router.pathname === '/signup') {
      return;
    }
    
    // 카카오톡 인앱 브라우저인지 확인
    if (!isKakaoTalkBrowser()) {
      return;
    }
    
    // 자동 로그인 시도 플래그 설정
    isAttemptingRef.current = true;
    
    // 카카오 SDK 로드 및 자동 로그인 시도
    loadKakaoSDK()
      .then(() => {
        // SDK 로드 후 약간의 지연을 두고 자동 로그인 시도
        timeoutRef.current = setTimeout(() => {
          if (isKakaoSDKReady()) {
            autoLoginWithKakaoTalk()
              .then(async (kakaoUserInfo) => {
                console.log('카카오톡 자동 로그인 성공:', kakaoUserInfo);
                
                try {
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
                    throw new Error(errorData.detail || '로그인 실패');
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
                } catch (error) {
                  console.error('자동 로그인 API 호출 실패:', error);
                } finally {
                  isAttemptingRef.current = false;
                }
              })
              .catch((error) => {
                // 자동 로그인 실패는 정상 (사용자가 카카오톡에 로그인하지 않았거나 취소한 경우)
                console.log('카카오톡 자동 로그인 실패 (정상):', error.message);
                isAttemptingRef.current = false;
              });
          } else {
            console.warn('카카오 SDK가 준비되지 않았습니다.');
            isAttemptingRef.current = false;
          }
        }, 500);
      })
      .catch((error) => {
        console.error('카카오 SDK 로드 실패:', error);
        isAttemptingRef.current = false;
      });
  }, [router.pathname, authChecked, isAuthenticated, setUser, setToken]);
  
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


