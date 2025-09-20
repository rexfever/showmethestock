import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';

export default function EmailVerify() {
  const [verificationCode, setVerificationCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');
  const [resendLoading, setResendLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (router.query.email) {
      setEmail(router.query.email);
    }
  }, [router.query.email]);

  const handleVerify = async (e) => {
    e.preventDefault();
    
    if (!verificationCode || verificationCode.length !== 6) {
      setMessage('6자리 인증 코드를 입력해주세요.');
      return;
    }

    setLoading(true);
    setMessage('');

    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';

      const response = await fetch(`${base}/auth/email/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          verification_code: verificationCode
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage('이메일 인증이 완료되었습니다! 로그인 페이지로 이동합니다.');
        setTimeout(() => {
          router.push('/login');
        }, 2000);
      } else {
        setMessage(data.detail || '인증에 실패했습니다.');
      }
    } catch (error) {
      setMessage('인증 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResendLoading(true);
    setMessage('');

    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';

      const response = await fetch(`${base}/auth/email/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage('인증 이메일이 재발송되었습니다.');
      } else {
        setMessage(data.detail || '이메일 재발송에 실패했습니다.');
      }
    } catch (error) {
      setMessage('이메일 재발송 중 오류가 발생했습니다.');
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <Head>
        <title>스톡인사이트 - 이메일 인증</title>
      </Head>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* 로고 */}
        <div className="flex justify-center">
          <div className="relative flex items-center justify-center">
            <span className="text-4xl">🔮</span>
            <span className="absolute text-xl top-0 left-2 text-green-500">📈</span>
          </div>
        </div>
        
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          이메일 인증
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          {email}로 발송된 인증 코드를 입력해주세요
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          
          {/* 안내 메시지 */}
          <div className="mb-6">
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <span className="text-blue-400">📧</span>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">
                    이메일을 확인해주세요
                  </h3>
                  <div className="mt-2 text-sm text-blue-700">
                    <p>
                      {email}로 인증 코드가 발송되었습니다.<br/>
                      이메일이 보이지 않는다면 스팸함을 확인해주세요.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 메시지 표시 */}
          {message && (
            <div className={`mb-4 p-3 rounded-md text-sm ${
              message.includes('완료') ? 'bg-green-100 text-green-700' : 
              message.includes('재발송') ? 'bg-blue-100 text-blue-700' : 
              'bg-red-100 text-red-700'
            }`}>
              {message}
            </div>
          )}

          {/* 인증 코드 입력 폼 */}
          <form onSubmit={handleVerify} className="space-y-6">
            <div>
              <label htmlFor="verificationCode" className="block text-sm font-medium text-gray-700">
                인증 코드
              </label>
              <input
                id="verificationCode"
                name="verificationCode"
                type="text"
                required
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-center text-lg tracking-widest"
                placeholder="123456"
                maxLength="6"
              />
              <p className="mt-1 text-xs text-gray-500">
                6자리 숫자를 입력해주세요
              </p>
            </div>

            <button
              type="submit"
              disabled={loading || verificationCode.length !== 6}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '인증 중...' : '인증하기'}
            </button>
          </form>

          {/* 재발송 버튼 */}
          <div className="mt-6 text-center">
            <button
              onClick={handleResend}
              disabled={resendLoading}
              className="text-sm text-blue-600 hover:text-blue-500 disabled:opacity-50"
            >
              {resendLoading ? '재발송 중...' : '인증 코드 재발송'}
            </button>
          </div>

          {/* 로그인 링크 */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              이미 인증을 완료하셨나요?{' '}
              <button
                onClick={() => router.push('/login')}
                className="font-medium text-blue-600 hover:text-blue-500"
              >
                로그인하기
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
