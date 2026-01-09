#!/usr/bin/env python3
"""
상태 평가 수동 실행 스크립트
"""
import sys
import os
import json
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.state_transition_service import evaluate_active_recommendations

if __name__ == '__main__':
    print("=" * 60)
    print("상태 평가 시작")
    print("=" * 60)
    
    # 오늘 날짜로 평가
    stats = evaluate_active_recommendations()
    
    print("\n" + "=" * 60)
    print("상태 평가 완료")
    print("=" * 60)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print("\n")


