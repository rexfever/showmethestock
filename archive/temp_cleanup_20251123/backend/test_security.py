#!/usr/bin/env python3
"""보안 취약점 테스트"""

import os
import tempfile
import shutil
from security_utils import sanitize_file_path, escape_html, sanitize_sql_input

def test_path_traversal_protection():
    """Path Traversal 방지 테스트"""
    print("=== Path Traversal 방지 테스트 ===")
    
    # 임시 디렉토리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"테스트 디렉토리: {temp_dir}")
        
        # 정상적인 파일 경로
        safe_paths = [
            "test.json",
            "scan-20251103.json",
            "subdir/file.txt"
        ]
        
        # 위험한 파일 경로
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "test/../../../etc/passwd",
            "test\\..\\..\\..\\windows\\system32\\config\\sam"
        ]
        
        print("\n--- 안전한 경로 테스트 ---")
        for path in safe_paths:
            result = sanitize_file_path(path, temp_dir)
            print(f"입력: {path}")
            print(f"결과: {result}")
            print(f"안전: {'✅' if result else '❌'}")
            print()
        
        print("--- 위험한 경로 테스트 ---")
        for path in dangerous_paths:
            result = sanitize_file_path(path, temp_dir)
            print(f"입력: {path}")
            print(f"결과: {result}")
            print(f"차단: {'✅' if not result else '❌ 위험!'}")
            print()

def test_xss_protection():
    """XSS 방지 테스트"""
    print("=== XSS 방지 테스트 ===")
    
    test_cases = [
        "정상 텍스트",
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "삼성전자 & LG전자",
        "<b>굵은 글씨</b>",
        "' OR 1=1 --",
        '"onclick="alert(\'XSS\')"'
    ]
    
    for test_input in test_cases:
        escaped = escape_html(test_input)
        print(f"입력: {test_input}")
        print(f"출력: {escaped}")
        print(f"안전: {'✅' if '<' not in escaped and '>' not in escaped else '⚠️'}")
        print()

def test_sql_injection_protection():
    """SQL 인젝션 방지 테스트"""
    print("=== SQL 인젝션 방지 테스트 ===")
    
    test_cases = [
        "정상 검색어",
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "admin'/*",
        "1' UNION SELECT * FROM users--",
        "삼성전자",
        "test@example.com"
    ]
    
    for test_input in test_cases:
        sanitized = sanitize_sql_input(test_input)
        print(f"입력: {test_input}")
        print(f"출력: {sanitized}")
        print(f"안전: {'✅' if not any(x in sanitized.lower() for x in ['drop', 'union', 'select', '--', ';']) else '⚠️'}")
        print()

def test_main_py_path_traversal():
    """main.py의 Path Traversal 취약점 테스트"""
    print("=== main.py Path Traversal 테스트 ===")
    
    # _db_path 함수 테스트
    from main import _db_path
    db_path = _db_path()
    print(f"DB 경로: {db_path}")
    print(f"안전한 경로: {'✅' if 'snapshots.db' in db_path else '❌'}")
    
    # SNAPSHOT_DIR 테스트
    from main import SNAPSHOT_DIR
    print(f"스냅샷 디렉토리: {SNAPSHOT_DIR}")
    print(f"안전한 디렉토리: {'✅' if 'snapshots' in SNAPSHOT_DIR else '❌'}")

if __name__ == "__main__":
    test_path_traversal_protection()
    test_xss_protection()
    test_sql_injection_protection()
    test_main_py_path_traversal()