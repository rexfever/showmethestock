/**
 * ArchivedCardV3 컴포넌트 테스트
 */

import { render, screen, waitFor } from '@testing-library/react';
import { useRouter } from 'next/router';
import ArchivedCardV3 from '../../components/v3/ArchivedCardV3';

// NextRouter 모킹 (useRouter 사용 컴포넌트 테스트 필수)
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

// tradingDaysUtils 모킹
jest.mock('../../utils/tradingDaysUtils', () => ({
  getTradingDaysElapsed: jest.fn(() => 20),
  formatDateForDisplay: jest.fn(() => '2025.12.15')
}));

describe('ArchivedCardV3', () => {
  // useRouter 모킹 설정
  let mockRouter;
  
  beforeEach(() => {
    mockRouter = {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      pathname: '/',
      route: '/',
      query: {},
      asPath: '/',
    };
    useRouter.mockReturnValue(mockRouter);
  });

  const mockItem = {
    ticker: '005930',
    name: '삼성전자',
    recommendation_id: 'test-id',
    anchor_date: '2025-12-15',
    status: 'ARCHIVED',
    archive_return_pct: 5.5,
    archive_at: '2026-01-02T15:00:00+09:00',
    observation_period_days: 20
  };

  describe('ARCHIVED 상태 아이템', () => {
    it('카드를 표시해야 함', async () => {
      render(<ArchivedCardV3 item={mockItem} />);
      
      await waitFor(() => {
        expect(screen.getByText('삼성전자')).toBeInTheDocument();
        expect(screen.getByText('관찰 종료')).toBeInTheDocument();
        expect(screen.getByText('추천 관리 기간이 종료되었습니다.')).toBeInTheDocument();
      });
    });

    it('archive_return_pct를 사용해야 함', async () => {
      render(<ArchivedCardV3 item={mockItem} />);
      
      await waitFor(() => {
        expect(screen.getByText('+5.50%')).toBeInTheDocument();
      });
    });

    it('observation_period_days가 있으면 사용해야 함', async () => {
      render(<ArchivedCardV3 item={mockItem} />);
      
      await waitFor(() => {
        expect(screen.getByText(/관찰 20거래일/)).toBeInTheDocument();
      });
    });
  });

  describe('archive_return_pct가 없는 경우', () => {
    it('current_return을 사용해야 함', async () => {
      const itemWithoutArchiveReturn = {
        ...mockItem,
        archive_return_pct: null,
        current_return: 3.2
      };

      render(<ArchivedCardV3 item={itemWithoutArchiveReturn} />);
      
      await waitFor(() => {
        expect(screen.getByText('+3.20%')).toBeInTheDocument();
      });
    });

    it('수익률이 없으면 수익률을 표시하지 않아야 함', async () => {
      const itemWithoutReturn = {
        ...mockItem,
        archive_return_pct: null,
        current_return: null
      };

      render(<ArchivedCardV3 item={itemWithoutReturn} />);
      
      await waitFor(() => {
        expect(screen.getByText('추천 관리 기간이 종료되었습니다.')).toBeInTheDocument();
        expect(screen.queryByText(/\+.*%/)).not.toBeInTheDocument();
      });
    });
  });

  describe('ARCHIVED가 아닌 상태', () => {
    it('카드를 표시하지 않아야 함', () => {
      const activeItem = {
        ...mockItem,
        status: 'ACTIVE'
      };

      const { container } = render(<ArchivedCardV3 item={activeItem} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('보조 설명', () => {
    it('수익이 있으면 "기간 동안 유효하게 관찰되었습니다"를 표시해야 함', async () => {
      const profitItem = {
        ...mockItem,
        archive_return_pct: 5.5
      };

      render(<ArchivedCardV3 item={profitItem} />);
      
      await waitFor(() => {
        expect(screen.getByText('기간 동안 유효하게 관찰되었습니다.')).toBeInTheDocument();
      });
    });

    it('손실이 있으면 "손절 기준에는 도달하지 않았습니다"를 표시해야 함', async () => {
      const lossItem = {
        ...mockItem,
        archive_return_pct: -1.5
      };

      render(<ArchivedCardV3 item={lossItem} />);
      
      await waitFor(() => {
        expect(screen.getByText('손절 기준에는 도달하지 않았습니다.')).toBeInTheDocument();
      });
    });

    it('수익률이 없으면 기본 보조 설명을 표시해야 함', async () => {
      const noReturnItem = {
        ...mockItem,
        archive_return_pct: null,
        current_return: null
      };

      render(<ArchivedCardV3 item={noReturnItem} />);
      
      await waitFor(() => {
        expect(screen.getByText('성과와 무관하게 추천 관찰이 마무리되었습니다.')).toBeInTheDocument();
      });
    });
  });
});

