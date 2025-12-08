/**
 * 관리자 화면 바텀메뉴 개별 메뉴 아이템 설정 테스트
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import AdminDashboard from '../pages/admin';
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

describe('Admin Dashboard - Bottom Nav Menu Items', () => {
  const mockPush = jest.fn();
  const mockRouter = {
    push: mockPush,
  };

  const mockAdminUser = {
    id: 1,
    email: 'admin@test.com',
    name: 'Admin',
    is_admin: true,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
    useRouter.mockReturnValue(mockRouter);
    useAuth.mockReturnValue({
      user: mockAdminUser,
      token: 'mock-token',
      authChecked: true,
      authLoading: false,
      isAuthenticated: true,
    });
  });

  describe('Menu Items UI', () => {
    it('should display all menu item checkboxes', async () => {
      // Mock API responses
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ ok: true, stats: {} }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_type: 'v1' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            korean_stocks: true,
            us_stocks: true,
            stock_analysis: true,
            portfolio: true,
            more: true,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            scanner_version: 'v2',
            regime_version: 'v4',
            scanner_v2_enabled: true,
          }),
        });

      render(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('개별 메뉴 아이템 표시')).toBeInTheDocument();
        expect(screen.getByLabelText('한국주식추천')).toBeInTheDocument();
        expect(screen.getByLabelText('미국주식추천')).toBeInTheDocument();
        expect(screen.getByLabelText('종목분석')).toBeInTheDocument();
        expect(screen.getByLabelText('나의투자종목')).toBeInTheDocument();
        expect(screen.getByLabelText('더보기')).toBeInTheDocument();
      });
    });

    it('should update checkbox state when clicked', async () => {
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ ok: true, stats: {} }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_type: 'v1' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            korean_stocks: true,
            us_stocks: true,
            stock_analysis: true,
            portfolio: true,
            more: true,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            scanner_version: 'v2',
            regime_version: 'v4',
            scanner_v2_enabled: true,
          }),
        });

      render(<AdminDashboard />);

      await waitFor(() => {
        const checkbox = screen.getByLabelText('한국주식추천');
        expect(checkbox).toBeChecked();
      });

      const checkbox = screen.getByLabelText('한국주식추천');
      fireEvent.click(checkbox);

      await waitFor(() => {
        expect(checkbox).not.toBeChecked();
      });
    });
  });

  describe('Save Functionality', () => {
    it('should save all settings with single alert', async () => {
      const mockMenuItems = {
        korean_stocks: true,
        us_stocks: false,
        stock_analysis: true,
        portfolio: false,
        more: true,
      };

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ ok: true, stats: {} }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_type: 'v1' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockMenuItems,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            scanner_version: 'v2',
            regime_version: 'v4',
            scanner_v2_enabled: true,
          }),
        });

      // Save API responses
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: '바텀메뉴 링크 설정이 저장되었습니다.' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: '바텀메뉴 노출 설정이 업데이트되었습니다.' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: '바텀메뉴 메뉴 아이템 설정이 업데이트되었습니다.' }),
        });

      // Mock alert
      global.alert = jest.fn();

      render(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('설정 저장')).toBeInTheDocument();
      });

      const saveButton = screen.getByText('설정 저장');
      fireEvent.click(saveButton);

      await waitFor(() => {
        // alert가 한 번만 호출되어야 함
        expect(global.alert).toHaveBeenCalledTimes(1);
        expect(global.alert).toHaveBeenCalledWith('바텀메뉴 설정이 모두 저장되었습니다.');
      });
    });

    it('should show error alert if any save fails', async () => {
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ ok: true, stats: {} }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ link_type: 'v1' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ is_visible: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            korean_stocks: true,
            us_stocks: true,
            stock_analysis: true,
            portfolio: true,
            more: true,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            scanner_version: 'v2',
            regime_version: 'v4',
            scanner_v2_enabled: true,
          }),
        });

      // Save API responses - one fails
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: '바텀메뉴 링크 설정이 저장되었습니다.' }),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: async () => ({ detail: '저장 실패' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: '바텀메뉴 메뉴 아이템 설정이 업데이트되었습니다.' }),
        });

      global.alert = jest.fn();

      render(<AdminDashboard />);

      await waitFor(() => {
        const saveButton = screen.getByText('설정 저장');
        fireEvent.click(saveButton);
      });

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledTimes(1);
        expect(global.alert).toHaveBeenCalledWith(
          expect.stringContaining('일부 설정 저장에 실패했습니다')
        );
      });
    });
  });
});

