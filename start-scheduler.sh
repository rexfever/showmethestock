#!/bin/bash

# 스케줄러 실행 스크립트
echo "⏰ 스케줄러 시작 중..."

# 프로젝트 루트로 이동
cd "$(dirname "$0")"

# 백엔드 디렉토리로 이동
cd backend

# 가상환경 활성화
source venv/bin/activate

# 스케줄러 실행
echo "스케줄러를 시작합니다..."
python scheduler.py
