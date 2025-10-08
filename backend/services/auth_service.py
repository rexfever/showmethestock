"""
인증 관련 서비스
"""
import os
import httpx
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from auth_service import auth_service
from social_auth import social_auth_service


async def process_kakao_callback(request: dict) -> Dict[str, Any]:
    """카카오 OAuth 콜백 처리"""
    try:
        print(f"카카오 콜백 요청: {request}")
        
        # 요청에서 코드 추출
        code = request.get("code")
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="인증 코드가 없습니다"
            )
        
        # 리다이렉트 URI 구성
        redirect_uri = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/kakao-callback"
        
        # 카카오에서 액세스 토큰 요청
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": os.getenv("KAKAO_CLIENT_ID", "4eb579e52709ea64e8b941b9c95d20da"),
                    "redirect_uri": redirect_uri,
                    "code": code
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            print(f"카카오 토큰 응답 상태: {token_response.status_code}")
            print(f"카카오 토큰 응답 내용: {token_response.text}")
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="카카오 토큰 요청에 실패했습니다"
                )
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="액세스 토큰을 받지 못했습니다"
                )
            
            # 카카오에서 사용자 정보 요청
            user_response = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="사용자 정보 요청에 실패했습니다"
                )
            
            user_data = user_response.json()
            kakao_account = user_data.get("kakao_account", {})
            profile = kakao_account.get("profile", {})
            
            # 사용자 정보 구성
            social_user_info = {
                "provider": "kakao",
                "provider_id": str(user_data.get("id")),
                "email": kakao_account.get("email", ""),
                "name": profile.get("nickname", ""),
                "profile_image": profile.get("profile_image_url", ""),
                "phone_number": kakao_account.get("phone_number", ""),
                "gender": kakao_account.get("gender", ""),
                "age_range": kakao_account.get("age_range", ""),
                "birthday": kakao_account.get("birthday", "")
            }
            
            print(f"사용자 정보 구성: {social_user_info}")
            
            # 소셜 인증 서비스를 통한 사용자 정보 검증
            verified_user_info = await social_auth_service.verify_kakao_token(access_token)
            
            if not verified_user_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="사용자 정보 검증에 실패했습니다"
                )
            
            # 사용자 생성 또는 업데이트
            user = await auth_service.create_or_update_social_user(verified_user_info)
            
            # JWT 토큰 생성
            token = auth_service.create_access_token(user.id)
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "provider": user.provider
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"카카오 콜백 처리 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카카오 로그인 처리 중 오류가 발생했습니다"
        )
