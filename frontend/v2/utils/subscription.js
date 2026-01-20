/**
 * 구독 관련 유틸리티 함수들
 */
import getConfig from '../config';

// 구독 상태 확인
export const checkSubscriptionStatus = async (token) => {
  try {
    const config = getConfig();
    const base = config.backendUrl;

    const response = await fetch(`${base}/subscription/status`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      return data.subscription;
    }
    return null;
  } catch (error) {
    console.error('구독 상태 확인 오류:', error);
    return null;
  }
};

// 스캔 가능 여부 확인
export const canPerformScan = (subscription, dailyScanCount = 0) => {
  if (!subscription) {
    // 구독 정보가 없으면 무료 플랜으로 간주
    return dailyScanCount < 3;
  }

  if (subscription.tier === 'free') {
    return dailyScanCount < 3;
  }

  // 프리미엄 이상은 무제한
  return true;
};

// 포트폴리오 추가 가능 여부 확인
export const canAddToPortfolio = (subscription, currentPortfolioCount = 0) => {
  if (!subscription) {
    // 구독 정보가 없으면 무료 플랜으로 간주
    return currentPortfolioCount < 5;
  }

  if (subscription.tier === 'free') {
    return currentPortfolioCount < 5;
  }

  // 프리미엄 이상은 무제한
  return true;
};

// 알림 기능 사용 가능 여부 확인
export const canUseNotifications = (subscription) => {
  if (!subscription) {
    return false;
  }

  return subscription.tier !== 'free';
};

// 고급 분석 도구 사용 가능 여부 확인
export const canUseAdvancedAnalysis = (subscription) => {
  if (!subscription) {
    return false;
  }

  return subscription.tier !== 'free';
};

// 구독 등급별 색상 반환
export const getTierColor = (tier) => {
  switch (tier) {
    case 'free': return 'bg-gray-100 text-gray-800';
    case 'premium': return 'bg-blue-100 text-blue-800';
    case 'vip': return 'bg-purple-100 text-purple-800';
    default: return 'bg-gray-100 text-gray-800';
  }
};

// 구독 등급명 반환
export const getTierName = (tier) => {
  switch (tier) {
    case 'free': return '무료';
    case 'premium': return '프리미엄';
    case 'vip': return 'VIP';
    default: return '무료';
  }
};

// 구독 만료일까지 남은 일수 계산
export const getDaysRemaining = (expiresAt) => {
  if (!expiresAt) return 0;
  
  const now = new Date();
  const expiry = new Date(expiresAt);
  const diffTime = expiry - now;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  return Math.max(0, diffDays);
};

// 구독 상태 메시지 생성
export const getSubscriptionMessage = (subscription, dailyScanCount = 0, portfolioCount = 0) => {
  if (!subscription) {
    return {
      type: 'info',
      message: `무료 플랜: 스캔 ${dailyScanCount}/3회, 포트폴리오 ${portfolioCount}/5개 사용 중`,
      canUpgrade: true
    };
  }

  if (subscription.tier === 'free') {
    const remainingScans = Math.max(0, 3 - dailyScanCount);
    const remainingPortfolio = Math.max(0, 5 - portfolioCount);
    
    return {
      type: 'info',
      message: `무료 플랜: 스캔 ${remainingScans}회, 포트폴리오 ${remainingPortfolio}개 남음`,
      canUpgrade: true
    };
  }

  if (subscription.is_active) {
    const daysRemaining = getDaysRemaining(subscription.expires_at);
    return {
      type: 'success',
      message: `${getTierName(subscription.tier)} 플랜: ${daysRemaining}일 남음`,
      canUpgrade: subscription.tier !== 'vip'
    };
  }

  return {
    type: 'warning',
    message: '구독이 만료되었습니다. 무료 플랜으로 전환됩니다.',
    canUpgrade: true
  };
};
