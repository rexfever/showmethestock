/**
 * 포트폴리오 서비스 테스트
 */
import { fetchPortfolio, addToPortfolio, removeFromPortfolio } from '../../services/portfolioService';
import { getAuthToken } from '../../utils/portfolioUtils';

// Mock dependencies
jest.mock('../../config', () => ({
  __esModule: true,
  default: () => ({
    backendUrl: 'http://localhost:8010'
  })
}));

jest.mock('../../utils/portfolioUtils', () => ({
  getAuthToken: jest.fn()
}));

// Mock fetch
global.fetch = jest.fn();

describe('portfolioService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchPortfolio', () => {
    it('성공적으로 포트폴리오를 가져와야 함', async () => {
      const mockToken = 'test-token';
      const mockPortfolio = [
        { id: 1, ticker: 'AAPL', name: 'Apple Inc.', entry_price: 150, quantity: 10 }
      ];

      getAuthToken.mockReturnValue(mockToken);
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: mockPortfolio })
      });

      const result = await fetchPortfolio();

      expect(fetch).toHaveBeenCalledWith('http://localhost:8010/portfolio', {
        headers: {
          'Authorization': `Bearer ${mockToken}`,
        },
      });
      expect(result).toEqual(mockPortfolio);
    });

    it('토큰이 없는 경우 에러를 던져야 함', async () => {
      getAuthToken.mockReturnValue(null);

      await expect(fetchPortfolio()).rejects.toThrow('인증 토큰이 없습니다.');
    });

    it('401 응답인 경우 인증 에러를 던져야 함', async () => {
      const mockToken = 'invalid-token';
      getAuthToken.mockReturnValue(mockToken);
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Unauthorized' })
      });

      await expect(fetchPortfolio()).rejects.toThrow('인증이 필요합니다. 다시 로그인해주세요.');
    });

    it('기타 오류 응답인 경우 일반 에러를 던져야 함', async () => {
      const mockToken = 'test-token';
      getAuthToken.mockReturnValue(mockToken);
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Server Error' })
      });

      await expect(fetchPortfolio()).rejects.toThrow('포트폴리오를 불러오는데 실패했습니다.');
    });
  });

  describe('addToPortfolio', () => {
    it('성공적으로 포트폴리오에 종목을 추가해야 함', async () => {
      const mockToken = 'test-token';
      const investmentData = {
        ticker: 'AAPL',
        name: 'Apple Inc.',
        entry_price: '150',
        quantity: '10',
        entry_date: '2025-10-10'
      };
      const mockResponse = { success: true, id: 1 };

      getAuthToken.mockReturnValue(mockToken);
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await addToPortfolio(investmentData);

      expect(fetch).toHaveBeenCalledWith('http://localhost:8010/portfolio/add', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${mockToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ticker: 'AAPL',
          name: 'Apple Inc.',
          entry_price: 150,
          quantity: 10,
          entry_date: '2025-10-10',
          status: 'holding'
        })
      });
      expect(result).toEqual(mockResponse);
    });

    it('토큰이 없는 경우 에러를 던져야 함', async () => {
      getAuthToken.mockReturnValue(null);
      const investmentData = {
        ticker: 'AAPL',
        name: 'Apple Inc.',
        entry_price: '150',
        quantity: '10',
        entry_date: '2025-10-10'
      };

      await expect(addToPortfolio(investmentData)).rejects.toThrow('인증 토큰이 없습니다.');
    });

    it('401 응답인 경우 인증 에러를 던져야 함', async () => {
      const mockToken = 'invalid-token';
      const investmentData = {
        ticker: 'AAPL',
        name: 'Apple Inc.',
        entry_price: '150',
        quantity: '10',
        entry_date: '2025-10-10'
      };

      getAuthToken.mockReturnValue(mockToken);
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Unauthorized' })
      });

      await expect(addToPortfolio(investmentData)).rejects.toThrow('인증이 필요합니다. 다시 로그인해주세요.');
    });

    it('기타 오류 응답인 경우 상세 에러를 던져야 함', async () => {
      const mockToken = 'test-token';
      const investmentData = {
        ticker: 'AAPL',
        name: 'Apple Inc.',
        entry_price: '150',
        quantity: '10',
        entry_date: '2025-10-10'
      };

      getAuthToken.mockReturnValue(mockToken);
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Invalid data' })
      });

      await expect(addToPortfolio(investmentData)).rejects.toThrow('Invalid data');
    });
  });

  describe('removeFromPortfolio', () => {
    it('성공적으로 포트폴리오에서 종목을 제거해야 함', async () => {
      const mockToken = 'test-token';
      const ticker = 'AAPL';
      const mockResponse = { success: true };

      getAuthToken.mockReturnValue(mockToken);
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await removeFromPortfolio(ticker);

      expect(fetch).toHaveBeenCalledWith('http://localhost:8010/portfolio/AAPL', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${mockToken}`,
        },
      });
      expect(result).toEqual(mockResponse);
    });

    it('토큰이 없는 경우 에러를 던져야 함', async () => {
      getAuthToken.mockReturnValue(null);

      await expect(removeFromPortfolio('AAPL')).rejects.toThrow('인증 토큰이 없습니다.');
    });

    it('401 응답인 경우 인증 에러를 던져야 함', async () => {
      const mockToken = 'invalid-token';
      getAuthToken.mockReturnValue(mockToken);
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Unauthorized' })
      });

      await expect(removeFromPortfolio('AAPL')).rejects.toThrow('인증이 필요합니다. 다시 로그인해주세요.');
    });

    it('기타 오류 응답인 경우 상세 에러를 던져야 함', async () => {
      const mockToken = 'test-token';
      getAuthToken.mockReturnValue(mockToken);
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Portfolio item not found' })
      });

      await expect(removeFromPortfolio('AAPL')).rejects.toThrow('Portfolio item not found');
    });
  });
});






