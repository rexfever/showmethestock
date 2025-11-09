#!/usr/bin/env python3
"""
Import 테스트
"""

import sys
import os

def test_auth_service_import():
    """auth_service import 테스트"""
    try:
        sys.path.insert(0, 'backend')
        from auth_service import auth_service
        print("✅ auth_service import 성공")
        return True
    except Exception as e:
        print(f"❌ auth_service import 실패: {e}")
        return False

def test_main_imports():
    """main.py의 주요 import 테스트"""
    try:
        sys.path.insert(0, 'backend')
        
        # 핵심 모듈들
        from auth_models import User, Token
        from auth_service import auth_service
        from social_auth import social_auth_service
        
        print("✅ 주요 모듈 import 성공")
        return True
    except Exception as e:
        print(f"❌ 주요 모듈 import 실패: {e}")
        return False

def test_no_duplicate_files():
    """중복 파일 확인"""
    auth_main = os.path.exists('backend/auth_service.py')
    auth_services = os.path.exists('backend/services/auth_service.py')
    
    if auth_main and not auth_services:
        print("✅ auth_service 중복 제거 완료")
        return True
    else:
        print(f"❌ 파일 상태: main={auth_main}, services={auth_services}")
        return False

if __name__ == "__main__":
    print("=== Import 테스트 ===")
    
    tests = [
        ("중복 파일 확인", test_no_duplicate_files),
        ("auth_service import", test_auth_service_import),
        ("주요 모듈 import", test_main_imports),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"{name} 오류: {e}")
            results.append((name, False))
    
    print("\n=== 결과 ===")
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("🎉 모든 import 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")