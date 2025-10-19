/**
 * 포트폴리오 컴포넌트 테스트
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import Portfolio from '../../pages/portfolio';
import { fetchPortfolio } from '../../services/portfolioService';

// Mock dependencies
jest.mock('next/router', () => ({
  useRouter: jest.fn()
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn()
}));

jest.mock('../../services/portfolioService', () => ({
  fetchPortfolio: jest.fn()
}));

jest.mock('../../utils/portfolioUtils', () => ({
  calculateHoldingPeriod: jest.fn((date) => date ? '30일' : '-'),
  formatDate: jest.fn((date) => date ? '2025.10.10' : '-'),
  formatCurrency: jest.fn((value) => value ? value.toLocaleString() : '-'),
  formatPercentage: jest.fn((value) => value ? `${value > 0 ? '+' : ''}${value.toFixed(2)}%` : '-')
}));

jest.mock('../../utils/errorHandler', () => ({
  handleError: jest.fn()
}));

describe('Portfolio Component', () => {
  const mockRouter = {
    push: jest.fn()
  };

  const mockAuth = {
    isAuthenticated: jest.fn(),
    user: { name: '테스트 사용자', provider: 'kakao' },
    loading: false,
    authChecked: true,
    logout: jest.fn()
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

  it('인증 상태 확인 중일 때 로딩 화면을 표시해야 함', () => {
    useAuth.mockReturnValue({
      ...mockAuth,
      authChecked: false,
      loading: true
    });

    render(<Portfolio />);
    
    expect(screen.getByText('로딩 중...')).toBeInTheDocument();
  });

  it('로그인되지 않은 경우 로그인 필요 메시지를 표시해야 함', () => {
    useAuth.mockReturnValue({
      ...mockAuth,
      isAuthenticated: jest.fn().mockReturnValue(false)
    });

    render(<Portfolio />);
    
    expect(screen.getByText('로그인이 필요합니다')).toBeInTheDocument();
    expect(screen.getByText('나의 투자 종목을 관리하려면 로그인해주세요.')).toBeInTheDocument();
    expect(screen.getByText('로그인하기')).toBeInTheDocument();
  });

  it('포트폴리오가 비어있을 때 빈 상태 메시지를 표시해야 함', async () => {
    mockAuth.isAuthenticated.mockReturnValue(true);
    fetchPortfolio.mockResolvedValue([]);

    render(<Portfolio />);

    await waitFor(() => {
      expect(screen.getByText('포트폴리오가 비어있습니다')).toBeInTheDocument();
      expect(screen.getByText('관심있는 종목을 포트폴리오에 추가해보세요.')).toBeInTheDocument();
    });
  });

  it('포트폴리오 데이터를 성공적으로 로드하고 표시해야 함', async () => {
    mockAuth.isAuthenticated.mockReturnValue(true);
    fetchPortfolio.mockResolvedValue(mockPortfolio);

    render(<Portfolio />);

    await waitFor(() => {
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
      expect(screen.getByText('(AAPL)')).toBeInTheDocument();
      expect(screen.getByText('현재가: 160,000원')).toBeInTheDocument();
    });
  });

  it('홈 버튼을 클릭하면 고객 스캐너로 이동해야 함', async () => {
    mockAuth.isAuthenticated.mockReturnValue(true);
    fetchPortfolio.mockResolvedValue(mockPortfolio);

    render(<Portfolio />);

    await waitFor(() => {
      const homeButton = screen.getByText('홈');
      fireEvent.click(homeButton);
      expect(mockRouter.push).toHaveBeenCalledWith('/customer-scanner');
    });
  });

  it('종목분석 버튼을 클릭하면 종목분석 페이지로 이동해야 함', async () => {
    mockAuth.isAuthenticated.mockReturnValue(true);
    fetchPortfolio.mockResolvedValue(mockPortfolio);

    render(<Portfolio />);

    await waitFor(() => {
      const analysisButton = screen.getByText('종목분석');
      fireEvent.click(analysisButton);
      expect(mockRouter.push).toHaveBeenCalledWith('/stock-analysis');
    });
  });

  it('로그아웃 버튼을 클릭하면 로그아웃 후 고객 스캐너로 이동해야 함', async () => {
    mockAuth.isAuthenticated.mockReturnValue(true);
    fetchPortfolio.mockResolvedValue(mockPortfolio);
    mockAuth.logout.mockResolvedValue();

    render(<Portfolio />);

    await waitFor(() => {
      const logoutButton = screen.getByText('로그아웃');
      fireEvent.click(logoutButton);
    });

    await waitFor(() => {
      expect(mockAuth.logout).toHaveBeenCalled();
      expect(mockRouter.push).toHaveBeenCalledWith('/customer-scanner');
    });
  });

  it('포트폴리오 로드 실패 시 에러 처리를 해야 함', async () => {
    mockAuth.isAuthenticated.mockReturnValue(true);
    const error = new Error('포트폴리오 로드 실패');
    fetchPortfolio.mockRejectedValue(error);

    render(<Portfolio />);

    await waitFor(() => {
      expect(screen.getByText('포트폴리오가 비어있습니다')).toBeInTheDocument();
    });
  });

  it('Stock Insight 로고를 클릭하면 인덱스 페이지로 이동해야 함', async () => {
    mockAuth.isAuthenticated.mockReturnValue(true);
    fetchPortfolio.mockResolvedValue(mockPortfolio);

    render(<Portfolio />);

    await waitFor(() => {
      const logoButton = screen.getByText('Stock Insight');
      fireEvent.click(logoButton);
      expect(mockRouter.push).toHaveBeenCalledWith('/');
    });
  });
});








