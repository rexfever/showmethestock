import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import { useState, useEffect } from 'react';
import { getScannerLink } from '../../utils/navigation';

// config는 동적 import로 처리
const getConfig = () => {
  if (typeof window !== 'undefined') {
    // 클라이언트 사이드 - 개발 환경에서는 항상 로컬 백엔드 사용
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    return {
      backendUrl: isLocal 
        ? 'http://localhost:8010'
        : (process.env.NODE_ENV === 'production' ? 'https://sohntech.ai.kr/api' : 'http://localhost:8010')
    };
  } else {
    return {
      backendUrl: process.env.BACKEND_URL || 'http://localhost:8010'
    };
  }
};

export default function BottomNavigation() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [scannerLink, setScannerLink] = useState('/v2/scanner-v2'); // 초기값만 설정, 실제 값은 API에서 가져옴
  const [isVisible, setIsVisible] = useState(true);
  const [menuItems, setMenuItems] = useState({
    korean_stocks: true,
    us_stocks: true,
    stock_analysis: true,
    portfolio: true,
    more: true,
    settings: true
  });

  useEffect(() => {
    // 바텀메뉴 노출 설정 가져오기
    const fetchBottomNavVisible = async () => {
      try {
        const config = getConfig();
        const base = config?.backendUrl || 'http://localhost:8010';
        const response = await fetch(`${base}/bottom-nav-visible`);
        if (response.ok) {
          const data = await response.json();
          setIsVisible(data.is_visible !== false);
        }
      } catch (error) {
        console.error('바텀메뉴 노출 설정 조회 실패:', error);
        // 에러 시 기본값 사용 (표시)
        setIsVisible(true);
      }
    };

    // 바텀메뉴 링크 설정 가져오기 (사용자별 설정 반영)
    const fetchBottomNavLink = async () => {
      try {
        const link = await getScannerLink();
        console.log('[BottomNavigation] fetchBottomNavLink 성공:', link);
        setScannerLink(link);
      } catch (error) {
        console.error('[BottomNavigation] 바텀메뉴 링크 설정 조회 실패:', error);
        // 에러 시 동적으로 다시 시도
        try {
          const link = await getScannerLink();
          console.log('[BottomNavigation] 재시도 성공:', link);
          setScannerLink(link);
        } catch (retryError) {
          console.error('[BottomNavigation] 재시도 실패, fallback 사용:', retryError);
          // 최종 fallback
          setScannerLink('/v2/scanner-v2');
        }
      }
    };

    // 바텀메뉴 개별 메뉴 아이템 설정 가져오기
    const fetchBottomNavMenuItems = async () => {
      try {
        const config = getConfig();
        const base = config?.backendUrl || 'http://localhost:8010';
        const response = await fetch(`${base}/bottom-nav-menu-items`);
        if (response.ok) {
          const data = await response.json();
          setMenuItems({
            korean_stocks: data.korean_stocks === true,
            us_stocks: data.us_stocks === true,
            stock_analysis: data.stock_analysis === true,
            portfolio: data.portfolio === true,
            more: data.more === true,
            settings: data.settings === true
          });
        }
      } catch (error) {
        console.error('바텀메뉴 메뉴 아이템 설정 조회 실패:', error);
        // 에러 시 기본값 사용 (모두 표시)
      }
    };
    
    fetchBottomNavVisible();
    fetchBottomNavLink();
    fetchBottomNavMenuItems();
    
    // 설정 변경 이벤트 리스너 추가
    const handlePreferencesChanged = () => {
      console.log('[BottomNavigation] 사용자 설정 변경 감지, 링크 다시 가져오기');
      fetchBottomNavLink();
    };
    
    if (typeof window !== 'undefined') {
      window.addEventListener('userPreferencesChanged', handlePreferencesChanged);
    }
    
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('userPreferencesChanged', handlePreferencesChanged);
      }
    };
  }, [user]); // user가 변경될 때마다 다시 호출 (로그인/로그아웃, 설정 변경 시)

  // 노출 설정이 false이면 렌더링하지 않음
  if (!isVisible) {
    return null;
  }

  return (
    <>
      {/* 하단 네비게이션 */}
      <div className="fixed bottom-0 left-0 right-0 bg-black text-white z-[9999]" style={{ pointerEvents: 'auto' }}>
        <div className="flex justify-around items-center py-2" style={{ pointerEvents: 'auto' }}>
          {menuItems.korean_stocks && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 px-4 hover:bg-gray-800 cursor-pointer flex-1 min-w-0"
              style={{ pointerEvents: 'auto' }}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('[BottomNav] 한국주식추천 버튼 클릭:', { router: !!router, scannerLink, currentPath: router?.asPath });
                if (scannerLink) {
                  const targetPath = scannerLink;
                  if (router?.asPath === targetPath) {
                    console.log('[BottomNav] 같은 페이지이므로 이동하지 않음');
                    return;
                  }
                  console.log('[BottomNav] 이동 시작:', targetPath);
                  window.location.href = targetPath;
                } else {
                  console.warn('[BottomNav] scannerLink가 없음');
                }
              }}
            >
              <span className="text-2xl mb-1">🇰🇷</span>
              <span className="text-xs text-center">한국</span>
            </button>
          )}
          {menuItems.us_stocks && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 px-4 hover:bg-gray-800 cursor-pointer flex-1 min-w-0"
              style={{ pointerEvents: 'auto' }}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const targetPath = '/v2/us-stocks-scanner';
                console.log('[BottomNav] 미국주식추천 버튼 클릭:', { currentPath: router?.asPath, targetPath });
                if (router?.asPath === targetPath) {
                  console.log('[BottomNav] 같은 페이지이므로 이동하지 않음');
                  return;
                }
                console.log('[BottomNav] 이동 시작:', targetPath);
                window.location.href = targetPath;
              }}
            >
              <span className="text-2xl mb-1">🇺🇸</span>
              <span className="text-xs text-center">미국</span>
            </button>
          )}
          {menuItems.stock_analysis && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 px-4 hover:bg-gray-800 cursor-pointer flex-1 min-w-0"
              style={{ pointerEvents: 'auto' }}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const targetPath = '/stock-analysis';
                console.log('[BottomNav] 종목분석 버튼 클릭:', { currentPath: router?.asPath, targetPath });
                if (router?.asPath === targetPath) {
                  console.log('[BottomNav] 같은 페이지이므로 이동하지 않음');
                  return;
                }
                console.log('[BottomNav] 이동 시작:', targetPath);
                window.location.href = targetPath;
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span className="text-xs text-center">종목분석</span>
            </button>
          )}
          {menuItems.portfolio && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 px-4 hover:bg-gray-800 cursor-pointer flex-1 min-w-0"
              style={{ pointerEvents: 'auto' }}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const targetPath = '/portfolio';
                console.log('[BottomNav] 나의투자종목 버튼 클릭:', { currentPath: router?.asPath, targetPath });
                if (router?.asPath === targetPath) {
                  console.log('[BottomNav] 같은 페이지이므로 이동하지 않음');
                  return;
                }
                console.log('[BottomNav] 이동 시작:', targetPath);
                window.location.href = targetPath;
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              <span className="text-xs text-center whitespace-nowrap">나의투자종목</span>
            </button>
          )}
          {user?.is_admin && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 px-4 hover:bg-gray-800 cursor-pointer flex-1 min-w-0"
              style={{ pointerEvents: 'auto' }}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const targetPath = '/admin';
                console.log('[BottomNav] 관리자 버튼 클릭:', { currentPath: router?.asPath, targetPath });
                if (router?.asPath === targetPath) {
                  console.log('[BottomNav] 같은 페이지이므로 이동하지 않음');
                  return;
                }
                console.log('[BottomNav] 이동 시작:', targetPath);
                window.location.href = targetPath;
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="text-xs text-center">관리자</span>
            </button>
          )}
          <button 
            type="button"
            className="flex flex-col items-center py-2 px-4 hover:bg-gray-800 cursor-pointer flex-1 min-w-0"
            style={{ pointerEvents: 'auto' }}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const targetPath = '/settings';
              console.log('[BottomNav] 개인설정 버튼 클릭:', { currentPath: router?.asPath, targetPath });
              if (router?.asPath === targetPath) {
                console.log('[BottomNav] 같은 페이지이므로 이동하지 않음');
                return;
              }
              console.log('[BottomNav] 이동 시작:', targetPath);
              window.location.href = targetPath;
            }}
          >
            <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-xs text-center">설정</span>
          </button>
          {menuItems.more && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 px-4 hover:bg-gray-800 cursor-pointer flex-1 min-w-0"
              style={{ pointerEvents: 'auto' }}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const targetPath = '/more';
                console.log('[BottomNav] 더보기 버튼 클릭:', { currentPath: router?.asPath, targetPath });
                if (router?.asPath === targetPath) {
                  console.log('[BottomNav] 같은 페이지이므로 이동하지 않음');
                  return;
                }
                console.log('[BottomNav] 이동 시작:', targetPath);
                window.location.href = targetPath;
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
              <span className="text-xs text-center">더보기</span>
            </button>
          )}
        </div>
      </div>

      {/* 하단 네비게이션 공간 확보 */}
      <div className="h-20"></div>
    </>
  );
}
