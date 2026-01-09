import React, { createContext, useContext, useState, useEffect } from 'react';
import Cookies from 'js-cookie';
import { logoutWithKakao } from '../utils/kakaoAuth';
import getConfig from '../config';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  // 토큰을 쿠키와 localStorage에서 가져오기
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const savedToken = Cookies.get('auth_token');
        const localToken = localStorage.getItem('token');
        const localUser = localStorage.getItem('user');
        
        if (savedToken) {
          setToken(savedToken);
          // 토큰이 있으면 사용자 정보 가져오기
          await fetchUserInfo(savedToken);
        } else if (localToken && localUser) {
          // localStorage에서 토큰과 사용자 정보 복원
          try {
            const userData = JSON.parse(localUser);
            setUser(userData);
            setToken(localToken);
            // localStorage 토큰도 쿠키에 동기화
            Cookies.set('auth_token', localToken, { expires: 7 });
          } catch (error) {
            console.error('사용자 정보 파싱 실패:', error);
            localStorage.removeItem('token');
            localStorage.removeItem('user');
          }
        }
      } catch (error) {
        console.error('인증 초기화 실패:', error);
      } finally {
        setLoading(false);
        setAuthChecked(true);
      }
    };

    initializeAuth();
  }, []);

  const fetchUserInfo = async (authToken) => {
    try {
      const config = getConfig();
      const response = await fetch(`${config.backendUrl}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
        localStorage.setItem('token', authToken);
      } else if (response.status === 401) {
        console.warn('토큰이 만료되었습니다.');
        await logout();
      } else {
        console.error('사용자 정보 가져오기 실패:', response.status);
      }
    } catch (error) {
      console.error('네트워크 오류:', error);
    }
  };

  const login = async (provider, accessToken) => {
    try {
      const config = getConfig();
      const response = await fetch(`${config.backendUrl}/auth/social-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider,
          access_token: accessToken,
          user_info: {} // 소셜 로그인에서는 서버에서 사용자 정보를 가져옴
        })
      });

      if (response.ok) {
        const data = await response.json();
        const { access_token, user: userData } = data;
        
        // 토큰을 쿠키와 localStorage에 저장 (7일간 유효)
        Cookies.set('auth_token', access_token, { expires: 7 });
        localStorage.setItem('token', access_token);
        localStorage.setItem('user', JSON.stringify(userData));
        
        setToken(access_token);
        setUser(userData);
        
        return { success: true, user: userData };
      } else {
        const errorData = await response.json();
        return { success: false, error: errorData.detail };
      }
    } catch (error) {
      console.error('로그인 실패:', error);
      return { success: false, error: '로그인 중 오류가 발생했습니다.' };
    }
  };

  const logout = async () => {
    try {
      // 카카오 로그아웃 (사용자가 카카오로 로그인한 경우)
      if (user && user.provider === 'kakao') {
        try {
          await logoutWithKakao();
          // 성공/실패 여부와 관계없이 로컬 로그아웃 진행
        } catch (error) {
          // 에러는 이미 logoutWithKakao에서 처리되므로 여기서는 무시
          console.warn('카카오 로그아웃 중 오류 (무시):', error);
        }
      }
      
      // 로컬 로그아웃
      Cookies.remove('auth_token');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setToken(null);
      setUser(null);
      
      console.log('로그아웃 완료');
    } catch (error) {
      console.error('로그아웃 중 오류 발생:', error);
      // 오류가 발생해도 로컬 상태는 초기화
      Cookies.remove('auth_token');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setToken(null);
      setUser(null);
    }
  };

  const isAuthenticated = () => {
    // 서버 사이드에서는 항상 false 반환
    if (typeof window === 'undefined') {
      return false;
    }
    
    // 현재 상태에서 토큰과 사용자 정보 확인
    if (token && user) {
      return true;
    }
    
    // 상태가 없으면 localStorage와 쿠키에서 확인
    const localToken = localStorage.getItem('token');
    const localUser = localStorage.getItem('user');
    const cookieToken = Cookies.get('auth_token');
    
    return !!(localToken || cookieToken) && !!localUser;
  };

  const getToken = () => {
    // 서버 사이드에서는 null 반환
    if (typeof window === 'undefined') {
      return null;
    }
    
    // localStorage에서 토큰 확인
    const localToken = localStorage.getItem('token');
    if (localToken) {
      return localToken;
    }
    
    // 쿠키에서 토큰 확인
    const cookieToken = Cookies.get('auth_token');
    if (cookieToken) {
      return cookieToken;
    }
    
    // 상태에서 토큰 확인
    return token;
  };

  const value = {
    user,
    token,
    loading,
    authLoading: loading, // Header 컴포넌트 호환성
    authChecked,
    login,
    logout,
    isAuthenticated,
    fetchUserInfo,
    getToken,
    setUser,
    setToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
