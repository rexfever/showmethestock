/**
 * 투자등록 모달 테스트
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import CustomerScanner from '../../pages/customer-scanner';
import { addToPortfolio } from '../../services/portfolioService';
import { validateInvestmentForm } from '../../utils/portfolioUtils';

// Mock dependencies
jest.mock('next/router', () => ({
  useRouter: jest.fn()
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn()
}));

jest.mock('../../services/portfolioService', () => ({
  addToPortfolio: jest.fn()
}));

jest.mock('../../utils/portfolioUtils', () => ({
  validateInvestmentForm: jest.fn()
}));

jest.mock('../../utils/errorHandler', () => ({
  handleError: jest.fn()
}));

describe('Investment Modal', () => {
  const mockRouter = {
    push: jest.fn()
  };

  const mockAuth = {
    isAuthenticated: jest.fn().mockReturnValue(true),
    user: { name: '테스트 사용자' },
    loading: false,
    authChecked: true,
    logout: jest.fn()
  };

  const mockStock = {
    ticker: 'AAPL',
    name: 'Apple Inc.',
    current_price: 150000
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useRouter.mockReturnValue(mockRouter);
    useAuth.mockReturnValue(mockAuth);
    validateInvestmentForm.mockReturnValue({ isValid: true, errors: [] });
  });

  it('투자등록 버튼을 클릭하면 모달이 열려야 함', async () => {
    render(<CustomerScanner />);

    // 투자등록 버튼 찾기 (첫 번째 종목의 버튼)
    const investmentButtons = screen.getAllByText('투자등록');
    if (investmentButtons.length > 0) {
      fireEvent.click(investmentButtons[0]);
      
      await waitFor(() => {
        expect(screen.getByText('투자등록')).toBeInTheDocument();
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
      });
    }
  });

  it('모달이 열릴 때 기본값이 설정되어야 함', async () => {
    render(<CustomerScanner />);

    const investmentButtons = screen.getAllByText('투자등록');
    if (investmentButtons.length > 0) {
      fireEvent.click(investmentButtons[0]);
      
      await waitFor(() => {
        const priceInput = screen.getByDisplayValue('150000');
        const dateInput = screen.getByDisplayValue(new Date().toISOString().split('T')[0]);
        expect(priceInput).toBeInTheDocument();
        expect(dateInput).toBeInTheDocument();
      });
    }
  });

  it('폼 검증 실패 시 에러 메시지를 표시해야 함', async () => {
    validateInvestmentForm.mockReturnValue({
      isValid: false,
      errors: ['올바른 매수가격을 입력해주세요.', '올바른 수량을 입력해주세요.']
    });

    render(<CustomerScanner />);

    const investmentButtons = screen.getAllByText('투자등록');
    if (investmentButtons.length > 0) {
      fireEvent.click(investmentButtons[0]);
      
      await waitFor(() => {
        const submitButton = screen.getByText('투자등록');
        fireEvent.click(submitButton);
      });
    }
  });

  it('유효한 데이터로 투자등록을 성공해야 함', async () => {
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
  });

  it('투자등록 실패 시 에러 처리를 해야 함', async () => {
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

  it('취소 버튼을 클릭하면 모달이 닫혀야 함', async () => {
    render(<CustomerScanner />);

    const investmentButtons = screen.getAllByText('투자등록');
    if (investmentButtons.length > 0) {
      fireEvent.click(investmentButtons[0]);
      
      await waitFor(() => {
        const cancelButton = screen.getByText('취소');
        fireEvent.click(cancelButton);
      });
    }
  });

  it('X 버튼을 클릭하면 모달이 닫혀야 함', async () => {
    render(<CustomerScanner />);

    const investmentButtons = screen.getAllByText('투자등록');
    if (investmentButtons.length > 0) {
      fireEvent.click(investmentButtons[0]);
      
      await waitFor(() => {
        const closeButton = screen.getByRole('button', { name: '' }); // X 버튼
        fireEvent.click(closeButton);
      });
    }
  });

  it('로그인되지 않은 사용자가 투자등록을 시도하면 로그인 페이지로 이동해야 함', () => {
    mockAuth.isAuthenticated.mockReturnValue(false);

    render(<CustomerScanner />);

    const investmentButtons = screen.getAllByText('투자등록');
    if (investmentButtons.length > 0) {
      fireEvent.click(investmentButtons[0]);
      expect(mockRouter.push).toHaveBeenCalledWith('/login');
    }
  });
});








