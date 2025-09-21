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
      const kakaoLoginUrl = `https://kauth.kakao.com/oauth/authorize?client_id=4eb579e52709ea64e8b941b9c95d20da&redirect_uri=${redirectUri}&response_type=code`;
      
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
