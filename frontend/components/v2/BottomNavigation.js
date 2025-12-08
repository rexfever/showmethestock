import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import { useState, useEffect } from 'react';

// config는 동적 import로 처리
const getConfig = () => {
  if (typeof window !== 'undefined') {
    return {
      backendUrl: process.env.NODE_ENV === 'production' 
        ? 'https://sohntech.ai.kr/api' 
        : 'http://localhost:8010'
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
  const [scannerLink, setScannerLink] = useState('/customer-scanner');
  const [isVisible, setIsVisible] = useState(true);
  const [menuItems, setMenuItems] = useState({
    korean_stocks: true,
    us_stocks: true,
    stock_analysis: true,
    portfolio: true,
    more: true
  });

  useEffect(() => {
    // 바텀메뉴 노출 설정 가져오기
    const fetchBottomNavVisible = async () => {
      try {
        const config = getConfig();
        const base = config.backendUrl;
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

    // 바텀메뉴 개별 메뉴 아이템 설정 가져오기
    const fetchBottomNavMenuItems = async () => {
      try {
        const config = getConfig();
        const base = config.backendUrl;
        const response = await fetch(`${base}/bottom-nav-menu-items`);
        if (response.ok) {
          const data = await response.json();
          setMenuItems({
            korean_stocks: data.korean_stocks === true,
            us_stocks: data.us_stocks === true,
            stock_analysis: data.stock_analysis === true,
            portfolio: data.portfolio === true,
            more: data.more === true
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
  }, []);

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
              className="flex flex-col items-center py-2 hover:bg-gray-800 cursor-pointer"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('한국주식추천 버튼 클릭:', { router: !!router, scannerLink });
                if (router && scannerLink) {
                  console.log('router.push 호출:', scannerLink);
                  router.push(scannerLink).catch(err => {
                    console.error('router.push 오류:', err);
                  });
                } else {
                  console.warn('router 또는 scannerLink가 없음:', { router: !!router, scannerLink });
                }
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="text-xs">한국주식추천</span>
            </button>
          )}
          {menuItems.us_stocks && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 hover:bg-gray-800 cursor-pointer"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('미국주식추천 버튼 클릭');
                if (router) {
                  router.push('/v2/us-stocks-scanner').catch(err => {
                    console.error('router.push 오류:', err);
                  });
                } else {
                  console.warn('router가 없음');
                }
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-xs">미국주식추천</span>
            </button>
          )}
          {menuItems.stock_analysis && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 hover:bg-gray-800 cursor-pointer"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('종목분석 버튼 클릭');
                if (router) {
                  router.push('/stock-analysis').catch(err => {
                    console.error('router.push 오류:', err);
                  });
                } else {
                  console.warn('router가 없음');
                }
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span className="text-xs">종목분석</span>
            </button>
          )}
          {menuItems.portfolio && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 hover:bg-gray-800 cursor-pointer"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('나의투자종목 버튼 클릭');
                if (router) {
                  router.push('/portfolio').catch(err => {
                    console.error('router.push 오류:', err);
                  });
                } else {
                  console.warn('router가 없음');
                }
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              <span className="text-xs">나의투자종목</span>
            </button>
          )}
          {user?.is_admin && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 hover:bg-gray-800 cursor-pointer"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('관리자 버튼 클릭');
                if (router) {
                  router.push('/admin').catch(err => {
                    console.error('router.push 오류:', err);
                  });
                } else {
                  console.warn('router가 없음');
                }
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="text-xs">관리자</span>
            </button>
          )}
          {menuItems.more && (
            <button 
              type="button"
              className="flex flex-col items-center py-2 hover:bg-gray-800 cursor-pointer"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('더보기 버튼 클릭');
                if (router) {
                  router.push('/more').catch(err => {
                    console.error('router.push 오류:', err);
                  });
                } else {
                  console.warn('router가 없음');
                }
              }}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
              <span className="text-xs">더보기</span>
            </button>
          )}
        </div>
      </div>

      {/* 하단 네비게이션 공간 확보 */}
      <div className="h-20"></div>
    </>
  );
}
