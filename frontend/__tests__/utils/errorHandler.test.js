/**
 * 에러 핸들러 유틸리티 테스트
 */
import { getErrorMessage, handleError, handleApiResponse } from '../../utils/errorHandler';

// Mock console.error
const mockConsoleError = jest.spyOn(console, 'error').mockImplementation(() => {});

describe('errorHandler', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('getErrorMessage', () => {
    it('인증 관련 에러 메시지를 변환해야 함', () => {
      const authError = new Error('인증 토큰이 유효하지 않습니다');
      const result = getErrorMessage(authError);
      expect(result).toBe('로그인이 필요합니다. 다시 로그인해주세요.');
    });

    it('네트워크 관련 에러 메시지를 변환해야 함', () => {
      const networkError = new Error('네트워크 연결 실패');
      const result = getErrorMessage(networkError);
      expect(result).toBe('네트워크 연결을 확인해주세요.');
    });

    it('fetch 관련 에러 메시지를 변환해야 함', () => {
      const fetchError = new Error('Failed to fetch');
      const result = getErrorMessage(fetchError);
      expect(result).toBe('네트워크 연결을 확인해주세요.');
    });

    it('서버 관련 에러 메시지를 변환해야 함', () => {
      const serverError = new Error('서버 내부 오류');
      const result = getErrorMessage(serverError);
      expect(result).toBe('서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.');
    });

    it('알 수 없는 에러의 경우 원본 메시지를 반환해야 함', () => {
      const unknownError = new Error('알 수 없는 오류');
      const result = getErrorMessage(unknownError);
      expect(result).toBe('알 수 없는 오류');
    });

    it('메시지가 없는 에러의 경우 기본 메시지를 반환해야 함', () => {
      const emptyError = new Error();
      const result = getErrorMessage(emptyError);
      expect(result).toBe('알 수 없는 오류가 발생했습니다.');
    });
  });

  describe('handleError', () => {
    it('에러를 콘솔에 로깅해야 함', () => {
      const error = new Error('테스트 에러');
      handleError(error, '테스트 컨텍스트');
      
      expect(mockConsoleError).toHaveBeenCalledWith('테스트 컨텍스트 오류:', error);
    });

    it('showAlert 함수가 제공된 경우 알림을 표시해야 함', () => {
      const error = new Error('인증 토큰이 유효하지 않습니다');
      const mockAlert = jest.fn();
      
      handleError(error, '테스트 컨텍스트', mockAlert);
      
      expect(mockAlert).toHaveBeenCalledWith('로그인이 필요합니다. 다시 로그인해주세요.');
    });

    it('showAlert 함수가 제공되지 않은 경우 알림을 표시하지 않아야 함', () => {
      const error = new Error('테스트 에러');
      const mockAlert = jest.fn();
      
      handleError(error, '테스트 컨텍스트');
      
      expect(mockAlert).not.toHaveBeenCalled();
    });
  });

  describe('handleApiResponse', () => {
    it('성공적인 응답을 처리해야 함', async () => {
      const mockData = { success: true, data: 'test' };
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue(mockData)
      };

      const result = await handleApiResponse(mockResponse);
      
      expect(result).toEqual(mockData);
      expect(mockResponse.json).toHaveBeenCalled();
    });

    it('401 응답을 처리해야 함', async () => {
      const mockResponse = {
        ok: false,
        status: 401,
        json: jest.fn().mockResolvedValue({ detail: 'Unauthorized' })
      };

      await expect(handleApiResponse(mockResponse)).rejects.toThrow('인증이 필요합니다. 다시 로그인해주세요.');
    });

    it('500 응답을 처리해야 함', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: jest.fn().mockResolvedValue({ detail: 'Internal Server Error' })
      };

      await expect(handleApiResponse(mockResponse)).rejects.toThrow('서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.');
    });

    it('JSON 파싱 실패 시 기본 메시지를 사용해야 함', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        json: jest.fn().mockRejectedValue(new Error('Invalid JSON'))
      };

      await expect(handleApiResponse(mockResponse)).rejects.toThrow('요청 처리에 실패했습니다.');
    });

    it('에러 데이터의 detail 필드를 사용해야 함', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        json: jest.fn().mockResolvedValue({ detail: 'Custom error message' })
      };

      await expect(handleApiResponse(mockResponse)).rejects.toThrow('Custom error message');
    });
  });
});








