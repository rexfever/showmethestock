/**
 * 포트폴리오 플로우 통합 테스트
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import CustomerScanner from '../../pages/customer-scanner';
import Portfolio from '../../pages/portfolio';
import { addToPortfolio, fetchPortfolio } from '../../services/portfolioService';

// Mock dependencies
jest.mock('next/router', () => ({
  useRouter: jest.fn()
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn()
}));

jest.mock('../../services/portfolioService', () => ({
  addToPortfolio: jest.fn(),
  fetchPortfolio: jest.fn()
}));

jest.mock('../../utils/portfolioUtils', () => ({
  validateInvestmentForm: jest.fn(() => ({ isValid: true, errors: [] })),
  calculateHoldingPeriod: jest.fn(() => '30일'),
  formatDate: jest.fn(() => '2025.10.10'),
  formatCurrency: jest.fn((value) => value ? value.toLocaleString() : '-'),
  formatPercentage: jest.fn((value) => value ? `${value > 0 ? '+' : ''}${value.toFixed(2)}%` : '-')
}));

jest.mock('../../utils/errorHandler', () => ({
  handleError: jest.fn()
}));

describe('Portfolio Flow Integration', () => {
  const mockRouter = {
    push: jest.fn()
  };

  const mockAuth = {
    isAuthenticated: jest.fn().mockReturnValue(true),
    user: { name: '테스트 사용자', provider: 'kakao' },
    loading: false,
    authChecked: true,
    logout: jest.fn()
  };

  const mockStock = {
    ticker: 'AAPL',
    name: 'Apple Inc.',
    current_price: 150000
  };

  const mockPortfolio = [
    {
      id: 1,
      ticker: 'AAPL',
      name: 'Apple Inc.',
      entry_price: 150000,
      quantity: 10,
      current_price: 160000,
      profit_loss: 100000,
      profit_loss_pct: 6.67,
      entry_date: '2025-09-10'
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    useRouter.mockReturnValue(mockRouter);
    useAuth.mockReturnValue(mockAuth);
  });

  describe('투자등록에서 포트폴리오까지의 플로우', () => {
    it('고객 스캐너에서 투자등록 후 포트폴리오에서 확인할 수 있어야 함', async () => {
      // 1. 고객 스캐너에서 투자등록
      addToPortfolio.mockResolvedValue({ success: true });
      
      render(<CustomerScanner />);

      const investmentButtons = screen.getAllByText('투자등록');
      if (investmentButtons.length > 0) {
        fireEvent.click(investmentButtons[0]);
        
        await waitFor(() => {
          const quantityInput = screen.getByPlaceholderText('수량을 입력하세요');
          fireEvent.change(quantityInput, { target: { value: '10' } });
          
          const submitButton = screen.getByText('투자등록');
          fireEvent.click(submitButton);
        });

        await waitFor(() => {
          expect(addToPortfolio).toHaveBeenCalledWith({
            ticker: 'AAPL',
            name: 'Apple Inc.',
            entry_price: '150000',
            quantity: '10',
            entry_date: new Date().toISOString().split('T')[0]
          });
        });
      }

      // 2. 포트폴리오 페이지로 이동
      fetchPortfolio.mockResolvedValue(mockPortfolio);
      
      render(<Portfolio />);

      await waitFor(() => {
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
        expect(screen.getByText('(AAPL)')).toBeInTheDocument();
        expect(screen.getByText('현재가: 160,000원')).toBeInTheDocument();
      });
    });

    it('포트폴리오에서 홈 버튼을 클릭하면 고객 스캐너로 이동해야 함', async () => {
      fetchPortfolio.mockResolvedValue(mockPortfolio);
      
      render(<Portfolio />);

      await waitFor(() => {
        const homeButton = screen.getByText('홈');
        fireEvent.click(homeButton);
        expect(mockRouter.push).toHaveBeenCalledWith('/customer-scanner');
      });
    });

    it('고객 스캐너에서 나의투자종목 버튼을 클릭하면 포트폴리오로 이동해야 함', async () => {
      render(<CustomerScanner />);

      const portfolioButton = screen.getByText('나의투자종목');
      fireEvent.click(portfolioButton);
      
      expect(mockRouter.push).toHaveBeenCalledWith('/portfolio');
    });
  });

  describe('에러 처리 플로우', () => {
    it('투자등록 실패 시 적절한 에러 처리를 해야 함', async () => {
      const error = new Error('투자등록 실패');
      addToPortfolio.mockRejectedValue(error);

      render(<CustomerScanner />);

      const investmentButtons = screen.getAllByText('투자등록');
      if (investmentButtons.length > 0) {
        fireEvent.click(investmentButtons[0]);
        
        await waitFor(() => {
          const quantityInput = screen.getByPlaceholderText('수량을 입력하세요');
          fireEvent.change(quantityInput, { target: { value: '10' } });
          
          const submitButton = screen.getByText('투자등록');
          fireEvent.click(submitButton);
        });
      }
    });

    it('포트폴리오 로드 실패 시 빈 상태를 표시해야 함', async () => {
      const error = new Error('포트폴리오 로드 실패');
      fetchPortfolio.mockRejectedValue(error);

      render(<Portfolio />);

      await waitFor(() => {
        expect(screen.getByText('포트폴리오가 비어있습니다')).toBeInTheDocument();
      });
    });
  });

  describe('인증 플로우', () => {
    it('로그인되지 않은 사용자가 투자등록을 시도하면 로그인 페이지로 이동해야 함', () => {
      mockAuth.isAuthenticated.mockReturnValue(false);

      render(<CustomerScanner />);

      const investmentButtons = screen.getAllByText('투자등록');
      if (investmentButtons.length > 0) {
        fireEvent.click(investmentButtons[0]);
        expect(mockRouter.push).toHaveBeenCalledWith('/login');
      }
    });

    it('로그인되지 않은 사용자가 포트폴리오에 접근하면 로그인 필요 메시지를 표시해야 함', () => {
      mockAuth.isAuthenticated.mockReturnValue(false);

      render(<Portfolio />);
      
      expect(screen.getByText('로그인이 필요합니다')).toBeInTheDocument();
    });
  });
});





