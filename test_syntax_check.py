#!/usr/bin/env python3
"""
구문 검사 테스트
"""

import ast
import re

def test_main_py_syntax():
    """main.py 구문 검사"""
    try:
        with open('backend/main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast.parse(content)
        print("✅ main.py 구문 검사 통과")
        return True
    except SyntaxError as e:
        print(f"❌ main.py 구문 오류: 라인 {e.lineno} - {e.msg}")
        return False
    except Exception as e:
        print(f"❌ main.py 검사 오류: {e}")
        return False

def test_duplicate_functions():
    """중복 함수 확인"""
    try:
        with open('backend/main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        scan_positions = len(re.findall(r'@app\.get\(\'/scan_positions\'\)', content))
        auto_add_positions = len(re.findall(r'@app\.post\(\'/auto_add_positions\'\)', content))
        
        print(f"scan_positions 함수: {scan_positions}개")
        print(f"auto_add_positions 함수: {auto_add_positions}개")
        
        if scan_positions == 1 and auto_add_positions == 1:
            print("✅ 중복 함수 제거 완료")
            return True
        else:
            print("❌ 중복 함수 존재")
            return False
    except Exception as e:
        print(f"❌ 중복 함수 검사 오류: {e}")
        return False

def test_import_statements():
    """import 문 검사"""
    try:
        with open('backend/main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # services/auth_service import가 제거되었는지 확인
        services_auth_import = 'from services.auth_service import' in content
        
        if not services_auth_import:
            print("✅ services/auth_service import 제거 완료")
            return True
        else:
            print("❌ services/auth_service import 여전히 존재")
            return False
    except Exception as e:
        print(f"❌ import 문 검사 오류: {e}")
        return False

if __name__ == "__main__":
    print("=== 구문 검사 테스트 ===")
    
    tests = [
        ("main.py 구문", test_main_py_syntax),
        ("중복 함수", test_duplicate_functions),
        ("import 문", test_import_statements),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    print("\n=== 결과 ===")
    all_passed = all(result for _, result in results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{name}: {status}")
    
    if all_passed:
        print("\n🎉 모든 구문 검사 통과!")
    else:
        print("\n❌ 일부 검사 실패")