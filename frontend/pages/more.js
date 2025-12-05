import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import Layout from '../layouts/v2/Layout';

// 초기화면 설정 컴포넌트
function InitialScreenSetting() {
  const [initialScreen, setInitialScreen] = useState('korean');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // localStorage에서 초기화면 설정 읽기
    const saved = localStorage.getItem('initialScreen');
    if (saved === 'us' || saved === 'korean') {
      setInitialScreen(saved);
    } else {
      // 기본값: 한국주식추천
      setInitialScreen('korean');
    }
  }, []);

  const handleChange = (value) => {
    setInitialScreen(value);
    localStorage.setItem('initialScreen', value);
  };

  if (!mounted) {
    return (
      <div className="space-y-3">
        <div className="h-12 bg-gray-100 rounded-lg animate-pulse"></div>
        <div className="h-12 bg-gray-100 rounded-lg animate-pulse"></div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <button
        onClick={() => handleChange('korean')}
        className={`w-full flex items-center justify-between p-4 rounded-lg border-2 transition-all ${
          initialScreen === 'korean'
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-200 bg-white hover:border-gray-300'
        }`}
      >
        <div className="flex items-center space-x-3">
          <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
            initialScreen === 'korean' ? 'border-blue-500' : 'border-gray-300'
          }`}>
            {initialScreen === 'korean' && (
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            )}
          </div>
          <div className="text-left">
            <div className="font-medium text-gray-900">한국주식추천</div>
            <div className="text-xs text-gray-500">한국 주식 스캐너 화면</div>
          </div>
        </div>
        {initialScreen === 'korean' && (
          <span className="text-blue-500 text-sm font-medium">✓</span>
        )}
      </button>

      <button
        onClick={() => handleChange('us')}
        className={`w-full flex items-center justify-between p-4 rounded-lg border-2 transition-all ${
          initialScreen === 'us'
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-200 bg-white hover:border-gray-300'
        }`}
      >
        <div className="flex items-center space-x-3">
          <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
            initialScreen === 'us' ? 'border-blue-500' : 'border-gray-300'
          }`}>
            {initialScreen === 'us' && (
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            )}
          </div>
          <div className="text-left">
            <div className="font-medium text-gray-900">미국주식추천</div>
            <div className="text-xs text-gray-500">미국 주식 스캐너 화면</div>
          </div>
        </div>
        {initialScreen === 'us' && (
          <span className="text-blue-500 text-sm font-medium">✓</span>
        )}
      </button>
    </div>
  );
}

// Config 가져오기
const getConfig = () => {
  if (typeof window !== 'undefined') {
    return {
      backendUrl: process.env.NODE_ENV === 'production' 
        ? 'https://sohntech.ai.kr/api' 
        : 'http://localhost:8010'
    };
  }
  return { backendUrl: 'http://localhost:8010' };
};

export default function More() {
  const router = useRouter();
  const { isAuthenticated, user, loading: authLoading, authChecked, logout } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [menuItems, setMenuItems] = useState({ us_stocks: false });
  const [menuLoading, setMenuLoading] = useState(true);

  useEffect(() => {
    setMounted(true);
    
    // 바텀메뉴 설정 가져오기
    const fetchMenuItems = async () => {
      try {
        const config = getConfig();
        const response = await fetch(`${config.backendUrl}/bottom-nav-menu-items`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        setMenuItems(data);
      } catch (error) {
        console.error('메뉴 설정 조회 실패:', error);
        // 에러 시 기본값 사용 (모든 메뉴 표시)
        setMenuItems({
          korean_stocks: true,
          us_stocks: true,
          stock_analysis: true,
          portfolio: true,
          more: true
        });
      } finally {
        setMenuLoading(false);
      }
    };
    
    fetchMenuItems();
  }, []);

  const handleLogout = async () => {
    if (user && logout) {
      try {
        await logout();
        router.push('/customer-scanner');
      } catch (error) {
        console.error('로그아웃 중 오류:', error);
        router.push('/customer-scanner');
      }
    }
  };

  if (!mounted) {
    return null;
  }

  return (
    <>
      <Head>
        <title>더보기 - 스톡인사이트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <Layout headerTitle="더보기">
        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">더보기</h2>
              <p className="text-sm opacity-90">다양한 서비스와 설정을 확인하세요</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <span className="text-2xl">⚙️</span>
            </div>
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="p-4">
          {/* 사용자 정보 카드 */}
          {!authLoading && authChecked && user ? (
            (() => {
              const isSpecialUser = user?.email === 'kuksos80215@daum.net';
              return (
                <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
                  <div className="flex items-center space-x-4">
                    <div className={`w-12 h-12 ${isSpecialUser ? 'bg-gradient-to-br from-pink-100 to-rose-100' : 'bg-blue-100'} rounded-full flex items-center justify-center`}>
                      {isSpecialUser ? (
                        <span className="special-user-icon text-xl">✨</span>
                      ) : (
                        <span className="text-xl">👤</span>
                      )}
                    </div>
                    <div className="flex-1">
                      {isSpecialUser ? (
                        <>
                          <div className="special-user-name font-semibold text-lg">윤봄님</div>
                          <div className="text-sm text-gray-600 mt-1 flex items-center space-x-2">
                            <span className="special-user-badge inline-block px-2 py-0.5 text-xs font-semibold rounded-full text-white">
                              💖 Special
                            </span>
                            {user.membership_tier === 'vip' ? (
                              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">
                                👑 VIP
                              </span>
                            ) : user.membership_tier === 'premium' ? (
                              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                                👑 프리미엄
                              </span>
                            ) : null}
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="font-semibold text-gray-900">{user.name}님</div>
                          <div className="text-sm text-gray-600">
                            {user.is_admin ? '🔧 관리자' : 
                             user.membership_tier === 'vip' ? '👑 VIP 회원' :
                             user.membership_tier === 'premium' ? '👑 프리미엄 회원' : '일반 회원'}
                          </div>
                          {/* 디버깅 정보 */}
                          <div className="text-xs text-gray-400 mt-1">
                            Debug: is_admin={String(user.is_admin)} ({typeof user.is_admin}), tier={user.membership_tier}
                          </div>
                        </>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-gray-500">포인트</div>
                      <div className="font-semibold text-blue-600">0P</div>
                    </div>
                  </div>
                </div>
              );
            })()
          ) : (
            <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-xl">👤</span>
                </div>
                <div className="font-semibold text-gray-900 mb-2">게스트 사용자</div>
                <button 
                  onClick={() => router.push('/login')}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
                >
                  로그인하기
                </button>
              </div>
            </div>
          )}




          {/* 초기화면 설정 - 미국주식 메뉴 활성화 시에만 표시 */}
          {menuItems.us_stocks && (
            <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
              <h3 className="font-semibold text-gray-900 mb-4">초기화면 설정</h3>
              <p className="text-sm text-gray-600 mb-4">앱 시작 시 표시할 화면을 선택하세요</p>
              <InitialScreenSetting />
            </div>
          )}

          {/* 투자 활용법 가이드 */}
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <h3 className="font-semibold text-gray-900 mb-4">투자 활용법</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xl">🔍</span>
                  <h4 className="font-semibold text-gray-800">어떤 종목을 찾나요?</h4>
                </div>
                <p className="text-sm text-gray-600 font-medium">📈 상승 초입 단계의 종목들</p>
                <p className="text-xs text-gray-500 mt-1">• 하락이 끝나고 막 오르기 시작하는 종목</p>
                <p className="text-xs text-gray-500">• 거래량이 늘어나며 관심받기 시작하는 종목</p>
                <p className="text-xs text-blue-600 mt-2 font-medium">💡 상승 초기에 발견해서 수익 기회 제공</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xl">💰</span>
                  <h4 className="font-semibold text-gray-800">어떻게 투자하나요?</h4>
                </div>
                <p className="text-sm text-gray-600 font-medium">🎯 추천가 기준 매수 → 보유 전략</p>
                <p className="text-xs text-gray-500 mt-1">• <strong>매수</strong>: 추천가(스캔일 종가) 기준 ±2% 이내 매수</p>
                <p className="text-xs text-gray-500">• <strong>익절</strong>: +3% 도달 시 즉시 매도</p>
                <p className="text-xs text-gray-500">• <strong>손절</strong>: -7% 하락 시 매도 (5일 후)</p>
                <p className="text-xs text-gray-500">• <strong>보존</strong>: +1.5% 도달 후 원가 이하 시 매도</p>
                <div className="mt-2 p-2 bg-green-100 rounded">
                  <p className="text-xs text-green-700 font-medium">💡 핵심: 종목당 100~200만원, 동시 3~5개 보유, 보유기간 5~45일</p>
                </div>
                <p className="text-xs text-red-500 mt-2 font-medium">⚠️ 투자는 본인 책임, 신중한 판단 필요</p>
              </div>
            </div>
          </div>

          {/* 준비중인 기능 */}
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <h3 className="font-semibold text-gray-900 mb-4">준비중인 기능</h3>
            <div className="bg-orange-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <h5 className="font-medium text-orange-700 mb-2">📱 알림 서비스</h5>
                  <ul className="space-y-1 text-orange-600">
                    <li>• <strong>카카오톡 알림톡</strong>: 스캔 결과 자동 알림</li>
                    <li>• <strong>푸시 알림</strong>: 모바일 앱 알림</li>
                    <li>• <strong>이메일 알림</strong>: 상세 분석 리포트</li>
                  </ul>
                </div>
                <div>
                  <h5 className="font-medium text-orange-700 mb-2">💼 관심종목 관리</h5>
                  <ul className="space-y-1 text-orange-600">
                    <li>• <strong>관심종목 등록</strong>: 스캔 결과에서 바로 등록</li>
                    <li>• <strong>관심종목 목록</strong>: 등록한 종목 관리</li>
                    <li>• <strong>알림 설정</strong>: 관심종목 변동 알림</li>
                  </ul>
                </div>
                <div>
                  <h5 className="font-medium text-orange-700 mb-2">📊 고급 분석</h5>
                  <ul className="space-y-1 text-orange-600">
                    <li>• <strong>상세 차트</strong>: 기술적 분석 도구</li>
                    <li>• <strong>기업정보</strong>: 재무제표 및 뉴스</li>
                    <li>• <strong>종목분석</strong>: 단일 종목 상세 분석</li>
                  </ul>
                </div>
              </div>
              <div className="mt-4 p-3 bg-orange-100 rounded-lg">
                <p className="text-sm text-orange-700">
                  <strong>💡 안내:</strong> 모든 기능은 순차적으로 출시될 예정입니다. 
                  먼저 기본 스캔 서비스를 이용해보시고, 추가 기능 출시 소식을 기다려주세요!
                </p>
              </div>
            </div>
          </div>

          {/* 계정 관리 */}
          {!authLoading && authChecked && user && (
            <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
              <h3 className="font-semibold text-gray-900 mb-4">계정 관리</h3>
              <div className="space-y-3">
                <button 
                  onClick={handleLogout}
                  className="w-full flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                      <span className="text-sm">🚪</span>
                    </div>
                    <span className="text-gray-700">로그아웃</span>
                  </div>
                  <span className="text-gray-400">›</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </Layout>
    </>
  );
}

// getServerSideProps 제거 - API 라우트를 통해 클라이언트에서 로드
export async function getServerSideProps() {
  return {
    props: {}
  };
}
