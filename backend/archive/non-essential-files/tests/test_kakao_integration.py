#!/usr/bin/env python3
"""
카카오 로그인 통합 테스트 (실제 API 호출 시뮬레이션)
"""

import json
from unittest.mock import Mock, patch
from social_auth import SocialAuthService


def test_kakao_api_response_simulation():
    """카카오 API 응답 시뮬레이션 테스트"""
    print("🔄 카카오 API 응답 시뮬레이션 테스트")
    
    # 정상적인 카카오 API 응답
    normal_response = {
        "id": 123456789,
        "kakao_account": {
            "email": "user@example.com",
            "profile": {
                "nickname": "카카오사용자",
                "profile_image_url": "https://example.com/profile.jpg"
            },
            "phone_number": "+82 10-1234-5678",
            "gender": "male",
            "age_range": "20~29",
            "birthday": "1201"
        }
    }
    
    # 정상 케이스 테스트
    social_auth_service = SocialAuthService()
    
    social_user_info = {
        "provider": "kakao",
        "provider_id": str(normal_response["id"]),
        "email": normal_response["kakao_account"]["email"],
        "name": normal_response["kakao_account"]["profile"]["nickname"],
        "profile_image": normal_response["kakao_account"]["profile"]["profile_image_url"],
        "phone_number": normal_response["kakao_account"]["phone_number"],
        "gender": normal_response["kakao_account"]["gender"],
        "age_range": normal_response["kakao_account"]["age_range"],
        "birthday": normal_response["kakao_account"]["birthday"]
    }
    
    try:
        result = social_auth_service.create_user_from_social(social_user_info)
        print(f"✅ 정상 응답 처리 성공: {result.provider_id}")
    except Exception as e:
        print(f"❌ 정상 응답 처리 실패: {e}")
        return False
    
    # ID가 없는 비정상 응답
    abnormal_response = {
        # "id" 필드 누락
        "kakao_account": {
            "email": "user@example.com",
            "profile": {
                "nickname": "카카오사용자"
            }
        }
    }
    
    try:
        social_user_info_abnormal = {
            "provider": "kakao",
            "provider_id": abnormal_response.get("id"),  # None
            "email": abnormal_response["kakao_account"]["email"],
            "name": abnormal_response["kakao_account"]["profile"]["nickname"]
        }
        
        social_auth_service.create_user_from_social(social_user_info_abnormal)
        print("❌ 비정상 응답에서 예외가 발생하지 않음")
        return False
    except ValueError as e:
        print(f"✅ 비정상 응답 처리 성공: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 예외: {e}")
        return False
    
    return True


def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n🔍 엣지 케이스 테스트")
    
    social_auth_service = SocialAuthService()
    
    # 케이스 1: 매우 긴 provider_id
    long_id = "1" * 100
    try:
        result = social_auth_service.create_user_from_social({
            "provider": "kakao",
            "provider_id": long_id,
            "email": "test@example.com",
            "name": "테스트"
        })
        print(f"✅ 긴 provider_id 처리 성공: {len(result.provider_id)}자")
    except Exception as e:
        print(f"❌ 긴 provider_id 처리 실패: {e}")
        return False
    
    # 케이스 2: 특수문자가 포함된 provider_id
    special_id = "kakao_123-456_789"
    try:
        result = social_auth_service.create_user_from_social({
            "provider": "kakao",
            "provider_id": special_id,
            "email": "test@example.com",
            "name": "테스트"
        })
        print(f"✅ 특수문자 provider_id 처리 성공: {result.provider_id}")
    except Exception as e:
        print(f"❌ 특수문자 provider_id 처리 실패: {e}")
        return False
    
    # 케이스 3: 0으로 시작하는 숫자 ID
    zero_start_id = "0123456789"
    try:
        result = social_auth_service.create_user_from_social({
            "provider": "kakao",
            "provider_id": zero_start_id,
            "email": "test@example.com",
            "name": "테스트"
        })
        print(f"✅ 0으로 시작하는 ID 처리 성공: {result.provider_id}")
    except Exception as e:
        print(f"❌ 0으로 시작하는 ID 처리 실패: {e}")
        return False
    
    return True


def test_data_consistency():
    """데이터 일관성 테스트"""
    print("\n📊 데이터 일관성 테스트")
    
    social_auth_service = SocialAuthService()
    
    # 동일한 데이터로 여러 번 호출했을 때 일관된 결과가 나오는지 확인
    test_data = {
        "provider": "kakao",
        "provider_id": "consistency_test_123",
        "email": "consistency@example.com",
        "name": "일관성테스트"
    }
    
    results = []
    for i in range(3):
        try:
            result = social_auth_service.create_user_from_social(test_data.copy())
            results.append(result)
        except Exception as e:
            print(f"❌ {i+1}번째 호출 실패: {e}")
            return False
    
    # 모든 결과가 동일한지 확인
    first_result = results[0]
    for i, result in enumerate(results[1:], 2):
        if (result.provider_id != first_result.provider_id or 
            result.email != first_result.email or 
            result.name != first_result.name):
            print(f"❌ {i}번째 결과가 첫 번째와 다름")
            return False
    
    print("✅ 데이터 일관성 확인 완료")
    return True


def run_integration_tests():
    """통합 테스트 실행"""
    print("🚀 카카오 로그인 통합 테스트 시작\n")
    
    tests = [
        ("카카오 API 응답 시뮬레이션", test_kakao_api_response_simulation),
        ("엣지 케이스", test_edge_cases),
        ("데이터 일관성", test_data_consistency),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 예외 발생: {e}")
            failed += 1
    
    print(f"\n📈 통합 테스트 결과: {passed}개 통과, {failed}개 실패")
    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)