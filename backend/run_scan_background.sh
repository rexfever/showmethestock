#!/bin/bash

# 2025년 1월-8월 V2 스캔 백그라운드 실행 스크립트
# SSH 연결이 끊어져도 계속 실행되도록 nohup 사용

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/scan_2025_jan_aug_v2.log"
PID_FILE="$SCRIPT_DIR/scan_2025_jan_aug_v2.pid"

echo "🚀 2025년 1월-8월 V2 스캔 백그라운드 실행 시작"
echo "📁 작업 디렉토리: $SCRIPT_DIR"
echo "📝 로그 파일: $LOG_FILE"
echo "🆔 PID 파일: $PID_FILE"

# 기존 프로세스 확인
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  기존 프로세스가 실행 중입니다 (PID: $OLD_PID)"
        echo "종료하려면 'kill $OLD_PID' 실행"
        exit 1
    else
        echo "🧹 기존 PID 파일 정리"
        rm -f "$PID_FILE"
    fi
fi

# 백그라운드에서 실행
echo "▶️  백그라운드 실행 시작..."
nohup python3 "$SCRIPT_DIR/scan_2025_jan_aug_v2.py" > "$LOG_FILE" 2>&1 &
PID=$!

# PID 저장
echo "$PID" > "$PID_FILE"

echo "✅ 백그라운드 실행 시작됨 (PID: $PID)"
echo "📊 진행 상황 확인: tail -f $LOG_FILE"
echo "🛑 중지: kill $PID"
echo "📋 상태 확인: ps -p $PID"

# 잠시 후 프로세스 상태 확인
sleep 2
if ps -p "$PID" > /dev/null 2>&1; then
    echo "🟢 프로세스 정상 실행 중"
else
    echo "🔴 프로세스 시작 실패"
    rm -f "$PID_FILE"
    exit 1
fi