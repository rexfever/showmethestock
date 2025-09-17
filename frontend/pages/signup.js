import { useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';

export default function Signup() {
  const [agreed, setAgreed] = useState(false);
  const router = useRouter();

  const handleSocialLogin = (provider) => {
    // 소셜 로그인 처리
    window.location.href = `/api/auth/${provider}`;
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <Head>
        <title>스톡인사이트 - 가입하기</title>
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
          스톡인사이트
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          AI가 찾아주는 숨겨진 주식 기회
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          
          {/* 서비스 소개 */}
          <div className="mb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-3">
              스톡인사이트란?
            </h3>
            <ul className="text-sm text-gray-600 space-y-2">
              <li>• AI가 실시간으로 주식 시장을 분석</li>
              <li>• 숨겨진 투자 기회를 찾아드립니다</li>
              <li>• 간단한 설정으로 맞춤형 알림</li>
              <li>• 카카오톡으로 실시간 알림</li>
            </ul>
          </div>

          {/* 약관 동의 */}
          <div className="mb-6">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-600">
                <Link href="/terms">
                  <a className="text-blue-600 hover:text-blue-500">
                    이용약관
                  </a>
                </Link> 및{' '}
                <Link href="/privacy">
                  <a className="text-blue-600 hover:text-blue-500">
                    개인정보처리방침
                  </a>
                </Link>에 동의합니다
              </span>
            </label>
          </div>

          {/* 소셜 로그인 버튼들 */}
          <div className="space-y-3">
            <button
              onClick={() => handleSocialLogin('kakao')}
              disabled={!agreed}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-yellow-400 hover:bg-yellow-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="mr-2">💬</span>
              카카오로 시작하기
            </button>

            <button
              onClick={() => handleSocialLogin('naver')}
              disabled={!agreed}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-500 hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="mr-2">N</span>
              네이버로 시작하기
            </button>

            <button
              onClick={() => handleSocialLogin('toss')}
              disabled={!agreed}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-500 hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="mr-2">💳</span>
              토스로 시작하기
            </button>
          </div>

          {/* 로그인 링크 */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              이미 계정이 있으신가요?{' '}
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
