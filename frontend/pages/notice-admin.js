import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
// import { clearAllNoticeHides, clearNoticeHide, NOTICE_LIST } from '../utils/noticeManager';

export default function NoticeAdmin() {
  const router = useRouter();
  const { isAuthenticated, user, loading: authLoading, authChecked } = useAuth();
  const [message, setMessage] = useState('');

  // 관리자 권한 확인
  if (!authChecked || authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated() || !user?.is_admin) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">접근 권한이 없습니다</h2>
          <p className="text-gray-600 mb-6">관리자만 접근할 수 있습니다.</p>
          <button
            onClick={() => router.push('/')}
            className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600"
          >
            홈으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  const handleClearAllNotices = () => {
    // clearAllNoticeHides();
    setMessage('모든 공지사항 숨김 설정이 해제되었습니다.');
    setTimeout(() => setMessage(''), 3000);
  };

  const handleClearSpecificNotice = (noticeId) => {
    // clearNoticeHide(noticeId);
    setMessage(`${noticeId} 공지사항 숨김 설정이 해제되었습니다.`);
    setTimeout(() => setMessage(''), 3000);
  };

  return (
    <>
      <Head>
        <title>공지사항 관리 - Stock Insight</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* 상단 헤더 */}
        <div className="bg-white shadow-sm border-b">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center">
              <button 
                onClick={() => router.push('/')}
                className="text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors"
              >
                Stock Insight
              </button>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                {user.name}님 (관리자)
              </span>
              <button
                onClick={() => router.push('/admin')}
                className="px-3 py-1 bg-gray-500 text-white text-xs font-semibold rounded-full"
              >
                관리자 페이지
              </button>
            </div>
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="container mx-auto p-6">
          <h1 className="text-2xl font-bold text-gray-800 mb-6">공지사항 관리</h1>

          {message && (
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6">
              {message}
            </div>
          )}

          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">공지사항 목록</h2>
            
            <div className="space-y-4">
              {/* {Object.values(NOTICE_LIST).map((notice) => (
                <div key={notice.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <h3 className="font-semibold text-gray-800">{notice.title}</h3>
                      <p className="text-sm text-gray-600">{notice.date} - {notice.version}</p>
                    </div>
                    <button
                      onClick={() => handleClearSpecificNotice(notice.id)}
                      className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
                    >
                      숨김 해제
                    </button>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p className="font-medium mb-1">주요 기능:</p>
                    <ul className="list-disc list-inside space-y-1">
                      {notice.features.map((feature, index) => (
                        <li key={index}>{feature}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))} */}
            </div>

            <div className="mt-6 pt-6 border-t border-gray-200">
              <button
                onClick={handleClearAllNotices}
                className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
              >
                모든 공지사항 숨김 해제
              </button>
              <p className="text-sm text-gray-600 mt-2">
                이 기능은 모든 사용자의 공지사항 숨김 설정을 해제합니다. (개발/테스트용)
              </p>
            </div>
          </div>

          <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h3 className="font-semibold text-yellow-800 mb-2">💡 사용법</h3>
            <ul className="text-sm text-yellow-700 space-y-1">
              <li>• "숨김 해제" 버튼을 클릭하면 해당 공지사항이 다시 표시됩니다.</li>
              <li>• "모든 공지사항 숨김 해제"는 모든 사용자의 설정을 초기화합니다.</li>
              <li>• 공지사항은 3일간 보지않기 설정이 적용됩니다.</li>
            </ul>
          </div>
        </div>
      </div>
    </>
  );
}
