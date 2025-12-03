// 카카오 로그인 유틸리티 함수들
import getConfig from '../config';

export const loginWithKakao = () => {
  return new Promise((resolve, reject) => {
    console.log('loginWithKakao 시작');
    console.log('window.Kakao:', window.Kakao);
    console.log('window.Kakao.Auth:', window.Kakao?.Auth);
    console.log('window.Kakao.Auth.login:', typeof window.Kakao?.Auth?.login);
    
    // SDK가 제대로 로드되지 않은 경우 URL 리다이렉트 방식 사용
    if (typeof window === 'undefined' || !window.Kakao || !window.Kakao.Auth || typeof window.Kakao.Auth.login !== 'function') {
      console.log('SDK 방식 실패, URL 리다이렉트 방식 사용');
      
      // 카카오 로그인 URL로 리다이렉트
      const config = getConfig();
      const redirectUri = encodeURIComponent(config.domain + '/kakao-callback');
      const kakaoClientId = process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID || '4eb579e52709ea64e8b941b9c95d20da';
      const kakaoLoginUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${kakaoClientId}&redirect_uri=${redirectUri}&response_type=code`;
      
      console.log('카카오 로그인 URL:', kakaoLoginUrl);
      window.location.href = kakaoLoginUrl;
      return;
    }

    if (!window.Kakao.isInitialized()) {
      reject(new Error('카카오 SDK가 초기화되지 않았습니다.'));
      return;
    }

    // 카카오 로그인 실행
    try {
      window.Kakao.Auth.login({
        success: (authObj) => {
          console.log('카카오 로그인 성공:', authObj);
          
          // 사용자 정보 가져오기
          window.Kakao.API.request({
            url: '/v2/user/me',
            success: (res) => {
              console.log('사용자 정보 조회 성공:', res);
              
              const kakaoAccount = res.kakao_account;
              const profile = kakaoAccount.profile;
              
              const userInfo = {
                access_token: authObj.access_token,
                provider: 'kakao',
                user_info: {
                  provider_id: res.id.toString(),
                  email: kakaoAccount.email || '',
                  name: profile.nickname || '',
                  profile_image: profile.profile_image_url || '',
                  phone_number: kakaoAccount.phone_number || '',
                  gender: kakaoAccount.gender || '',
                  age_range: kakaoAccount.age_range || '',
                  birthday: kakaoAccount.birthday || ''
                }
              };
              
              resolve(userInfo);
            },
            fail: (error) => {
              console.error('사용자 정보 가져오기 실패:', error);
              reject(new Error('사용자 정보를 가져오는데 실패했습니다.'));
            }
          });
        },
        fail: (error) => {
          console.error('카카오 로그인 실패:', error);
          reject(new Error('카카오 로그인에 실패했습니다.'));
        }
      });
    } catch (error) {
      console.error('카카오 로그인 실행 중 오류:', error);
      reject(new Error('카카오 로그인 실행 중 오류가 발생했습니다.'));
    }
  });
};

export const logoutWithKakao = () => {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.Kakao) {
      // SDK가 없어도 로컬 로그아웃은 진행
      resolve();
      return;
    }

    window.Kakao.Auth.logout(() => {
      resolve();
    });
  });
};

export const isKakaoSDKReady = () => {
  return typeof window !== 'undefined' && 
         window.Kakao && 
         window.Kakao.isInitialized();
};

/**
 * 카카오톡 인앱 브라우저인지 확인
 * @returns {boolean} 카카오톡 인앱 브라우저 여부
 */
export const isKakaoTalkBrowser = () => {
  if (typeof window === 'undefined') {
    return false;
  }
  
  // User-Agent로 카카오톡 인앱 브라우저 감지
  const userAgent = window.navigator.userAgent || '';
  const isKakaoTalk = /KAKAOTALK/i.test(userAgent);
  
  // 카카오 SDK가 로드되어 있으면 SDK 메서드 사용 (더 정확함)
  if (window.Kakao && typeof window.Kakao.isKakaoTalkBrowser === 'function') {
    return window.Kakao.isKakaoTalkBrowser();
  }
  
  return isKakaoTalk;
};

/**
 * 카카오 액세스 토큰 가져오기
 * @returns {string|null} 액세스 토큰 또는 null
 */
export const getKakaoAccessToken = () => {
  if (typeof window === 'undefined' || !window.Kakao || !isKakaoSDKReady()) {
    return null;
  }
  
  try {
    return window.Kakao.Auth.getAccessToken() || null;
  } catch (error) {
    console.error('카카오 토큰 가져오기 실패:', error);
    return null;
  }
};

/**
 * 카카오 세션 확인 및 사용자 정보 가져오기
 * @returns {Promise} 사용자 정보 또는 null
 */
export const checkKakaoSession = async () => {
  return new Promise((resolve, reject) => {
    if (!isKakaoSDKReady()) {
      reject(new Error('카카오 SDK가 준비되지 않았습니다.'));
      return;
    }
    
    // 액세스 토큰 확인
    const accessToken = getKakaoAccessToken();
    if (!accessToken) {
      resolve(null); // 토큰이 없으면 null 반환 (에러 아님)
      return;
    }
    
    // 사용자 정보 가져오기
    try {
      window.Kakao.API.request({
        url: '/v2/user/me',
        success: (res) => {
          console.log('카카오 세션 확인 성공:', res);
          
          // 응답 데이터 검증
          if (!res || !res.kakao_account || !res.kakao_account.profile) {
            console.warn('카카오 사용자 정보 형식이 올바르지 않습니다.');
            resolve(null);
            return;
          }
          
          const kakaoAccount = res.kakao_account;
          const profile = kakaoAccount.profile;
          
          const userInfo = {
            access_token: accessToken,
            provider: 'kakao',
            user_info: {
              provider_id: res.id.toString(),
              email: kakaoAccount.email || '',
              name: profile.nickname || '',
              profile_image: profile.profile_image_url || '',
              phone_number: kakaoAccount.phone_number || '',
              gender: kakaoAccount.gender || '',
              age_range: kakaoAccount.age_range || '',
              birthday: kakaoAccount.birthday || ''
            }
          };
          
          resolve(userInfo);
        },
        fail: (error) => {
          // 에러 코드 확인
          const errorCode = error?.code || error?.error || 'UNKNOWN';
          const errorMessage = error?.msg || error?.message || '알 수 없는 오류';
          
          // 토큰 만료 또는 인증 실패 (401, -401 등)
          if (errorCode === -401 || errorCode === 401 || errorMessage.includes('expired') || errorMessage.includes('invalid')) {
            console.warn('카카오 토큰이 만료되었거나 유효하지 않습니다:', errorMessage);
          } else {
            console.error('카카오 사용자 정보 조회 실패:', errorCode, errorMessage);
          }
          
          // 토큰이 만료되었을 수 있으므로 null 반환 (에러 아님)
          resolve(null);
        }
      });
    } catch (error) {
      console.error('카카오 세션 확인 중 오류:', error);
      resolve(null);
    }
  });
};

/**
 * 카카오톡 인앱 브라우저에서 자동 로그인 시도
 * @returns {Promise} 로그인 결과
 */
export const autoLoginWithKakaoTalk = async () => {
  return new Promise((resolve, reject) => {
    // 카카오톡 인앱 브라우저가 아니면 실패
    if (!isKakaoTalkBrowser()) {
      reject(new Error('카카오톡 인앱 브라우저가 아닙니다.'));
      return;
    }
    
    // SDK가 준비되지 않았으면 실패
    if (!isKakaoSDKReady()) {
      reject(new Error('카카오 SDK가 준비되지 않았습니다.'));
      return;
    }
    
    // 카카오 로그인 실행 (카카오톡 앱에 로그인되어 있으면 자동으로 진행됨)
    loginWithKakao()
      .then(resolve)
      .catch(reject);
  });
};

/**
 * 일반 브라우저에서 카카오 세션 확인 및 자동 로그인 시도
 * @returns {Promise} 로그인 결과 또는 null
 */
export const autoLoginWithKakaoSession = async () => {
  return new Promise((resolve, reject) => {
    // SDK가 준비되지 않았으면 실패
    if (!isKakaoSDKReady()) {
      reject(new Error('카카오 SDK가 준비되지 않았습니다.'));
      return;
    }
    
    // 카카오 세션 확인
    checkKakaoSession()
      .then((userInfo) => {
        if (userInfo) {
          resolve(userInfo);
        } else {
          // 세션이 없으면 null 반환 (에러 아님)
          resolve(null);
        }
      })
      .catch(reject);
  });
};
