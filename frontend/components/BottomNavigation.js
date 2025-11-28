import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import { useState, useEffect } from 'react';
import getConfig from '../config';

export default function BottomNavigation() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [scannerLink, setScannerLink] = useState('/customer-scanner');

  useEffect(() => {
    // 바텀메뉴 링크 설정 가져오기
    const fetchBottomNavLink = async () => {
      try {
        const config = getConfig();
        const base = config.backendUrl;
        const response = await fetch(`${base}/bottom-nav-link`);
        if (response.ok) {
          const data = await response.json();
          setScannerLink(data.link_url || '/customer-scanner');
        }
      } catch (error) {
        console.error('바텀메뉴 링크 설정 조회 실패:', error);
        // 에러 시 기본값 사용
        setScannerLink('/customer-scanner');
      }
    };
    fetchBottomNavLink();
  }, []);

  return (
    <>
      {/* 하단 네비게이션 */}
      <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
        <div className="flex justify-around items-center py-2">
          <button 
            className="flex flex-col items-center py-2 hover:bg-gray-800"
            onClick={() => router.push(scannerLink)}
          >
            <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            <span className="text-xs">추천종목</span>
          </button>
          <button 
            className="flex flex-col items-center py-2 hover:bg-gray-800"
            onClick={() => router.push('/stock-analysis')}
          >
            <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span className="text-xs">종목분석</span>
          </button>
          {user?.is_admin && (
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => router.push('/admin')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="text-xs">관리자</span>
            </button>
          )}
          <button 
            className="flex flex-col items-center py-2 hover:bg-gray-800"
            onClick={() => router.push('/more')}
          >
            <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
            </svg>
            <span className="text-xs">더보기</span>
          </button>
        </div>
      </div>

      {/* 하단 네비게이션 공간 확보 */}
      <div className="h-20"></div>
    </>
  );
}
