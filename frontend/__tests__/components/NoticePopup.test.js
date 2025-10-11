/**
 * 공지사항 팝업 컴포넌트 테스트
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NoticePopup from '../../components/NoticePopup';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

describe('NoticePopup', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('처음 방문 시 공지사항 팝업이 표시되어야 함', () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    render(<NoticePopup />);
    
    expect(screen.getByText('🎉 새로운 기능 업데이트!')).toBeInTheDocument();
    expect(screen.getByText('투자등록')).toBeInTheDocument();
    expect(screen.getByText('나의투자종목')).toBeInTheDocument();
  });

  it('3일 이내에 본 경우 공지사항 팝업이 표시되지 않아야 함', () => {
    const recentTime = new Date().getTime() - (2 * 24 * 60 * 60 * 1000); // 2일 전
    localStorageMock.getItem.mockReturnValue(recentTime.toString());
    
    const { container } = render(<NoticePopup />);
    
    // 컴포넌트가 렌더링되지 않았는지 확인
    expect(container.firstChild).toBeNull();
  });

  it('3일 이상 지난 경우 공지사항 팝업이 표시되어야 함', () => {
    const oldTime = new Date().getTime() - (4 * 24 * 60 * 60 * 1000); // 4일 전
    localStorageMock.getItem.mockReturnValue(oldTime.toString());
    
    render(<NoticePopup />);
    
    expect(screen.getByText('🎉 새로운 기능 업데이트!')).toBeInTheDocument();
  });

  it('확인 버튼을 클릭하면 팝업이 닫혀야 함', () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    render(<NoticePopup />);
    
    const confirmButton = screen.getByText('확인');
    fireEvent.click(confirmButton);
    
    expect(screen.queryByText('🎉 새로운 기능 업데이트!')).not.toBeInTheDocument();
  });

  it('X 버튼을 클릭하면 팝업이 닫혀야 함', () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    render(<NoticePopup />);
    
    const closeButton = screen.getByRole('button', { name: '' }); // X 버튼
    fireEvent.click(closeButton);
    
    expect(screen.queryByText('🎉 새로운 기능 업데이트!')).not.toBeInTheDocument();
  });

  it('3일간 보지않기 버튼을 클릭하면 로컬스토리지에 저장되고 팝업이 닫혀야 함', () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    render(<NoticePopup />);
    
    const dontShowButton = screen.getByText('3일간 보지않기');
    fireEvent.click(dontShowButton);
    
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'stock-insight-notice-2025-10-11',
      expect.any(String)
    );
    // 팝업이 닫혔는지 확인
    expect(screen.queryByText('🎉 새로운 기능 업데이트!')).not.toBeInTheDocument();
  });

  it('공지사항 내용이 올바르게 표시되어야 함', () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    render(<NoticePopup />);
    
    // 주요 업데이트 내용 확인 - 부분 텍스트로 검색
    expect(screen.getByText(/투자등록/)).toBeInTheDocument();
    expect(screen.getByText(/나의투자종목/)).toBeInTheDocument();
    expect(screen.getByText(/종목분석/)).toBeInTheDocument();
    
    // 투자등록 기능 설명 확인
    expect(screen.getByText(/추천 종목 리스트에서 바로 투자종목 등록/)).toBeInTheDocument();
    
    // 나의투자종목 기능 설명 확인
    expect(screen.getByText(/매수일, 보유기간, 수익률 확인/)).toBeInTheDocument();
    
    // 종목분석 기능 설명 확인
    expect(screen.getByText(/개별 종목 상세 분석 기능/)).toBeInTheDocument();
  });

  it('팁 메시지가 표시되어야 함', () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    render(<NoticePopup />);
    
    expect(screen.getByText(/💡 매수가격, 수량, 매수일을 입력하여 투자관리를 시작하세요!/)).toBeInTheDocument();
  });

  it('날짜가 올바르게 표시되어야 함', () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    render(<NoticePopup />);
    
    expect(screen.getByText(/2025년 10월 11일/)).toBeInTheDocument();
  });
});
