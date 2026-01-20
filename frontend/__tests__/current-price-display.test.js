/**
 * current_price 표시 변경사항 테스트
 * 
 * 변경사항:
 * - current_price가 오늘 종가를 우선 표시하도록 변경
 */
import { render, screen } from '@testing-library/react';
import StockCardV2 from '../v2/components/StockCardV2';

describe('Current Price Display', () => {
  test('과거 스캔인 경우 오늘 종가를 표시', () => {
    const mockItem = {
      ticker: '005930',
      name: '삼성전자',
      current_price: 75000, // 오늘 종가 (백엔드에서 설정됨)
      recommended_price: 72000, // 스캔일 종가
      recommended_date: '20251126', // 과거 날짜
      returns: {
        current_price: 75000, // 오늘 종가
        current_return: 4.17
      },
      change_rate: 2.5,
      score: 10.5,
      score_label: '강력 추천',
      strategy: '스윙',
      market: 'KOSPI'
    };

    render(<StockCardV2 item={mockItem} />);
    
    // current_price가 표시되는지 확인
    const priceElement = screen.getByText(/75,000원/);
    expect(priceElement).toBeInTheDocument();
  });

  test('당일 스캔인 경우 스캔일 종가를 표시', () => {
    const today = new Date();
    const todayStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`;
    
    const mockItem = {
      ticker: '005930',
      name: '삼성전자',
      current_price: 72000, // 스캔일 종가 (당일이므로 동일)
      recommended_price: 72000, // 스캔일 종가
      recommended_date: todayStr, // 오늘 날짜
      returns: {
        current_price: 72000, // 당일이므로 동일
        current_return: 0
      },
      change_rate: 2.5,
      score: 10.5,
      score_label: '강력 추천',
      strategy: '스윙',
      market: 'KOSPI'
    };

    render(<StockCardV2 item={mockItem} />);
    
    // current_price가 표시되는지 확인
    const priceElement = screen.getByText(/72,000원/);
    expect(priceElement).toBeInTheDocument();
  });

  test('returns.current_price가 없으면 current_price 사용', () => {
    const mockItem = {
      ticker: '005930',
      name: '삼성전자',
      current_price: 72000, // fallback 가격
      recommended_price: 72000,
      recommended_date: '20251126',
      returns: {
        current_price: null, // 없음
        current_return: 0
      },
      change_rate: 2.5,
      score: 10.5,
      score_label: '강력 추천',
      strategy: '스윙',
      market: 'KOSPI'
    };

    render(<StockCardV2 item={mockItem} />);
    
    // current_price가 표시되는지 확인
    const priceElement = screen.getByText(/72,000원/);
    expect(priceElement).toBeInTheDocument();
  });
});

