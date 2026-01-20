/**
 * 재등장 종목 UI 테스트
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import StockCardV2 from '../v2/components/StockCardV2';

describe('재등장 종목 UI 테스트', () => {
  const mockOnViewChart = jest.fn();

  describe('재등장 정보 카드', () => {
    it('재등장 종목인 경우 재등장 정보 카드가 표시되어야 함', () => {
      const mockItem = {
        ticker: '005930',
        name: '삼성전자',
        score: 9.5,
        score_label: '강한 매수',
        current_price: 75000,
        change_rate: 2.5,
        strategy: '스윙',
        flags: {
          target_profit: 0.05,
          stop_loss: -0.05,
          holding_period: '3~10일'
        },
        recurrence: {
          appeared_before: true,
          appear_count: 3,
          first_as_of: '20251120',
          last_as_of: '20251128',
          days_since_last: 3
        },
        recommended_date: '20251120',
        recommended_price: 73000,
        current_return: 2.74
      };

      render(<StockCardV2 item={mockItem} onViewChart={mockOnViewChart} />);

      // 재등장 정보 카드 확인
      expect(screen.getByText('재등장 정보')).toBeInTheDocument();
      expect(screen.getByText(/재등장 횟수:/)).toBeInTheDocument();
      expect(screen.getByText('3회')).toBeInTheDocument();
      expect(screen.getByText(/첫 등장:/)).toBeInTheDocument();
      expect(screen.getByText(/2025년 11월 20일/)).toBeInTheDocument();
    });

    it('재등장 종목이 아닌 경우 재등장 정보 카드가 표시되지 않아야 함', () => {
      const mockItem = {
        ticker: '000660',
        name: 'SK하이닉스',
        score: 8.0,
        score_label: '추천',
        current_price: 125000,
        change_rate: 1.8,
        strategy: '포지션',
        flags: {
          target_profit: 0.10,
          stop_loss: -0.07,
          holding_period: '2주~3개월'
        },
        recurrence: {
          appeared_before: false,
          appear_count: 0
        },
        recommended_date: '20251201',
        recommended_price: 123000,
        current_return: 1.63
      };

      render(<StockCardV2 item={mockItem} onViewChart={mockOnViewChart} />);

      // 재등장 정보 카드가 없어야 함
      expect(screen.queryByText('재등장 정보')).not.toBeInTheDocument();
    });

    it('3일 이내 재등장 시 긴급성 배지가 표시되어야 함', () => {
      const mockItem = {
        ticker: '005930',
        name: '삼성전자',
        score: 9.5,
        score_label: '강한 매수',
        current_price: 75000,
        change_rate: 2.5,
        strategy: '스윙',
        flags: {},
        recurrence: {
          appeared_before: true,
          appear_count: 3,
          first_as_of: '20251120',
          last_as_of: '20251128',
          days_since_last: 2  // 3일 이내
        },
        recommended_date: '20251120',
        recommended_price: 73000,
        current_return: 2.74
      };

      render(<StockCardV2 item={mockItem} onViewChart={mockOnViewChart} />);

      expect(screen.getByText(/⚡ 2일 만에 재등장/)).toBeInTheDocument();
    });

    it('3일 초과 재등장 시 긴급성 배지가 표시되지 않아야 함', () => {
      const mockItem = {
        ticker: '005930',
        name: '삼성전자',
        score: 9.5,
        score_label: '강한 매수',
        current_price: 75000,
        change_rate: 2.5,
        strategy: '스윙',
        flags: {},
        recurrence: {
          appeared_before: true,
          appear_count: 3,
          first_as_of: '20251120',
          last_as_of: '20251128',
          days_since_last: 5  // 3일 초과
        },
        recommended_date: '20251120',
        recommended_price: 73000,
        current_return: 2.74
      };

      render(<StockCardV2 item={mockItem} onViewChart={mockOnViewChart} />);

      expect(screen.queryByText(/⚡.*일 만에 재등장/)).not.toBeInTheDocument();
    });
  });

  describe('수익률 카드 제목', () => {
    it('재등장 종목인 경우 "최초 추천일 대비 수익률"로 표시되어야 함', () => {
      const mockItem = {
        ticker: '005930',
        name: '삼성전자',
        score: 9.5,
        score_label: '강한 매수',
        current_price: 75000,
        change_rate: 2.5,
        strategy: '스윙',
        flags: {},
        recurrence: {
          appeared_before: true,
          appear_count: 3,
          first_as_of: '20251120',
          last_as_of: '20251128',
          days_since_last: 3
        },
        recommended_date: '20251120',
        recommended_price: 73000,
        current_return: 2.74
      };

      render(<StockCardV2 item={mockItem} onViewChart={mockOnViewChart} />);

      expect(screen.getByText('최초 추천일 대비 수익률')).toBeInTheDocument();
    });

    it('일반 종목인 경우 "추천일 대비 수익률"로 표시되어야 함', () => {
      const mockItem = {
        ticker: '000660',
        name: 'SK하이닉스',
        score: 8.0,
        score_label: '추천',
        current_price: 125000,
        change_rate: 1.8,
        strategy: '포지션',
        flags: {},
        recurrence: {
          appeared_before: false,
          appear_count: 0
        },
        recommended_date: '20251201',
        recommended_price: 123000,
        current_return: 1.63
      };

      render(<StockCardV2 item={mockItem} onViewChart={mockOnViewChart} />);

      expect(screen.getByText('추천일 대비 수익률')).toBeInTheDocument();
    });
  });

  describe('매매 가이드', () => {
    it('재등장 종목도 현재 시점의 매매 가이드가 표시되어야 함', () => {
      const mockItem = {
        ticker: '005930',
        name: '삼성전자',
        score: 9.5,
        score_label: '강한 매수',
        current_price: 75000,
        change_rate: 2.5,
        strategy: '스윙',
        flags: {
          target_profit: 0.05,  // 현재 시점 전략
          stop_loss: -0.05,
          holding_period: '3~10일'
        },
        recurrence: {
          appeared_before: true,
          appear_count: 3,
          first_as_of: '20251120',
          last_as_of: '20251128',
          days_since_last: 3
        },
        recommended_date: '20251120',
        recommended_price: 73000,
        current_return: 2.74
      };

      render(<StockCardV2 item={mockItem} onViewChart={mockOnViewChart} />);

      // 매매 가이드가 표시되어야 함
      expect(screen.getByText('매매 가이드')).toBeInTheDocument();
      expect(screen.getByText(/목표 수익률:/)).toBeInTheDocument();
      expect(screen.getByText('+5.0%')).toBeInTheDocument();  // 현재 시점 전략
    });

    it('매매 가이드 제목이 "최초 추천일 기준 매매 가이드"가 아닌 "매매 가이드"여야 함', () => {
      const mockItem = {
        ticker: '005930',
        name: '삼성전자',
        score: 9.5,
        score_label: '강한 매수',
        current_price: 75000,
        change_rate: 2.5,
        strategy: '스윙',
        flags: {
          target_profit: 0.05,
          stop_loss: -0.05,
          holding_period: '3~10일'
        },
        recurrence: {
          appeared_before: true,
          appear_count: 3,
          first_as_of: '20251120',
          last_as_of: '20251128',
          days_since_last: 3
        },
        recommended_date: '20251120',
        recommended_price: 73000,
        current_return: 2.74
      };

      render(<StockCardV2 item={mockItem} onViewChart={mockOnViewChart} />);

      // "매매 가이드"로 표시되어야 함 (재등장 종목도 동일)
      expect(screen.getByText('매매 가이드')).toBeInTheDocument();
      expect(screen.queryByText('최초 추천일 기준 매매 가이드')).not.toBeInTheDocument();
    });
  });

  describe('점수/평가/전략', () => {
    it('재등장 종목의 점수와 평가가 현재 시점 기준이어야 함', () => {
      const mockItem = {
        ticker: '005930',
        name: '삼성전자',
        score: 9.5,  // 현재 시점 점수
        score_label: '강한 매수',  // 현재 시점 평가
        current_price: 75000,
        change_rate: 2.5,
        strategy: '스윙',  // 현재 시점 전략
        flags: {
          target_profit: 0.05,
          stop_loss: -0.05,
          holding_period: '3~10일'
        },
        recurrence: {
          appeared_before: true,
          appear_count: 3,
          first_as_of: '20251120',  // 최초 추천일 (과거)
          last_as_of: '20251128',
          days_since_last: 3
        },
        recommended_date: '20251120',
        recommended_price: 73000,
        current_return: 2.74
      };

      render(<StockCardV2 item={mockItem} onViewChart={mockOnViewChart} />);

      // 현재 시점의 점수와 평가가 표시되어야 함
      expect(screen.getByText('9.5점')).toBeInTheDocument();
      expect(screen.getByText(/🔥 강력 추천/)).toBeInTheDocument();
      expect(screen.getByText(/⚡ 스윙/)).toBeInTheDocument();
    });
  });

  describe('수익률 계산', () => {
    it('재등장 종목의 수익률이 최초 추천일 기준으로 계산되어야 함', () => {
      const mockItem = {
        ticker: '005930',
        name: '삼성전자',
        score: 9.5,
        score_label: '강한 매수',
        current_price: 75000,
        change_rate: 2.5,
        strategy: '스윙',
        flags: {},
        recurrence: {
          appeared_before: true,
          appear_count: 3,
          first_as_of: '20251120',
          last_as_of: '20251128',
          days_since_last: 3
        },
        recommended_date: '20251120',  // 최초 추천일
        recommended_price: 73000,  // 최초 추천일 종가
        current_return: 2.74  // (75000 - 73000) / 73000 * 100
      };

      render(<StockCardV2 item={mockItem} onViewChart={mockOnViewChart} />);

      // 수익률 카드 확인
      expect(screen.getByText('최초 추천일 대비 수익률')).toBeInTheDocument();
      expect(screen.getByText(/추천일:/)).toBeInTheDocument();
      expect(screen.getByText(/2025년 11월 20일/)).toBeInTheDocument();  // 최초 추천일
      expect(screen.getByText(/추천가:/)).toBeInTheDocument();
      expect(screen.getByText(/73,000원/)).toBeInTheDocument();  // 최초 추천가
      expect(screen.getByText(/\+2.74%/)).toBeInTheDocument();  // 최초 추천일 기준 수익률
    });
  });
});

