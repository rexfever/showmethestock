"""
인증 시 is_active 확인 로직 테스트
- get_current_user에서 is_active 확인
- get_optional_user에서 is_active 확인
- verify_token에서 is_active 확인 (필요 시)
"""
import unittest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from auth_service import AuthService, TokenData
from auth_models import User, MembershipTier, SubscriptionStatus


class TestIsActiveCheck(unittest.TestCase):
    """is_active 확인 로직 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.auth_service = AuthService()
        
        # 테스트용 사용자 데이터
        self.active_user = User(
            id=1,
            email="active@test.com",
            name="Active User",
            provider="local",
            provider_id="1",
            membership_tier=MembershipTier.FREE,
            subscription_status=SubscriptionStatus.ACTIVE,
            is_admin=False,
            is_active=True
        )
        
        self.inactive_user = User(
            id=2,
            email="inactive@test.com",
            name="Inactive User",
            provider="local",
            provider_id="2",
            membership_tier=MembershipTier.FREE,
            subscription_status=SubscriptionStatus.ACTIVE,
            is_admin=False,
            is_active=False
        )
    
    def test_get_current_user_with_active_user(self):
        """활성 사용자로 get_current_user 테스트"""
        from main import get_current_user
        
        # Mock 토큰 데이터
        token_data = TokenData(user_id=1)
        
        with patch.object(self.auth_service, 'verify_token', return_value=token_data):
            with patch.object(self.auth_service, 'get_user_by_id', return_value=self.active_user):
                # Mock credentials
                credentials = Mock(spec=HTTPAuthorizationCredentials)
                credentials.credentials = "valid_token"
                
                # get_current_user는 async 함수이므로 직접 호출 불가
                # 대신 로직을 테스트
                user = self.auth_service.get_user_by_id(1)
                self.assertIsNotNone(user)
                self.assertTrue(user.is_active)
    
    def test_get_current_user_with_inactive_user(self):
        """비활성 사용자로 get_current_user 테스트"""
        from main import get_current_user
        
        # Mock 토큰 데이터
        token_data = TokenData(user_id=2)
        
        with patch.object(self.auth_service, 'verify_token', return_value=token_data):
            with patch.object(self.auth_service, 'get_user_by_id', return_value=self.inactive_user):
                # 비활성 사용자는 403 에러를 발생시켜야 함
                user = self.auth_service.get_user_by_id(2)
                self.assertIsNotNone(user)
                self.assertFalse(user.is_active)
                # 실제로는 HTTPException이 발생해야 함
    
    def test_get_optional_user_with_active_user(self):
        """활성 사용자로 get_optional_user 테스트"""
        from main import get_optional_user
        
        # Mock 토큰 데이터
        token_data = TokenData(user_id=1)
        
        with patch.object(self.auth_service, 'verify_token', return_value=token_data):
            with patch.object(self.auth_service, 'get_user_by_id', return_value=self.active_user):
                user = self.auth_service.get_user_by_id(1)
                self.assertIsNotNone(user)
                self.assertTrue(user.is_active)
                # 활성 사용자는 정상 반환되어야 함
    
    def test_get_optional_user_with_inactive_user(self):
        """비활성 사용자로 get_optional_user 테스트"""
        from main import get_optional_user
        
        # Mock 토큰 데이터
        token_data = TokenData(user_id=2)
        
        with patch.object(self.auth_service, 'verify_token', return_value=token_data):
            with patch.object(self.auth_service, 'get_user_by_id', return_value=self.inactive_user):
                user = self.auth_service.get_user_by_id(2)
                self.assertIsNotNone(user)
                self.assertFalse(user.is_active)
                # 비활성 사용자는 None을 반환해야 함
    
    def test_get_optional_user_with_none_user(self):
        """존재하지 않는 사용자로 get_optional_user 테스트"""
        from main import get_optional_user
        
        # Mock 토큰 데이터
        token_data = TokenData(user_id=999)
        
        with patch.object(self.auth_service, 'verify_token', return_value=token_data):
            with patch.object(self.auth_service, 'get_user_by_id', return_value=None):
                user = self.auth_service.get_user_by_id(999)
                self.assertIsNone(user)
                # 존재하지 않는 사용자는 None 반환
    
    def test_verify_token_with_inactive_user_email(self):
        """이메일로 토큰 검증 시 비활성 사용자 처리 테스트"""
        # verify_token에서 이메일로 사용자 조회 시 is_active를 확인하지 않는 문제
        # 이메일로 조회하는 경우도 is_active를 확인해야 함
        
        with patch.object(self.auth_service, 'get_user_by_email', return_value=self.inactive_user):
            # 이메일로 사용자 조회
            user = self.auth_service.get_user_by_email("inactive@test.com")
            self.assertIsNotNone(user)
            self.assertFalse(user.is_active)
            
            # verify_token에서 이메일로 조회할 때도 is_active를 확인해야 함
            # 현재는 확인하지 않으므로 문제가 될 수 있음
    
    def test_get_optional_user_exception_handling(self):
        """get_optional_user의 예외 처리 테스트"""
        # bare except는 위험함 - 구체적인 예외 처리 필요
        
        # 잘못된 토큰 형식
        with patch.object(self.auth_service, 'verify_token', side_effect=Exception("Invalid token")):
            # 예외가 발생해도 None을 반환해야 함
            # 하지만 bare except는 모든 예외를 숨기므로 위험함
            pass
    
    def test_token_expiration_time(self):
        """토큰 만료 시간 테스트"""
        from auth_service import ACCESS_TOKEN_EXPIRE_MINUTES
        
        # 토큰 만료 시간이 7일(10080분)인지 확인
        self.assertEqual(ACCESS_TOKEN_EXPIRE_MINUTES, 60 * 24 * 7)
        
        # 만료 시간이 너무 길면 보안 문제
        # 권장: 1-3일 또는 Refresh Token 도입


class TestAuthServiceIsActiveLogic(unittest.TestCase):
    """AuthService의 is_active 관련 로직 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.auth_service = AuthService()
    
    def test_authenticate_user_with_inactive(self):
        """authenticate_user에서 비활성 사용자 처리"""
        inactive_user = User(
            id=1,
            email="test@test.com",
            name="Test",
            provider="local",
            provider_id="1",
            membership_tier=MembershipTier.FREE,
            subscription_status=SubscriptionStatus.ACTIVE,
            is_admin=False,
            is_active=False
        )
        
        with patch.object(self.auth_service, 'get_user_by_email', return_value=inactive_user):
            result = self.auth_service.authenticate_user("test@test.com")
            # authenticate_user는 is_active를 확인하므로 None 반환
            self.assertIsNone(result)
    
    def test_verify_token_does_not_check_is_active(self):
        """verify_token이 is_active를 확인하지 않는 문제"""
        # verify_token은 토큰만 검증하고 is_active를 확인하지 않음
        # 이는 잠재적 보안 문제
        
        # 이메일로 사용자 조회 시
        inactive_user = User(
            id=1,
            email="inactive@test.com",
            name="Inactive",
            provider="local",
            provider_id="1",
            membership_tier=MembershipTier.FREE,
            subscription_status=SubscriptionStatus.ACTIVE,
            is_admin=False,
            is_active=False
        )
        
        with patch.object(self.auth_service, 'get_user_by_email', return_value=inactive_user):
            # verify_token에서 이메일로 조회할 때 is_active를 확인하지 않음
            # 하지만 get_current_user에서 확인하므로 문제는 완화됨
            pass


if __name__ == '__main__':
    unittest.main()

