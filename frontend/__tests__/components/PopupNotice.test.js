/**
 * PopupNotice 컴포넌트 테스트
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import PopupNotice from '../../components/PopupNotice';
import getConfig from '../../config';

// Mock config
const mockGetConfig = jest.fn(() => ({
  backendUrl: 'http://localhost:8010',
}));

jest.mock('../../config', () => ({
  __esModule: true,
  default: mockGetConfig,
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

describe('PopupNotice 컴포넌트', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
    global.fetch = jest.fn();
  });

  describe('공지가 없을 때', () => {
    it('공지가 비활성화되어 있으면 표시되지 않아야 함', async () => {
      global.fetch.mockResolvedValueOnce({
        json: async () => ({
          is_enabled: false,
        }),
      });

      render(<PopupNotice />);
      
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('API 에러 시 표시되지 않아야 함', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      render(<PopupNotice />);
      
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('공지가 있을 때', () => {
    const mockNotice = {
      is_enabled: true,
      title: '테스트 공지',
      message: '이것은 테스트 공지입니다.',
      start_date: '20250101',
      end_date: '20251231',
    };

    it('공지가 활성화되어 있으면 표시되어야 함', async () => {
      global.fetch.mockResolvedValueOnce({
        json: async () => mockNotice,
      });

      render(<PopupNotice />);
      
      await waitFor(() => {
        expect(screen.getByText('테스트 공지')).toBeInTheDocument();
        expect(screen.getByText('이것은 테스트 공지입니다.')).toBeInTheDocument();
      });
    });

    it('닫기 버튼 클릭 시 팝업이 닫혀야 함', async () => {
      global.fetch.mockResolvedValueOnce({
        json: async () => mockNotice,
      });

      render(<PopupNotice />);
      
      await waitFor(() => {
        expect(screen.getByText('테스트 공지')).toBeInTheDocument();
      });

      const closeButton = screen.getByText('닫기');
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByText('테스트 공지')).not.toBeInTheDocument();
      });
    });

    it('X 버튼 클릭 시 팝업이 닫혀야 함', async () => {
      global.fetch.mockResolvedValueOnce({
        json: async () => mockNotice,
      });

      render(<PopupNotice />);
      
      await waitFor(() => {
        expect(screen.getByText('테스트 공지')).toBeInTheDocument();
      });

      // X 버튼 찾기 (SVG 또는 버튼)
      const closeButtons = screen.getAllByRole('button');
      const xButton = closeButtons.find(btn => 
        btn.querySelector('svg') || btn.textContent === ''
      );
      
      if (xButton) {
        fireEvent.click(xButton);
        
        await waitFor(() => {
          expect(screen.queryByText('테스트 공지')).not.toBeInTheDocument();
        });
      }
    });

    it('다시 보지 않기 클릭 시 localStorage에 저장되어야 함', async () => {
      global.fetch.mockResolvedValueOnce({
        json: async () => mockNotice,
      });

      render(<PopupNotice />);
      
      await waitFor(() => {
        expect(screen.getByText('테스트 공지')).toBeInTheDocument();
      });

      const dontShowButton = screen.getByText('다시 보지 않기');
      fireEvent.click(dontShowButton);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        `popup_notice_hide_${mockNotice.start_date}_${mockNotice.end_date}`,
        'true'
      );

      await waitFor(() => {
        expect(screen.queryByText('테스트 공지')).not.toBeInTheDocument();
      });
    });

    it('다시 보지 않기로 저장된 공지는 표시되지 않아야 함', async () => {
      const hideKey = `popup_notice_hide_${mockNotice.start_date}_${mockNotice.end_date}`;
      localStorageMock.getItem.mockReturnValue('true');

      global.fetch.mockResolvedValueOnce({
        json: async () => mockNotice,
      });

      render(<PopupNotice />);
      
      await waitFor(() => {
        expect(screen.queryByText('테스트 공지')).not.toBeInTheDocument();
      });
    });
  });

  describe('API 호출', () => {
    it('올바른 API 엔드포인트를 호출해야 함', async () => {
      global.fetch.mockResolvedValueOnce({
        json: async () => ({ is_enabled: false }),
      });

      render(<PopupNotice />);
      
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8010/popup-notice/status'
        );
      });
    });
  });
});

