import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import getConfig from '../config';
import MarketConditionDetailCard from '../components/MarketConditionDetailCard';

export default function AdminDashboard() {
  const router = useRouter();
  const { isAuthenticated, user, token, loading: authLoading, authChecked } = useAuth();
  
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
  const [scanDates, setScanDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [rescanLoading, setRescanLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  
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

  // 추세 변동 대응 상태
  const [trendAnalysis, setTrendAnalysis] = useState(null);
  const [trendLoading, setTrendLoading] = useState(false);
  const [trendApplyLoading, setTrendApplyLoading] = useState(false);
  
  // 장세 분석 상태
  const [marketCondition, setMarketCondition] = useState(null);
  const [marketLoading, setMarketLoading] = useState(false);
  
  // 스캐너 설정 상태
  const [scannerSettings, setScannerSettings] = useState({
    scanner_version: 'v1',
    regime_version: 'v1',
    scanner_v2_enabled: false
  });
  const [scannerLoading, setScannerLoading] = useState(false);
  
  // 바텀메뉴 링크 설정 상태
  const [bottomNavLink, setBottomNavLink] = useState({
    link_type: 'v1'  // 'v1' 또는 'v2'
  });
  const [bottomNavLinkLoading, setBottomNavLinkLoading] = useState(false);
  const [scannerLink, setScannerLink] = useState('/customer-scanner'); // 동적 스캐너 링크

  useEffect(() => {
    // 인증 체크가 완료되지 않았거나 로딩 중이면 대기
    if (!authChecked || authLoading) {
      return;
    }
    
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    
    // 사용자 정보가 로드되지 않았으면 대기
    if (!user) {
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
          const config = getConfig();
          const base = config.backendUrl;
          const response = await fetch(`${base}/bottom-nav-link`);
          if (response.ok) {
            const data = await response.json();
            const linkUrl = data.link_url || '/customer-scanner';
            router.push(linkUrl);
          } else {
            router.push('/customer-scanner');
          }
        } catch (error) {
          console.error('스캐너 링크 조회 실패:', error);
          router.push('/customer-scanner');
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
      fetchScanDates();
      fetchTrendAnalysis();
      fetchMarketCondition();
      fetchScannerSettings();
      fetchBottomNavLink();
    }
  }, [authChecked, authLoading, isAuthenticated, router, token]);

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
      }
    } catch (error) {
      console.error('바텀메뉴 링크 설정 조회 실패:', error);
      // 에러 시 기본값 사용
      setScannerLink('/customer-scanner');
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
        alert(data.message || '바텀메뉴 링크 설정이 저장되었습니다.');
        // 설정 다시 불러오기
        fetchBottomNavLink();
      } else {
        const data = await response.json();
        alert(`저장 실패: ${data.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('바텀메뉴 링크 설정 저장 실패:', error);
      alert('저장 중 오류가 발생했습니다.');
    } finally {
      setBottomNavLinkLoading(false);
    }
  };

  const fetchTrendAnalysis = async () => {
    setTrendLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/admin/trend-analysis`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.ok) {
          setTrendAnalysis(data.data);
        }
      } else if (response.status === 401) {
        alert('세션이 만료되었습니다. 다시 로그인해주세요.');
        router.push('/login');
      }
    } catch (error) {
      console.error('추세 분석 조회 실패:', error);
    } finally {
      setTrendLoading(false);
    }
  };
  
  const fetchMarketCondition = async () => {
    setMarketLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/latest-scan`);
      
      if (response.ok) {
        const data = await response.json();
        if (data.ok && data.data && data.data.market_condition) {
          setMarketCondition(data.data.market_condition);
        }
      }
    } catch (error) {
      console.error('장세 분석 조회 실패:', error);
    } finally {
      setMarketLoading(false);
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
            scanner_v2_enabled: data.settings.scanner_v2_enabled === 'true' || data.settings.scanner_v2_enabled === true
          });
        }
      } else if (response.status === 401) {
        alert('세션이 만료되었습니다. 다시 로그인해주세요.');
        router.push('/login');
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
          scanner_version: scannerSettings.scanner_version,
          scanner_v2_enabled: scannerSettings.scanner_v2_enabled,
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
        alert('세션이 만료되었습니다. 다시 로그인해주세요.');
        router.push('/login');
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

  const applyTrendParams = async () => {
    if (!trendAnalysis || !trendAnalysis.recommended_params) {
      alert('권장 파라미터가 없습니다.');
      return;
    }

    if (!confirm('권장 파라미터를 적용하시겠습니까? .env 파일이 백업되고 업데이트됩니다.')) {
      return;
    }

    setTrendApplyLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/admin/trend-apply`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(trendAnalysis.recommended_params)
      });
      
      const data = await response.json();
      
      if (data.ok) {
        const changesText = Array.isArray(data.changes) && data.changes.length > 0
          ? data.changes.join('\n')
          : '변경 사항 없음';
        alert(`파라미터 적용 완료!\n변경 사항:\n${changesText}\n\n서버 재시작이 필요할 수 있습니다.`);
        // 분석 데이터 다시 불러오기
        fetchTrendAnalysis();
      } else {
        alert(`파라미터 적용 실패: ${data.error || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('파라미터 적용 실패:', error);
      alert('파라미터 적용 중 오류가 발생했습니다.');
    } finally {
      setTrendApplyLoading(false);
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
        alert('세션이 만료되었습니다. 다시 로그인해주세요.');
        router.push('/login');
        return;
      }

      if (usersResponse.ok) {
        const usersData = await usersResponse.json();
        setUsers(usersData.users);
      }

      if (maintenanceResponse.ok) {
        const maintenanceData = await maintenanceResponse.json();
        setMaintenanceSettings({
          is_enabled: maintenanceData.is_enabled,
          end_date: convertToYYYYMMDD_Display(maintenanceData.end_date) || '',
          message: maintenanceData.message || '서비스 점검 중입니다.'
        });
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
      }
    } catch (error) {
      console.error('관리자 데이터 로딩 오류:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchScanDates = async () => {
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/available-scan-dates`);
      const data = await response.json();
      
      if (data.ok) {
        setScanDates(data.dates || []);
      } else {
      }
    } catch (error) {
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
        alert('세션이 만료되었습니다. 다시 로그인해주세요.');
        router.push('/login');
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
        alert('세션이 만료되었습니다. 다시 로그인해주세요.');
        router.push('/login');
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

  const handleRescan = async () => {
    if (!selectedDate) {
      alert('날짜를 선택해주세요.');
      return;
    }

    if (!confirm(`${selectedDate} 날짜로 재스캔을 실행하시겠습니까?`)) {
      return;
    }

    setRescanLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/scan?date=${convertToYYYYMMDD(selectedDate)}&save_snapshot=true`);
      const data = await response.json();
      
      if (data.ok) {
        alert(`${selectedDate} 재스캔이 완료되었습니다. 추천 종목: ${data.items.length}개`);
        fetchScanDates(); // 날짜 목록 새로고침
      } else {
        alert(`재스캔 실패: ${data.error || '알 수 없는 오류'}`);
      }
    } catch (error) {
      alert('재스캔 중 오류가 발생했습니다.');
    } finally {
      setRescanLoading(false);
    }
  };

  const handleDeleteScan = async () => {
    if (!selectedDate) {
      alert('날짜를 선택해주세요.');
      return;
    }

    if (!confirm(`${selectedDate} 날짜의 스캔 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
      return;
    }

    setDeleteLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      
      const response = await fetch(`${base}/scan/${convertToYYYYMMDD(selectedDate)}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      
      if (data.ok) {
        alert(`${selectedDate} 스캔 데이터가 삭제되었습니다. (삭제된 레코드: ${data.deleted_records}개)`);
        fetchScanDates(); // 날짜 목록 새로고침
        setSelectedDate(''); // 선택 초기화
      } else {
        alert(`삭제 실패: ${data.error || '알 수 없는 오류'}`);
      }
    } catch (error) {
      alert('삭제 중 오류가 발생했습니다.');
    } finally {
      setDeleteLoading(false);
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
            onClick={() => router.push(scannerLink)}
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

        {/* 스캔 데이터 관리 */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">스캔 데이터 관리</h2>
            <p className="text-sm text-gray-600">날짜별 스캔 데이터 삭제 및 재스캔</p>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* 날짜 선택 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  스캔 날짜 선택
                </label>
                <select
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">날짜를 선택하세요</option>
                  {scanDates.map((date) => (
                    <option key={date} value={date}>
                      {date}
                    </option>
                  ))}
                </select>
              </div>

              {/* 액션 버튼들 */}
              <div className="flex flex-col space-y-3">
                <button
                  onClick={handleRescan}
                  disabled={!selectedDate || rescanLoading}
                  className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {rescanLoading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      재스캔 중...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      재스캔 실행
                    </>
                  )}
                </button>

                <button
                  onClick={handleDeleteScan}
                  disabled={!selectedDate || deleteLoading}
                  className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {deleteLoading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      삭제 중...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      스캔 데이터 삭제
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* 스캔 날짜 목록 */}
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-700 mb-3">사용 가능한 스캔 날짜 ({scanDates.length}개)</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
                {scanDates.map((date) => (
                  <button
                    key={date}
                    onClick={() => setSelectedDate(date)}
                    className={`px-3 py-2 text-sm rounded-md border ${
                      selectedDate === date
                        ? 'bg-blue-500 text-white border-blue-500'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    {date}
                  </button>
                ))}
              </div>
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

        {/* 장세 분석 */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-medium text-gray-900">📊 오늘의 장세 분석</h2>
                <p className="text-sm text-gray-600">시장 상황 및 스캔 파라미터</p>
              </div>
              <button
                onClick={fetchMarketCondition}
                disabled={marketLoading}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
              >
                {marketLoading ? '조회 중...' : '🔄 새로고침'}
              </button>
            </div>
          </div>
          <div className="px-6 py-4">
            {marketLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-sm text-gray-600">조회 중...</p>
              </div>
            ) : marketCondition ? (
              <MarketConditionDetailCard marketCondition={marketCondition} />
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>장세 분석 데이터가 없습니다.</p>
                <p className="text-sm mt-2">스캔이 실행되면 자동으로 표시됩니다.</p>
              </div>
            )}
          </div>
        </div>

        {/* 추세 변동 대응 */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-medium text-gray-900">📊 추세 변동 대응</h2>
                <p className="text-sm text-gray-600">성과 분석 및 파라미터 자동 조정</p>
              </div>
              <button
                onClick={fetchTrendAnalysis}
                disabled={trendLoading}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
              >
                {trendLoading ? '분석 중...' : '🔄 새로고침'}
              </button>
            </div>
          </div>
          <div className="px-6 py-4">
            {trendLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-sm text-gray-600">분석 중...</p>
              </div>
            ) : trendAnalysis ? (
              <div className="space-y-6">
                {/* 성과 지표 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* 최근 4주간 성과 */}
                  <div className="border rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">최근 4주간 성과</h3>
                    {trendAnalysis.recent_4weeks.avg_return !== null ? (
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">평균 수익률:</span>
                          <span className={`font-semibold ${trendAnalysis.recent_4weeks.avg_return >= 30 ? 'text-green-600' : trendAnalysis.recent_4weeks.avg_return >= 20 ? 'text-blue-600' : trendAnalysis.recent_4weeks.avg_return >= 10 ? 'text-yellow-600' : 'text-red-600'}`}>
                            {trendAnalysis.recent_4weeks.avg_return?.toFixed(2)}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">승률:</span>
                          <span className={`font-semibold ${trendAnalysis.recent_4weeks.win_rate >= 90 ? 'text-green-600' : trendAnalysis.recent_4weeks.win_rate >= 80 ? 'text-blue-600' : 'text-red-600'}`}>
                            {trendAnalysis.recent_4weeks.win_rate?.toFixed(2)}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">추천 종목:</span>
                          <span className="font-medium">{trendAnalysis.recent_4weeks.total_stocks}개</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500">데이터 없음</p>
                    )}
                  </div>

                  {/* 현재 월 성과 */}
                  <div className="border rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">현재 월 성과</h3>
                    {trendAnalysis.current_month.avg_return !== null ? (
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">평균 수익률:</span>
                          <span className={`font-semibold ${trendAnalysis.current_month.avg_return >= 30 ? 'text-green-600' : trendAnalysis.current_month.avg_return >= 20 ? 'text-blue-600' : trendAnalysis.current_month.avg_return >= 10 ? 'text-yellow-600' : 'text-red-600'}`}>
                            {trendAnalysis.current_month.avg_return?.toFixed(2)}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">승률:</span>
                          <span className={`font-semibold ${trendAnalysis.current_month.win_rate >= 90 ? 'text-green-600' : trendAnalysis.current_month.win_rate >= 80 ? 'text-blue-600' : 'text-red-600'}`}>
                            {trendAnalysis.current_month.win_rate?.toFixed(2)}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">추천 종목:</span>
                          <span className="font-medium">{trendAnalysis.current_month.total_stocks}개</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500">데이터 없음</p>
                    )}
                  </div>
                </div>

                {/* 평가 결과 */}
                <div className={`border-l-4 rounded p-4 ${
                  trendAnalysis.evaluation === 'excellent' ? 'bg-green-50 border-green-500' :
                  trendAnalysis.evaluation === 'good' ? 'bg-blue-50 border-blue-500' :
                  trendAnalysis.evaluation === 'fair' ? 'bg-yellow-50 border-yellow-500' :
                  'bg-red-50 border-red-500'
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        평가: {
                          trendAnalysis.evaluation === 'excellent' ? '⭐ 매우 우수' :
                          trendAnalysis.evaluation === 'good' ? '✅ 양호' :
                          trendAnalysis.evaluation === 'fair' ? '⚠️ 보통' :
                          '❌ 저조'
                        }
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {trendAnalysis.evaluation === 'poor' && '즉시 파라미터 조정을 권장합니다.'}
                        {trendAnalysis.evaluation === 'fair' && '파라미터 조정을 검토하세요.'}
                        {trendAnalysis.evaluation === 'good' && '현재 성과가 양호합니다.'}
                        {trendAnalysis.evaluation === 'excellent' && '현재 성과가 매우 우수합니다!'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* 파라미터 비교 */}
                <div className="border rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4">권장 파라미터 조정</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-2 px-3 font-medium text-gray-700">파라미터</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-700">현재 값</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-700">권장 값</th>
                          <th className="text-center py-2 px-3 font-medium text-gray-700">변경</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.keys(trendAnalysis.current_params).map((key) => {
                          const current = trendAnalysis.current_params[key];
                          const recommended = trendAnalysis.recommended_params[key];
                          const changed = current !== recommended;
                          return (
                            <tr key={key} className="border-b">
                              <td className="py-2 px-3 text-gray-700">{key}</td>
                              <td className="py-2 px-3 text-right font-medium">{current}</td>
                              <td className={`py-2 px-3 text-right font-medium ${changed ? 'text-blue-600' : ''}`}>
                                {recommended}
                              </td>
                              <td className="py-2 px-3 text-center">
                                {changed ? (
                                  <span className="text-orange-600 font-semibold">변경</span>
                                ) : (
                                  <span className="text-gray-400">-</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Fallback 정보 */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Fallback 설정</h3>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">활성화:</span>
                      <span className={`ml-2 font-medium ${trendAnalysis.fallback_enabled ? 'text-green-600' : 'text-gray-400'}`}>
                        {trendAnalysis.fallback_enabled ? '✅ 활성화' : '❌ 비활성화'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">최소 목표:</span>
                      <span className="ml-2 font-medium">{trendAnalysis.fallback_target_min}개</span>
                    </div>
                    <div>
                      <span className="text-gray-600">최대 목표:</span>
                      <span className="ml-2 font-medium">{trendAnalysis.fallback_target_max}개</span>
                    </div>
                  </div>
                </div>

                {/* 적용 버튼 */}
                <div className="flex justify-end">
                  <button
                    onClick={applyTrendParams}
                    disabled={trendApplyLoading || !trendAnalysis.recommended_params}
                    className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                  >
                    {trendApplyLoading ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        적용 중...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        권장 파라미터 적용
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-sm text-gray-500">분석 데이터를 불러올 수 없습니다.</p>
                <button
                  onClick={fetchTrendAnalysis}
                  className="mt-4 px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  다시 시도
                </button>
              </div>
            )}
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

        {/* 스캐너 설정 */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">스캐너 설정</h2>
            <p className="text-sm text-gray-600">스캐너 버전을 선택하고 관리합니다</p>
          </div>
          <div className="px-6 py-4 space-y-4">
            {/* 스캐너 버전 선택 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                스캐너 버전
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={scannerSettings.scanner_version}
                onChange={(e) => setScannerSettings({
                  ...scannerSettings,
                  scanner_version: e.target.value
                })}
              >
                <option value="v1">V1 (기본 스캐너)</option>
                <option value="v2">V2 (개선된 스캐너)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                V2는 최근 개선된 로직(신호 우선 원칙, 멀티데이 트렌드 분석 등)을 포함합니다
              </p>
              <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
                💡 <strong>버전 전환 안내:</strong> 버전을 변경하면 다음 스캔부터 적용됩니다. 
                V2는 매매 가이드(목표 수익률, 손절, 보유기간)를 제공합니다.
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
                <option value="v4">V4 (Global Regime v4)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                시장 상황 분석 방법을 선택합니다. V4는 한국/미국 시장 + 리스크 분석을 포함합니다
              </p>
            </div>

            {/* V2 활성화 스위치 */}
            {scannerSettings.scanner_version === 'v2' && (
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-gray-700">V2 활성화</label>
                  <p className="text-xs text-gray-500">V2를 사용하려면 활성화해야 합니다</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={scannerSettings.scanner_v2_enabled}
                    onChange={(e) => setScannerSettings({
                      ...scannerSettings,
                      scanner_v2_enabled: e.target.checked
                    })}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
            )}

            {/* 현재 설정 정보 */}
            <div className="bg-gray-50 rounded-md p-4">
              <div className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">스캐너 버전:</span>
                  <span className="font-medium">{scannerSettings.scanner_version === 'v2' && scannerSettings.scanner_v2_enabled ? 'V2 (활성화됨)' : 'V1'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">레짐 분석 버전:</span>
                  <span className="font-medium">{scannerSettings.regime_version || 'v1'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">적용 시점:</span>
                  <span className="font-medium text-blue-600">다음 스캔부터 적용</span>
                </div>
              </div>
            </div>

            {/* 저장 버튼 */}
            <div className="flex justify-end">
              <button
                onClick={updateScannerSettings}
                disabled={scannerLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {scannerLoading ? '저장 중...' : '설정 저장'}
              </button>
            </div>
          </div>
        </div>

        {/* 바텀메뉴 링크 설정 */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">바텀메뉴 링크 설정</h2>
            <p className="text-sm text-gray-600">바텀메뉴의 "추천종목" 버튼이 연결될 화면을 설정합니다</p>
          </div>
          <div className="px-6 py-4 space-y-4">
            {/* 링크 타입 선택 */}
            <div>
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
                onClick={updateBottomNavLink}
                disabled={bottomNavLinkLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {bottomNavLinkLoading ? '저장 중...' : '설정 저장'}
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
