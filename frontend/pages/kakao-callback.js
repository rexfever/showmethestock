import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import getConfig from '../config';

export default function KakaoCallback() {
  const router = useRouter();
  const [status, setStatus] = useState('카카오 로그인 처리 중...');

  useEffect(() => {
    const handleKakaoCallback = async () => {
      const { code, error } = router.query;

      if (error) {
        if (error === 'access_denied') {
          setStatus('카카오 로그인이 취소되었습니다.');
        } else {
          setStatus('카카오 로그인에 실패했습니다.');
        }
        setTimeout(() => {
          router.push('/login');
        }, 2000);
        return;
      }

      if (!code) {
        setStatus('인증 코드를 받지 못했습니다.');
        setTimeout(() => {
          router.push('/login');
        }, 2000);
        return;
      }

      try {
        // 백엔드로 인증 코드 전송
        const config = getConfig();
        const base = config.backendUrl;

        const response = await fetch(`${base}/auth/kakao/callback`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code: code,
            redirect_uri: config.domain + '/kakao-callback'
          }),
        });

        const data = await response.json();

        if (response.ok) {
          // 토큰 저장
          localStorage.setItem('token', data.access_token);
          localStorage.setItem('user', JSON.stringify(data.user));
          
          setStatus('로그인 성공! 메인 페이지로 이동합니다.');
          setTimeout(() => {
            router.push('/customer-scanner');
          }, 2000);
        } else {
          setStatus('로그인 처리 중 오류가 발생했습니다.');
          setTimeout(() => {
            router.push('/login');
          }, 2000);
        }
      } catch (error) {
        console.error('카카오 콜백 처리 오류:', error);
        setStatus('로그인 처리 중 오류가 발생했습니다.');
        setTimeout(() => {
          router.push('/login');
        }, 2000);
      }
    };

    if (router.isReady) {
      handleKakaoCallback();
    }
  }, [router.isReady, router.query]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <Head>
        <title>카카오 로그인 처리 중 - Stock Insight</title>
      </Head>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <div className="text-center">
            <div className="text-2xl mb-4">🔮</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Stock Insight
            </h2>
            <p className="text-gray-600">{status}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
