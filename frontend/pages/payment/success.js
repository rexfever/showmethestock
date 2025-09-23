import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import Head from 'next/head';
import getConfig from '../../config';

export default function PaymentSuccess() {
  const router = useRouter();
  const { isAuthenticated, token } = useAuth();
  const [status, setStatus] = useState('결제 승인 중...');
  const [subscription, setSubscription] = useState(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }

    const handlePaymentSuccess = async () => {
      const { payment_id, pg_token, plan_id } = router.query;

      if (!payment_id || !pg_token || !plan_id) {
        setStatus('결제 정보가 올바르지 않습니다.');
        setTimeout(() => {
          router.push('/subscription');
        }, 3000);
        return;
      }

      try {
        const config = getConfig();
        const base = config.backendUrl;

        const response = await fetch(`${base}/payment/approve`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            payment_id,
            pg_token,
            plan_id
          })
        });

        if (response.ok) {
          const data = await response.json();
          setStatus('결제가 완료되었습니다!');
          setSubscription(data.subscription);
          
          setTimeout(() => {
            router.push('/subscription');
          }, 3000);
        } else {
          const errorData = await response.json();
          setStatus(`결제 승인 실패: ${errorData.detail}`);
          setTimeout(() => {
            router.push('/subscription');
          }, 3000);
        }
      } catch (error) {
        console.error('결제 승인 오류:', error);
        setStatus('결제 승인 중 오류가 발생했습니다.');
        setTimeout(() => {
          router.push('/subscription');
        }, 3000);
      }
    };

    if (router.isReady) {
      handlePaymentSuccess();
    }
  }, [router, isAuthenticated, token]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <Head>
        <title>결제 완료 - Stock Insight</title>
      </Head>
      
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
              <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
              {status}
            </h2>
            
            {subscription && (
              <div className="mt-6 p-4 bg-green-50 rounded-md">
                <h3 className="text-lg font-medium text-green-800">구독 정보</h3>
                <p className="mt-2 text-sm text-green-700">
                  플랜: {subscription.plan_id}
                </p>
                <p className="text-sm text-green-700">
                  만료일: {new Date(subscription.expires_at).toLocaleDateString('ko-KR')}
                </p>
              </div>
            )}
            
            <p className="mt-4 text-center text-sm text-gray-600">
              잠시 후 구독 관리 페이지로 이동합니다...
            </p>
            
            <div className="mt-6">
              <button
                onClick={() => router.push('/subscription')}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                구독 관리로 이동
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
