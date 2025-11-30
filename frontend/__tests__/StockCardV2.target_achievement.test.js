/**
 * StockCardV2 목표 달성 및 손절 기준 테스트
 * 다양한 수익률 시나리오 테스트
 */

import { render, screen } from '@testing-library/react';
import StockCardV2 from '../v2/components/StockCardV2';

const mockOnViewChart = jest.fn();

describe('StockCardV2 - 목표 달성 및 손절 기준 상세 테스트', () => {
  
  const baseItem = {
    ticker: '005930',
    name: '삼성전자',
    score: 8.5,
    score_label: '추천',
    strategy: '포지션',
    current_price: 70000,
    change_rate: 2.5,
    flags: {
      target_profit: 0.05,  // 5%
      stop_loss: -0.03,     // -3%
      holding_period: '2주~3개월'
    },
    market: 'KOSPI',
    recommended_price: 68000,
    recommended_date: '20251127'
  };

  describe('목표 달성 케이스', () => {
    test('정확히 목표 달성 (5.0%)', () => {
      const item = {
        ...baseItem,
        current_return: 5.0,
        returns: {
          current_return: 5.0,
          max_return: 5.0,
          min_return: 2.0,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(/✅ 목표 달성/)).toBeInTheDocument();
      expect(screen.queryByText(/초과/)).not.toBeInTheDocument();
      expect(screen.queryByText(/하락/)).not.toBeInTheDocument();
    });

    test('목표 초과 달성 (7.5%)', () => {
      const item = {
        ...baseItem,
        current_return: 7.5,
        returns: {
          current_return: 7.5,
          max_return: 7.5,
          min_return: 2.0,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(/✅ 목표 달성/)).toBeInTheDocument();
      expect(screen.getByText(/\+2\.50% 초과/)).toBeInTheDocument();
      expect(screen.getByText(/🎉 목표 대비.*초과 달성/)).toBeInTheDocument();
    });

    test('목표 달성했지만 최고점에서 하락 (목표 5%, 최고 7%, 현재 5.5%)', () => {
      const item = {
        ...baseItem,
        current_return: 5.5,
        returns: {
          current_return: 5.5,
          max_return: 7.0,  // 최고점
          min_return: 2.0,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(/✅ 목표 달성/)).toBeInTheDocument();
      expect(screen.getByText(/최고.*에서.*하락/)).toBeInTheDocument();
    });
  });

  describe('목표 달성 후 수익률 감소 케이스', () => {
    test('목표 달성했으나 현재는 미달 (최고 6%, 현재 3%)', () => {
      const item = {
        ...baseItem,
        current_return: 3.0,
        returns: {
          current_return: 3.0,
          max_return: 6.0,  // 목표 초과했었음
          min_return: 1.0,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(/⚠️ 목표 달성했으나 수익률 하락/)).toBeInTheDocument();
      expect(screen.getByText(/최고.*→ 현재/)).toBeInTheDocument();
      expect(screen.getByText(/⚠️ 최고 수익률.*하락/)).toBeInTheDocument();
    });

    test('목표 달성했으나 큰 폭 하락 (최고 8%, 현재 2%)', () => {
      const item = {
        ...baseItem,
        current_return: 2.0,
        returns: {
          current_return: 2.0,
          max_return: 8.0,
          min_return: 1.0,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(/⚠️ 목표 달성했으나 수익률 하락/)).toBeInTheDocument();
      expect(screen.getByText(/최고 8\.00% → 현재 2\.00%/)).toBeInTheDocument();
    });
  });

  describe('손절 기준 케이스', () => {
    test('손절 기준 정확히 도달 (-3.0%)', () => {
      const item = {
        ...baseItem,
        current_return: -3.0,
        returns: {
          current_return: -3.0,
          max_return: 2.0,
          min_return: -3.0,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(/⚠️ 손절 기준 도달/)).toBeInTheDocument();
      expect(screen.getByText(/🛑 손절 기준.*도달 - 매도 고려 권장/)).toBeInTheDocument();
    });

    test('손절 기준보다 큰 손실 (-5.0%)', () => {
      const item = {
        ...baseItem,
        current_return: -5.0,
        returns: {
          current_return: -5.0,
          max_return: 1.0,
          min_return: -5.0,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(/⚠️ 손절 기준 도달/)).toBeInTheDocument();
      expect(screen.getByText(/🛑 손절 기준.*도달 - 매도 고려 권장/)).toBeInTheDocument();
    });

    test('손절 기준 근처 (-2.5%)', () => {
      const item = {
        ...baseItem,
        current_return: -2.5,
        returns: {
          current_return: -2.5,
          max_return: 2.0,
          min_return: -2.5,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      // 손절 기준 도달하지 않음
      expect(screen.queryByText(/⚠️ 손절 기준 도달/)).not.toBeInTheDocument();
      expect(screen.queryByText(/🛑 손절 기준/)).not.toBeInTheDocument();
    });
  });

  describe('복합 케이스', () => {
    test('목표 달성 후 손절 기준 도달 (최고 6%, 현재 -3.5%)', () => {
      const item = {
        ...baseItem,
        current_return: -3.5,
        returns: {
          current_return: -3.5,
          max_return: 6.0,  // 목표 달성했었음
          min_return: -3.5,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      // 손절 기준이 우선 표시되어야 함
      expect(screen.getByText(/⚠️ 손절 기준 도달/)).toBeInTheDocument();
      expect(screen.getByText(/🛑 손절 기준.*도달 - 매도 고려 권장/)).toBeInTheDocument();
    });

    test('목표 미달이지만 최고점에서 하락 (목표 5%, 최고 4%, 현재 2%)', () => {
      const item = {
        ...baseItem,
        current_return: 2.0,
        returns: {
          current_return: 2.0,
          max_return: 4.0,  // 목표 미달
          min_return: 1.0,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      // 목표 달성 후 하락으로 표시되지 않아야 함 (목표 미달이므로)
      expect(screen.queryByText(/⚠️ 목표 달성했으나 수익률 하락/)).not.toBeInTheDocument();
      expect(screen.getByText(/목표까지/)).toBeInTheDocument();
    });
  });

  describe('경계값 테스트', () => {
    test('목표와 정확히 같음 (5.00%)', () => {
      const item = {
        ...baseItem,
        current_return: 5.00,
        returns: {
          current_return: 5.00,
          max_return: 5.00,
          min_return: 2.0,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(/✅ 목표 달성/)).toBeInTheDocument();
    });

    test('목표보다 0.01% 높음 (5.01%)', () => {
      const item = {
        ...baseItem,
        current_return: 5.01,
        returns: {
          current_return: 5.01,
          max_return: 5.01,
          min_return: 2.0,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(/✅ 목표 달성/)).toBeInTheDocument();
      expect(screen.getByText(/\+0\.01% 초과/)).toBeInTheDocument();
    });

    test('손절 기준과 정확히 같음 (-3.00%)', () => {
      const item = {
        ...baseItem,
        current_return: -3.00,
        returns: {
          current_return: -3.00,
          max_return: 2.0,
          min_return: -3.00,
          days_elapsed: 3
        }
      };

      render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(/⚠️ 손절 기준 도달/)).toBeInTheDocument();
    });
  });
});

