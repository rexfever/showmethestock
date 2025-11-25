/**
 * customer-scanner.js 네비게이션 테스트
 * - 다른 페이지에서 돌아왔을 때 SSR 데이터가 없어도 작동하는지 테스트
 * - 클라이언트 API 자동 호출 기능 테스트
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import CustomerScanner from '../pages/customer-scanner';

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

// Mock AuthContext
jest.mock('../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

// Mock getConfig
jest.mock('../config', () => ({
  __esModule: true,
  default: jest.fn(() => ({
    backendUrl: 'http://localhost:8000',
  })),
}));

describe('CustomerScanner Navigation', () => {
  const mockRouter = {
    push: jest.fn(),
    query: {},
    pathname: '/customer-scanner',
  };

  const mockAuth = {
    user: null,
    isAuthenticated: jest.fn(() => false),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useRouter.mockReturnValue(mockRouter);
    useAuth.mockReturnValue(mockAuth);
    
    // Mock fetch
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('SSR 데이터가 있을 때', () => {
    it('초기 데이터를 바로 표시해야 함', async () => {
      const mockInitialData = [
        {
          ticker: '005930',
          name: '삼성전자',
          score: 8.5,
          current_price: 75000,
          volume: 1000000,
          change_rate: 2.5,
        },
      ];

      render(
        <CustomerScanner
          initialData={mockInitialData}
          initialScanFile="scan-20250101.json"
          initialScanDate="2025-01-01"
        />
      );

      await waitFor(() => {
        expect(screen.getByText('삼성전자')).toBeInTheDocument();
      });
    });
  });

  describe('SSR 데이터가 없을 때', () => {
    it('클라이언트 API를 자동으로 호출해야 함', async () => {
      const mockApiResponse = {
        ok: true,
        data: {
          items: [
            {
              ticker: '035720',
              name: '카카오',
              score: 9.0,
              current_price: 85000,
              volume: 500000,
              change_rate: 3.2,
            },
          ],
          as_of: '2025-01-01',
        },
        file: 'scan-20250101.json',
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockApiResponse,
      });

      render(
        <CustomerScanner
          initialData={[]}
          initialScanFile=""
          initialScanDate=""
        />
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/latest-scan',
          expect.objectContaining({
            method: 'GET',
            headers: expect.any(Object),
          })
        );
      });
    });

    it('API 호출 중 로딩 화면을 표시해야 함', async () => {
      global.fetch.mockImplementation(() => new Promise(() => {})); // 무한 pending

      render(
        <CustomerScanner
          initialData={[]}
          initialScanFile=""
          initialScanDate=""
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/스캔 결과를 불러오는 중/)).toBeInTheDocument();
      });
    });

    it('API 호출 실패 시 에러 메시지를 표시해야 함', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      render(
        <CustomerScanner
          initialData={[]}
          initialScanFile=""
          initialScanDate=""
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/네트워크 연결을 확인해주세요/)).toBeInTheDocument();
      });
    });
  });

  describe('메인트넌스 모드', () => {
    it('메인트넌스가 활성화되면 점검 페이지를 표시해야 함', async () => {
      const mockMaintenanceResponse = {
        is_enabled: true,
        end_date: '2025-01-31',
        message: '점검 중입니다',
      };

      global.fetch.mockImplementation((url) => {
        if (url.includes('/maintenance/status')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockMaintenanceResponse,
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ ok: true, data: { items: [] } }),
        });
      });

      render(
        <CustomerScanner
          initialData={[]}
          initialScanFile=""
          initialScanDate=""
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/서비스 점검 중/)).toBeInTheDocument();
      });
    });

    it('점검 페이지에서 메인 페이지로 이동할 수 있어야 함', async () => {
      const mockMaintenanceResponse = {
        is_enabled: true,
        end_date: '2025-01-31',
        message: '점검 중입니다',
      };

      global.fetch.mockImplementation((url) => {
        if (url.includes('/maintenance/status')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockMaintenanceResponse,
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ ok: true, data: { items: [] } }),
        });
      });

      render(
        <CustomerScanner
          initialData={[]}
          initialScanFile=""
          initialScanDate=""
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/메인 페이지로 이동/)).toBeInTheDocument();
      });

      const backButton = screen.getByText(/메인 페이지로 이동/);
      fireEvent.click(backButton);

      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith('/');
      });
    });
  });

  describe('재등장 종목', () => {
    it('재등장 종목 정보를 표시해야 함', async () => {
      const mockInitialData = [
        {
          ticker: '005930',
          name: '삼성전자',
          score: 8.5,
          current_price: 75000,
          volume: 1000000,
          change_rate: 2.5,
        },
      ];

      const mockRecurringStocksResponse = {
        ok: true,
        data: {
          recurring_stocks: {
            '005930': {
              appearances: 3,
              dates: ['2025-01-01', '2025-01-02', '2025-01-03'],
            },
          },
        },
      };

      global.fetch.mockImplementation((url) => {
        if (url.includes('/recurring-stocks')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockRecurringStocksResponse,
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ ok: true, data: { items: [] } }),
        });
      });

      render(
        <CustomerScanner
          initialData={mockInitialData}
          initialScanFile="scan-20250101.json"
          initialScanDate="2025-01-01"
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/재등장 정보/)).toBeInTheDocument();
        expect(screen.getByText(/재등장 횟수: 3회/)).toBeInTheDocument();
      });
    });
  });
});




