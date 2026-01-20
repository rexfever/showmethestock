#!/usr/bin/env python3
"""
스캐너 백테스트 테스트 실행 스크립트
"""
import sys
import subprocess
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """테스트 실행"""
    test_file = Path(__file__).parent / "test_scanner_backtest.py"
    
    print("=" * 80)
    print("스캐너 백테스트 상세 테스트 실행")
    print("=" * 80)
    print()
    
    # pytest 실행
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
        cwd=Path(__file__).parent.parent
    )
    
    print()
    print("=" * 80)
    if result.returncode == 0:
        print("✅ 모든 테스트 통과")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 80)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

