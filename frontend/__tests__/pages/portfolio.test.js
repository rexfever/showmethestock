import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import Portfolio from '../../pages/portfolio';

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

jest.mock('../../utils/errorHandler', () => ({
  handleError: jest.fn()
}));

describe('Portfolio Page - Enhanced Features', () => {
  const mockRouter = {
    push: jest.fn()
  };

  const mockUser = {
    id: 1,
    name: '테스트 사용자',
    provider: 'local'
  };

  const mockPortfolio = [
    {
      id: 1,
      ticker: '005930',
      name: '삼성전자',
      entry_price: 70000,
      quantity: 10,
      entry_date: '2025-10-01',
      current_price: 75000,
      profit_loss: 50000,
      profit_loss_pct: 7.14,
      source: 'recommended',
      recommendation_score: 12,
      recommendation_date: '2025-10-01',
      daily_return_pct: 2.5,
      max_return_pct: 8.5,
      min_return_pct: 5.0,
      holding_days: 11
    },
    {
      id: 2,
      ticker: '000660',
      name: 'SK하이닉스',
      entry_price: 120000,
      quantity: 5,
      entry_date: '2025-10-02',
      current_price: 125000,
      profit_loss: 25000,
      profit_loss_pct: 4.17,
      source: 'personal',
      recommendation_score: null,
      recommendation_date: null,
      daily_return_pct: 1.2,
      max_return_pct: 5.2,
      min_return_pct: 3.0,
      holding_days: 10
    }
  ];

  beforeEach(() => {
    useRouter.mockReturnValue(mockRouter);
    useAuth.mockReturnValue({
      isAuthenticated: () => true,
      user: mockUser,
      loading: false,
      authChecked: true,
      logout: jest.fn()
    });
    
    // Mock fetchPortfolio
    const { fetchPortfolio } = require('../../services/portfolioService');
    fetchPortfolio.mockResolvedValue(mockPortfolio);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('개인 종목 추가 버튼이 표시된다', async () => {
    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('+ 개인 종목 추가')).toBeInTheDocument();
    });
  });

  test('개인 종목 추가 모달이 열린다', async () => {
    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('+ 개인 종목 추가')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('+ 개인 종목 추가'));

    expect(screen.getByText('개인 종목 추가')).toBeInTheDocument();
    expect(screen.getByLabelText('종목코드 *')).toBeInTheDocument();
    expect(screen.getByLabelText('종목명 *')).toBeInTheDocument();
    expect(screen.getByLabelText('매수가 (원) *')).toBeInTheDocument();
    expect(screen.getByLabelText('수량 (주) *')).toBeInTheDocument();
    expect(screen.getByLabelText('매수일 *')).toBeInTheDocument();
  });

  test('개인 종목 추가 모달이 닫힌다', async () => {
    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('+ 개인 종목 추가')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('+ 개인 종목 추가'));
    fireEvent.click(screen.getByText('취소'));

    expect(screen.queryByText('개인 종목 추가')).not.toBeInTheDocument();
  });

  test('성과 비교 섹션이 표시된다', async () => {
    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('성과 비교')).toBeInTheDocument();
    });

    expect(screen.getByText('추천종목')).toBeInTheDocument();
    expect(screen.getByText('개인종목')).toBeInTheDocument();
  });

  test('추천종목과 개인종목이 올바르게 분류되어 표시된다', async () => {
    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getAllByText('추천종목')).toHaveLength(2); // 성과 비교 섹션과 배지
    });

    // 추천종목 배지 확인
    expect(screen.getAllByText('추천종목')).toHaveLength(2);
    expect(screen.getByText('개인종목')).toBeInTheDocument();
  });

  test('포트폴리오 아이템에 소스 배지가 표시된다', async () => {
    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument();
    });

    expect(screen.getAllByText('추천종목')).toHaveLength(2);
    expect(screen.getByText('개인종목')).toBeInTheDocument();
  });

  test('일일 수익률이 표시된다', async () => {
    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('일일 수익률:')).toBeInTheDocument();
    });
  });

  test('보유일수가 표시된다', async () => {
    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('보유일수:')).toBeInTheDocument();
    });
  });

  test('개인 종목 추가 폼 입력이 작동한다', async () => {
    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('+ 개인 종목 추가')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('+ 개인 종목 추가'));

    // 모달이 열렸는지 확인
    expect(screen.getByText('개인 종목 추가')).toBeInTheDocument();

    // input 필드들을 placeholder나 name으로 찾기
    const tickerInput = screen.getByPlaceholderText('종목코드를 입력하세요');
    const nameInput = screen.getByPlaceholderText('종목명을 입력하세요');
    const priceInput = screen.getByPlaceholderText('매수가를 입력하세요');
    const quantityInput = screen.getByPlaceholderText('수량을 입력하세요');

    fireEvent.change(tickerInput, { target: { value: '035720' } });
    fireEvent.change(nameInput, { target: { value: '카카오' } });
    fireEvent.change(priceInput, { target: { value: '50000' } });
    fireEvent.change(quantityInput, { target: { value: '20' } });

    expect(tickerInput.value).toBe('035720');
    expect(nameInput.value).toBe('카카오');
    expect(priceInput.value).toBe('50000');
    expect(quantityInput.value).toBe('20');
  });

  test('빈 필드로 개인 종목 추가 시도 시 경고가 표시된다', async () => {
    // Mock alert
    window.alert = jest.fn();

    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('+ 개인 종목 추가')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('+ 개인 종목 추가'));
    fireEvent.click(screen.getByText('추가'));

    expect(window.alert).toHaveBeenCalledWith('모든 필드를 입력해주세요.');
  });

  test('로그인하지 않은 사용자는 개인 종목 추가 버튼이 보이지 않는다', async () => {
    useAuth.mockReturnValue({
      isAuthenticated: () => false,
      user: null,
      loading: false,
      authChecked: true,
      logout: jest.fn()
    });

    render(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.queryByText('+ 개인 종목 추가')).not.toBeInTheDocument();
    });
  });
});
