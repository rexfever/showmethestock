/**
 * DayStatusBanner 컴포넌트 테스트
 */

import { render, screen } from '@testing-library/react';
import DayStatusBanner from '../../components/v3/DayStatusBanner';
import { DAY_STATUS_BANNER_MESSAGES } from '../../utils/v3StatusMapping';

describe('DayStatusBanner', () => {
  const mockActiveItems = [
    { ticker: '005930', name: '삼성전자', status: 'ACTIVE' }
  ];
  const mockTodayRecommendations = [
    { ticker: '000660', name: 'SK하이닉스', status: 'ACTIVE', anchor_date: '2026-01-02' }
  ];

  describe('dailyDigest가 없는 경우', () => {
    it('기본 배너를 표시해야 함', () => {
      render(
        <DayStatusBanner 
          dailyDigest={null}
          activeItems={mockActiveItems}
          todayRecommendations={[]}
        />
      );
      
      const header = screen.getByText(DAY_STATUS_BANNER_MESSAGES.BEFORE_1535.header);
      expect(header).toBeInTheDocument();
    });
  });

  describe('PRE_1535 윈도우', () => {
    it('15:35 이전 배너를 표시해야 함', () => {
      const dailyDigest = {
        window: 'PRE_1535',
        new_recommendations: 0
      };

      render(
        <DayStatusBanner 
          dailyDigest={dailyDigest}
          activeItems={mockActiveItems}
          todayRecommendations={[]}
        />
      );
      
      const header = screen.getByText(DAY_STATUS_BANNER_MESSAGES.BEFORE_1535.header);
      expect(header).toBeInTheDocument();
    });
  });

  describe('POST_1535 윈도우', () => {
    it('신규 추천이 있으면 신규 추천 배너를 표시해야 함', () => {
      const dailyDigest = {
        window: 'POST_1535',
        new_recommendations: 2
      };

      render(
        <DayStatusBanner 
          dailyDigest={dailyDigest}
          activeItems={mockActiveItems}
          todayRecommendations={mockTodayRecommendations}
        />
      );
      
      const header = screen.getByText(DAY_STATUS_BANNER_MESSAGES.NEW_RECOMMENDATIONS_AFTER_1535.header);
      expect(header).toBeInTheDocument();
    });

    it('기존 추천만 있으면 유지 배너를 표시해야 함', () => {
      const dailyDigest = {
        window: 'POST_1535',
        new_recommendations: 0
      };

      render(
        <DayStatusBanner 
          dailyDigest={dailyDigest}
          activeItems={mockActiveItems}
          todayRecommendations={[]}
        />
      );
      
      const header = screen.getByText(DAY_STATUS_BANNER_MESSAGES.MAINTAINED_AFTER_1535.header);
      expect(header).toBeInTheDocument();
    });

    it('추천이 없으면 추천 없음 배너를 표시해야 함', () => {
      const dailyDigest = {
        window: 'POST_1535',
        new_recommendations: 0
      };

      render(
        <DayStatusBanner 
          dailyDigest={dailyDigest}
          activeItems={[]}
          todayRecommendations={[]}
        />
      );
      
      const header = screen.getByText(DAY_STATUS_BANNER_MESSAGES.NO_RECOMMENDATIONS_AFTER_1535.header);
      expect(header).toBeInTheDocument();
    });
  });

  describe('HOLIDAY 윈도우', () => {
    it('휴장일 배너를 표시해야 함', () => {
      const dailyDigest = {
        window: 'HOLIDAY',
        new_recommendations: 0
      };

      render(
        <DayStatusBanner 
          dailyDigest={dailyDigest}
          activeItems={mockActiveItems}
          todayRecommendations={[]}
        />
      );
      
      const header = screen.getByText(DAY_STATUS_BANNER_MESSAGES.MARKET_HOLIDAY.header);
      expect(header).toBeInTheDocument();
    });
  });

  describe('알 수 없는 윈도우', () => {
    it('기본 배너를 표시해야 함', () => {
      const dailyDigest = {
        window: 'UNKNOWN',
        new_recommendations: 0
      };

      render(
        <DayStatusBanner 
          dailyDigest={dailyDigest}
          activeItems={mockActiveItems}
          todayRecommendations={[]}
        />
      );
      
      const header = screen.getByText(DAY_STATUS_BANNER_MESSAGES.BEFORE_1535.header);
      expect(header).toBeInTheDocument();
    });
  });
});


