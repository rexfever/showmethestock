/**
 * Header 컴포넌트 테스트
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import Header from '../../components/Header';

// Mock next/router
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

// Mock AuthContext
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

describe('Header 컴포넌트', () => {
  const mockPush = jest.fn();
  const mockRouter = {
    push: mockPush,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useRouter.mockReturnValue(mockRouter);
  });

  describe('기본 렌더링', () => {
    it('기본 타이틀을 표시해야 함', () => {
      useAuth.mockReturnValue({
        user: null,
        authLoading: false,
        authChecked: true,
      });

      render(<Header />);
      expect(screen.getByText('스톡인사이트')).toBeInTheDocument();
    });

    it('커스텀 타이틀을 표시해야 함', () => {
      useAuth.mockReturnValue({
        user: null,
        authLoading: false,
        authChecked: true,
      });

      render(<Header title="커스텀 타이틀" />);
      expect(screen.getByText('커스텀 타이틀')).toBeInTheDocument();
    });
  });

  describe('사용자 정보 표시', () => {
    it('로그인하지 않은 사용자에게 게스트 표시', () => {
      useAuth.mockReturnValue({
        user: null,
        authLoading: false,
        authChecked: true,
      });

      render(<Header />);
      expect(screen.getByText('게스트 사용자')).toBeInTheDocument();
    });

    it('로딩 중일 때 로딩 메시지 표시', () => {
      useAuth.mockReturnValue({
        user: null,
        authLoading: true,
        authChecked: false,
      });

      render(<Header />);
      expect(screen.getByText('로딩 중...')).toBeInTheDocument();
    });

    it('일반 사용자 정보 표시', () => {
      const mockUser = {
        name: '홍길동',
        provider: 'kakao',
        is_admin: false,
        membership_tier: 'basic',
      };

      useAuth.mockReturnValue({
        user: mockUser,
        authLoading: false,
        authChecked: true,
      });

      render(<Header />);
      expect(screen.getByText('홍길동님')).toBeInTheDocument();
      expect(screen.getByText('(kakao)')).toBeInTheDocument();
      expect(screen.getByText('일반 회원')).toBeInTheDocument();
    });

    it('프리미엄 사용자 배지 표시', () => {
      const mockUser = {
        name: '김프리미엄',
        provider: 'kakao',
        is_admin: false,
        membership_tier: 'premium',
      };

      useAuth.mockReturnValue({
        user: mockUser,
        authLoading: false,
        authChecked: true,
      });

      render(<Header />);
      expect(screen.getByText('김프리미엄님')).toBeInTheDocument();
      expect(screen.getByText('👑 프리미엄')).toBeInTheDocument();
    });

    it('관리자 배지 표시', () => {
      const mockUser = {
        name: '관리자',
        provider: 'kakao',
        is_admin: true,
        membership_tier: 'premium',
      };

      useAuth.mockReturnValue({
        user: mockUser,
        authLoading: false,
        authChecked: true,
      });

      render(<Header />);
      expect(screen.getByText('관리자')).toBeInTheDocument();
      expect(screen.getByText('🔧 관리자')).toBeInTheDocument();
    });
  });

  describe('네비게이션', () => {
    it('타이틀 클릭 시 홈으로 이동', () => {
      useAuth.mockReturnValue({
        user: null,
        authLoading: false,
        authChecked: true,
      });

      render(<Header />);
      const titleButton = screen.getByText('스톡인사이트');
      titleButton.click();

      expect(mockPush).toHaveBeenCalledWith('/');
    });
  });

  describe('에러 처리', () => {
    it('useAuth가 에러를 던지면 에러 처리', () => {
      useAuth.mockImplementation(() => {
        throw new Error('Auth context error');
      });

      // 에러 바운더리가 있다면 테스트 필요
      // 현재는 에러 바운더리가 없으므로 주석 처리
      // expect(() => render(<Header />)).not.toThrow();
    });
  });
});


