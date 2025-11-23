#!/usr/bin/env python3
"""
카카오 로그인 종합 테스트 - 누락된 테스트 케이스 보완
"""

from social_auth import SocialAuthService
from auth_models import UserCreate
import asyncio


class TestKakaoComprehensive:
    """카카오 로그인 종합 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.social_auth_service = SocialAuthService()
    
    def test_whitespace_provider_id(self):
        """공백만 있는 provider_id 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": "   ",  # 공백만
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider_id가 유효하지 않습니다" in str(e)
    
    def test_zero_provider_id(self):
        """0인 provider_id 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": 0,
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider_id가 유효하지 않습니다" in str(e)
    
    def test_boolean_provider_id(self):
        """불린 값 provider_id 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": False,
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider_id가 유효하지 않습니다" in str(e)
    
    def test_list_provider_id(self):
        """리스트 타입 provider_id 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": [123, 456],
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        result = self.social_auth_service.create_user_from_social(social_user_info)
        assert result.provider_id == "[123, 456]"
    
    def test_unicode_provider_id(self):
        """유니코드 문자 provider_id 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": "카카오123",
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        result = self.social_auth_service.create_user_from_social(social_user_info)
        assert result.provider_id == "카카오123"
    
    def test_none_provider(self):
        """None provider 테스트"""
        social_user_info = {
            "provider": None,
            "provider_id": "12345678",
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider가 누락되었습니다" in str(e)
    
    def test_whitespace_provider(self):
        """공백만 있는 provider 테스트"""
        social_user_info = {
            "provider": "   ",
            "provider_id": "12345678",
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        # 공백은 유효한 문자열로 처리됨 (현재 구현)
        result = self.social_auth_service.create_user_from_social(social_user_info)
        assert result.provider == "   "
    
    def test_invalid_provider_type(self):
        """잘못된 타입의 provider 테스트"""
        social_user_info = {
            "provider": 123,  # 숫자
            "provider_id": "12345678",
            "email": "test@example.com",
            "name": "테스트사용자"
        }
        
        result = self.social_auth_service.create_user_from_social(social_user_info)
        assert result.provider == "123"
    
    def test_missing_all_optional_fields(self):
        """모든 선택적 필드가 없는 경우"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": "12345678"
        }
        
        result = self.social_auth_service.create_user_from_social(social_user_info)
        assert result.email == ""
        assert result.name == ""
        assert result.kakao_account == ""
    
    def test_none_optional_fields(self):
        """선택적 필드가 None인 경우"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": "12345678",
            "email": None,
            "name": None,
            "phone_number": None
        }
        
        result = self.social_auth_service.create_user_from_social(social_user_info)
        assert result.email == ""
        assert result.name == ""
        assert result.kakao_account == ""
    
    def test_empty_dict_input(self):
        """빈 딕셔너리 입력 테스트"""
        social_user_info = {}
        
        try:
            self.social_auth_service.create_user_from_social(social_user_info)
            raise AssertionError("예외가 발생해야 합니다")
        except ValueError as e:
            assert "provider_id가 유효하지 않습니다" in str(e)
    
    def test_very_long_fields(self):
        """매우 긴 필드값 테스트"""
        long_string = "a" * 1000
        social_user_info = {
            "provider": "kakao",
            "provider_id": long_string,
            "email": f"{long_string}@example.com",
            "name": long_string
        }
        
        result = self.social_auth_service.create_user_from_social(social_user_info)
        assert len(result.provider_id) == 1000
        assert len(result.name) == 1000
    
    def test_special_characters_in_fields(self):
        """특수문자가 포함된 필드 테스트"""
        social_user_info = {
            "provider": "kakao",
            "provider_id": "test@#$%^&*()",
            "email": "test+special@example.com",
            "name": "테스트<>&\"'"
        }
        
        result = self.social_auth_service.create_user_from_social(social_user_info)
        assert result.provider_id == "test@#$%^&*()"
        assert result.email == "test+special@example.com"
        assert result.name == "테스트<>&\"'"


class TestKakaoTokenVerification:
    """카카오 토큰 검증 테스트"""
    
    def setup_method(self):
        self.social_auth_service = SocialAuthService()
    
    def test_verify_kakao_token_missing_id(self):
        """카카오 토큰 검증 시 ID 누락 테스트"""
        # 실제 API 호출 없이 테스트하기 위해 mock 필요
        # 여기서는 verify_kakao_token의 로직만 확인
        pass
    
    def test_verify_social_token_invalid_provider(self):
        """잘못된 provider로 토큰 검증 테스트"""
        async def run_test():
            result = await self.social_auth_service.verify_social_token("invalid", "token")
            assert result is None
        
        asyncio.run(run_test())
    
    def test_verify_social_token_empty_provider(self):
        """빈 provider로 토큰 검증 테스트"""
        async def run_test():
            result = await self.social_auth_service.verify_social_token("", "token")
            assert result is None
        
        asyncio.run(run_test())


def run_comprehensive_tests():
    """종합 테스트 실행"""
    print("🔍 카카오 로그인 종합 테스트 시작")
    
    # 기본 테스트
    test_class = TestKakaoComprehensive()
    test_class.setup_method()
    
    # 토큰 검증 테스트
    token_test_class = TestKakaoTokenVerification()
    token_test_class.setup_method()
    
    tests = [
        ("공백 provider_id 테스트", test_class.test_whitespace_provider_id),
        ("0 provider_id 테스트", test_class.test_zero_provider_id),
        ("불린 provider_id 테스트", test_class.test_boolean_provider_id),
        ("리스트 provider_id 테스트", test_class.test_list_provider_id),
        ("유니코드 provider_id 테스트", test_class.test_unicode_provider_id),
        ("None provider 테스트", test_class.test_none_provider),
        ("공백 provider 테스트", test_class.test_whitespace_provider),
        ("잘못된 타입 provider 테스트", test_class.test_invalid_provider_type),
        ("모든 선택적 필드 누락 테스트", test_class.test_missing_all_optional_fields),
        ("None 선택적 필드 테스트", test_class.test_none_optional_fields),
        ("빈 딕셔너리 입력 테스트", test_class.test_empty_dict_input),
        ("매우 긴 필드값 테스트", test_class.test_very_long_fields),
        ("특수문자 필드 테스트", test_class.test_special_characters_in_fields),
        ("잘못된 provider 토큰 검증", token_test_class.test_verify_social_token_invalid_provider),
        ("빈 provider 토큰 검증", token_test_class.test_verify_social_token_empty_provider),
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
    
    print(f"\n📊 종합 테스트 결과: {passed}개 통과, {failed}개 실패")
    return failed == 0


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)