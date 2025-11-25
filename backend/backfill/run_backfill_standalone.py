#!/usr/bin/env python3
"""
독립 실행용 백필 스크립트
- PYTHONPATH 설정 없이 직접 실행 가능
- 상위 디렉토리 모듈 자동 import
"""
import os
import sys
from pathlib import Path

# 백엔드 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 이제 안전하게 import 가능
try:
    from backfill.backfill_runner import main
except ImportError:
    from backfill_runner import main

if __name__ == '__main__':
    main()