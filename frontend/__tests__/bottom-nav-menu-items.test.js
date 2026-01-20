/**
 * 바텀메뉴 개별 메뉴 아이템 설정 테스트
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import BottomNavigation from '../components/BottomNavigation';
import getConfig from '../config';

// Mock dependencies
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

jest.mock('../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../config', () => ({
  __esModule: true,
  default: jest.fn(() => ({
    backendUrl: 'http://localhost:8010',
  })),
}));

describe('BottomNavigation - Menu Items', () => {
  const mockPush = jest.fn();
  const mockRouter = {
    push: mockPush,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
    useRouter.mockReturnValue(mockRouter);
    useAuth.mockReturnValue({
      user: { is_admin: false },
      logout: jest.fn(),
    });
  });

  describe('Menu Items Fetching', () => {
    it('should fetch menu items on mount', async () => {
      const mockMenuItems = {
        korean_stocks: true,
        us_stocks: true,
        stock_analysis: true,
        portfolio: true,
        more: true,
      };

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_url: '/customer-scanner' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockMenuItems,
        });

      render(<BottomNavigation />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8010/bottom-nav-menu-items'
        );
      });
    });

    it('should use default values when API fails', async () => {
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_url: '/customer-scanner' }),
        })
        .mockRejectedValueOnce(new Error('API Error'));

      render(<BottomNavigation />);

      await waitFor(() => {
        // 기본값으로 모든 메뉴가 표시되어야 함
        expect(screen.getByText('한국주식추천')).toBeInTheDocument();
        expect(screen.getByText('미국주식추천')).toBeInTheDocument();
        expect(screen.getByText('종목분석')).toBeInTheDocument();
        expect(screen.getByText('더보기')).toBeInTheDocument();
      });
    });
  });

  describe('Conditional Rendering', () => {
    it('should render all menu items when all are enabled', async () => {
      const mockMenuItems = {
        korean_stocks: true,
        us_stocks: true,
        stock_analysis: true,
        portfolio: true,
        more: true,
      };

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_url: '/customer-scanner' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockMenuItems,
        });

      render(<BottomNavigation />);

      await waitFor(() => {
        expect(screen.getByText('한국주식추천')).toBeInTheDocument();
        expect(screen.getByText('미국주식추천')).toBeInTheDocument();
        expect(screen.getByText('종목분석')).toBeInTheDocument();
        expect(screen.getByText('나의투자종목')).toBeInTheDocument();
        expect(screen.getByText('더보기')).toBeInTheDocument();
      });
    });

    it('should hide menu items when disabled', async () => {
      const mockMenuItems = {
        korean_stocks: false,
        us_stocks: true,
        stock_analysis: false,
        portfolio: true,
        more: false,
      };

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_url: '/customer-scanner' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockMenuItems,
        });

      render(<BottomNavigation />);

      await waitFor(() => {
        // 숨겨진 메뉴
        expect(screen.queryByText('한국주식추천')).not.toBeInTheDocument();
        expect(screen.queryByText('종목분석')).not.toBeInTheDocument();
        expect(screen.queryByText('더보기')).not.toBeInTheDocument();

        // 표시된 메뉴
        expect(screen.getByText('미국주식추천')).toBeInTheDocument();
        expect(screen.getByText('나의투자종목')).toBeInTheDocument();
      });
    });

    it('should always show admin menu for admin users', async () => {
      useAuth.mockReturnValue({
        user: { is_admin: true },
        logout: jest.fn(),
      });

      const mockMenuItems = {
        korean_stocks: false,
        us_stocks: false,
        stock_analysis: false,
        portfolio: false,
        more: false,
      };

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_url: '/customer-scanner' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockMenuItems,
        });

      render(<BottomNavigation />);

      await waitFor(() => {
        // 관리자 메뉴는 항상 표시
        expect(screen.getByText('관리자')).toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle undefined menu items gracefully', async () => {
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_url: '/customer-scanner' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({}), // 빈 객체
        });

      render(<BottomNavigation />);

      await waitFor(() => {
        // 기본값으로 모든 메뉴가 표시되어야 함
        expect(screen.getByText('한국주식추천')).toBeInTheDocument();
      });
    });

    it('should handle null values as false', async () => {
      const mockMenuItems = {
        korean_stocks: null,
        us_stocks: undefined,
        stock_analysis: false,
        portfolio: true,
        more: true,
      };

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_url: '/customer-scanner' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockMenuItems,
        });

      render(<BottomNavigation />);

      await waitFor(() => {
        // null/undefined는 false로 처리되어야 함
        expect(screen.queryByText('한국주식추천')).not.toBeInTheDocument();
        expect(screen.queryByText('미국주식추천')).not.toBeInTheDocument();
        expect(screen.queryByText('종목분석')).not.toBeInTheDocument();
        expect(screen.getByText('나의투자종목')).toBeInTheDocument();
        expect(screen.getByText('더보기')).toBeInTheDocument();
      });
    });
  });
});

