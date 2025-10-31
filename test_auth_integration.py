#!/usr/bin/env python3
"""
auth_service 모듈 통합 테스트
"""

import os
import sys

def test_no_circular_imports():
    """순환 import 확인"""
    try:
        # main.py import 테스트
        sys.path.insert(0, 'backend')
        
        # auth_service 단독 import
        from auth_service import auth_service
        print("✅ auth_service import 성공")
        
        # main.py의 auth 관련 import 테스트
        from auth_models import User, Token
        print("✅ auth_models import 성공")
        
        return True
    except ImportError as e:
        print(f"❌ Import 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 기타 오류: {e}")
        return False

def test_file_structure():
    """파일 구조 확인"""
    auth_service_exists = os.path.exists('backend/auth_service.py')
    services_auth_exists = os.path.exists('backend/services/auth_service.py')
    
    print(f"backend/auth_service.py 존재: {auth_service_exists}")
    print(f"backend/services/auth_service.py 존재: {services_auth_exists}")
    
    return auth_service_exists and not services_auth_exists

def test_main_py_syntax():
    """main.py 구문 검사"""
    try:
        import ast
        with open('backend/main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast.parse(content)
        print("✅ main.py 구문 검사 통과")
        return True
    except SyntaxError as e:
        print(f"❌ main.py 구문 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ main.py 검사 오류: {e}")
        return False

if __name__ == "__main__":
    print("=== auth_service 모듈 통합 테스트 ===")
    
    tests = [
        ("파일 구조", test_file_structure),
        ("main.py 구문", test_main_py_syntax),
        ("순환 import", test_no_circular_imports),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ 통과" if result else "❌ 실패"
            print(f"{test_name}: {status}")
        except Exception as e:
            results.append((test_name, False))
            print(f"{test_name}: ❌ 오류 - {e}")
    
    print("\n=== 테스트 결과 ===")
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("🎉 모든 테스트 통과! 순환 import 문제 해결됨")
    else:
        print("⚠️ 일부 테스트 실패")
        
    sys.exit(0 if all_passed else 1)