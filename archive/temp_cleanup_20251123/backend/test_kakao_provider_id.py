#!/usr/bin/env python3
"""
카카오 로그인 provider_id 처리 테스트
"""

from social_auth import SocialAuthService
from auth_models import UserCreate


class TestKakaoProviderIdHandling:
    """카카오 로그인 provider_id 처리 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.social_auth_service = SocialAuthService()
    
    def test_valid_provider_id(self):
        """유효한 provider_id로 사용자 생성 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": "12345678",
            "email": "test@example.com",
            "name": "테스트사용자",
            "phone_number": "010-1234-5678"
        }
        
        result = self.social_auth_service.create_user_from_social(social_user_info)
        
        assert isinstance(result, UserCreate)
        assert result.provider_id == "12345678"
        assert result.provider == "kakao"
        assert result.email == "test@example.com"
        assert result.name == "테스트사용자"
    
    def test_missing_provider_id(self):
        """provider_id가 없는 경우 테스트"""
        social_user_info = {
            "provider": "kakao",
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider_id가 유효하지 않습니다" in str(e)
    
    def test_none_provider_id(self):
        """provider_id가 None인 경우 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": None,
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider_id가 유효하지 않습니다" in str(e)
    
    def test_string_none_provider_id(self):
        """provider_id가 "None" 문자열인 경우 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": "None",
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider_id가 유효하지 않습니다" in str(e)
    
    def test_empty_provider_id(self):
        """provider_id가 빈 문자열인 경우 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": "",
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider_id가 유효하지 않습니다" in str(e)
    
    def test_missing_provider(self):
        """provider가 없는 경우 테스트"""
        social_user_info = {
            "provider_id": "12345678",
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider가 누락되었습니다" in str(e)
    
    def test_empty_provider(self):
        """provider가 빈 문자열인 경우 테스트"""
        social_user_info = {
            "provider": "",
            "provider_id": "12345678",
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider가 누락되었습니다" in str(e)
    
    def test_optional_fields_handling(self):
        """선택적 필드들의 기본값 처리 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": "12345678"
        }
        
        result = self.social_auth_service.create_user_from_social(social_user_info)
        
        assert result.provider_id == "12345678"
        assert result.provider == "kakao"
        assert result.email == ""
        assert result.name == ""
        assert result.kakao_account == ""
    
    def test_numeric_provider_id(self):
        """숫자형 provider_id 처리 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": 12345678,
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        result = self.social_auth_service.create_user_from_social(social_user_info)
        
        assert result.provider_id == "12345678"  # 문자열로 변환됨
        assert result.provider == "kakao"


def run_tests():
    """테스트 실행 함수"""
    print("🧪 카카오 로그인 provider_id 처리 테스트 시작")
    
    test_class = TestKakaoProviderIdHandling()
    test_class.setup_method()
    
    tests = [
        ("유효한 provider_id 테스트", test_class.test_valid_provider_id),
        ("provider_id 누락 테스트", test_class.test_missing_provider_id),
        ("None provider_id 테스트", test_class.test_none_provider_id),
        ("'None' 문자열 provider_id 테스트", test_class.test_string_none_provider_id),
        ("빈 provider_id 테스트", test_class.test_empty_provider_id),
        ("provider 누락 테스트", test_class.test_missing_provider),
        ("빈 provider 테스트", test_class.test_empty_provider),
        ("선택적 필드 처리 테스트", test_class.test_optional_fields_handling),
        ("숫자형 provider_id 테스트", test_class.test_numeric_provider_id),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            failed += 1
    
    print(f"\n📊 테스트 결과: {passed}개 통과, {failed}개 실패")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)