import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import More from '../../pages/more';

// Mock dependencies
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../layouts/v2/Layout', () => {
  return function MockLayout({ children, headerTitle }) {
    return (
      <div data-testid="layout">
        <div data-testid="header">{headerTitle}</div>
        {children}
      </div>
    );
  };
});

describe('More Page', () => {
  let mockRouter;
  let mockPush;

  beforeEach(() => {
    mockPush = jest.fn();
    mockRouter = {
      push: mockPush,
      pathname: '/more',
      query: {},
    };
    useRouter.mockReturnValue(mockRouter);

    // Mock useAuth
    useAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      loading: false,
      authChecked: true,
      logout: jest.fn(),
    });

    // Mock fetch
    global.fetch = jest.fn();

    // Mock localStorage
    Storage.prototype.getItem = jest.fn();
    Storage.prototype.setItem = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('초기화면 설정 표시 조건', () => {
    test('미국주식 메뉴가 활성화되어 있으면 초기화면 설정이 표시됨', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          korean_stocks: true,
          us_stocks: true,
          stock_analysis: true,
          portfolio: true,
          more: true,
        }),
      });

      render(<More />);

      await waitFor(() => {
        expect(screen.getByText('초기화면 설정')).toBeInTheDocument();
      });
    });

    test('미국주식 메뉴가 비활성화되어 있으면 초기화면 설정이 숨겨짐', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          korean_stocks: true,
          us_stocks: false,
          stock_analysis: true,
          portfolio: true,
          more: true,
        }),
      });

      render(<More />);

      await waitFor(() => {
        expect(screen.queryByText('초기화면 설정')).not.toBeInTheDocument();
      });
    });

    test('API 호출 실패 시 기본값으로 모든 메뉴 표시 (초기화면 설정 포함)', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      render(<More />);

      await waitFor(() => {
        expect(screen.getByText('초기화면 설정')).toBeInTheDocument();
      });
    });

    test('HTTP 에러 응답 시 기본값으로 모든 메뉴 표시', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      render(<More />);

      await waitFor(() => {
        expect(screen.getByText('초기화면 설정')).toBeInTheDocument();
      });
    });
  });

  describe('API 호출', () => {
    test('올바른 엔드포인트로 API 호출', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ us_stocks: true }),
      });

      render(<More />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/bottom-nav-menu-items')
        );
      });
    });

    test('개발 환경에서 localhost:8010 사용', async () => {
      process.env.NODE_ENV = 'development';
      
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ us_stocks: true }),
      });

      render(<More />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8010/bottom-nav-menu-items'
        );
      });
    });
  });

  describe('초기화면 설정 기능', () => {
    beforeEach(() => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ us_stocks: true }),
      });
    });

    test('localStorage에서 저장된 설정을 읽어옴', async () => {
      Storage.prototype.getItem.mockReturnValue('us');

      render(<More />);

      await waitFor(() => {
        const usButton = screen.getByText('미국주식추천').closest('button');
        expect(usButton).toHaveClass('border-blue-500');
      });
    });

    test('한국주식추천 선택 시 localStorage에 저장', async () => {
      render(<More />);

      await waitFor(() => {
        const koreanButton = screen.getByText('한국주식추천').closest('button');
        fireEvent.click(koreanButton);
      });

      expect(Storage.prototype.setItem).toHaveBeenCalledWith('initialScreen', 'korean');
    });

    test('미국주식추천 선택 시 localStorage에 저장', async () => {
      render(<More />);

      await waitFor(() => {
        const usButton = screen.getByText('미국주식추천').closest('button');
        fireEvent.click(usButton);
      });

      expect(Storage.prototype.setItem).toHaveBeenCalledWith('initialScreen', 'us');
    });
  });

  describe('사용자 인증 상태', () => {
    test('로그인하지 않은 경우 게스트 UI 표시', () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ us_stocks: true }),
      });

      render(<More />);

      expect(screen.getByText('게스트 사용자')).toBeInTheDocument();
      expect(screen.getByText('로그인하기')).toBeInTheDocument();
    });

    test('로그인한 경우 사용자 정보 표시', async () => {
      useAuth.mockReturnValue({
        isAuthenticated: true,
        user: {
          name: '테스트유저',
          email: 'test@example.com',
          is_admin: false,
          membership_tier: 'free',
        },
        loading: false,
        authChecked: true,
        logout: jest.fn(),
      });

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ us_stocks: true }),
      });

      render(<More />);

      await waitFor(() => {
        expect(screen.getByText('테스트유저님')).toBeInTheDocument();
      });
    });

    test('로그아웃 버튼 클릭 시 로그아웃 처리', async () => {
      const mockLogout = jest.fn();
      useAuth.mockReturnValue({
        isAuthenticated: true,
        user: {
          name: '테스트유저',
          email: 'test@example.com',
        },
        loading: false,
        authChecked: true,
        logout: mockLogout,
      });

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ us_stocks: true }),
      });

      render(<More />);

      await waitFor(() => {
        const logoutButton = screen.getByText('로그아웃');
        fireEvent.click(logoutButton);
      });

      expect(mockLogout).toHaveBeenCalled();
    });
  });

  describe('로딩 상태', () => {
    test('초기 로딩 중에는 스켈레톤 UI 표시', () => {
      global.fetch.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<More />);

      // InitialScreenSetting 컴포넌트의 스켈레톤 확인
      const skeletons = screen.getAllByRole('generic').filter(
        el => el.className.includes('animate-pulse')
      );
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });
});
