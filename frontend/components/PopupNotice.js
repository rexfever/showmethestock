import React, { useState, useEffect } from 'react';
import getConfig from '../config';

const PopupNotice = () => {
  const [notice, setNotice] = useState(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const checkNotice = async () => {
      try {
        const config = getConfig();
        const backendUrl = config?.backendUrl || 'http://localhost:8010';
        
        // 타임아웃 설정 (3초)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        
        const response = await fetch(`${backendUrl}/popup-notice/status`, {
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        const data = await response.json();
        
        if (data.is_enabled && data.title && data.message) {
          // 다시보지 않기 체크
          const hideKey = `popup_notice_hide_${data.start_date}_${data.end_date}`;
          const isHidden = localStorage.getItem(hideKey) === 'true';
          
          if (!isHidden) {
            setNotice(data);
            setIsVisible(true);
          }
        }
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('팝업 공지 확인 실패:', error);
        }
        // 타임아웃이나 에러 시 팝업 표시 안 함
      }
    };

    checkNotice();
  }, []);

  const handleClose = () => {
    setIsVisible(false);
  };

  const handleDontShowAgain = () => {
    if (notice) {
      const hideKey = `popup_notice_hide_${notice.start_date}_${notice.end_date}`;
      localStorage.setItem(hideKey, 'true');
    }
    setIsVisible(false);
  };

  if (!isVisible || !notice) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              {notice.title}
            </h3>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="mb-6">
            <p className="text-gray-700 whitespace-pre-line">
              {notice.message}
            </p>
          </div>
          
          <div className="flex justify-end space-x-3">
            <button
              onClick={handleDontShowAgain}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            >
              다시 보지 않기
            </button>
            <button
              onClick={handleClose}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
            >
              닫기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PopupNotice;