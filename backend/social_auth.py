import requests
import os
from typing import Dict, Any, Optional
from auth_models import UserCreate

class SocialAuthService:
    def __init__(self):
        # 소셜 로그인 API 키들 (환경변수에서 가져옴)
        self.kakao_client_id = os.getenv("KAKAO_CLIENT_ID")
        self.naver_client_id = os.getenv("NAVER_CLIENT_ID")
        self.naver_client_secret = os.getenv("NAVER_CLIENT_SECRET")
        self.toss_client_id = os.getenv("TOSS_CLIENT_ID")
        self.toss_client_secret = os.getenv("TOSS_CLIENT_SECRET")
    
    async def verify_kakao_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """카카오 액세스 토큰 검증 및 사용자 정보 가져오기"""
        try:
            # 카카오 사용자 정보 API 호출
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            response = requests.get("https://kapi.kakao.com/v2/user/me", headers=headers)
            
            if response.status_code == 200:
                user_info = response.json()
                kakao_account = user_info.get("kakao_account", {})
                profile = kakao_account.get("profile", {})
                
                return {
                    "provider_id": str(user_info["id"]),
                    "email": kakao_account.get("email", ""),
                    "name": profile.get("nickname", ""),
                    "profile_image": profile.get("profile_image_url", ""),
                    "phone_number": kakao_account.get("phone_number", ""),  # 전화번호 추가
                    "provider": "kakao"
                }
        except Exception as e:
            print(f"카카오 토큰 검증 실패: {e}")
        
        return None
    
    async def verify_naver_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """네이버 액세스 토큰 검증 및 사용자 정보 가져오기"""
        try:
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            response = requests.get("https://openapi.naver.com/v1/nid/me", headers=headers)
            
            if response.status_code == 200:
                user_info = response.json()
                if user_info.get("resultcode") == "00":
                    profile = user_info.get("response", {})
                    return {
                        "provider_id": profile.get("id", ""),
                        "email": profile.get("email", ""),
                        "name": profile.get("name", ""),
                        "profile_image": profile.get("profile_image", ""),
                        "provider": "naver"
                    }
        except Exception as e:
            print(f"네이버 토큰 검증 실패: {e}")
        
        return None
    
    async def verify_toss_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """토스 액세스 토큰 검증 및 사용자 정보 가져오기"""
        try:
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            response = requests.get("https://api.toss.im/user-api/v2/me", headers=headers)
            
            if response.status_code == 200:
                user_info = response.json()
                return {
                    "provider_id": str(user_info.get("id", "")),
                    "email": user_info.get("email", ""),
                    "name": user_info.get("name", ""),
                    "profile_image": user_info.get("profileImage", ""),
                    "provider": "toss"
                }
        except Exception as e:
            print(f"토스 토큰 검증 실패: {e}")
        
        return None
    
    async def verify_social_token(self, provider: str, access_token: str) -> Optional[Dict[str, Any]]:
        """소셜 로그인 토큰 검증"""
        if provider == "kakao":
            return await self.verify_kakao_token(access_token)
        elif provider == "naver":
            return await self.verify_naver_token(access_token)
        elif provider == "toss":
            return await self.verify_toss_token(access_token)
        else:
            return None
    
    def create_user_from_social(self, social_user_info: Dict[str, Any]) -> UserCreate:
        """소셜 로그인 정보로 사용자 생성"""
        print(f"create_user_from_social 입력: {social_user_info}")
        
        # 필수 필드 검증
        provider_id = social_user_info.get('provider_id')
        
        # provider_id 유효성 검사
        if provider_id is None or provider_id == "None" or provider_id == "" or (isinstance(provider_id, str) and provider_id.strip() == ""):
            raise ValueError(f"provider_id가 유효하지 않습니다: {provider_id}")
        
        # False, 0 등도 유효하지 않은 값으로 처리
        if provider_id is False or provider_id == 0:
            raise ValueError(f"provider_id가 유효하지 않습니다: {provider_id}")
        
        # provider_id를 문자열로 변환
        provider_id = str(provider_id)
        
        email = social_user_info.get('email') or ''
        name = social_user_info.get('name') or ''
        provider = social_user_info.get('provider') or ''
        
        # None 값들을 빈 문자열로 변환
        if email is None:
            email = ''
        if name is None:
            name = ''
        if provider is None:
            provider = ''
        
        # provider를 문자열로 변환
        provider = str(provider)
        
        if not provider:
            raise ValueError("provider가 누락되었습니다")
        
        print(f"provider_id 값: {provider_id}")
        
        phone_number = social_user_info.get("phone_number") or ""
        if phone_number is None:
            phone_number = ""
        
        user_create = UserCreate(
            email=email,
            name=name,
            provider=provider,
            provider_id=provider_id,
            kakao_account=phone_number
        )
        
        print(f"UserCreate 객체 생성 완료: {user_create}")
        return user_create

# 전역 소셜 인증 서비스 인스턴스
social_auth_service = SocialAuthService()
