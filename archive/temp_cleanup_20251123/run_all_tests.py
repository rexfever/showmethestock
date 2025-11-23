#!/usr/bin/env python3
"""
전체 테스트 실행
"""

import subprocess
import sys

def run_test(test_file, test_name):
    """테스트 실행"""
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, timeout=30)
        
        success = result.returncode == 0
        print(f"{test_name}: {'✅' if success else '❌'}")
        
        if not success:
            print(f"  오류: {result.stderr.strip()}")
        
        return success
    except subprocess.TimeoutExpired:
        print(f"{test_name}: ❌ (타임아웃)")
        return False
    except Exception as e:
        print(f"{test_name}: ❌ ({e})")
        return False

if __name__ == "__main__":
    print("=== 전체 테스트 실행 ===")
    
    tests = [
        ("test_syntax_check.py", "구문 검사"),
        ("test_imports.py", "Import 테스트"),
        ("test_auth_integration.py", "Auth 통합"),
    ]
    
    results = []
    for test_file, test_name in tests:
        result = run_test(test_file, test_name)
        results.append((test_name, result))
    
    print("\n=== 최종 결과 ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"통과: {passed}/{total}")
    
    if passed == total:
        print("🎉 모든 테스트 통과!")
        print("\n✅ 중복 제거 및 통합 작업 완료:")
        print("  - API 엔드포인트 중복 제거")
        print("  - auth_service 모듈 통합")
        print("  - 순환 import 문제 해결")
    else:
        print("❌ 일부 테스트 실패")
        sys.exit(1)