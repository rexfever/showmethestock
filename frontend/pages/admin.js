import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import getConfig from '../config';
import Cookies from 'js-cookie';

export default function AdminDashboard() {
  const router = useRouter();
  const { isAuthenticated, user, token, loading: authLoading, authChecked, logout } = useAuth();
  
  // 날짜 형식 변환 함수
  const convertToYYYYMMDD = (dateStr) => {
    if (!dateStr) return '';
    return dateStr.replace(/-/g, '');
  };
  
  const convertToYYYYMMDD_Display = (dateStr) => {
    if (!dateStr || dateStr.length !== 8) return '';
    return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
  };
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  
  // 방문자 통계 상태
  const [dailyVisitorStats, setDailyVisitorStats] = useState([]);
  const [dailyVisitorStatsByPath, setDailyVisitorStatsByPath] = useState([]);
  const [cumulativeVisitorStats, setCumulativeVisitorStats] = useState(null);
  const [visitorStatsLoading, setVisitorStatsLoading] = useState(false);
  const [visitorStatsStartDate, setVisitorStatsStartDate] = useState('');
  const [visitorStatsEndDate, setVisitorStatsEndDate] = useState('');
  const authErrorShownRef = useRef(false); // 인증 에러 알림 중복 방지 (ref 사용)
  const isRedirectingRef = useRef(false); // 리다이렉트 중 플래그 (ref 사용)
  const authCheckDoneRef = useRef(false); // 인증 체크 완료 플래그
  
  // 메인트넌스 설정 상태
  const [maintenanceSettings, setMaintenanceSettings] = useState({
    is_enabled: false,
    end_date: '',
    message: '서비스 점검 중입니다.'
  });
  const [maintenanceLoading, setMaintenanceLoading] = useState(false);
  
  // 팝업 공지 설정 상태
  const [popupNotice, setPopupNotice] = useState({
    is_enabled: false,
    title: '',
    message: '',
    start_date: '',
    end_date: ''
  });
  const [popupLoading, setPopupLoading] = useState(false);

  
  // 스캐너 설정 상태 (엔진 중심으로 단순화)
  const [scannerSettings, setScannerSettings] = useState({
    active_engine: 'v1',
    regime_version: 'v1'
  });
  const [scannerLoading, setScannerLoading] = useState(false);
  
  // 바텀메뉴 링크 설정 상태
  const [bottomNavLink, setBottomNavLink] = useState({
    link_type: 'v1'  // 'v1' 또는 'v2'
  });
  const [bottomNavLinkLoading, setBottomNavLinkLoading] = useState(false);
  
  // 바텀메뉴 노출 설정 상태
  const [bottomNavVisible, setBottomNavVisible] = useState(true);
  const [bottomNavVisibleLoading, setBottomNavVisibleLoading] = useState(false);
  
  // 바텀메뉴 개별 메뉴 아이템 설정 상태
  const [bottomNavMenuItems, setBottomNavMenuItems] = useState({
    korean_stocks: true,
    us_stocks: true,
    stock_analysis: true,
    portfolio: true,
    more: true
  });
  const [bottomNavMenuItemsLoading, setBottomNavMenuItemsLoading] = useState(false);
  const [scannerLink, setScannerLink] = useState('/customer-scanner'); // 동적 스캐너 링크

  useEffect(() => {
    // 리다이렉트 중이면 추가 체크 안 함
    if (isRedirectingRef.current) {
      return;
    }
    
    // 이미 인증 체크를 완료했으면 다시 실행하지 않음
    if (authCheckDoneRef.current) {
      return;
    }
    
    // 인증 체크가 완료되지 않았거나 로딩 중이면 대기
    if (!authChecked || authLoading) {
      return;
    }
    
    // 인증 체크 완료 플래그 설정
    authCheckDoneRef.current = true;
    
    if (!isAuthenticated()) {
      isRedirectingRef.current = true;
      router.replace('/login');
      return;
    }
    
    // 사용자 정보가 로드되지 않았으면 대기
    if (!user) {
      authCheckDoneRef.current = false; // 사용자 정보 로드 대기
      return;
    }
    
    // 강화된 관리자 권한 확인 - 다양한 타입 처리
    const isAdmin = user && (
      user.is_admin === true || 
      user.is_admin === 1 || 
      user.is_admin === "1" ||
      user.is_admin === "true"
    );
    
    if (!isAdmin) {
      // 동적 스캐너 링크를 먼저 가져온 후 리다이렉트
      const redirectToScanner = async () => {
        try {
          const { getScannerLink } = await import('../utils/navigation');
          const scannerLink = await getScannerLink();
          router.replace(scannerLink);
        } catch (error) {
          console.error('스캐너 링크 조회 실패:', error);
          // 에러 시 기본값 사용
          router.replace('/v2/scanner-v2');
        }
      };
      alert('관리자 권한이 필요합니다.');
      redirectToScanner();
      return;
    }
    
    // URL 파라미터에서 analyze 값 확인
    if (router.query.analyze) {
      performAnalysis(router.query.analyze);
    } else {
      fetchAdminData();
      fetchScannerSettings();
      fetchBottomNavLink();
      fetchBottomNavVisible();
      fetchBottomNavMenuItems();
    }
  }, [authChecked, authLoading, user, token, router]);
  
  // router 이벤트 리스너: 리다이렉트 시작 시 추가 실행 방지
  useEffect(() => {
    const handleRouteChangeStart = (url) => {
      isRedirectingRef.current = true;
      // 로그인 페이지로 이동하는 경우에만 플래그 설정
      if (url === '/login') {
        authErrorShownRef.current = true;
      }
    };
    
    const handleRouteChangeComplete = (url) => {
      // 리다이렉트 완료 후 플래그 리셋 (로그인 페이지 도착 시)
      // url 파라미터와 router.pathname 모두 확인 (Next.js 버전별 차이 대응)
      const targetUrl = url || router.pathname || router.asPath;
      if (targetUrl === '/login' || targetUrl.startsWith('/login')) {
        isRedirectingRef.current = false;
        authErrorShownRef.current = false;
        authCheckDoneRef.current = false;
      }
    };
    
    router.events?.on('routeChangeStart', handleRouteChangeStart);
    router.events?.on('routeChangeComplete', handleRouteChangeComplete);
    
    return () => {
      router.events?.off('routeChangeStart', handleRouteChangeStart);
      router.events?.off('routeChangeComplete', handleRouteChangeComplete);
    };
  }, [router]);

  const handleAuthError = useCallback(() => {
    // 이미 리다이렉트 중이거나 에러를 표시한 경우 무시
    if (isRedirectingRef.current || authErrorShownRef.current) {
      return;
    }
    
    // 플래그 설정 (동기적으로) - 먼저 설정하여 중복 실행 방지
    // 이 순서가 중요: 먼저 플래그를 설정한 후 다른 작업 수행
    authErrorShownRef.current = true;
    isRedirectingRef.current = true;
    authCheckDoneRef.current = false; // 인증 체크 재실행 방지 해제
    
    // 로그아웃 처리
    if (logout) {
      logout();
    }
    // 쿠키와 localStorage 정리
    Cookies.remove('auth_token');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    // 리다이렉트 (replace로 히스토리에 남기지 않음)
    // alert는 리다이렉트 전에 표시 (리다이렉트 후에는 alert가 표시되지 않을 수 있음)
    alert('세션이 만료되었습니다. 다시 로그인해주세요.');
    
    // 리다이렉트는 alert 확인 후 실행되도록 약간의 지연
    setTimeout(() => {
      router.replace('/login');
    }, 100);
  }, [logout, router]);

  const fetchBottomNavLink = async () => {
    try {
      const config = getConfig();
      const base = config.backendUrl;
      const response = await fetch(`${base}/admin/bottom-nav-link`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const data = await response.json();
        setBottomNavLink({
          link_type: data.link_type || 'v1'
        });
        // 동적 스캐너 링크 설정
        const linkUrl = data.link_url || (data.link_type === 'v2' ? '/v2/scanner-v2' : '/customer-scanner');
        setScannerLink(linkUrl);
      } else if (response.status === 401) {
        handleAuthError();
      }
    } catch (error) {
      console.error('바텀메뉴 링크 설정 조회 실패:', error);
      // 에러 시 기본값 사용
      setScannerLink('/customer-scanner');
    }
  };

  const fetchBottomNavVisible = async () => {
    setBottomNavVisibleLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      const response = await fetch(`${base}/admin/bottom-nav-visible`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setBottomNavVisible(data.is_visible !== false);
      } else if (response.status === 401) {
        handleAuthError();
        return;
      }
    } catch (error) {
      console.error('바텀메뉴 노출 설정 조회 실패:', error);
    } finally {
      setBottomNavVisibleLoading(false);
    }
  };

  const updateBottomNavVisible = async () => {
    setBottomNavVisibleLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      const response = await fetch(`${base}/admin/bottom-nav-visible`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ is_visible: bottomNavVisible })
      });
      if (response.ok) {
        const data = await response.json();
        fetchBottomNavVisible();
        return { success: true, message: data.message || '바텀메뉴 노출 설정이 저장되었습니다.' };
      } else if (response.status === 401) {
        handleAuthError();
        return { success: false, error: '인증 오류' };
      } else {
        const errorData = await response.json();
        return { success: false, error: errorData.detail || '바텀메뉴 노출 설정 저장에 실패했습니다.' };
      }
    } catch (error) {
      console.error('바텀메뉴 노출 설정 저장 실패:', error);
      return { success: false, error: '바텀메뉴 노출 설정 저장 중 오류가 발생했습니다.' };
    } finally {
      setBottomNavVisibleLoading(false);
    }
  };

  const fetchBottomNavMenuItems = async () => {
    setBottomNavMenuItemsLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      const response = await fetch(`${base}/admin/bottom-nav-menu-items`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setBottomNavMenuItems({
          korean_stocks: data.korean_stocks === true,
          us_stocks: data.us_stocks === true,
          stock_analysis: data.stock_analysis === true,
          portfolio: data.portfolio === true,
          more: data.more === true
        });
      } else if (response.status === 401) {
        handleAuthError();
        return;
      }
    } catch (error) {
      console.error('바텀메뉴 메뉴 아이템 설정 조회 실패:', error);
    } finally {
      setBottomNavMenuItemsLoading(false);
    }
  };

  const updateBottomNavMenuItems = async () => {
    setBottomNavMenuItemsLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      const response = await fetch(`${base}/admin/bottom-nav-menu-items`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ menu_items: bottomNavMenuItems })
      });
      if (response.ok) {
        const data = await response.json();
        fetchBottomNavMenuItems();
        return { success: true, message: data.message || '바텀메뉴 메뉴 아이템 설정이 저장되었습니다.' };
      } else if (response.status === 401) {
        handleAuthError();
        return { success: false, error: '인증 오류' };
      } else {
        const errorData = await response.json();
        return { success: false, error: errorData.detail || '바텀메뉴 메뉴 아이템 설정 저장에 실패했습니다.' };
      }
    } catch (error) {
      console.error('바텀메뉴 메뉴 아이템 설정 저장 실패:', error);
      return { success: false, error: '바텀메뉴 메뉴 아이템 설정 저장 중 오류가 발생했습니다.' };
    } finally {
      setBottomNavMenuItemsLoading(false);
    }
  };

  const updateBottomNavLink = async () => {
    setBottomNavLinkLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      const response = await fetch(`${base}/admin/bottom-nav-link`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ link_type: bottomNavLink.link_type }),
      });
      if (response.ok) {
        const data = await response.json();
        // 설정 다시 불러오기
        fetchBottomNavLink();
        return { success: true, message: data.message || '바텀메뉴 링크 설정이 저장되었습니다.' };
      } else {
        const data = await response.json();
        return { success: false, error: `저장 실패: ${data.detail || '알 수 없는 오류'}` };
      }
    } catch (error) {
      console.error('바텀메뉴 링크 설정 저장 실패:', error);
      return { success: false, error: '저장 중 오류가 발생했습니다.' };
    } finally {
      setBottomNavLinkLoading(false);
    }
  };

  const fetchScannerSettings = async () => {
    setScannerLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/admin/scanner-settings`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.ok && data.settings) {
          setScannerSettings({
            scanner_version: data.settings.scanner_version || 'v1',
            regime_version: data.settings.regime_version || 'v1',
            scanner_v2_enabled: data.settings.scanner_v2_enabled === 'true' || data.settings.scanner_v2_enabled === true,
            active_engine: data.settings.active_engine || 'v1'
          });
        }
      } else if (response.status === 401) {
        handleAuthError();
      }
    } catch (error) {
      console.error('스캐너 설정 조회 실패:', error);
    } finally {
      setScannerLoading(false);
    }
  };
  
  const updateScannerSettings = async () => {
    setScannerLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/admin/scanner-settings`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          active_engine: scannerSettings.active_engine || 'v1',
          regime_version: scannerSettings.regime_version || 'v1'
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.ok) {
          alert(data.message || '스캐너 설정이 업데이트되었습니다.');
        } else {
          alert(data.error || '설정 업데이트에 실패했습니다.');
        }
      } else if (response.status === 401) {
        handleAuthError();
      } else {
        const data = await response.json();
        alert(data.error || '설정 업데이트에 실패했습니다.');
      }
    } catch (error) {
      console.error('스캐너 설정 업데이트 실패:', error);
      alert('설정 업데이트 중 오류가 발생했습니다.');
    } finally {
      setScannerLoading(false);
    }
  };

  const performAnalysis = async (ticker) => {
    setAnalysisLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/analyze?name_or_code=${encodeURIComponent(ticker)}`);
      const data = await response.json();
      
      if (data.ok) {
        setAnalysisResult(data);
      } else {
        alert(`분석 실패: ${data.error}`);
      }
    } catch (error) {
      alert('분석 중 오류가 발생했습니다.');
    } finally {
      setAnalysisLoading(false);
    }
  };

  const fetchVisitorStats = async () => {
    setVisitorStatsLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const params = new URLSearchParams();
      if (visitorStatsStartDate) {
        params.append('start_date', visitorStatsStartDate);
      }
      if (visitorStatsEndDate) {
        params.append('end_date', visitorStatsEndDate);
      }
      
      const [dailyResponse, dailyByPathResponse, cumulativeResponse] = await Promise.all([
        fetch(`${base}/admin/access-logs/daily-stats?${params.toString()}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }),
        fetch(`${base}/admin/access-logs/daily-stats-by-path?${params.toString()}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }),
        fetch(`${base}/admin/access-logs/cumulative-stats?${params.toString()}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      ]);
      
      if (dailyResponse.ok) {
        const dailyData = await dailyResponse.json();
        if (dailyData.ok) {
          setDailyVisitorStats(dailyData.stats || []);
        }
      } else if (dailyResponse.status === 401) {
        handleAuthError();
        return;
      }
      
      if (dailyByPathResponse.ok) {
        const dailyByPathData = await dailyByPathResponse.json();
        if (dailyByPathData.ok) {
          setDailyVisitorStatsByPath(dailyByPathData.stats || []);
        }
      } else if (dailyByPathResponse.status === 401) {
        handleAuthError();
        return;
      }
      
      if (cumulativeResponse.ok) {
        const cumulativeData = await cumulativeResponse.json();
        if (cumulativeData.ok) {
          setCumulativeVisitorStats(cumulativeData.data);
        }
      } else if (cumulativeResponse.status === 401) {
        handleAuthError();
        return;
      }
    } catch (error) {
      console.error('방문자 통계 조회 실패:', error);
    } finally {
      setVisitorStatsLoading(false);
    }
  };

  const fetchAdminData = async () => {
    try {
      const config = getConfig();
      const base = config.backendUrl;

      const [statsResponse, usersResponse, maintenanceResponse, popupResponse] = await Promise.all([
        fetch(`${base}/admin/stats`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }),
        fetch(`${base}/admin/users`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }),
        fetch(`${base}/admin/maintenance`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }),
        fetch(`${base}/admin/popup-notice`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      ]);

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      } else if (statsResponse.status === 401) {
        handleAuthError();
        return;
      }

      if (usersResponse.ok) {
        const usersData = await usersResponse.json();
        setUsers(usersData.users);
      } else if (usersResponse.status === 401) {
        handleAuthError();
        return;
      }

      if (maintenanceResponse.ok) {
        const maintenanceData = await maintenanceResponse.json();
        setMaintenanceSettings({
          is_enabled: maintenanceData.is_enabled,
          end_date: convertToYYYYMMDD_Display(maintenanceData.end_date) || '',
          message: maintenanceData.message || '서비스 점검 중입니다.'
        });
      } else if (maintenanceResponse.status === 401) {
        handleAuthError();
        return;
      }

      if (popupResponse.ok) {
        const popupData = await popupResponse.json();
        setPopupNotice({
          is_enabled: popupData.is_enabled,
          title: popupData.title || '',
          message: popupData.message || '',
          start_date: convertToYYYYMMDD_Display(popupData.start_date) || '',
          end_date: convertToYYYYMMDD_Display(popupData.end_date) || ''
        });
      } else if (popupResponse.status === 401) {
        handleAuthError();
        return;
      }
    } catch (error) {
      console.error('관리자 데이터 로딩 오류:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateMaintenanceSettings = async () => {
    setMaintenanceLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/admin/maintenance`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...maintenanceSettings,
          end_date: convertToYYYYMMDD(maintenanceSettings.end_date)
        })
      });

      if (response.ok) {
        alert('메인트넌스 설정이 업데이트되었습니다.');
      } else if (response.status === 401) {
        handleAuthError();
      } else {
        alert('메인트넌스 설정 업데이트에 실패했습니다.');
      }
    } catch (error) {
      console.error('메인트넌스 설정 업데이트 실패:', error);
      alert('메인트넌스 설정 업데이트 중 오류가 발생했습니다.');
    } finally {
      setMaintenanceLoading(false);
    }
  };

  const updatePopupNotice = async () => {
    setPopupLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/admin/popup-notice`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...popupNotice,
          start_date: convertToYYYYMMDD(popupNotice.start_date),
          end_date: convertToYYYYMMDD(popupNotice.end_date)
        })
      });

      if (response.ok) {
        alert('팝업 공지 설정이 업데이트되었습니다.');
      } else if (response.status === 401) {
        handleAuthError();
      } else {
        alert('팝업 공지 설정 업데이트에 실패했습니다.');
      }
    } catch (error) {
      console.error('팝업 공지 설정 업데이트 실패:', error);
      alert('팝업 공지 설정 업데이트 중 오류가 발생했습니다.');
    } finally {
      setPopupLoading(false);
    }
  };


  const handleUserEdit = (user) => {
    setEditingUser({ ...user });
    setShowUserModal(true);
  };

  const handleUserUpdate = async () => {
    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';

      const response = await fetch(`${base}/admin/users/${editingUser.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: editingUser.id,
          membership_tier: editingUser.membership_tier,
          subscription_status: editingUser.subscription_status,
          is_admin: editingUser.is_admin
        })
      });

      if (response.ok) {
        alert('사용자 정보가 업데이트되었습니다.');
        setShowUserModal(false);
        fetchAdminData(); // 데이터 새로고침
      } else {
        const errorData = await response.json();
        alert(`업데이트 실패: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('사용자 업데이트 오류:', error);
      alert('사용자 업데이트 중 오류가 발생했습니다.');
    }
  };

  const handleUserDelete = async (userId) => {
    if (!confirm('정말 이 사용자를 삭제하시겠습니까?')) {
      return;
    }

    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';

      const response = await fetch(`${base}/admin/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: userId,
          confirm: true
        })
      });

      if (response.ok) {
        alert('사용자가 삭제되었습니다.');
        fetchAdminData(); // 데이터 새로고침
      } else {
        const errorData = await response.json();
        alert(`삭제 실패: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('사용자 삭제 오류:', error);
      alert('사용자 삭제 중 오류가 발생했습니다.');
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('ko-KR').format(price);
  };

  const getTierColor = (tier) => {
    switch (tier) {
      case 'free': return 'bg-gray-100 text-gray-800';
      case 'premium': return 'bg-blue-100 text-blue-800';
      case 'vip': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTierName = (tier) => {
    switch (tier) {
      case 'free': return '무료';
      case 'premium': return '프리미엄';
      case 'vip': return 'VIP';
      default: return '무료';
    }
  };

  if (loading || analysisLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">
            {analysisLoading ? '종목 분석 중...' : '관리자 데이터를 불러오는 중...'}
          </p>
        </div>
      </div>
    );
  }

  // 분석 결과가 있으면 분석 화면 표시
  if (analysisResult) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Head>
          <title>종목 분석 결과 - Stock Insight</title>
        </Head>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* 헤더 */}
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">종목 분석 결과</h1>
              <p className="mt-2 text-gray-600">{analysisResult.item?.name} ({analysisResult.item?.ticker})</p>
            </div>
            <button
              onClick={() => {
                setAnalysisResult(null);
                router.push('/admin');
              }}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-700 border border-gray-300 rounded-md"
            >
              관리자 대시보드로 돌아가기
            </button>
          </div>

          {/* 분석 결과 카드 */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* 기본 정보 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">기본 정보</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">종목명:</span>
                    <span className="font-medium">{analysisResult.item?.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">종목코드:</span>
                    <span className="font-medium">{analysisResult.item?.ticker}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">현재가:</span>
                    <span className="font-medium">{analysisResult.item?.indicators?.close?.toLocaleString()}원</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">거래량:</span>
                    <span className="font-medium">{analysisResult.item?.indicators?.VOL?.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* 분석 결과 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">분석 결과</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">매칭 여부:</span>
                    <span className={`font-medium ${analysisResult.item?.match ? 'text-green-600' : 'text-red-600'}`}>
                      {analysisResult.item?.match ? '매칭' : '비매칭'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">점수:</span>
                    <span className="font-medium">{analysisResult.item?.score}점</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">전략:</span>
                    <span className="font-medium">{analysisResult.item?.strategy}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">시장:</span>
                    <span className="font-medium">{analysisResult.item?.market}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 기술적 지표 */}
            {analysisResult.item?.indicators && (
              <div className="mt-8">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">기술적 지표</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm text-gray-600">TEMA(20)</div>
                    <div className="font-medium">{analysisResult.item.indicators.TEMA?.toFixed(2)}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm text-gray-600">DEMA(10)</div>
                    <div className="font-medium">{analysisResult.item.indicators.DEMA?.toFixed(2)}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm text-gray-600">RSI(14)</div>
                    <div className="font-medium">{analysisResult.item.indicators.RSI?.toFixed(2)}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm text-gray-600">MACD</div>
                    <div className="font-medium">{analysisResult.item.indicators.MACD?.toFixed(2)}</div>
                  </div>
                </div>
              </div>
            )}

            {/* 액션 버튼 */}
            <div className="mt-8 flex justify-center space-x-4">
              <button
                onClick={() => {
                  const naverUrl = `https://finance.naver.com/item/main.naver?code=${analysisResult.item?.ticker}`;
                  window.open(naverUrl, '_blank');
                }}
                className="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                네이버 금융에서 보기
              </button>
              <button
                onClick={() => {
                  const newTicker = prompt('다른 종목을 분석하시겠습니까? 종목 코드 또는 종목명을 입력하세요:');
                  if (newTicker) {
                    performAnalysis(newTicker);
                  }
                }}
                className="px-6 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600"
              >
                다른 종목 분석
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 로딩 상태 처리
  if (!authChecked || authLoading) {
    return (
      <>
        <Head>
          <title>관리자 대시보드 - Stock Insight</title>
        </Head>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">인증 확인 중...</p>
          </div>
        </div>
      </>
    );
  }

  if (!isAuthenticated()) {
    return null; // useEffect에서 리다이렉트 처리됨
  }

  if (!user) {
    return (
      <>
        <Head>
          <title>관리자 대시보드 - Stock Insight</title>
        </Head>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">사용자 정보 로딩 중...</p>
          </div>
        </div>
      </>
    );
  }

  // 관리자 권한 재확인 (추가 안전장치)
  const isAdmin = user && (
    user.is_admin === true || 
    user.is_admin === 1 || 
    user.is_admin === "1" ||
    user.is_admin === "true"
  );

  if (!isAdmin) {
    return null; // useEffect에서 리다이렉트 처리됨
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>관리자 대시보드 - Stock Insight</title>
      </Head>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 헤더 */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">관리자 대시보드</h1>
            <p className="mt-2 text-gray-600">사용자 관리 및 시스템 통계</p>
          </div>
          <button
            onClick={() => {
              // 동적 메인 링크: active_engine에 따라 적절한 페이지로 이동
              let targetPath = '/';
              if (scannerLink && scannerLink !== '/customer-scanner') {
                targetPath = scannerLink;
              }
              console.log('[Admin] 메인으로 돌아가기 클릭:', { scannerLink, targetPath, currentPath: router?.asPath });
              if (router?.asPath === targetPath) {
                console.log('[Admin] 같은 페이지이므로 이동하지 않음');
                return;
              }
              console.log('[Admin] 이동 시작:', targetPath);
              window.location.href = targetPath;
            }}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-700 border border-gray-300 rounded-md"
          >
            메인으로 돌아가기
          </button>
        </div>

        {/* 통계 카드 */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">총 사용자</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.total_users}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 rounded-lg">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">활성 구독</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.active_subscriptions}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-yellow-100 rounded-lg">
                  <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">총 수익</p>
                  <p className="text-2xl font-semibold text-gray-900">{formatPrice(stats.total_revenue)}원</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">VIP 사용자</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.vip_users}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 방문자 통계 */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-medium text-gray-900">📊 방문자 통계</h2>
                <p className="text-sm text-gray-600">일별 방문자 수 및 누적 방문자 수 조회</p>
              </div>
              <button
                onClick={fetchVisitorStats}
                disabled={visitorStatsLoading}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
              >
                {visitorStatsLoading ? '조회 중...' : '🔄 새로고침'}
              </button>
            </div>
          </div>
          <div className="px-6 py-4 space-y-6">
            {/* 날짜 범위 선택 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  시작 날짜
                </label>
                <input
                  type="date"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={visitorStatsStartDate}
                  onChange={(e) => setVisitorStatsStartDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  종료 날짜
                </label>
                <input
                  type="date"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={visitorStatsEndDate}
                  onChange={(e) => setVisitorStatsEndDate(e.target.value)}
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={fetchVisitorStats}
                  disabled={visitorStatsLoading}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {visitorStatsLoading ? '조회 중...' : '조회'}
                </button>
              </div>
            </div>

            {/* 누적 방문자 수 */}
            {cumulativeVisitorStats && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">누적 방문자 수</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-white rounded-lg p-4 shadow-sm">
                    <p className="text-sm text-gray-600 mb-1">기간</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {cumulativeVisitorStats.start_date || '전체'} ~ {cumulativeVisitorStats.end_date || '전체'}
                    </p>
                  </div>
                  <div className="bg-white rounded-lg p-4 shadow-sm">
                    <p className="text-sm text-gray-600 mb-1">고유 방문자 수</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {cumulativeVisitorStats.total_unique_visitors?.toLocaleString() || 0}명
                    </p>
                  </div>
                  <div className="bg-white rounded-lg p-4 shadow-sm">
                    <p className="text-sm text-gray-600 mb-1">총 방문 횟수</p>
                    <p className="text-2xl font-bold text-indigo-600">
                      {cumulativeVisitorStats.total_visits?.toLocaleString() || 0}회
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 일별 방문자 수 테이블 */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">일별 방문자 수</h3>
              {visitorStatsLoading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="mt-2 text-sm text-gray-600">조회 중...</p>
                </div>
              ) : dailyVisitorStats.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          날짜
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          고유 방문자 수
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          총 방문 횟수
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {dailyVisitorStats.map((stat, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {stat.date}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {stat.unique_visitors?.toLocaleString() || 0}명
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {stat.total_visits?.toLocaleString() || 0}회
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <p>조회된 데이터가 없습니다.</p>
                  <p className="text-sm mt-2">날짜 범위를 선택하고 조회 버튼을 클릭하세요.</p>
                </div>
              )}
            </div>

            {/* 화면별 방문자 수 테이블 */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">화면별 방문자 수</h3>
              {visitorStatsLoading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="mt-2 text-sm text-gray-600">조회 중...</p>
                </div>
              ) : dailyVisitorStatsByPath.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          날짜
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          화면
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          고유 방문자 수
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          총 방문 횟수
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {dailyVisitorStatsByPath.map((stat, index) => {
                        // 경로를 화면명으로 변환
                        const getPathName = (path) => {
                          const pathMap = {
                            '/v2/us-stocks-scanner': '미국주식추천',
                            '/v2/scanner-v2': '한국주식추천 (V2)',
                            '/customer-scanner': '한국주식추천 (V1)',
                            '/stock-analysis': '종목분석',
                            '/portfolio': '나의투자종목',
                            '/my-stocks': '나의투자종목 (대체)',
                            '/more': '더보기'
                          };
                          return pathMap[path] || path;
                        };
                        
                        return (
                          <tr key={`${stat.date}-${stat.path}-${index}`} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {stat.date}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {getPathName(stat.path)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {stat.unique_visitors?.toLocaleString() || 0}명
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {stat.total_visits?.toLocaleString() || 0}회
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <p>조회된 데이터가 없습니다.</p>
                  <p className="text-sm mt-2">날짜 범위를 선택하고 조회 버튼을 클릭하세요.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 팝업 공지 설정 */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">팝업 공지 설정</h2>
            <p className="text-sm text-gray-600">사용자에게 표시될 팝업 공지를 관리합니다</p>
          </div>
          <div className="px-6 py-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">팝업 공지 활성화</label>
                <p className="text-xs text-gray-500">활성화 시 사용자에게 팝업 공지가 표시됩니다</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={popupNotice.is_enabled}
                  onChange={(e) => setPopupNotice({
                    ...popupNotice,
                    is_enabled: e.target.checked
                  })}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            {popupNotice.is_enabled && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    공지 제목
                  </label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={popupNotice.title}
                    onChange={(e) => setPopupNotice({
                      ...popupNotice,
                      title: e.target.value
                    })}
                    placeholder="공지 제목을 입력하세요"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    공지 내용
                  </label>
                  <textarea
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={4}
                    value={popupNotice.message}
                    onChange={(e) => setPopupNotice({
                      ...popupNotice,
                      message: e.target.value
                    })}
                    placeholder="공지 내용을 입력하세요"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      시작 날짜
                    </label>
                    <input
                      type="date"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={popupNotice.start_date}
                      onChange={(e) => setPopupNotice({
                        ...popupNotice,
                        start_date: e.target.value
                      })}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      종료 날짜
                    </label>
                    <input
                      type="date"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={popupNotice.end_date}
                      onChange={(e) => setPopupNotice({
                        ...popupNotice,
                        end_date: e.target.value
                      })}
                    />
                  </div>
                </div>
              </>
            )}

            <div className="flex justify-end">
              <button
                onClick={updatePopupNotice}
                disabled={popupLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {popupLoading ? '저장 중...' : '설정 저장'}
              </button>
            </div>
          </div>
        </div>

        {/* 메인트넌스 설정 */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">메인트넌스 설정</h2>
            <p className="text-sm text-gray-600">서비스 점검 모드를 관리합니다</p>
          </div>
          <div className="px-6 py-4 space-y-4">
            {/* 메인트넌스 온오프 스위치 */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">메인트넌스 모드</label>
                <p className="text-xs text-gray-500">활성화 시 스캐너 페이지가 점검 페이지로 표시됩니다</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={maintenanceSettings.is_enabled}
                  onChange={(e) => setMaintenanceSettings({
                    ...maintenanceSettings,
                    is_enabled: e.target.checked
                  })}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            {/* 종료 날짜 설정 */}
            {maintenanceSettings.is_enabled && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  종료 날짜 (선택사항)
                </label>
                <input
                  type="date"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={maintenanceSettings.end_date}
                  onChange={(e) => setMaintenanceSettings({
                    ...maintenanceSettings,
                    end_date: e.target.value
                  })}
                />
                <p className="text-xs text-gray-500 mt-1">
                  설정하지 않으면 수동으로 비활성화해야 합니다
                </p>
              </div>
            )}

            {/* 메시지 설정 */}
            {maintenanceSettings.is_enabled && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  점검 메시지
                </label>
                <textarea
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  value={maintenanceSettings.message}
                  onChange={(e) => setMaintenanceSettings({
                    ...maintenanceSettings,
                    message: e.target.value
                  })}
                  placeholder="서비스 점검 중입니다."
                />
              </div>
            )}

            {/* 저장 버튼 */}
            <div className="flex justify-end">
              <button
                onClick={updateMaintenanceSettings}
                disabled={maintenanceLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {maintenanceLoading ? '저장 중...' : '설정 저장'}
              </button>
            </div>
          </div>
        </div>

        {/* 스캐너 엔진 설정 */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">스캐너 엔진 설정</h2>
            <p className="text-sm text-gray-600">실행할 엔진을 선택합니다. 엔진은 내부적으로 적절한 스캐너를 선택하여 실행합니다.</p>
          </div>
          <div className="px-6 py-4 space-y-4">
            {/* 활성 엔진 선택 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                활성 엔진 ⭐
              </label>
              <select
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-base font-medium bg-gradient-to-br from-blue-50 to-indigo-50"
                value={scannerSettings.active_engine || 'v1'}
                onChange={(e) => setScannerSettings({
                  ...scannerSettings,
                  active_engine: e.target.value
                })}
              >
                <option value="v1">V1 엔진 - 레거시 검색기</option>
                <option value="v2">V2 엔진 - 단기 검색기</option>
                <option value="v3">V3 엔진 - 중기+단기 조합</option>
              </select>
              
              {/* 엔진별 상세 설명 */}
              {scannerSettings.active_engine === 'v1' && (
                <div className="mt-3 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                  <p className="text-sm font-semibold text-gray-800 mb-2">V1 엔진 특징</p>
                  <ul className="text-xs text-gray-600 space-y-1 list-disc list-inside">
                    <li>기존 레거시 검색기 사용</li>
                    <li>안정적인 성능과 검증된 로직</li>
                    <li>기본적인 기술적 지표 기반 스캔</li>
                  </ul>
                </div>
              )}
              
              {scannerSettings.active_engine === 'v2' && (
                <div className="mt-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm font-semibold text-blue-800 mb-2">V2 엔진 특징</p>
                  <ul className="text-xs text-blue-700 space-y-1 list-disc list-inside">
                    <li>단기 검색기 (5-10거래일 보유 목표)</li>
                    <li>개선된 로직: 신호 우선 원칙, 멀티데이 트렌드 분석</li>
                    <li>매매 가이드 제공: 목표 수익률, 손절, 보유기간</li>
                    <li>레짐 분석 기반 필터링</li>
                  </ul>
                </div>
              )}
              
              {scannerSettings.active_engine === 'v3' && (
                <div className="mt-3 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                  <p className="text-sm font-semibold text-purple-800 mb-2">V3 엔진 특징</p>
                  <p className="text-xs text-purple-700 mb-2">
                    V3는 <strong>중기(midterm)</strong>와 <strong>단기(v2-lite)</strong> 스캐너를 조합한 엔진입니다.
                  </p>
                  <ul className="text-xs text-purple-700 space-y-1 list-disc list-inside">
                    <li><strong>Midterm 스캐너:</strong> 항상 실행 (1-4주 보유 목표, 추세 관점)</li>
                    <li><strong>V2-Lite 스캐너:</strong> neutral/normal 레짐에서만 실행 (5-10거래일, 빠른 반응 관점)</li>
                    <li>두 스캐너 결과는 분리되어 표시됨 (병합하지 않음)</li>
                    <li>V1/V2와 완전히 독립된 실행 및 저장</li>
                  </ul>
                  <div className="mt-2 p-2 bg-purple-100 rounded text-xs text-purple-800">
                    💡 <strong>레짐 판정:</strong> neutral/normal 레짐일 때만 단기 스캐너가 실행됩니다.
                  </div>
                </div>
              )}
              
              <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-xs text-yellow-800">
                  ⚠️ <strong>중요:</strong> 엔진을 변경하면 다음 스캔부터 해당 엔진만 실행됩니다. 
                  다른 엔진은 실행되지 않으며, 각 엔진의 결과는 독립적으로 저장됩니다.
                </p>
              </div>
            </div>

            {/* 레짐 분석 버전 선택 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                레짐 분석 버전
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={scannerSettings.regime_version || 'v1'}
                onChange={(e) => setScannerSettings({
                  ...scannerSettings,
                  regime_version: e.target.value
                })}
              >
                <option value="v1">V1 (기본 장세 분석)</option>
                <option value="v3">V3 (Global Regime v3)</option>
                <option value="v4">V4 (Global Regime v4) - 권장</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                시장 상황 분석 방법을 선택합니다. V4는 한국/미국 시장 + 리스크 분석을 포함합니다.
                모든 엔진에서 공통으로 사용됩니다.
              </p>
            </div>

            {/* 현재 설정 요약 */}
            <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 border border-gray-200">
              <p className="text-sm font-semibold text-gray-700 mb-3">현재 설정 요약</p>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">활성 엔진:</span>
                  <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
                    {scannerSettings.active_engine === 'v3' 
                      ? 'V3 (중기+단기 조합)'
                      : scannerSettings.active_engine === 'v2'
                        ? 'V2 (단기 검색기)'
                        : 'V1 (레거시 검색기)'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">레짐 분석:</span>
                  <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                    {scannerSettings.regime_version || 'v1'}
                  </span>
                </div>
                <div className="flex justify-between items-center pt-2 border-t border-gray-200">
                  <span className="text-sm text-gray-600">적용 시점:</span>
                  <span className="text-sm font-medium text-blue-600">다음 스캔부터 적용</span>
                </div>
              </div>
            </div>

            {/* 저장 버튼 */}
            <div className="flex justify-end pt-2">
              <button
                onClick={updateScannerSettings}
                disabled={scannerLoading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-md hover:shadow-lg transition-all"
              >
                {scannerLoading ? '저장 중...' : '설정 저장'}
              </button>
            </div>
          </div>
        </div>

        {/* 바텀메뉴 설정 */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">바텀메뉴 설정</h2>
            <p className="text-sm text-gray-600">바텀메뉴의 노출 여부 및 링크 설정을 관리합니다</p>
          </div>
          <div className="px-6 py-4 space-y-6">
            {/* 바텀메뉴 노출 설정 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                바텀메뉴 노출
              </label>
              <div className="flex items-center space-x-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="bottomNavVisible"
                    checked={bottomNavVisible === true}
                    onChange={() => setBottomNavVisible(true)}
                    className="mr-2"
                  />
                  <span>표시</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="bottomNavVisible"
                    checked={bottomNavVisible === false}
                    onChange={() => setBottomNavVisible(false)}
                    className="mr-2"
                  />
                  <span>숨김</span>
                </label>
              </div>
              <p className="mt-2 text-sm text-gray-500">
                💡 <strong>설정 안내:</strong> "숨김"으로 설정하면 모든 화면에서 바텀메뉴가 표시되지 않습니다.
              </p>
            </div>

            {/* 바텀메뉴 링크 설정 */}
            <div className="border-t pt-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                추천종목 링크
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={bottomNavLink.link_type}
                onChange={(e) => setBottomNavLink({
                  ...bottomNavLink,
                  link_type: e.target.value
                })}
              >
                <option value="v1">V1 화면 (/customer-scanner)</option>
                <option value="v2">V2 화면 (/v2/scanner-v2)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                V1: 기존 스캐너 화면 | V2: 인피니티 스크롤 스캐너 화면
              </p>
              <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
                💡 <strong>설정 안내:</strong> 변경 사항은 즉시 적용됩니다. 사용자가 바텀메뉴의 "추천종목" 버튼을 클릭하면 선택한 화면으로 이동합니다.
              </div>
            </div>

            {/* 개별 메뉴 아이템 설정 */}
            <div className="border-t pt-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                개별 메뉴 아이템 표시
              </label>
              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={bottomNavMenuItems.korean_stocks}
                    onChange={(e) => setBottomNavMenuItems({
                      ...bottomNavMenuItems,
                      korean_stocks: e.target.checked
                    })}
                    className="mr-2"
                  />
                  <span>한국</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={bottomNavMenuItems.us_stocks}
                    onChange={(e) => setBottomNavMenuItems({
                      ...bottomNavMenuItems,
                      us_stocks: e.target.checked
                    })}
                    className="mr-2"
                  />
                  <span>미국</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={bottomNavMenuItems.stock_analysis}
                    onChange={(e) => setBottomNavMenuItems({
                      ...bottomNavMenuItems,
                      stock_analysis: e.target.checked
                    })}
                    className="mr-2"
                  />
                  <span>종목분석</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={bottomNavMenuItems.portfolio}
                    onChange={(e) => setBottomNavMenuItems({
                      ...bottomNavMenuItems,
                      portfolio: e.target.checked
                    })}
                    className="mr-2"
                  />
                  <span>나의투자종목</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={bottomNavMenuItems.more}
                    onChange={(e) => setBottomNavMenuItems({
                      ...bottomNavMenuItems,
                      more: e.target.checked
                    })}
                    className="mr-2"
                  />
                  <span>더보기</span>
                </label>
              </div>
              <p className="mt-2 text-sm text-gray-500">
                💡 <strong>설정 안내:</strong> 체크 해제된 메뉴는 바텀메뉴에서 표시되지 않습니다. 관리자 메뉴는 관리자 권한이 있는 사용자에게만 자동으로 표시됩니다.
              </p>
            </div>

            {/* 현재 설정 정보 */}
            <div className="bg-gray-50 rounded-md p-4">
              <div className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">현재 링크:</span>
                  <span className="font-medium">
                    {bottomNavLink.link_type === 'v1' ? 'V1 화면 (/customer-scanner)' : 'V2 화면 (/v2/scanner-v2)'}
                  </span>
                </div>
              </div>
            </div>

            {/* 저장 버튼 */}
            <div className="flex justify-end">
              <button
                onClick={async () => {
                  const results = await Promise.all([
                    updateBottomNavLink(),
                    updateBottomNavVisible(),
                    updateBottomNavMenuItems()
                  ]);
                  
                  // 모든 결과 확인
                  const allSuccess = results.every(r => r && r.success);
                  const errors = results.filter(r => r && !r.success).map(r => r.error);
                  
                  if (allSuccess) {
                    alert('바텀메뉴 설정이 모두 저장되었습니다.');
                  } else {
                    alert(`일부 설정 저장에 실패했습니다:\n${errors.join('\n')}`);
                  }
                }}
                disabled={bottomNavLinkLoading || bottomNavVisibleLoading || bottomNavMenuItemsLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {(bottomNavLinkLoading || bottomNavVisibleLoading || bottomNavMenuItemsLoading) ? '저장 중...' : '설정 저장'}
              </button>
            </div>
          </div>
        </div>

        {/* 사용자 목록 */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">사용자 관리</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">사용자</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">등급</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">가입일</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">관리자</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">작업</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">{user.name || '이름 없음'}</div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                        <div className="text-xs text-gray-400">{user.provider}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getTierColor(user.membership_tier)}`}>
                        {getTierName(user.membership_tier)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {user.subscription_status}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(user.created_at).toLocaleDateString('ko-KR')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {user.is_admin ? (
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                          관리자
                        </span>
                      ) : (
                        <span className="text-sm text-gray-500">일반</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => handleUserEdit(user)}
                        className="text-blue-600 hover:text-blue-900 mr-3"
                      >
                        수정
                      </button>
                      <button
                        onClick={() => handleUserDelete(user.id)}
                        className="text-red-600 hover:text-red-900"
                        disabled={user.id === user.id} // 자기 자신 삭제 방지
                      >
                        삭제
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 사용자 수정 모달 */}
        {showUserModal && editingUser && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
              <div className="mt-3">
                <h3 className="text-lg font-medium text-gray-900 mb-4">사용자 정보 수정</h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">이름</label>
                    <input
                      type="text"
                      value={editingUser.name || ''}
                      onChange={(e) => setEditingUser({...editingUser, name: e.target.value})}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">회원 등급</label>
                    <select
                      value={editingUser.membership_tier}
                      onChange={(e) => setEditingUser({...editingUser, membership_tier: e.target.value})}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="free">무료</option>
                      <option value="premium">프리미엄</option>
                      <option value="vip">VIP</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">구독 상태</label>
                    <select
                      value={editingUser.subscription_status}
                      onChange={(e) => setEditingUser({...editingUser, subscription_status: e.target.value})}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="active">활성</option>
                      <option value="expired">만료</option>
                      <option value="cancelled">취소</option>
                    </select>
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="is_admin"
                      checked={editingUser.is_admin}
                      onChange={(e) => setEditingUser({...editingUser, is_admin: e.target.checked})}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="is_admin" className="ml-2 block text-sm text-gray-900">
                      관리자 권한
                    </label>
                  </div>
                </div>
                
                <div className="flex justify-end space-x-3 mt-6">
                  <button
                    onClick={() => setShowUserModal(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                  >
                    취소
                  </button>
                  <button
                    onClick={handleUserUpdate}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md"
                  >
                    저장
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
