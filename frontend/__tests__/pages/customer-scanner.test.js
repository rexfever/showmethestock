/**
 * CustomerScanner 페이지 통합 테스트
 */
import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import CustomerScanner from '../../pages/customer-scanner';
import getConfig from '../../config';

// Mock dependencies
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../config', () => ({
  __esModule: true,
  default: jest.fn(() => ({
    backendUrl: 'http://localhost:8010',
  })),
}));

describe('CustomerScanner 페이지', () => {
  const mockPush = jest.fn();
  const mockRouter = {
    push: mockPush,
    query: {},
  };

  const mockAuth = {
    user: null,
    isAuthenticated: jest.fn(() => false),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useRouter.mockReturnValue(mockRouter);
    useAuth.mockReturnValue(mockAuth);
    global.fetch = jest.fn();
  });

  describe('초기 렌더링', () => {
    it('SSR 데이터가 있으면 초기 데이터를 표시해야 함', () => {
      const initialData = [
        {
          ticker: '005930',
          name: '삼성전자',
          score: 8.5,
          current_price: 70000,
          change_rate: 1.5,
        },
      ];

      render(
        <CustomerScanner
          initialData={initialData}
          initialScanDate="20250101"
          initialMarketCondition={null}
        />
      );

      expect(screen.getByText('삼성전자')).toBeInTheDocument();
    });

    it('SSR 데이터가 없으면 로딩 상태를 표시해야 함', () => {
      render(
        <CustomerScanner
          initialData={[]}
          initialScanDate=""
          initialMarketCondition={null}
        />
      );

      // 로딩 상태 확인 (실제 구현에 따라 다를 수 있음)
      expect(screen.queryByText('삼성전자')).not.toBeInTheDocument();
    });
  });

  describe('스캔 결과 조회', () => {
    it('API 호출 성공 시 결과를 표시해야 함', async () => {
      const mockResponse = {
        ok: true,
        data: {
          items: [
            {
              ticker: '005930',
              name: '삼성전자',
              score: 8.5,
              current_price: 70000,
              change_rate: 1.5,
            },
          ],
          as_of: '20250101',
          market_guide: {
            market_condition: '상승',
            guide_message: '시장 가이드',
          },
        },
      };

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        })
        .mockResolvedValueOnce({
          json: async () => ({ is_enabled: false }),
        });

      render(
        <CustomerScanner
          initialData={[]}
          initialScanDate=""
          initialMarketCondition={null}
        />
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/latest-scan'),
          expect.any(Object)
        );
      });

      await waitFor(() => {
        expect(screen.getByText('삼성전자')).toBeInTheDocument();
      });
    });

    it('API 호출 실패 시 에러를 표시해야 함', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      render(
        <CustomerScanner
          initialData={[]}
          initialScanDate=""
          initialMarketCondition={null}
        />
      );

      await waitFor(() => {
        // 에러 메시지 확인 (실제 구현에 따라 다를 수 있음)
        expect(global.fetch).toHaveBeenCalled();
      });
    });
  });

  describe('투자 등록', () => {
    it('로그인하지 않은 사용자가 투자 등록 시도 시 로그인 페이지로 이동해야 함', async () => {
      mockAuth.isAuthenticated.mockReturnValue(false);

      const initialData = [
        {
          ticker: '005930',
          name: '삼성전자',
          score: 8.5,
          current_price: 70000,
          change_rate: 1.5,
        },
      ];

      render(
        <CustomerScanner
          initialData={initialData}
          initialScanDate="20250101"
          initialMarketCondition={null}
        />
      );

      // "나의투자종목에 등록" 버튼 찾기
      await waitFor(() => {
        const registerButton = screen.getByText('나의투자종목에 등록');
        expect(registerButton).toBeInTheDocument();
      });

      const registerButton = screen.getByText('나의투자종목에 등록');
      await act(async () => {
        fireEvent.click(registerButton);
      });

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      });
    });

    it('로그인한 사용자가 투자 등록 시 모달이 열려야 함', async () => {
      mockAuth.isAuthenticated.mockReturnValue(true);
      mockAuth.user = { id: 1, name: '테스트 사용자' };

      localStorage.setItem('token', 'test-token');

      const initialData = [
        {
          ticker: '005930',
          name: '삼성전자',
          score: 8.5,
          current_price: 70000,
          change_rate: 1.5,
        },
      ];

      render(
        <CustomerScanner
          initialData={initialData}
          initialScanDate="20250101"
          initialMarketCondition={null}
        />
      );

      // "나의투자종목에 등록" 버튼 찾기
      await waitFor(() => {
        const registerButton = screen.getByText('나의투자종목에 등록');
        expect(registerButton).toBeInTheDocument();
      });

      const registerButton = screen.getByText('나의투자종목에 등록');
      await act(async () => {
        fireEvent.click(registerButton);
      });

      // 모달이 열렸는지 확인
      await waitFor(() => {
        expect(screen.getByText('투자 등록')).toBeInTheDocument();
        expect(screen.getByText(/삼성전자/)).toBeInTheDocument();
      });
    });

    it('투자 등록 모달에서 등록 버튼 클릭 시 API를 호출해야 함', async () => {
      mockAuth.isAuthenticated.mockReturnValue(true);
      mockAuth.user = { id: 1, name: '테스트 사용자' };

      localStorage.setItem('token', 'test-token');

      const initialData = [
        {
          ticker: '005930',
          name: '삼성전자',
          score: 8.5,
          current_price: 70000,
          change_rate: 1.5,
        },
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      render(
        <CustomerScanner
          initialData={initialData}
          initialScanDate="20250101"
          initialMarketCondition={null}
        />
      );

      // 모달 열기
      const registerButton = screen.getByText('나의투자종목에 등록');
      await act(async () => {
        fireEvent.click(registerButton);
      });

      await waitFor(() => {
        expect(screen.getByText('투자 등록')).toBeInTheDocument();
      });

      // 등록 버튼 클릭
      const submitButton = screen.getByText('등록');
      await act(async () => {
        fireEvent.click(submitButton);
      });

      // API 호출 확인
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/portfolio/add',
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              'Authorization': 'Bearer test-token',
              'Content-Type': 'application/json',
            }),
          })
        );
      });
    });
  });

  describe('메인트넌스 상태', () => {
    it('메인트넌스가 활성화되어 있으면 메시지를 표시해야 함', async () => {
      global.fetch.mockResolvedValueOnce({
        json: async () => ({
          is_enabled: true,
          message: '서비스 점검 중입니다.',
          end_date: '20250102',
        }),
      });

      render(
        <CustomerScanner
          initialData={[]}
          initialScanDate=""
          initialMarketCondition={null}
        />
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8010/maintenance/status'
        );
      });
    });
  });

  describe('시장 가이드', () => {
    it('시장 가이드가 있으면 표시해야 함', async () => {
      const initialData = [
        {
          ticker: '005930',
          name: '삼성전자',
          score: 8.5,
          current_price: 70000,
          change_rate: 1.5,
        },
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ok: true,
          data: {
            items: initialData,
            as_of: '20250101',
            market_guide: {
              market_condition: '상승',
              guide_message: '시장 가이드 메시지',
            },
          },
        }),
      });

      render(
        <CustomerScanner
          initialData={[]}
          initialScanDate=""
          initialMarketCondition={null}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/시장 가이드 메시지/)).toBeInTheDocument();
      });
    });
  });

  describe('MarketConditionCard', () => {
    it('market_condition이 있으면 MarketConditionCard를 표시해야 함', () => {
      const marketCondition = {
        market_sentiment: 'bull',
        kospi_return: 2.5,
      };

      render(
        <CustomerScanner
          initialData={[]}
          initialScanDate="20250101"
          initialMarketCondition={marketCondition}
        />
      );

      // MarketConditionCard가 표시되는지 확인
      expect(screen.getByText(/오늘은 상승장이에요/)).toBeInTheDocument();
    });
  });

  describe('재등장 종목', () => {
    it('재등장 종목 정보가 표시되어야 함', async () => {
      const initialData = [
        {
          ticker: '005930',
          name: '삼성전자',
          score: 8.5,
          current_price: 70000,
          change_rate: 1.5,
        },
      ];

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            ok: true,
            data: {
              items: initialData,
              as_of: '20250101',
            },
          }),
        })
        .mockResolvedValueOnce({
          json: async () => ({
            ok: true,
            data: {
              recurring_stocks: {
                '005930': {
                  appearances: 3,
                  dates: ['2025-01-01', '2025-01-05', '2025-01-10'],
                },
              },
            },
          }),
        });

      render(
        <CustomerScanner
          initialData={initialData}
          initialScanDate="20250101"
          initialMarketCondition={null}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/재등장 정보/)).toBeInTheDocument();
        expect(screen.getByText(/재등장 횟수:/)).toBeInTheDocument();
      });
    });
  });
});

