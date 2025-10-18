#!/bin/bash
echo "🚀 백엔드 배포 시작"
cd backend
python3 -m py_compile main.py
pip3 install -r requirements.txt --quiet
pkill -f "python3.*main.py" || true
uvicorn main:app --host 0.0.0.0 --port 8010 --reload &
echo "✅ 백엔드 배포 완료"
