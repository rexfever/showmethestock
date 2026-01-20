/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import Admin from '../../pages/admin';

// Mock dependencies
jest.mock('next/router', () => ({
  useRouter: jest.fn()
}));
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn()
}));
jest.mock('../../config', () => ({
  getConfig: () => ({
    backendUrl: 'http://localhost:8010'
  })
}));

// Mock fetch
global.fetch = jest.fn();

describe('Admin Page - Rescan Functionality', () => {
  const mockRouter = {
    push: jest.fn(),
    query: {}
  };

  const mockAuth = {
    isAuthenticated: () => true,
    user: { id: 1, name: 'Test Admin', is_admin: true },
    token: 'mock-token'
  };

  beforeEach(() => {
    useRouter.mockReturnValue(mockRouter);
    useAuth.mockReturnValue(mockAuth);
    fetch.mockClear();
    mockRouter.push.mockClear();
    
    // Admin 페이지 초기 로딩을 위한 API 모킹
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        stats: { total_users: 0, total_positions: 0 },
        users: [],
        scan_dates: []
      })
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Rescan Function', () => {
    test('날짜를 선택하지 않으면 경고 메시지가 표시되어야 함', async () => {
      render(<Admin />);
      
      // 로딩 완료 대기
      await waitFor(() => {
        expect(screen.queryByText('관리자 데이터를 불러오는 중...')).not.toBeInTheDocument();
      }, { timeout: 3000 });
      
      const rescanButton = screen.getByText('재스캔');
      fireEvent.click(rescanButton);
      
      await waitFor(() => {
        expect(screen.getByText('날짜를 선택해주세요.')).toBeInTheDocument();
      });
    });

    test('올바른 날짜로 재스캔 API를 호출해야 함', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          items: [
            { ticker: '005930', name: '삼성전자', score: 8.5 },
            { ticker: '000660', name: 'SK하이닉스', score: 7.2 }
          ]
        })
      };
      
      fetch.mockResolvedValueOnce(mockResponse);

      render(<Admin />);
      
      // 로딩 완료 대기
      await waitFor(() => {
        expect(screen.queryByText('관리자 데이터를 불러오는 중...')).not.toBeInTheDocument();
      }, { timeout: 3000 });
      
      // 날짜 입력
      const dateInputs = screen.getAllByDisplayValue('');
      const dateInput = dateInputs.find(input => input.type === 'date' || input.type === 'text');
      if (dateInput) {
        fireEvent.change(dateInput, { target: { value: '2025-10-01' } });
      }
      
      // 재스캔 버튼 클릭
      const rescanButton = screen.getByText('재스캔');
      fireEvent.click(rescanButton);
      
      // 확인 대화상자 승인
      window.confirm = jest.fn(() => true);
      
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          expect.stringContaining('/scan/historical')
        );
      });
    });

    test('재스캔 성공 시 성공 메시지가 표시되어야 함', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          items: [
            { ticker: '005930', name: '삼성전자', score: 8.5 },
            { ticker: '000660', name: 'SK하이닉스', score: 7.2 }
          ]
        })
      };
      
      fetch.mockResolvedValueOnce(mockResponse);
      window.confirm = jest.fn(() => true);
      window.alert = jest.fn();

      render(<Admin />);
      
      // 로딩 완료 대기
      await waitFor(() => {
        expect(screen.queryByText('관리자 데이터를 불러오는 중...')).not.toBeInTheDocument();
      }, { timeout: 3000 });
      
      // 날짜 입력
      const dateInputs = screen.getAllByDisplayValue('');
      const dateInput = dateInputs.find(input => input.type === 'date' || input.type === 'text');
      if (dateInput) {
        fireEvent.change(dateInput, { target: { value: '2025-10-01' } });
      }
      
      // 재스캔 버튼 클릭
      const rescanButton = screen.getByText('재스캔');
      fireEvent.click(rescanButton);
      
      await waitFor(() => {
        expect(window.alert).toHaveBeenCalled();
      });
    });

    test('재스캔 실패 시 오류 메시지가 표시되어야 함', async () => {
      const mockResponse = {
        ok: false,
        json: () => Promise.resolve({
          error: '스캔 실행 중 오류가 발생했습니다.'
        })
      };
      
      fetch.mockResolvedValueOnce(mockResponse);
      window.confirm = jest.fn(() => true);
      window.alert = jest.fn();

      render(<Admin />);
      
      // 로딩 완료 대기
      await waitFor(() => {
        expect(screen.queryByText('관리자 데이터를 불러오는 중...')).not.toBeInTheDocument();
      }, { timeout: 3000 });
      
      // 날짜 입력
      const dateInputs = screen.getAllByDisplayValue('');
      const dateInput = dateInputs.find(input => input.type === 'date' || input.type === 'text');
      if (dateInput) {
        fireEvent.change(dateInput, { target: { value: '2025-10-01' } });
      }
      
      // 재스캔 버튼 클릭
      const rescanButton = screen.getByText('재스캔');
      fireEvent.click(rescanButton);
      
      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith(
          '재스캔 실패: 스캔 실행 중 오류가 발생했습니다.'
        );
      });
    });

    test('네트워크 오류 시 적절한 오류 메시지가 표시되어야 함', async () => {
      fetch.mockRejectedValueOnce(new Error('Network error'));
      window.confirm = jest.fn(() => true);
      window.alert = jest.fn();

      render(<Admin />);
      
      // 날짜 입력
      const dateInput = screen.getByDisplayValue('');
      fireEvent.change(dateInput, { target: { value: '2025-10-01' } });
      
      // 재스캔 버튼 클릭
      const rescanButton = screen.getByText('재스캔');
      fireEvent.click(rescanButton);
      
      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith(
          '재스캔 중 오류가 발생했습니다.'
        );
      });
    });

    test('재스캔 중에는 로딩 상태가 표시되어야 함', async () => {
      const mockResponse = {
        ok: true,
        json: () => new Promise(resolve => {
          setTimeout(() => resolve({ items: [] }), 100);
        })
      };
      
      fetch.mockResolvedValueOnce(mockResponse);
      window.confirm = jest.fn(() => true);

      render(<Admin />);
      
      // 날짜 입력
      const dateInput = screen.getByDisplayValue('');
      fireEvent.change(dateInput, { target: { value: '2025-10-01' } });
      
      // 재스캔 버튼 클릭
      const rescanButton = screen.getByText('재스캔');
      fireEvent.click(rescanButton);
      
      // 로딩 상태 확인
      expect(screen.getByText('재스캔 중...')).toBeInTheDocument();
      expect(rescanButton).toBeDisabled();
    });
  });

  describe('Date Input Validation', () => {
    test('날짜 입력 필드가 올바르게 렌더링되어야 함', () => {
      render(<Admin />);
      
      const dateInput = screen.getByDisplayValue('');
      expect(dateInput).toBeInTheDocument();
      expect(dateInput).toHaveAttribute('type', 'date');
    });

    test('날짜 형식이 올바르게 변환되어야 함', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ items: [] })
      };
      
      fetch.mockResolvedValueOnce(mockResponse);
      window.confirm = jest.fn(() => true);

      render(<Admin />);
      
      // 날짜 입력 (YYYY-MM-DD 형식)
      const dateInput = screen.getByDisplayValue('');
      fireEvent.change(dateInput, { target: { value: '2025-10-01' } });
      
      // 재스캔 버튼 클릭
      const rescanButton = screen.getByText('재스캔');
      fireEvent.click(rescanButton);
      
      await waitFor(() => {
        // API 호출 시 YYYYMMDD 형식으로 변환되어야 함
        expect(fetch).toHaveBeenCalledWith(
          'http://localhost:8010/scan/historical?date=20251001&save_snapshot=true'
        );
      });
    });
  });

  describe('Delete Function', () => {
    test('삭제 기능이 올바른 API를 호출해야 함', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          ok: true,
          deleted_records: 5
        })
      };
      
      fetch.mockResolvedValueOnce(mockResponse);
      window.confirm = jest.fn(() => true);
      window.alert = jest.fn();

      render(<Admin />);
      
      // 날짜 입력
      const dateInput = screen.getByDisplayValue('');
      fireEvent.change(dateInput, { target: { value: '2025-10-01' } });
      
      // 삭제 버튼 클릭
      const deleteButton = screen.getByText('삭제');
      fireEvent.click(deleteButton);
      
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          'http://localhost:8010/scan/2025-10-01',
          {
            method: 'DELETE'
          }
        );
      });
    });
  });

  describe('User Authentication', () => {
    test('관리자가 아닌 사용자는 접근할 수 없어야 함', () => {
      const nonAdminAuth = {
        isAuthenticated: () => true,
        user: { id: 2, name: 'Regular User', is_admin: false },
        token: 'mock-token'
      };
      
      useAuth.mockReturnValue(nonAdminAuth);
      
      render(<Admin />);
      
      expect(screen.getByText('관리자 권한이 필요합니다.')).toBeInTheDocument();
    });

    test('로그인하지 않은 사용자는 로그인 페이지로 리다이렉트되어야 함', () => {
      const unauthenticatedAuth = {
        isAuthenticated: () => false,
        user: null,
        token: null
      };
      
      useAuth.mockReturnValue(unauthenticatedAuth);
      
      render(<Admin />);
      
      expect(mockRouter.push).toHaveBeenCalledWith('/login');
    });
  });
});
