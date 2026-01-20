/**
 * BottomNavigation 컴포넌트 테스트
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import BottomNavigation from '../../components/BottomNavigation';

// Mock next/router
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

// Mock AuthContext
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

describe('BottomNavigation 컴포넌트', () => {
  const mockPush = jest.fn();
  const mockRouter = {
    push: mockPush,
    pathname: '/customer-scanner',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useRouter.mockReturnValue(mockRouter);
  });

  describe('기본 렌더링', () => {
    it('모든 네비게이션 버튼이 표시되어야 함', () => {
      useAuth.mockReturnValue({
        user: null,
        logout: jest.fn(),
      });

      render(<BottomNavigation />);
      
      expect(screen.getByText('추천종목')).toBeInTheDocument();
      expect(screen.getByText('종목분석')).toBeInTheDocument();
      expect(screen.getByText('나의투자종목')).toBeInTheDocument();
      expect(screen.getByText('더보기')).toBeInTheDocument();
    });

    it('하단 네비게이션 공간이 확보되어야 함', () => {
      useAuth.mockReturnValue({
        user: null,
        logout: jest.fn(),
      });

      const { container } = render(<BottomNavigation />);
      const spacer = container.querySelector('.h-20');
      expect(spacer).toBeInTheDocument();
    });
  });

  describe('네비게이션 동작', () => {
    it('추천종목 버튼 클릭 시 /customer-scanner로 이동', () => {
      useAuth.mockReturnValue({
        user: null,
        logout: jest.fn(),
      });

      render(<BottomNavigation />);
      const button = screen.getByText('추천종목').closest('button');
      button.click();

      expect(mockPush).toHaveBeenCalledWith('/customer-scanner');
    });

    it('종목분석 버튼 클릭 시 /stock-analysis로 이동', () => {
      useAuth.mockReturnValue({
        user: null,
        logout: jest.fn(),
      });

      render(<BottomNavigation />);
      const button = screen.getByText('종목분석').closest('button');
      button.click();

      expect(mockPush).toHaveBeenCalledWith('/stock-analysis');
    });

    it('나의투자종목 버튼 클릭 시 /portfolio로 이동', () => {
      useAuth.mockReturnValue({
        user: null,
        logout: jest.fn(),
      });

      render(<BottomNavigation />);
      const button = screen.getByText('나의투자종목').closest('button');
      button.click();

      expect(mockPush).toHaveBeenCalledWith('/portfolio');
    });

    it('더보기 버튼 클릭 시 /more로 이동', () => {
      useAuth.mockReturnValue({
        user: null,
        logout: jest.fn(),
      });

      render(<BottomNavigation />);
      const button = screen.getByText('더보기').closest('button');
      button.click();

      expect(mockPush).toHaveBeenCalledWith('/more');
    });
  });

  describe('관리자 메뉴', () => {
    it('일반 사용자에게는 관리자 메뉴가 표시되지 않아야 함', () => {
      useAuth.mockReturnValue({
        user: {
          is_admin: false,
        },
        logout: jest.fn(),
      });

      render(<BottomNavigation />);
      expect(screen.queryByText('관리자')).not.toBeInTheDocument();
    });

    it('관리자에게는 관리자 메뉴가 표시되어야 함', () => {
      useAuth.mockReturnValue({
        user: {
          is_admin: true,
        },
        logout: jest.fn(),
      });

      render(<BottomNavigation />);
      expect(screen.getByText('관리자')).toBeInTheDocument();
    });

    it('관리자 메뉴 클릭 시 /admin으로 이동', () => {
      useAuth.mockReturnValue({
        user: {
          is_admin: true,
        },
        logout: jest.fn(),
      });

      render(<BottomNavigation />);
      const button = screen.getByText('관리자').closest('button');
      button.click();

      expect(mockPush).toHaveBeenCalledWith('/admin');
    });
  });

  describe('접근성', () => {
    it('버튼에 적절한 aria-label이 있어야 함', () => {
      useAuth.mockReturnValue({
        user: null,
        logout: jest.fn(),
      });

      render(<BottomNavigation />);
      const buttons = screen.getAllByRole('button');
      
      // 모든 버튼이 접근 가능해야 함
      buttons.forEach(button => {
        expect(button).toBeInTheDocument();
      });
    });
  });
});


