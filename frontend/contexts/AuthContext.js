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

  // 토큰을 쿠키와 localStorage에서 가져오기
  useEffect(() => {
    const savedToken = Cookies.get('auth_token');
    const localToken = localStorage.getItem('token');
    const localUser = localStorage.getItem('user');
    
    if (savedToken) {
      setToken(savedToken);
      // 토큰이 있으면 사용자 정보 가져오기
      fetchUserInfo(savedToken);
    } else if (localToken && localUser) {
      // localStorage에서 토큰과 사용자 정보 복원
      try {
        const userData = JSON.parse(localUser);
        setUser(userData);
        setToken(localToken);
        setLoading(false);
      } catch (error) {
        console.error('사용자 정보 파싱 실패:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setLoading(false);
      }
    } else {
      setLoading(false);
    }
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
      } else {
        // 토큰이 유효하지 않으면 쿠키에서 제거
        Cookies.remove('auth_token');
        setToken(null);
      }
    } catch (error) {
      console.error('사용자 정보 가져오기 실패:', error);
      Cookies.remove('auth_token');
      setToken(null);
    } finally {
      setLoading(false);
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
        
        // 토큰을 쿠키에 저장 (7일간 유효)
        Cookies.set('auth_token', access_token, { expires: 7 });
        
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
    // 카카오 로그아웃 (사용자가 카카오로 로그인한 경우)
    if (user && user.provider === 'kakao') {
      try {
        await logoutWithKakao();
      } catch (error) {
        console.error('카카오 로그아웃 실패:', error);
      }
    }
    
    // 로컬 로그아웃
    Cookies.remove('auth_token');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  const isAuthenticated = () => {
    // 서버 사이드에서는 항상 false 반환
    if (typeof window === 'undefined') {
      return false;
    }
    
    // 현재 상태에서 토큰과 사용자 정보 확인
    return !!token && !!user;
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
    login,
    logout,
    isAuthenticated,
    fetchUserInfo,
    getToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
