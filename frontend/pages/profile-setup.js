import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';

export default function ProfileSetup() {
  const [formData, setFormData] = useState({
    // 필수 정보
    name: '',
    birthYear: '',
    kakaoAccount: '',
    
    // 선택 정보
    gender: '',
    ageGroup: '',
    birthday: ''
  });
  
  const [errors, setErrors] = useState({});
  const router = useRouter();

  // 소셜 로그인에서 받은 정보로 초기화
  useEffect(() => {
    // URL 파라미터나 localStorage에서 소셜 로그인 정보 가져오기
    const socialData = JSON.parse(localStorage.getItem('socialLoginData') || '{}');
    if (socialData.name) {
      setFormData(prev => ({
        ...prev,
        name: socialData.name,
        kakaoAccount: socialData.email || ''
      }));
    }
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // 에러 제거
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    // 필수 정보 검증
    if (!formData.name.trim()) {
      newErrors.name = '이름을 입력해주세요';
    }
    
    if (!formData.birthYear) {
      newErrors.birthYear = '출생연도를 선택해주세요';
    } else {
      const year = parseInt(formData.birthYear);
      const currentYear = new Date().getFullYear();
      if (year < 1900 || year > currentYear) {
        newErrors.birthYear = '올바른 출생연도를 선택해주세요';
      }
    }
    
    if (!formData.kakaoAccount.trim()) {
      newErrors.kakaoAccount = '카카오계정(전화번호)을 입력해주세요';
    } else if (!/^[0-9-+\s]+$/.test(formData.kakaoAccount)) {
      newErrors.kakaoAccount = '올바른 전화번호 형식을 입력해주세요';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    try {
      // 프로필 정보 저장
      const profileData = {
        ...formData,
        isProfileComplete: true
      };
      
      // localStorage에 저장 (실제로는 API 호출)
      localStorage.setItem('userProfile', JSON.stringify(profileData));
      
      // 메인 페이지로 이동
      router.push('/');
      
    } catch (error) {
      console.error('프로필 저장 실패:', error);
    }
  };

  const currentYear = new Date().getFullYear();
  const birthYears = Array.from({ length: 100 }, (_, i) => currentYear - i);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <Head>
        <title>프로필 설정 - 스톡인사이트</title>
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
          프로필 설정
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          맞춤형 서비스를 위해 추가 정보를 입력해주세요
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            
            {/* 필수 정보 섹션 */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                필수 정보 <span className="text-red-500">*</span>
              </h3>
              
              {/* 이름 */}
              <div className="mb-4">
                <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                  이름 <span className="text-red-500">*</span>
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleInputChange}
                  className={`mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 ${
                    errors.name ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="이름을 입력하세요"
                />
                {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
              </div>

              {/* 출생연도 */}
              <div className="mb-4">
                <label htmlFor="birthYear" className="block text-sm font-medium text-gray-700">
                  출생연도 <span className="text-red-500">*</span>
                </label>
                <select
                  id="birthYear"
                  name="birthYear"
                  value={formData.birthYear}
                  onChange={handleInputChange}
                  className={`mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 ${
                    errors.birthYear ? 'border-red-300' : 'border-gray-300'
                  }`}
                >
                  <option value="">출생연도를 선택하세요</option>
                  {birthYears.map(year => (
                    <option key={year} value={year}>{year}년</option>
                  ))}
                </select>
                {errors.birthYear && <p className="mt-1 text-sm text-red-600">{errors.birthYear}</p>}
              </div>

              {/* 카카오계정(전화번호) */}
              <div className="mb-4">
                <label htmlFor="kakaoAccount" className="block text-sm font-medium text-gray-700">
                  카카오계정(전화번호) <span className="text-red-500">*</span>
                </label>
                <input
                  id="kakaoAccount"
                  name="kakaoAccount"
                  type="tel"
                  value={formData.kakaoAccount}
                  onChange={handleInputChange}
                  className={`mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 ${
                    errors.kakaoAccount ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="010-1234-5678"
                />
                {errors.kakaoAccount && <p className="mt-1 text-sm text-red-600">{errors.kakaoAccount}</p>}
              </div>
            </div>

            {/* 선택 정보 섹션 */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                선택 정보
              </h3>
              
              {/* 성별 */}
              <div className="mb-4">
                <label htmlFor="gender" className="block text-sm font-medium text-gray-700">
                  성별
                </label>
                <select
                  id="gender"
                  name="gender"
                  value={formData.gender}
                  onChange={handleInputChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">선택하세요</option>
                  <option value="male">남성</option>
                  <option value="female">여성</option>
                  <option value="other">기타</option>
                </select>
              </div>

              {/* 연령대 */}
              <div className="mb-4">
                <label htmlFor="ageGroup" className="block text-sm font-medium text-gray-700">
                  연령대
                </label>
                <select
                  id="ageGroup"
                  name="ageGroup"
                  value={formData.ageGroup}
                  onChange={handleInputChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">선택하세요</option>
                  <option value="10s">10대</option>
                  <option value="20s">20대</option>
                  <option value="30s">30대</option>
                  <option value="40s">40대</option>
                  <option value="50s">50대</option>
                  <option value="60s">60대 이상</option>
                </select>
              </div>

              {/* 생일 */}
              <div className="mb-6">
                <label htmlFor="birthday" className="block text-sm font-medium text-gray-700">
                  생일
                </label>
                <input
                  id="birthday"
                  name="birthday"
                  type="date"
                  value={formData.birthday}
                  onChange={handleInputChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {/* 제출 버튼 */}
            <div>
              <button
                type="submit"
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                프로필 설정 완료
              </button>
            </div>

            {/* 건너뛰기 */}
            <div className="text-center">
              <button
                type="button"
                onClick={() => router.push('/')}
                className="text-sm text-gray-600 hover:text-gray-500"
              >
                나중에 설정하기
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
