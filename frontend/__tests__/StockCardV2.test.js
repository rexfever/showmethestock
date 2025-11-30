/**
 * StockCardV2 컴포넌트 테스트
 * 목표 수익률 달성, 손절 기준, 수익률 감소 케이스 테스트
 */

import { render, screen } from '@testing-library/react';
import StockCardV2 from '../v2/components/StockCardV2';

// Mock 함수
const mockOnViewChart = jest.fn();

describe('StockCardV2 - 목표 수익률 및 손절 기준 표시', () => {
  
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
    recommended_date: '20251127',
    current_return: 2.94,  // (70000 - 68000) / 68000 * 100
    returns: {
      current_return: 2.94,
      max_return: 3.5,
      min_return: 1.0,
      days_elapsed: 3
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('목표 미달성 상태 표시', () => {
    const item = {
      ...baseItem,
      current_return: 3.0,  // 목표 5% 미달
      returns: {
        current_return: 3.0,
        max_return: 3.5,
        min_return: 1.0,
        days_elapsed: 3
      }
    };

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 목표까지 남은 수익률 표시 확인
    expect(screen.getByText(/목표까지/)).toBeInTheDocument();
    expect(screen.getByText(/2\.00%/)).toBeInTheDocument(); // 5% - 3% = 2%
  });

  test('목표 달성 상태 표시', () => {
    const item = {
      ...baseItem,
      current_return: 5.0,  // 목표 5% 달성
      returns: {
        current_return: 5.0,
        max_return: 5.0,
        min_return: 1.0,
        days_elapsed: 3
      }
    };

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 목표 달성 표시 확인
    expect(screen.getByText(/✅ 목표 달성/)).toBeInTheDocument();
  });

  test('목표 초과 달성 상태 표시', () => {
    const item = {
      ...baseItem,
      current_return: 7.5,  // 목표 5% 초과 달성
      returns: {
        current_return: 7.5,
        max_return: 7.5,
        min_return: 1.0,
        days_elapsed: 3
      }
    };

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 초과 달성 표시 확인
    expect(screen.getByText(/✅ 목표 달성/)).toBeInTheDocument();
    expect(screen.getByText(/\+2\.50% 초과/)).toBeInTheDocument();
    expect(screen.getByText(/🎉 목표 대비.*초과 달성/)).toBeInTheDocument();
  });

  test('목표 달성 후 수익률 감소 상태 표시', () => {
    const item = {
      ...baseItem,
      current_return: 3.0,  // 현재는 목표 미달
      returns: {
        current_return: 3.0,
        max_return: 6.0,  // 최고는 목표 초과
        min_return: 1.0,
        days_elapsed: 3
      }
    };

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 목표 달성했으나 하락 표시 확인
    expect(screen.getByText(/⚠️ 목표 달성했으나 수익률 하락/)).toBeInTheDocument();
    expect(screen.getByText(/최고.*→ 현재/)).toBeInTheDocument();
    expect(screen.getByText(/⚠️ 최고 수익률.*하락/)).toBeInTheDocument();
  });

  test('목표 달성 중이지만 최고점에서 하락 상태 표시', () => {
    const item = {
      ...baseItem,
      current_return: 5.5,  // 목표는 달성했지만
      returns: {
        current_return: 5.5,
        max_return: 7.0,  // 최고점보다 낮음
        min_return: 1.0,
        days_elapsed: 3
      }
    };

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 목표 달성했지만 하락 표시 확인
    expect(screen.getByText(/✅ 목표 달성/)).toBeInTheDocument();
    expect(screen.getByText(/최고.*에서.*하락/)).toBeInTheDocument();
  });

  test('손절 기준 도달 상태 표시', () => {
    const item = {
      ...baseItem,
      current_return: -3.5,  // 손절 기준 -3% 도달
      returns: {
        current_return: -3.5,
        max_return: 2.0,
        min_return: -3.5,
        days_elapsed: 3
      }
    };

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 손절 기준 도달 표시 확인
    expect(screen.getByText(/⚠️ 손절 기준 도달/)).toBeInTheDocument();
    expect(screen.getByText(/🛑 손절 기준.*도달 - 매도 고려 권장/)).toBeInTheDocument();
  });

  test('손절 기준보다 더 큰 손실 상태 표시', () => {
    const item = {
      ...baseItem,
      current_return: -5.0,  // 손절 기준보다 더 큰 손실
      returns: {
        current_return: -5.0,
        max_return: 1.0,
        min_return: -5.0,
        days_elapsed: 3
      }
    };

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 손절 기준 도달 표시 확인
    expect(screen.getByText(/⚠️ 손절 기준 도달/)).toBeInTheDocument();
  });

  test('returns 객체가 없는 경우 처리', () => {
    const item = {
      ...baseItem,
      current_return: 5.0,
      returns: undefined  // returns 객체 없음
    };

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 에러 없이 렌더링되는지 확인
    expect(screen.getByText('삼성전자')).toBeInTheDocument();
  });

  test('max_return이 없는 경우 처리', () => {
    const item = {
      ...baseItem,
      current_return: 5.0,
      returns: {
        current_return: 5.0,
        max_return: null,
        min_return: null,
        days_elapsed: 3
      }
    };

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 에러 없이 렌더링되는지 확인
    expect(screen.getByText('삼성전자')).toBeInTheDocument();
  });

  test('targetProfit이 없는 경우 목표 달성 섹션 미표시', () => {
    const item = {
      ...baseItem,
      flags: {
        stop_loss: -0.03,
        holding_period: '2주~3개월'
        // target_profit 없음
      },
      current_return: 5.0
    };

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 목표 달성 섹션이 표시되지 않는지 확인
    expect(screen.queryByText(/목표 수익률/)).not.toBeInTheDocument();
  });
});

