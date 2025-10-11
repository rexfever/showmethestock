import React, { useState, useEffect } from 'react';
import { shouldShowNotice, hideNotice, getNoticeInfo } from '../utils/noticeManager';

const NoticePopup = () => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // 공지사항 표시 여부 확인
    const noticeId = '2025-10-11';
    if (shouldShowNotice(noticeId, 3)) {
      setIsVisible(true);
    }
  }, []);

  const handleClose = () => {
    setIsVisible(false);
  };

  const handleDontShowFor3Days = () => {
    const noticeId = '2025-10-11';
    hideNotice(noticeId);
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-lg w-full shadow-2xl">
        {/* 헤더 */}
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-4 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold">🎉 새로운 기능 업데이트!</h2>
              <p className="text-blue-100 text-xs">2025년 10월 11일</p>
            </div>
            <button
              onClick={handleClose}
              className="text-white hover:text-blue-200 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* 내용 */}
        <div className="p-4">
          <div className="space-y-3">
            {/* 새로운 기능 */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <h3 className="font-semibold text-gray-800 mb-2">🎉 새로운 기능 추가!</h3>
              <div className="space-y-2 text-sm text-gray-700">
                <div>• <strong>투자등록</strong>: 추천 종목 리스트에서 바로 투자종목 등록</div>
                <div>• <strong>나의투자종목</strong>: 매수일, 보유기간, 수익률 확인</div>
                <div>• <strong>종목분석</strong>: 개별 종목 상세 분석 기능</div>
                <div className="text-xs text-gray-600 mt-2 pt-2 border-t border-green-200">
                  💡 매수가격, 수량, 매수일을 입력하여 투자관리를 시작하세요!
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 푸터 */}
        <div className="bg-gray-50 px-4 py-3 rounded-b-lg border-t">
          <div className="flex justify-end space-x-2">
            <button
              onClick={handleDontShowFor3Days}
              className="px-3 py-1 text-xs text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors"
            >
              3일간 보지않기
            </button>
            <button
              onClick={handleClose}
              className="px-4 py-1 bg-blue-500 text-white text-xs font-medium rounded hover:bg-blue-600 transition-colors"
            >
              확인
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NoticePopup;
