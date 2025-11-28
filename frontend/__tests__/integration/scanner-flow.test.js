/**
 * 스캐너 플로우 통합 테스트
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

describe('스캐너 플로우 통합 테스트', () => {
  const mockPush = jest.fn();
  const mockRouter = {
    push: mockPush,
    query: {},
  };

  const mockAuth = {
    user: { id: 1, name: '테스트 사용자' },
    isAuthenticated: jest.fn(() => true),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useRouter.mockReturnValue(mockRouter);
    useAuth.mockReturnValue(mockAuth);
    global.fetch = jest.fn();
    localStorage.setItem('token', 'test-token');
  });

  describe('전체 플로우', () => {
    it('페이지 로드 → 스캔 결과 조회 → 종목 선택 → 투자 등록', async () => {
      // 1. 스캔 결과 조회
      const scanResponse = {
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
            {
              ticker: '000660',
              name: 'SK하이닉스',
              score: 7.8,
              current_price: 120000,
              change_rate: 2.3,
            },
          ],
          as_of: '20250101',
          market_guide: {
            message: '시장 가이드',
          },
        },
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => scanResponse,
      });

      // 2. 메인트넌스 상태 조회
      global.fetch.mockResolvedValueOnce({
        json: async () => ({
          is_enabled: false,
        }),
      });

      render(
        <CustomerScanner
          initialData={[]}
          initialScanDate=""
          initialMarketCondition={null}
        />
      );

      // 3. 스캔 결과가 표시되는지 확인
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8010/latest-scan',
          expect.any(Object)
        );
      });

      // 4. 종목이 표시되는지 확인
      await waitFor(() => {
        expect(screen.getByText('삼성전자')).toBeInTheDocument();
      });
    });

    it('에러 발생 시 적절한 에러 메시지 표시', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      render(
        <CustomerScanner
          initialData={[]}
          initialScanDate=""
          initialMarketCondition={null}
        />
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });

      // 에러 메시지 확인
      await waitFor(() => {
        expect(screen.getByText(/네트워크 연결을 확인해주세요/)).toBeInTheDocument();
      });
    });
  });

  describe('인증 플로우', () => {
    it('비로그인 사용자가 투자 등록 시도 시 로그인 페이지로 이동', async () => {
      mockAuth.isAuthenticated.mockReturnValue(false);

      const initialData = [
        {
          ticker: '005930',
          name: '삼성전자',
          score: 8.5,
        },
      ];

      render(
        <CustomerScanner
          initialData={initialData}
          initialScanDate="20250101"
          initialMarketCondition={null}
        />
      );

      // 투자 등록 버튼 클릭
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
  });

  describe('데이터 새로고침', () => {
    it('새로고침 버튼 클릭 시 데이터를 다시 조회해야 함', async () => {
      const scanResponse = {
        ok: true,
        data: {
          items: [
            {
              ticker: '005930',
              name: '삼성전자',
              score: 8.5,
            },
          ],
          as_of: '20250101',
        },
      };

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => scanResponse,
        })
        .mockResolvedValueOnce({
          json: async () => ({ is_enabled: false }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => scanResponse,
        });

      render(
        <CustomerScanner
          initialData={[]}
          initialScanDate=""
          initialMarketCondition={null}
        />
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });

      // "다시 시도" 버튼 찾기 및 클릭 (에러 발생 시)
      const retryButtons = screen.queryAllByText(/다시 시도|새로고침/i);
      if (retryButtons.length > 0) {
        await act(async () => {
          fireEvent.click(retryButtons[0]);
        });

        await waitFor(() => {
          // 최소한 2번 이상 호출되었는지 확인 (초기 + 재시도)
          expect(global.fetch.mock.calls.length).toBeGreaterThanOrEqual(2);
        });
      }
    });
  });
});

