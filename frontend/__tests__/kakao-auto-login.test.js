/**
 * 카카오톡 인앱 브라우저 자동 로그인 테스트
 */

import { isKakaoTalkBrowser, autoLoginWithKakaoTalk, autoLoginWithKakaoSession, checkKakaoSession, getKakaoAccessToken, isKakaoSDKReady } from '../utils/kakaoAuth';

// Mock window 객체
const mockWindow = {
  navigator: {
    userAgent: ''
  },
  Kakao: null
};

describe('카카오톡 인앱 브라우저 감지', () => {
  beforeEach(() => {
    // window 객체 초기화
    global.window = { ...mockWindow };
    global.window.navigator = { ...mockWindow.navigator };
  });

  afterEach(() => {
    delete global.window;
  });

  test('카카오톡 인앱 브라우저 User-Agent 감지', () => {
    global.window.navigator.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 KAKAOTALK';
    
    expect(isKakaoTalkBrowser()).toBe(true);
  });

  test('일반 브라우저 User-Agent 감지', () => {
    global.window.navigator.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1';
    
    expect(isKakaoTalkBrowser()).toBe(false);
  });

  test('서버 사이드에서는 false 반환', () => {
    delete global.window;
    
    expect(isKakaoTalkBrowser()).toBe(false);
  });

  test('카카오 SDK 메서드 사용 (우선순위)', () => {
    global.window.Kakao = {
      isKakaoTalkBrowser: jest.fn(() => true)
    };
    global.window.navigator.userAgent = '일반 브라우저';
    
    expect(isKakaoTalkBrowser()).toBe(true);
    expect(global.window.Kakao.isKakaoTalkBrowser).toHaveBeenCalled();
  });
});

describe('카카오 SDK 준비 상태 확인', () => {
  beforeEach(() => {
    global.window = { ...mockWindow };
  });

  afterEach(() => {
    delete global.window;
  });

  test('SDK가 초기화된 경우', () => {
    global.window.Kakao = {
      isInitialized: jest.fn(() => true)
    };
    
    expect(isKakaoSDKReady()).toBe(true);
  });

  test('SDK가 초기화되지 않은 경우', () => {
    global.window.Kakao = {
      isInitialized: jest.fn(() => false)
    };
    
    expect(isKakaoSDKReady()).toBe(false);
  });

  test('SDK가 없는 경우', () => {
    global.window.Kakao = null;
    
    expect(isKakaoSDKReady()).toBe(false);
  });

  test('서버 사이드에서는 false 반환', () => {
    delete global.window;
    
    expect(isKakaoSDKReady()).toBe(false);
  });
});

describe('자동 로그인', () => {
  beforeEach(() => {
    global.window = {
      ...mockWindow,
      Kakao: {
        isInitialized: jest.fn(() => true),
        Auth: {
          login: jest.fn((options) => {
            options.success({ access_token: 'test_token' });
          }),
          API: {
            request: jest.fn((options) => {
              options.success({
                id: '123456',
                kakao_account: {
                  email: 'test@example.com',
                  profile: {
                    nickname: 'Test User',
                    profile_image_url: 'https://example.com/image.jpg'
                  }
                }
              });
            })
          }
        }
      }
    };
    global.window.navigator.userAgent = 'KAKAOTALK';
  });

  afterEach(() => {
    jest.clearAllMocks();
    delete global.window;
  });

  test('카카오톡 인앱 브라우저가 아닌 경우 실패', async () => {
    global.window.navigator.userAgent = '일반 브라우저';
    
    await expect(autoLoginWithKakaoTalk()).rejects.toThrow('카카오톡 인앱 브라우저가 아닙니다.');
  });

  test('SDK가 준비되지 않은 경우 실패', async () => {
    global.window.Kakao.isInitialized = jest.fn(() => false);
    
    await expect(autoLoginWithKakaoTalk()).rejects.toThrow('카카오 SDK가 준비되지 않았습니다.');
  });

  test('자동 로그인 성공', async () => {
    const result = await autoLoginWithKakaoTalk();
    
    expect(result).toHaveProperty('access_token');
    expect(result).toHaveProperty('provider', 'kakao');
    expect(result).toHaveProperty('user_info');
    expect(global.window.Kakao.Auth.login).toHaveBeenCalled();
  });
});

describe('일반 브라우저 카카오 세션 자동 로그인', () => {
  beforeEach(() => {
    global.window = {
      ...mockWindow,
      Kakao: {
        isInitialized: jest.fn(() => true),
        Auth: {
          getAccessToken: jest.fn(() => 'mock_access_token'),
        },
        API: {
          request: jest.fn(({ success }) => {
            success({
              id: '123456789',
              kakao_account: {
                email: 'test@example.com',
                profile: {
                  nickname: 'Test User',
                  profile_image_url: 'https://example.com/image.jpg'
                }
              }
            });
          })
        }
      }
    };
    global.window.navigator.userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';
  });

  afterEach(() => {
    jest.clearAllMocks();
    delete global.window;
  });

  test('카카오 세션이 있는 경우 자동 로그인 성공', async () => {
    const result = await autoLoginWithKakaoSession();
    
    expect(result).toBeTruthy();
    expect(result.provider).toBe('kakao');
    expect(result.access_token).toBe('mock_access_token');
    expect(global.window.Kakao.Auth.getAccessToken).toHaveBeenCalled();
    expect(global.window.Kakao.API.request).toHaveBeenCalled();
  });

  test('카카오 세션이 없는 경우 null 반환', async () => {
    global.window.Kakao.Auth.getAccessToken = jest.fn(() => null);
    
    const result = await autoLoginWithKakaoSession();
    
    expect(result).toBeNull();
    expect(global.window.Kakao.Auth.getAccessToken).toHaveBeenCalled();
  });

  test('getKakaoAccessToken 함수 테스트', () => {
    const token = getKakaoAccessToken();
    
    expect(token).toBe('mock_access_token');
    expect(global.window.Kakao.Auth.getAccessToken).toHaveBeenCalled();
  });

  test('checkKakaoSession 함수 테스트', async () => {
    const result = await checkKakaoSession();
    
    expect(result).toBeTruthy();
    expect(result.provider).toBe('kakao');
    expect(result.access_token).toBe('mock_access_token');
  });
});

