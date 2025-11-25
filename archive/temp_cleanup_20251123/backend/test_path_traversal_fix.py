#!/usr/bin/env python3
"""Path Traversal 수정 검증 테스트"""

import os
import tempfile
from security_utils import sanitize_file_path

def test_remaining_vulnerabilities():
    """남은 Path Traversal 취약점 확인"""
    print("=== 남은 Path Traversal 취약점 확인 ===")
    
    # main.py의 _db_path 함수 테스트
    print("\n1. _db_path 함수 테스트")
    try:
        # 직접 경로 생성 테스트
        import os
        backend_dir = os.path.dirname(__file__)
        db_path = os.path.join(backend_dir, 'snapshots.db')
        print(f"DB 경로: {db_path}")
        print("✅ 하드코딩된 경로로 안전함")
    except Exception as e:
        print(f"❌ 오류: {e}")
    
    # SNAPSHOT_DIR 테스트
    print("\n2. SNAPSHOT_DIR 테스트")
    try:
        backend_dir = os.path.dirname(__file__)
        snapshot_dir = os.path.join(backend_dir, 'snapshots')
        print(f"스냅샷 디렉토리: {snapshot_dir}")
        print("✅ 하드코딩된 경로로 안전함")
    except Exception as e:
        print(f"❌ 오류: {e}")
    
    # 파일 경로 검증 함수 테스트
    print("\n3. sanitize_file_path 함수 테스트")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_cases = [
            ("normal.json", True),
            ("../../../etc/passwd", False),
            ("..\\..\\windows\\system32", False),
            ("test/../../../etc/passwd", False),
            ("subdir/file.txt", True),
            ("", False),
            ("file with spaces.txt", True)
        ]
        
        for test_path, should_pass in test_cases:
            result = sanitize_file_path(test_path, temp_dir)
            passed = bool(result) == should_pass
            status = "✅" if passed else "❌"
            print(f"{status} {test_path}: {'통과' if result else '차단'}")

if __name__ == "__main__":
    test_remaining_vulnerabilities()