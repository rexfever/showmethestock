/**
 * DailyDigestCard 컴포넌트 테스트
 */

import { render, screen } from '@testing-library/react';
import DailyDigestCard from '../../components/v3/DailyDigestCard';

describe('DailyDigestCard', () => {
  describe('has_changes가 false인 경우', () => {
    it('카드를 표시하지 않아야 함', () => {
      const dailyDigest = {
        has_changes: false,
        new_recommendations: 1,
        new_broken: 0,
        new_archived: 0
      };

      const { container } = render(<DailyDigestCard dailyDigest={dailyDigest} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('has_changes가 true인 경우', () => {
    it('신규 추천만 있을 때 카드를 표시해야 함', () => {
      const dailyDigest = {
        has_changes: true,
        new_recommendations: 2,
        new_broken: 0,
        new_archived: 0
      };

      render(<DailyDigestCard dailyDigest={dailyDigest} />);
      
      expect(screen.getByText('오늘 발생한 변화가 있습니다.')).toBeInTheDocument();
      expect(screen.getByText('• 신규 추천 2건')).toBeInTheDocument();
      expect(screen.queryByText(/관리 필요/)).not.toBeInTheDocument();
      expect(screen.queryByText(/관리 종료/)).not.toBeInTheDocument();
    });

    it('모든 변화가 있을 때 카드를 표시해야 함', () => {
      const dailyDigest = {
        has_changes: true,
        new_recommendations: 1,
        new_broken: 2,
        new_archived: 3
      };

      render(<DailyDigestCard dailyDigest={dailyDigest} />);
      
      expect(screen.getByText('오늘 발생한 변화가 있습니다.')).toBeInTheDocument();
      expect(screen.getByText('• 신규 추천 1건')).toBeInTheDocument();
      expect(screen.getByText('• 관리 필요 2건')).toBeInTheDocument();
      expect(screen.getByText('• 관리 종료 3건')).toBeInTheDocument();
    });

    it('모든 값이 0이면 카드를 표시하지 않아야 함', () => {
      const dailyDigest = {
        has_changes: true,
        new_recommendations: 0,
        new_broken: 0,
        new_archived: 0
      };

      const { container } = render(<DailyDigestCard dailyDigest={dailyDigest} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('null/undefined 처리', () => {
    it('dailyDigest가 null이면 카드를 표시하지 않아야 함', () => {
      const { container } = render(<DailyDigestCard dailyDigest={null} />);
      expect(container.firstChild).toBeNull();
    });

    it('dailyDigest가 undefined이면 카드를 표시하지 않아야 함', () => {
      const { container } = render(<DailyDigestCard dailyDigest={undefined} />);
      expect(container.firstChild).toBeNull();
    });

    it('필드가 undefined일 때도 안전하게 처리해야 함', () => {
      const dailyDigest = {
        has_changes: true,
        new_recommendations: undefined,
        new_broken: undefined,
        new_archived: undefined
      };

      const { container } = render(<DailyDigestCard dailyDigest={dailyDigest} />);
      // 모든 값이 0이므로 표시하지 않음
      expect(container.firstChild).toBeNull();
    });
  });
});


