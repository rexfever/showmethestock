/**
 * StockCardV2 전략 표시 테스트
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import StockCardV2 from '../../v2/components/StockCardV2';

describe('StockCardV2 Strategy Display', () => {
  const mockOnViewChart = jest.fn();

  const createMockItem = (overrides = {}) => ({
    ticker: '206650',
    name: '유바이오로직스',
    score: 9.0,
    score_label: '매수 후보',
    current_price: 12740,
    change_rate: 2.17,
    market: null,
    flags: {},
    returns: {},
    ...overrides
  });

  test('strategy가 직접 제공된 경우 표시', () => {
    const item = createMockItem({
      strategy: '포지션',
      flags: {}
    });

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 전략 이름이 표시되어야 함
    expect(screen.getByText('포지션')).toBeInTheDocument();
    // 전략 설명이 표시되어야 함
    expect(screen.getByText('중기 추세 추종 (2주~3개월)')).toBeInTheDocument();
  });

  test('strategy가 null이고 flags.trading_strategy가 있는 경우', () => {
    const item = createMockItem({
      strategy: null,
      flags: {
        trading_strategy: '스윙',
        label: '강한 매수'
      }
    });

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // flags.trading_strategy에서 가져온 전략이 표시되어야 함
    expect(screen.getByText('스윙')).toBeInTheDocument();
    expect(screen.getByText('단기 매매 (3~10일)')).toBeInTheDocument();
  });

  test('strategy와 flags.trading_strategy 모두 없는 경우 기본값 "관찰" 표시', () => {
    const item = createMockItem({
      strategy: null,
      flags: {}
    });

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 기본값 "관찰"이 표시되어야 함
    expect(screen.getByText('관찰')).toBeInTheDocument();
    expect(screen.getByText('관심 종목 (매수 대기)')).toBeInTheDocument();
  });

  test('strategy가 빈 문자열인 경우 flags.trading_strategy 사용', () => {
    const item = createMockItem({
      strategy: '',
      flags: {
        trading_strategy: '장기'
      }
    });

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // flags.trading_strategy가 표시되어야 함
    expect(screen.getByText('장기')).toBeInTheDocument();
    expect(screen.getByText('장기 투자 (3개월 이상)')).toBeInTheDocument();
  });

  test('모든 전략 타입이 올바른 아이콘과 함께 표시되는지', () => {
    const strategies = [
      { name: '스윙', icon: '⚡', desc: '단기 매매 (3~10일)' },
      { name: '포지션', icon: '📈', desc: '중기 추세 추종 (2주~3개월)' },
      { name: '장기', icon: '🌱', desc: '장기 투자 (3개월 이상)' },
      { name: '관찰', icon: '⏳', desc: '관심 종목 (매수 대기)' }
    ];

    strategies.forEach(({ name, desc }) => {
      const item = createMockItem({
        strategy: name,
        flags: {}
      });

      const { unmount } = render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
      
      expect(screen.getByText(name)).toBeInTheDocument();
      expect(screen.getByText(desc)).toBeInTheDocument();
      
      unmount();
    });
  });

  test('전략 배지에 아이콘과 텍스트가 모두 표시되는지', () => {
    const item = createMockItem({
      strategy: '관찰',
      flags: {}
    });

    render(<StockCardV2 item={item} onViewChart={mockOnViewChart} />);
    
    // 전략 배지를 찾음
    const strategyBadge = screen.getByText('관찰').closest('span');
    expect(strategyBadge).toBeInTheDocument();
    
    // 배지 안에 아이콘(모래시계)과 텍스트가 모두 있어야 함
    expect(strategyBadge).toHaveTextContent('⏳');
    expect(strategyBadge).toHaveTextContent('관찰');
  });
});

