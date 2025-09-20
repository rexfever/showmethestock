import { useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';
import { loginWithKakao, isKakaoSDKReady } from '../utils/kakaoAuth';

export default function Signup() {
  const [agreed, setAgreed] = useState(false);
  const [signupMethod, setSignupMethod] = useState('social'); // 'social' or 'email'
  const [emailForm, setEmailForm] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    name: '',
    birthYear: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const router = useRouter();

  const handleSocialLogin = async (provider) => {
    if (!agreed) {
      setMessage('약관에 동의해주세요.');
      return;
    }

    if (provider === 'kakao') {
      setLoading(true);
      setMessage('');

      try {
        if (!isKakaoSDKReady()) {
          setMessage('카카오 SDK가 아직 로드되지 않았습니다. 잠시 후 다시 시도해주세요.');
          setLoading(false);
          return;
        }

        const kakaoUserInfo = await loginWithKakao();
        
        // 백엔드로 소셜 로그인 요청
        const base = process.env.NODE_ENV === 'development' 
          ? 'http://localhost:8010' 
          : 'https://sohntech.ai.kr/backend';

        const response = await fetch(`${base}/auth/social-login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            provider: kakaoUserInfo.provider,
            access_token: kakaoUserInfo.access_token,
            user_info: kakaoUserInfo.user_info
          }),
        });

        const data = await response.json();

        if (response.ok) {
          // 토큰 저장
          localStorage.setItem('token', data.access_token);
          localStorage.setItem('user', JSON.stringify(data.user));
          
          // 메인 페이지로 이동
          router.push('/customer-scanner');
        } else {
          setMessage(data.detail || '로그인에 실패했습니다.');
        }
      } catch (error) {
        console.error('카카오 로그인 에러:', error);
        setMessage(error.message || '로그인 중 오류가 발생했습니다.');
      } finally {
        setLoading(false);
      }
    } else {
      setMessage(`${provider} 로그인은 아직 구현되지 않았습니다.`);
    }
  };

  const handleEmailSignup = async (e) => {
    e.preventDefault();
    
    if (!agreed) {
      setMessage('약관에 동의해주세요.');
      return;
    }

    if (emailForm.password !== emailForm.confirmPassword) {
      setMessage('비밀번호가 일치하지 않습니다.');
      return;
    }

    if (emailForm.password.length < 6) {
      setMessage('비밀번호는 6자 이상이어야 합니다.');
      return;
    }

    setLoading(true);
    setMessage('');

    try {
      const base = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:8010' 
        : 'https://sohntech.ai.kr/backend';

      const response = await fetch(`${base}/auth/email/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: emailForm.email,
          password: emailForm.password,
          name: emailForm.name,
          birth_year: emailForm.birthYear ? parseInt(emailForm.birthYear) : null
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage('회원가입이 완료되었습니다. 이메일을 확인하여 인증을 완료해주세요.');
        // 이메일 인증 페이지로 이동
        router.push(`/email-verify?email=${encodeURIComponent(emailForm.email)}`);
      } else {
        setMessage(data.detail || '회원가입에 실패했습니다.');
      }
    } catch (error) {
      setMessage('회원가입 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setEmailForm(prev => ({
      ...prev,
      [name]: value
    }));
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

          {/* 가입 방법 선택 */}
          <div className="mb-6">
            <div className="flex space-x-4">
              <button
                onClick={() => setSignupMethod('social')}
                className={`flex-1 py-2 px-4 rounded-md text-sm font-medium ${
                  signupMethod === 'social'
                    ? 'bg-blue-100 text-blue-700 border-2 border-blue-300'
                    : 'bg-gray-100 text-gray-700 border-2 border-gray-300'
                }`}
              >
                소셜 가입
              </button>
              <button
                onClick={() => setSignupMethod('email')}
                className={`flex-1 py-2 px-4 rounded-md text-sm font-medium ${
                  signupMethod === 'email'
                    ? 'bg-blue-100 text-blue-700 border-2 border-blue-300'
                    : 'bg-gray-100 text-gray-700 border-2 border-gray-300'
                }`}
              >
                이메일 가입
              </button>
            </div>
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

          {/* 메시지 표시 */}
          {message && (
            <div className={`mb-4 p-3 rounded-md text-sm ${
              message.includes('완료') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}>
              {message}
            </div>
          )}

          {/* 소셜 로그인 버튼들 */}
          {signupMethod === 'social' && (
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
                onClick={() => alert('준비중입니다.')}
                disabled={true}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-400 cursor-not-allowed"
              >
                <span className="mr-2">N</span>
                준비중입니다
              </button>

              <button
                onClick={() => alert('준비중입니다.')}
                disabled={true}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-400 cursor-not-allowed"
              >
                <span className="mr-2">💳</span>
                준비중입니다
              </button>
            </div>
          )}

          {/* 이메일 가입 폼 */}
          {signupMethod === 'email' && (
            <form onSubmit={handleEmailSignup} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  이메일
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  value={emailForm.email}
                  onChange={handleInputChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="example@email.com"
                />
              </div>

              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                  이름
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  required
                  value={emailForm.name}
                  onChange={handleInputChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="홍길동"
                />
              </div>

              <div>
                <label htmlFor="birthYear" className="block text-sm font-medium text-gray-700">
                  출생연도 (선택)
                </label>
                <input
                  id="birthYear"
                  name="birthYear"
                  type="number"
                  value={emailForm.birthYear}
                  onChange={handleInputChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="1990"
                  min="1900"
                  max="2025"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                  비밀번호
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  value={emailForm.password}
                  onChange={handleInputChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="6자 이상"
                />
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                  비밀번호 확인
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  required
                  value={emailForm.confirmPassword}
                  onChange={handleInputChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="비밀번호 재입력"
                />
              </div>

              <button
                type="submit"
                disabled={!agreed || loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? '가입 중...' : '이메일로 가입하기'}
              </button>
            </form>
          )}

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
