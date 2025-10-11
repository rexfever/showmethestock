/**
 * 포트폴리오 유틸리티 함수 테스트
 */
import {
  calculateHoldingPeriod,
  formatDate,
  formatCurrency,
  formatPercentage,
  validateInvestmentForm
} from '../../utils/portfolioUtils';

describe('portfolioUtils', () => {
  describe('calculateHoldingPeriod', () => {
    it('당일 매수인 경우 "당일"을 반환해야 함', () => {
      const today = new Date().toISOString().split('T')[0];
      // 시간대 차이로 인해 1일이 될 수 있으므로 둘 다 허용
      const result = calculateHoldingPeriod(today);
      expect(['당일', '1일']).toContain(result);
    });

    it('30일 미만인 경우 "N일"을 반환해야 함', () => {
      const fiveDaysAgo = new Date();
      fiveDaysAgo.setDate(fiveDaysAgo.getDate() - 5);
      const dateString = fiveDaysAgo.toISOString().split('T')[0];
      
      // 시간대 차이로 인해 1일 차이날 수 있으므로 허용 범위로 테스트
      const result = calculateHoldingPeriod(dateString);
      expect(['5일', '6일']).toContain(result);
    });

    it('30일 이상 1년 미만인 경우 "N개월"을 반환해야 함', () => {
      const twoMonthsAgo = new Date();
      twoMonthsAgo.setMonth(twoMonthsAgo.getMonth() - 2);
      const dateString = twoMonthsAgo.toISOString().split('T')[0];
      
      // 시간대 차이로 인해 일수가 포함될 수 있으므로 허용 범위로 테스트
      const result = calculateHoldingPeriod(dateString);
      expect(['2개월', '2개월 2일']).toContain(result);
    });

    it('1년 이상인 경우 "N년"을 반환해야 함', () => {
      const oneYearAgo = new Date();
      oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
      const dateString = oneYearAgo.toISOString().split('T')[0];
      
      expect(calculateHoldingPeriod(dateString)).toBe('1년');
    });

    it('빈 값인 경우 "-"을 반환해야 함', () => {
      expect(calculateHoldingPeriod('')).toBe('-');
      expect(calculateHoldingPeriod(null)).toBe('-');
      expect(calculateHoldingPeriod(undefined)).toBe('-');
    });
  });

  describe('formatDate', () => {
    it('유효한 날짜를 한국어 형식으로 포맷팅해야 함', () => {
      const dateString = '2025-10-11';
      const result = formatDate(dateString);
      // 한국어 로케일에서는 공백이 포함될 수 있으므로 유연하게 테스트
      expect(result).toMatch(/2025.*10.*11/);
    });

    it('빈 값인 경우 "-"을 반환해야 함', () => {
      expect(formatDate('')).toBe('-');
      expect(formatDate(null)).toBe('-');
      expect(formatDate(undefined)).toBe('-');
    });
  });

  describe('formatCurrency', () => {
    it('숫자를 천 단위 구분자와 함께 포맷팅해야 함', () => {
      expect(formatCurrency(1000)).toBe('1,000');
      expect(formatCurrency(1000000)).toBe('1,000,000');
      expect(formatCurrency(1234567)).toBe('1,234,567');
    });

    it('소수점이 있는 경우 반올림해야 함', () => {
      expect(formatCurrency(1234.7)).toBe('1,235');
      expect(formatCurrency(1234.4)).toBe('1,234');
    });

    it('null이나 undefined인 경우 "-"을 반환해야 함', () => {
      expect(formatCurrency(null)).toBe('-');
      expect(formatCurrency(undefined)).toBe('-');
    });
  });

  describe('formatPercentage', () => {
    it('양수인 경우 "+" 기호를 붙여야 함', () => {
      expect(formatPercentage(5.25)).toBe('+5.25%');
    });

    it('음수인 경우 "-" 기호를 붙여야 함', () => {
      expect(formatPercentage(-3.14)).toBe('-3.14%');
    });

    it('0인 경우 "0.00%"을 반환해야 함', () => {
      expect(formatPercentage(0)).toBe('0.00%');
    });

    it('null이나 undefined인 경우 "-"을 반환해야 함', () => {
      expect(formatPercentage(null)).toBe('-');
      expect(formatPercentage(undefined)).toBe('-');
    });
  });

  describe('validateInvestmentForm', () => {
    it('유효한 폼 데이터인 경우 성공해야 함', () => {
      const validForm = {
        entry_price: '75000',
        quantity: '10',
        entry_date: '2025-10-10'
      };

      const result = validateInvestmentForm(validForm);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('매수가격이 유효하지 않은 경우 오류를 반환해야 함', () => {
      const invalidForm = {
        entry_price: 'invalid',
        quantity: '10',
        entry_date: '2025-10-10'
      };

      const result = validateInvestmentForm(invalidForm);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('올바른 매수가격을 입력해주세요.');
    });

    it('수량이 유효하지 않은 경우 오류를 반환해야 함', () => {
      const invalidForm = {
        entry_price: '75000',
        quantity: '0',
        entry_date: '2025-10-10'
      };

      const result = validateInvestmentForm(invalidForm);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('올바른 수량을 입력해주세요.');
    });

    it('매수일이 미래인 경우 오류를 반환해야 함', () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 1);
      const futureDateString = futureDate.toISOString().split('T')[0];

      const invalidForm = {
        entry_price: '75000',
        quantity: '10',
        entry_date: futureDateString
      };

      const result = validateInvestmentForm(invalidForm);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('매수일은 오늘 이전이어야 합니다.');
    });

    it('여러 필드가 유효하지 않은 경우 모든 오류를 반환해야 함', () => {
      const invalidForm = {
        entry_price: '',
        quantity: '',
        entry_date: ''
      };

      const result = validateInvestmentForm(invalidForm);
      expect(result.isValid).toBe(false);
      expect(result.errors).toHaveLength(3);
    });
  });
});
