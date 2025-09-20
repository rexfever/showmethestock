import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';

export default function Subscription() {
  const router = useRouter();
  const { isAuthenticated, user, token } = useAuth();
  const [plans, setPlans] = useState([]);
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    
    fetchSubscriptionData();
  }, [isAuthenticated, router]);

  const fetchSubscriptionData = async () => {
    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';

      // 구독 플랜과 상태를 병렬로 조회
      const [plansResponse, statusResponse] = await Promise.all([
        fetch(`${base}/subscription/plans`),
        fetch(`${base}/subscription/status`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      ]);

      if (plansResponse.ok) {
        const plansData = await plansResponse.json();
        setPlans(plansData.plans);
      }

      if (statusResponse.ok) {
        const statusData = await statusResponse.json();
        setSubscription(statusData.subscription);
      }
    } catch (error) {
      console.error('구독 정보 조회 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (plan) => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }

    setIsProcessing(true);
    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';

      const response = await fetch(`${base}/payment/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          plan_id: plan.id,
          payment_method: 'kakaopay',
          return_url: `${window.location.origin}/payment/success`,
          cancel_url: `${window.location.origin}/subscription`
        })
      });

      if (response.ok) {
        const paymentData = await response.json();
        // 카카오페이 결제 페이지로 리다이렉트
        window.location.href = paymentData.payment_url;
      } else {
        const errorData = await response.json();
        alert(`결제 생성 실패: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('결제 생성 오류:', error);
      alert('결제 생성 중 오류가 발생했습니다.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!confirm('정말 구독을 취소하시겠습니까?')) {
      return;
    }

    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';

      const response = await fetch(`${base}/subscription/cancel`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        alert('구독이 취소되었습니다.');
        fetchSubscriptionData(); // 상태 새로고침
      } else {
        const errorData = await response.json();
        alert(`구독 취소 실패: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('구독 취소 오류:', error);
      alert('구독 취소 중 오류가 발생했습니다.');
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">구독 정보를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>구독 관리 - Stock Insight</title>
      </Head>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 헤더 */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">구독 관리</h1>
          <p className="mt-2 text-gray-600">원하는 플랜을 선택하여 더 많은 기능을 이용하세요</p>
        </div>

        {/* 현재 구독 상태 */}
        {subscription && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">현재 구독 상태</h2>
            <div className="flex items-center justify-between">
              <div>
                <span className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${getTierColor(subscription.tier)}`}>
                  {getTierName(subscription.tier)}
                </span>
                {subscription.is_active && (
                  <p className="mt-2 text-sm text-gray-600">
                    {subscription.days_remaining}일 남음
                  </p>
                )}
              </div>
              {subscription.is_active && subscription.tier !== 'free' && (
                <button
                  onClick={handleCancelSubscription}
                  className="px-4 py-2 text-sm text-red-600 hover:text-red-700 border border-red-300 rounded-md hover:bg-red-50"
                >
                  구독 취소
                </button>
              )}
            </div>
          </div>
        )}

        {/* 구독 플랜 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`bg-white rounded-lg shadow-md p-6 ${
                plan.tier === 'vip' ? 'ring-2 ring-purple-500' : ''
              }`}
            >
              {plan.tier === 'vip' && (
                <div className="text-center mb-4">
                  <span className="inline-flex px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                    인기
                  </span>
                </div>
              )}
              
              <div className="text-center">
                <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                <div className="mt-4">
                  <span className="text-3xl font-bold text-gray-900">
                    {formatPrice(plan.price)}원
                  </span>
                  <span className="text-gray-600">/{plan.duration_days === 30 ? '월' : '년'}</span>
                </div>
                
                <ul className="mt-6 space-y-3">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-center text-sm text-gray-600">
                      <svg className="flex-shrink-0 w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>
                
                <button
                  onClick={() => handleSubscribe(plan)}
                  disabled={isProcessing || (subscription && subscription.is_active && subscription.tier === plan.tier)}
                  className={`mt-6 w-full py-2 px-4 rounded-md text-sm font-medium ${
                    plan.tier === 'vip'
                      ? 'bg-purple-600 hover:bg-purple-700 text-white'
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {isProcessing ? '처리 중...' : 
                   subscription && subscription.is_active && subscription.tier === plan.tier ? '현재 플랜' : 
                   '구독하기'}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* 무료 플랜 정보 */}
        <div className="mt-8 bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">무료 플랜</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">3회</div>
              <div className="text-sm text-gray-600">일일 스캔</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">5개</div>
              <div className="text-sm text-gray-600">포트폴리오</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">기본</div>
              <div className="text-sm text-gray-600">분석 도구</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
