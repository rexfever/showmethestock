/**
 * v3 카드 숫자 노출 금지 테스트
 * 
 * 목적: ActiveStockCardV3, BrokenStockCardV3에서 숫자(가격/수익률 등)가 노출되지 않음을 확인
 */

import { render } from '@testing-library/react';
import { useRouter } from 'next/router';
import ActiveStockCardV3 from '../../components/v3/ActiveStockCardV3';
import BrokenStockCardV3 from '../../components/v3/BrokenStockCardV3';

// NextRouter 모킹 (useRouter 사용 컴포넌트 테스트 필수)
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

// 금지 패턴 (통화/퍼센트 기반)
const FORBIDDEN_PATTERNS = [
  /원/g,
  /%/g,
  /KRW/g,
  /USD/g,
  /\d+,\d+/g, // 천단위 구분 숫자 (예: 1,000)
  /\d+\.\d+/g, // 소수점 숫자 (예: 12.34)
];

// 종목명에 숫자가 들어갈 수 있으므로, 숫자 자체는 금지하지 않음
// 대신 통화/퍼센트 기반 패턴만 체크

describe('v3 카드 숫자 노출 금지 테스트', () => {
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
  const mockActiveItem = {
    ticker: '005930',
    name: '삼성전자',
    status: 'ACTIVE',
    recommended_date: '20251215',
    scanner_version: 'v3',
  };

  const mockBrokenItem = {
    ticker: '000660',
    name: 'SK하이닉스',
    status: 'BROKEN',
    recommended_date: '20251210',
    scanner_version: 'v3',
  };

  test('ActiveStockCardV3에 금지 패턴이 없어야 함', () => {
    const { container } = render(
      <ActiveStockCardV3 item={mockActiveItem} isNew={false} />
    );
    
    const htmlContent = container.innerHTML;
    
    FORBIDDEN_PATTERNS.forEach(pattern => {
      const matches = htmlContent.match(pattern);
      if (matches) {
        console.error(`[금지 패턴 발견] ${pattern}:`, matches);
      }
      expect(matches).toBeNull();
    });
  });

  test('ActiveStockCardV3 (신규)에 금지 패턴이 없어야 함', () => {
    const { container } = render(
      <ActiveStockCardV3 item={mockActiveItem} isNew={true} />
    );
    
    const htmlContent = container.innerHTML;
    
    FORBIDDEN_PATTERNS.forEach(pattern => {
      const matches = htmlContent.match(pattern);
      if (matches) {
        console.error(`[금지 패턴 발견] ${pattern}:`, matches);
      }
      expect(matches).toBeNull();
    });
  });

  test('BrokenStockCardV3에 금지 패턴이 없어야 함', () => {
    const { container } = render(
      <BrokenStockCardV3 item={mockBrokenItem} />
    );
    
    const htmlContent = container.innerHTML;
    
    FORBIDDEN_PATTERNS.forEach(pattern => {
      const matches = htmlContent.match(pattern);
      if (matches) {
        console.error(`[금지 패턴 발견] ${pattern}:`, matches);
      }
      expect(matches).toBeNull();
    });
  });

  test('숫자가 포함된 종목명도 정상 렌더링되어야 함', () => {
    const itemWithNumber = {
      ...mockActiveItem,
      name: '3M',
      ticker: 'MMM',
    };
    
    const { container } = render(
      <ActiveStockCardV3 item={itemWithNumber} isNew={false} />
    );
    
    // 종목명에 숫자가 있어도 렌더링은 정상
    expect(container.textContent).toContain('3M');
    
    // 하지만 금지 패턴은 여전히 없어야 함
    const htmlContent = container.innerHTML;
    FORBIDDEN_PATTERNS.forEach(pattern => {
      const matches = htmlContent.match(pattern);
      expect(matches).toBeNull();
    });
  });
});

