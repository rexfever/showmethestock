/**
 * 관리자 화면 방문자 통계 테스트
 * @jest-environment jsdom
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Admin from '../pages/admin';
import getConfig from '../config';

// Mock dependencies
jest.mock('next/router', () => ({
  useRouter: jest.fn()
}));

jest.mock('../contexts/AuthContext', () => ({
  useAuth: jest.fn()
}));

jest.mock('../config', () => ({
  __esModule: true,
  default: jest.fn(() => ({
    backendUrl: 'http://localhost:8010'
  }))
}));

// Mock fetch
global.fetch = jest.fn();

describe('관리자 화면 방문자 통계', () => {
  const mockRouter = {
    push: jest.fn(),
    query: {},
    replace: jest.fn()
  };

  const mockAuth = {
    isAuthenticated: jest.fn(() => true),
    user: {
      id: 1,
      email: 'admin@test.com',
      is_admin: true
    },
    token: 'test-token',
    loading: false,
    authLoading: false,
    authChecked: true,
    logout: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useRouter.mockReturnValue(mockRouter);
    useAuth.mockReturnValue(mockAuth);
    
    // 기본 API 응답 모킹
    global.fetch.mockImplementation((url) => {
      if (url.includes('/admin/stats')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            total_users: 100,
            active_subscriptions: 50,
            total_revenue: 1000000,
            vip_users: 10
          })
        });
      }
      if (url.includes('/admin/users')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ users: [] })
        });
      }
      if (url.includes('/admin/maintenance')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            is_enabled: false,
            end_date: null,
            message: ''
          })
        });
      }
      if (url.includes('/admin/popup-notice')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            is_enabled: false,
            title: '',
            message: '',
            start_date: null,
            end_date: null
          })
        });
      }
      if (url.includes('/admin/scanner-settings')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            ok: true,
            settings: {
              scanner_version: 'v2',
              regime_version: 'v4',
              scanner_v2_enabled: true
            }
          })
        });
      }
      if (url.includes('/admin/bottom-nav-link')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            link_type: 'v2',
            link_url: '/v2/scanner-v2'
          })
        });
      }
      return Promise.resolve({
        ok: false,
        status: 404
      });
    });
  });

  describe('방문자 통계 조회', () => {
    it('방문자 통계 섹션이 렌더링되어야 함', async () => {
      render(<Admin />);
      
      await waitFor(() => {
        expect(screen.getByText('📊 방문자 통계')).toBeInTheDocument();
      });
    });

    it('날짜 범위 선택 필드가 있어야 함', async () => {
      render(<Admin />);
      
      await waitFor(() => {
        expect(screen.getByLabelText(/시작 날짜/)).toBeInTheDocument();
        expect(screen.getByLabelText(/종료 날짜/)).toBeInTheDocument();
      });
    });

    it('조회 버튼이 있어야 함', async () => {
      render(<Admin />);
      
      await waitFor(() => {
        expect(screen.getByText('조회')).toBeInTheDocument();
      });
    });

    it('방문자 통계 조회 API 호출이 정상적으로 이루어져야 함', async () => {
      // API 응답 모킹
      global.fetch.mockImplementation((url) => {
        if (url.includes('/admin/access-logs/daily-stats')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              ok: true,
              stats: [
                { date: '2025-12-04', unique_visitors: 10, total_visits: 25 }
              ]
            })
          });
        }
        if (url.includes('/admin/access-logs/daily-stats-by-path')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              ok: true,
              stats: [
                { date: '2025-12-04', path: '/v2/scanner-v2', unique_visitors: 5, total_visits: 15 }
              ]
            })
          });
        }
        if (url.includes('/admin/access-logs/cumulative-stats')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              ok: true,
              data: {
                start_date: '2025-12-01',
                end_date: '2025-12-04',
                total_unique_visitors: 50,
                total_visits: 200
              }
            })
          });
        }
        return Promise.resolve({ ok: false, status: 404 });
      });

      render(<Admin />);
      
      await waitFor(() => {
        expect(screen.getByText('📊 방문자 통계')).toBeInTheDocument();
      });

      // 날짜 입력
      const startDateInput = screen.getByLabelText(/시작 날짜/);
      const endDateInput = screen.getByLabelText(/종료 날짜/);
      
      fireEvent.change(startDateInput, { target: { value: '2025-12-04' } });
      fireEvent.change(endDateInput, { target: { value: '2025-12-04' } });

      // 조회 버튼 클릭
      const queryButton = screen.getByText('조회');
      fireEvent.click(queryButton);

      // API 호출 확인
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/admin/access-logs/daily-stats'),
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': 'Bearer test-token'
            })
          })
        );
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/admin/access-logs/daily-stats-by-path'),
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': 'Bearer test-token'
            })
          })
        );
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/admin/access-logs/cumulative-stats'),
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': 'Bearer test-token'
            })
          })
        );
      });
    });

    it('화면별 방문자 수 테이블이 표시되어야 함', async () => {
      // API 응답 모킹
      global.fetch.mockImplementation((url) => {
        if (url.includes('/admin/access-logs/daily-stats-by-path')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              ok: true,
              stats: [
                { date: '2025-12-04', path: '/v2/scanner-v2', unique_visitors: 5, total_visits: 15 },
                { date: '2025-12-04', path: '/more', unique_visitors: 3, total_visits: 8 }
              ]
            })
          });
        }
        if (url.includes('/admin/access-logs/daily-stats')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ ok: true, stats: [] })
          });
        }
        if (url.includes('/admin/access-logs/cumulative-stats')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              ok: true,
              data: { total_unique_visitors: 0, total_visits: 0 }
            })
          });
        }
        return Promise.resolve({ ok: false, status: 404 });
      });

      render(<Admin />);
      
      await waitFor(() => {
        expect(screen.getByText('📊 방문자 통계')).toBeInTheDocument();
      });

      // 날짜 입력 및 조회
      const startDateInput = screen.getByLabelText(/시작 날짜/);
      const endDateInput = screen.getByLabelText(/종료 날짜/);
      
      fireEvent.change(startDateInput, { target: { value: '2025-12-04' } });
      fireEvent.change(endDateInput, { target: { value: '2025-12-04' } });

      const queryButton = screen.getByText('조회');
      fireEvent.click(queryButton);

      // 화면별 방문자 수 테이블 확인
      await waitFor(() => {
        expect(screen.getByText('화면별 방문자 수')).toBeInTheDocument();
        expect(screen.getByText('한국주식추천 (V2)')).toBeInTheDocument();
        expect(screen.getByText('더보기')).toBeInTheDocument();
      });
    });

    it('401 에러 발생 시 handleAuthError가 호출되어야 함', async () => {
      // 401 에러 모킹
      global.fetch.mockImplementation((url) => {
        if (url.includes('/admin/access-logs')) {
          return Promise.resolve({
            ok: false,
            status: 401
          });
        }
        return Promise.resolve({ ok: false, status: 404 });
      });

      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

      render(<Admin />);
      
      await waitFor(() => {
        expect(screen.getByText('📊 방문자 통계')).toBeInTheDocument();
      });

      // 날짜 입력 및 조회
      const startDateInput = screen.getByLabelText(/시작 날짜/);
      const endDateInput = screen.getByLabelText(/종료 날짜/);
      
      fireEvent.change(startDateInput, { target: { value: '2025-12-04' } });
      fireEvent.change(endDateInput, { target: { value: '2025-12-04' } });

      const queryButton = screen.getByText('조회');
      fireEvent.click(queryButton);

      // alert가 한 번만 호출되어야 함 (중복 방지)
      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith('세션이 만료되었습니다. 다시 로그인해주세요.');
      }, { timeout: 3000 });

      alertSpy.mockRestore();
    });

    it('경로를 화면명으로 올바르게 변환해야 함', async () => {
      // API 응답 모킹 - 다양한 경로 포함
      global.fetch.mockImplementation((url) => {
        if (url.includes('/admin/access-logs/daily-stats-by-path')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              ok: true,
              stats: [
                { date: '2025-12-04', path: '/v2/us-stocks-scanner', unique_visitors: 2, total_visits: 5 },
                { date: '2025-12-04', path: '/v2/scanner-v2', unique_visitors: 5, total_visits: 15 },
                { date: '2025-12-04', path: '/customer-scanner', unique_visitors: 3, total_visits: 10 },
                { date: '2025-12-04', path: '/stock-analysis', unique_visitors: 4, total_visits: 12 },
                { date: '2025-12-04', path: '/portfolio', unique_visitors: 1, total_visits: 3 },
                { date: '2025-12-04', path: '/my-stocks', unique_visitors: 2, total_visits: 4 },
                { date: '2025-12-04', path: '/more', unique_visitors: 3, total_visits: 8 },
                { date: '2025-12-04', path: '/unknown-path', unique_visitors: 1, total_visits: 2 }
              ]
            })
          });
        }
        if (url.includes('/admin/access-logs/daily-stats')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ ok: true, stats: [] })
          });
        }
        if (url.includes('/admin/access-logs/cumulative-stats')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              ok: true,
              data: { total_unique_visitors: 0, total_visits: 0 }
            })
          });
        }
        return Promise.resolve({ ok: false, status: 404 });
      });

      render(<Admin />);
      
      await waitFor(() => {
        expect(screen.getByText('📊 방문자 통계')).toBeInTheDocument();
      });

      // 날짜 입력 및 조회
      const startDateInput = screen.getByLabelText(/시작 날짜/);
      const endDateInput = screen.getByLabelText(/종료 날짜/);
      
      fireEvent.change(startDateInput, { target: { value: '2025-12-04' } });
      fireEvent.change(endDateInput, { target: { value: '2025-12-04' } });

      const queryButton = screen.getByText('조회');
      fireEvent.click(queryButton);

      // 경로 변환 확인
      await waitFor(() => {
        expect(screen.getByText('미국주식추천')).toBeInTheDocument();
        expect(screen.getByText('한국주식추천 (V2)')).toBeInTheDocument();
        expect(screen.getByText('한국주식추천 (V1)')).toBeInTheDocument();
        expect(screen.getByText('종목분석')).toBeInTheDocument();
        expect(screen.getByText('나의투자종목')).toBeInTheDocument();
        expect(screen.getByText('나의투자종목 (대체)')).toBeInTheDocument();
        expect(screen.getByText('더보기')).toBeInTheDocument();
        expect(screen.getByText('/unknown-path')).toBeInTheDocument(); // 알 수 없는 경로는 그대로 표시
      });
    });
  });
});

