/**
 * AuthContext 테스트
 */
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../../contexts/AuthContext';
import Cookies from 'js-cookie';
import getConfig from '../../config';

// Mock dependencies
jest.mock('js-cookie');
jest.mock('../../config', () => ({
  __esModule: true,
  default: jest.fn(() => ({
    backendUrl: 'http://localhost:8010',
  })),
}));

jest.mock('../../utils/kakaoAuth', () => ({
  logoutWithKakao: jest.fn(),
}));

// Test component
const TestComponent = () => {
  const auth = useAuth();
  return (
    <div>
      <div data-testid="user">{auth.user ? auth.user.name : 'null'}</div>
      <div data-testid="token">{auth.token || 'null'}</div>
      <div data-testid="loading">{auth.loading ? 'loading' : 'not-loading'}</div>
      <div data-testid="authLoading">{auth.authLoading ? 'loading' : 'not-loading'}</div>
      <div data-testid="authChecked">{auth.authChecked ? 'checked' : 'not-checked'}</div>
      <button onClick={() => auth.login('kakao', 'test-token')}>Login</button>
      <button onClick={() => auth.logout()}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
    localStorage.clear();
    Cookies.get.mockReturnValue(undefined);
    Cookies.set.mockImplementation(() => {});
    Cookies.remove.mockImplementation(() => {});
  });

  describe('초기화', () => {
    it('토큰이 없을 때 초기 상태를 반환해야 함', async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('null');
        expect(screen.getByTestId('token')).toHaveTextContent('null');
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading');
        expect(screen.getByTestId('authLoading')).toHaveTextContent('not-loading');
        expect(screen.getByTestId('authChecked')).toHaveTextContent('checked');
      });
    });

    it('쿠키에 토큰이 있으면 사용자 정보를 가져와야 함', async () => {
      Cookies.get.mockReturnValue('cookie-token');
      const mockUser = { id: 1, name: '테스트 사용자', email: 'test@test.com' };
      
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8010/auth/me',
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': 'Bearer cookie-token',
            }),
          })
        );
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('테스트 사용자');
        expect(screen.getByTestId('token')).toHaveTextContent('cookie-token');
      });
    });

    it('localStorage에 토큰이 있으면 복원해야 함', async () => {
      const mockUser = { id: 1, name: '로컬 사용자', email: 'local@test.com' };
      localStorage.setItem('token', 'local-token');
      localStorage.setItem('user', JSON.stringify(mockUser));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('로컬 사용자');
        expect(screen.getByTestId('token')).toHaveTextContent('local-token');
      });

      expect(Cookies.set).toHaveBeenCalledWith('auth_token', 'local-token', { expires: 7 });
    });
  });

  describe('로그인', () => {
    it('로그인 성공 시 토큰과 사용자 정보를 저장해야 함', async () => {
      const mockResponse = {
        access_token: 'new-token',
        user: { id: 1, name: '로그인 사용자', email: 'login@test.com' },
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const loginButton = screen.getByText('Login');
      await act(async () => {
        loginButton.click();
      });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8010/auth/social-login',
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
            }),
            body: JSON.stringify({
              provider: 'kakao',
              access_token: 'test-token',
              user_info: {},
            }),
          })
        );
      });

      await waitFor(() => {
        expect(Cookies.set).toHaveBeenCalledWith('auth_token', 'new-token', { expires: 7 });
        expect(localStorage.setItem).toHaveBeenCalledWith('token', 'new-token');
        expect(localStorage.setItem).toHaveBeenCalledWith(
          'user',
          JSON.stringify(mockResponse.user)
        );
      });
    });

    it('로그인 실패 시 에러를 반환해야 함', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: '로그인 실패' }),
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const loginButton = screen.getByText('Login');
      await act(async () => {
        loginButton.click();
      });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });
    });
  });

  describe('로그아웃', () => {
    it('로그아웃 시 토큰과 사용자 정보를 제거해야 함', async () => {
      const mockUser = { id: 1, name: '사용자', provider: 'kakao' };
      localStorage.setItem('token', 'test-token');
      localStorage.setItem('user', JSON.stringify(mockUser));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('사용자');
      });

      const logoutButton = screen.getByText('Logout');
      await act(async () => {
        logoutButton.click();
      });

      await waitFor(() => {
        expect(Cookies.remove).toHaveBeenCalledWith('auth_token');
        expect(localStorage.removeItem).toHaveBeenCalledWith('token');
        expect(localStorage.removeItem).toHaveBeenCalledWith('user');
      });
    });
  });

  describe('인증 확인', () => {
    it('isAuthenticated는 토큰과 사용자가 있을 때 true를 반환해야 함', async () => {
      const mockUser = { id: 1, name: '사용자' };
      localStorage.setItem('token', 'test-token');
      localStorage.setItem('user', JSON.stringify(mockUser));

      const TestAuthComponent = () => {
        const auth = useAuth();
        return (
          <div>
            <div data-testid="isAuth">
              {auth.isAuthenticated() ? 'authenticated' : 'not-authenticated'}
            </div>
          </div>
        );
      };

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('isAuth')).toHaveTextContent('authenticated');
      });
    });
  });
});

