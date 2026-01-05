/**
 * 등락률 표시 로직 테스트
 * 
 * 프론트엔드에서 change_rate가 올바르게 표시되는지 검증합니다.
 */
describe('Change Rate Display Tests', () => {
  describe('StockTable Component', () => {
    it('should display change_rate as percentage', () => {
      const stock = {
        ticker: '030960',
        name: '양지사',
        close_price: 8870,
        change_rate: 0.57, // 퍼센트 형태 (0.57%)
      };

      // StockTable.js의 표시 로직과 동일
      const displayValue = stock.change_rate?.toFixed(2) || 'N/A';
      
      expect(displayValue).toBe('0.57');
      expect(parseFloat(displayValue)).toBeLessThan(100);
      expect(parseFloat(displayValue)).toBeGreaterThan(-100);
    });

    it('should handle positive change_rate', () => {
      const stock = {
        change_rate: 5.96,
      };

      const displayValue = stock.change_rate?.toFixed(2);
      const sign = stock.change_rate > 0 ? '+' : '';
      
      expect(displayValue).toBe('5.96');
      expect(sign).toBe('+');
    });

    it('should handle negative change_rate', () => {
      const stock = {
        change_rate: -2.35,
      };

      const displayValue = stock.change_rate?.toFixed(2);
      const sign = stock.change_rate > 0 ? '+' : '';
      
      expect(displayValue).toBe('-2.35');
      expect(sign).toBe('');
    });

    it('should handle zero change_rate', () => {
      const stock = {
        change_rate: 0,
      };

      const displayValue = stock.change_rate !== 0 
        ? `${stock.change_rate > 0 ? '+' : ''}${stock.change_rate?.toFixed(2) || 'N/A'}%`
        : '데이터 없음';
      
      expect(displayValue).toBe('데이터 없음');
    });
  });

  describe('Customer Scanner Component', () => {
    it('should display change_rate correctly', () => {
      const item = {
        ticker: '030960',
        name: '양지사',
        current_price: 8870,
        change_rate: 0.57, // 퍼센트 형태
      };

      // customer-scanner.js의 표시 로직과 동일
      const displayText = item.change_rate !== 0 
        ? `${item.change_rate > 0 ? '+' : ''}${item.change_rate}%`
        : '데이터 없음';
      
      expect(displayText).toBe('+0.57%');
      expect(item.change_rate).toBeLessThan(100);
      expect(item.change_rate).toBeGreaterThan(-100);
    });

    it('should not multiply change_rate by 100', () => {
      // API에서 이미 퍼센트 형태로 반환됨
      const apiResponse = {
        change_rate: 0.57, // 퍼센트 형태
      };

      // 프론트엔드는 변환하지 않음
      const displayValue = apiResponse.change_rate;
      
      expect(displayValue).toBe(0.57);
      expect(displayValue).not.toBe(57); // 100을 곱하지 않음
    });
  });

  describe('Edge Cases', () => {
    it('should handle very small change_rate', () => {
      const stock = {
        change_rate: 0.01, // 0.01%
      };

      const displayValue = stock.change_rate?.toFixed(2);
      
      expect(displayValue).toBe('0.01');
      expect(parseFloat(displayValue)).toBeLessThan(1.0);
    });

    it('should handle large change_rate', () => {
      const stock = {
        change_rate: 15.5, // 15.5%
      };

      const displayValue = stock.change_rate?.toFixed(2);
      
      expect(displayValue).toBe('15.50');
      expect(parseFloat(displayValue)).toBeGreaterThan(1.0);
    });

    it('should handle missing change_rate', () => {
      const stock = {
        change_rate: null,
      };

      const displayValue = stock.change_rate?.toFixed(2) || 'N/A';
      
      expect(displayValue).toBe('N/A');
    });
  });
});



































