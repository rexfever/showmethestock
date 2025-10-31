#!/usr/bin/env python3
"""
main.py 파일 구문 검사
"""

import ast
import sys

def test_syntax():
    """Python 구문 검사"""
    try:
        with open('backend/main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # AST 파싱으로 구문 검사
        ast.parse(content)
        print("✅ 구문 검사 통과")
        return True
    except SyntaxError as e:
        print(f"❌ 구문 오류: {e}")
        print(f"   라인 {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ 파일 읽기 오류: {e}")
        return False

def count_functions():
    """함수 개수 확인"""
    import re
    
    try:
        with open('backend/main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        scan_positions = len(re.findall(r'@app\.get\(\'/scan_positions\'\)', content))
        auto_add_positions = len(re.findall(r'@app\.post\(\'/auto_add_positions\'\)', content))
        
        print(f"scan_positions 함수: {scan_positions}개")
        print(f"auto_add_positions 함수: {auto_add_positions}개")
        
        return scan_positions == 1 and auto_add_positions == 1
    except Exception as e:
        print(f"❌ 함수 개수 확인 오류: {e}")
        return False

if __name__ == "__main__":
    print("=== main.py 파일 검증 ===")
    
    syntax_ok = test_syntax()
    functions_ok = count_functions()
    
    if syntax_ok and functions_ok:
        print("\n🎉 모든 검증 통과!")
        sys.exit(0)
    else:
        print("\n❌ 검증 실패")
        sys.exit(1)