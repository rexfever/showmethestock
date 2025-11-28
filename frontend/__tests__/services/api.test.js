/**
 * API 통신 테스트
 */
import {
  fetchScan,
  fetchAnalyze,
  fetchUniverse,
  fetchPositions,
  addPosition,
  updatePosition,
  deletePosition,
} from '../../lib/api';

// Mock fetch
global.fetch = jest.fn();

describe('API 통신', () => {
  const originalEnv = process.env.NEXT_PUBLIC_BACKEND_URL;

  beforeEach(() => {
    jest.clearAllMocks();
    // 환경 변수 초기화
    delete process.env.NEXT_PUBLIC_BACKEND_URL;
  });

  afterEach(() => {
    // 환경 변수 복원
    if (originalEnv) {
      process.env.NEXT_PUBLIC_BACKEND_URL = originalEnv;
    } else {
      delete process.env.NEXT_PUBLIC_BACKEND_URL;
    }
  });

  describe('fetchScan', () => {
    it('성공 시 스캔 결과를 반환해야 함', async () => {
      const mockData = {
        ok: true,
        data: {
          items: [{ ticker: '005930', name: '삼성전자' }],
        },
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await fetchScan();

      // 기본값이 http://127.0.0.1:8010이므로 이를 확인
      expect(global.fetch).toHaveBeenCalledWith('http://127.0.0.1:8010/scan');
      expect(result).toEqual(mockData);
    });

    it('실패 시 에러를 던져야 함', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(fetchScan()).rejects.toThrow('scan failed');
    });
  });

  describe('fetchAnalyze', () => {
    it('성공 시 분석 결과를 반환해야 함', async () => {
      const mockData = {
        ok: true,
        item: { ticker: '005930', name: '삼성전자' },
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await fetchAnalyze('삼성전자');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8010/analyze?name_or_code=' + encodeURIComponent('삼성전자')
      );
      expect(result).toEqual(mockData);
    });

    it('실패 시 에러를 던져야 함', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      await expect(fetchAnalyze('없는종목')).rejects.toThrow('analyze failed');
    });
  });

  describe('fetchUniverse', () => {
    it('성공 시 유니버스 목록을 반환해야 함', async () => {
      const mockData = {
        ok: true,
        universe: ['005930', '000660'],
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await fetchUniverse();

      expect(global.fetch).toHaveBeenCalledWith('http://127.0.0.1:8010/universe');
      expect(result).toEqual(mockData);
    });
  });

  describe('fetchPositions', () => {
    it('성공 시 포지션 목록을 반환해야 함', async () => {
      const mockData = {
        ok: true,
        positions: [
          { id: 1, ticker: '005930', quantity: 10 },
        ],
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await fetchPositions();

      expect(global.fetch).toHaveBeenCalledWith('http://127.0.0.1:8010/positions');
      expect(result).toEqual(mockData);
    });
  });

  describe('addPosition', () => {
    it('성공 시 추가된 포지션을 반환해야 함', async () => {
      const position = {
        ticker: '005930',
        name: '삼성전자',
        entry_price: 70000,
        quantity: 10,
        entry_date: '20250101',
      };

      const mockData = {
        ok: true,
        position: { id: 1, ...position },
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await addPosition(position);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8010/positions',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(position),
        })
      );
      expect(result).toEqual(mockData);
    });
  });

  describe('updatePosition', () => {
    it('성공 시 업데이트된 포지션을 반환해야 함', async () => {
      const updateData = { quantity: 20 };

      const mockData = {
        ok: true,
        position: { id: 1, quantity: 20 },
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await updatePosition(1, updateData);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8010/positions/1',
        expect.objectContaining({
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updateData),
        })
      );
      expect(result).toEqual(mockData);
    });
  });

  describe('deletePosition', () => {
    it('성공 시 삭제 결과를 반환해야 함', async () => {
      const mockData = {
        ok: true,
        message: '삭제되었습니다.',
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await deletePosition(1);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8010/positions/1',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
      expect(result).toEqual(mockData);
    });
  });

  describe('에러 핸들링', () => {
    it('네트워크 에러 시 적절히 처리해야 함', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(fetchScan()).rejects.toThrow();
    });

    it('타임아웃 에러 시 적절히 처리해야 함', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Timeout'));

      await expect(fetchScan()).rejects.toThrow();
    });
  });
});

