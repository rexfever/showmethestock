#!/bin/bash

# 개발 환경 모니터링 스크립트
# 사용법: ./dev-monitor.sh [명령어]

# 서버 설정
SERVER_IP="52.79.145.238"
SERVER_USER="ubuntu"
SERVER_PATH="/home/ubuntu/showmethestock"

# SSH 연결 옵션 (타임아웃 개선)
SSH_OPTS="-o ConnectTimeout=30 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -o TCPKeepAlive=yes"

# 모니터링 설정
CHECK_INTERVAL=60  # 60초마다 확인
LOG_FILE="dev-monitor.log"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# 로컬 상태 확인
check_local_health() {
    local status="OK"
    local issues=()
    
    # 1. 백엔드 상태 확인
    local backend_count=$(ps aux | grep 'uvicorn main:app' | grep -v grep | wc -l)
    if [ "$backend_count" -eq 0 ]; then
        issues+=("로컬 백엔드 중지됨")
        status="ERROR"
    fi
    
    # 2. 프론트엔드 상태 확인
    local frontend_count=$(ps aux | grep 'next dev' | grep -v grep | wc -l)
    if [ "$frontend_count" -eq 0 ]; then
        issues+=("로컬 프론트엔드 중지됨")
        status="ERROR"
    fi
    
    # 3. 로컬 API 확인
    if ! curl -s http://localhost:8010/ > /dev/null 2>&1; then
        issues+=("로컬 백엔드 API 응답 없음")
        status="ERROR"
    fi
    
    # 4. 로컬 프론트엔드 확인
    if ! curl -s http://localhost:3000/ > /dev/null 2>&1; then
        issues+=("로컬 프론트엔드 응답 없음")
        status="ERROR"
    fi
    
    # 결과 출력
    if [ "$status" = "OK" ]; then
        log_message "로컬 환경: 정상"
    else
        log_message "로컬 환경: $status - ${issues[*]}"
    fi
}

# 서버 상태 확인
check_server_health() {
    local status="OK"
    local issues=()
    
    # 1. SSH 연결 확인
    if ! ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "echo 'SSH OK'" > /dev/null 2>&1; then
        issues+=("서버 SSH 연결 실패")
        status="ERROR"
    fi
    
    # 2. 서버 백엔드 상태 확인
    local backend_count=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "ps aux | grep 'uvicorn main:app' | grep -v grep | wc -l" 2>/dev/null)
    if [ "$backend_count" -eq 0 ]; then
        issues+=("서버 백엔드 중지됨")
        status="ERROR"
    fi
    
    # 3. 서버 프론트엔드 상태 확인
    local frontend_count=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "ps aux | grep 'next' | grep -v grep | wc -l" 2>/dev/null)
    if [ "$frontend_count" -eq 0 ]; then
        issues+=("서버 프론트엔드 중지됨")
        status="ERROR"
    fi
    
    # 4. 웹 서비스 확인
    local web_status=$(curl -s -o /dev/null -w "%{http_code}" https://sohntech.ai.kr 2>/dev/null)
    if [ "$web_status" != "200" ]; then
        issues+=("웹 서비스 오류 (HTTP $web_status)")
        status="ERROR"
    fi
    
    # 5. 서버 리소스 확인
    local disk_usage=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "df / | tail -1 | awk '{print \$5}' | sed 's/%//'" 2>/dev/null)
    if [ "$disk_usage" -gt 80 ]; then
        issues+=("서버 디스크 사용량 높음 (${disk_usage}%)")
        status="WARNING"
    fi
    
    local memory_usage=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "free | grep Mem | awk '{printf \"%.0f\", \$3/\$2 * 100.0}'" 2>/dev/null)
    if [ "$memory_usage" -gt 90 ]; then
        issues+=("서버 메모리 사용량 높음 (${memory_usage}%)")
        status="WARNING"
    fi
    
    # 결과 출력
    if [ "$status" = "OK" ]; then
        log_message "서버 환경: 정상"
    else
        log_message "서버 환경: $status - ${issues[*]}"
        
        # 문제 발생 시 자동 복구 시도
        if [ "$status" = "ERROR" ]; then
            log_message "서버 자동 복구 시도 중..."
            ./dev-server.sh restart
        fi
    fi
}

# 전체 상태 확인
check_all() {
    log_message "=== 개발 환경 상태 확인 ==="
    check_local_health
    check_server_health
    log_message "=== 확인 완료 ==="
}

# 지속적 모니터링
start_monitoring() {
    log_message "개발 환경 모니터링 시작 (${CHECK_INTERVAL}초 간격)"
    
    while true; do
        check_all
        sleep $CHECK_INTERVAL
    done
}

# 실시간 로그 모니터링
monitor_logs() {
    log_message "실시간 로그 모니터링 시작 (Ctrl+C로 종료)"
    
    # 로컬과 서버 로그를 동시에 모니터링
    if [ -f "backend/backend.log" ] && [ -f "frontend/frontend.log" ]; then
        # 로컬 로그 모니터링
        tail -f backend/backend.log frontend/frontend.log &
        LOCAL_PID=$!
        
        # 서버 로그 모니터링
        ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $SERVER_PATH && tail -f backend/backend.log frontend/frontend.log" &
        SERVER_PID=$!
        
        # 종료 시 정리
        trap "kill $LOCAL_PID $SERVER_PID 2>/dev/null; exit" INT
        wait
    else
        log_message "로그 파일을 찾을 수 없습니다"
    fi
}

# 상태 요약
show_summary() {
    echo "=== 개발 환경 상태 요약 ==="
    echo ""
    
    # 로컬 상태
    echo "🖥️  로컬 환경:"
    if ps aux | grep 'uvicorn main:app' | grep -v grep > /dev/null; then
        echo "  ✅ 백엔드: 실행 중 (포트 8010)"
    else
        echo "  ❌ 백엔드: 중지됨"
    fi
    
    if ps aux | grep 'next dev' | grep -v grep > /dev/null; then
        echo "  ✅ 프론트엔드: 실행 중 (포트 3000)"
    else
        echo "  ❌ 프론트엔드: 중지됨"
    fi
    
    echo ""
    
    # 서버 상태
    echo "🌐 서버 환경:"
    BACKEND_STATUS=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "ps aux | grep 'uvicorn main:app' | grep -v grep | wc -l" 2>/dev/null)
    if [ "$BACKEND_STATUS" -gt 0 ]; then
        echo "  ✅ 백엔드: 실행 중"
    else
        echo "  ❌ 백엔드: 중지됨"
    fi
    
    FRONTEND_STATUS=$(ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "ps aux | grep 'next' | grep -v grep | wc -l" 2>/dev/null)
    if [ "$FRONTEND_STATUS" -gt 0 ]; then
        echo "  ✅ 프론트엔드: 실행 중"
    else
        echo "  ❌ 프론트엔드: 중지됨"
    fi
    
    WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://sohntech.ai.kr 2>/dev/null)
    if [ "$WEB_STATUS" = "200" ]; then
        echo "  ✅ 웹 서비스: 정상 (HTTP $WEB_STATUS)"
    else
        echo "  ❌ 웹 서비스: 오류 (HTTP $WEB_STATUS)"
    fi
    
    echo ""
    echo "📋 관리 명령어:"
    echo "  ./local.sh status    - 로컬 상태 확인"
    echo "  ./server.sh status   - 서버 상태 확인"
    echo "  ./local.sh start     - 로컬 시작"
    echo "  ./server.sh start    - 서버 시작"
}

# 도움말
show_help() {
    echo "개발 환경 모니터링 스크립트"
    echo ""
    echo "사용법: $0 [명령어]"
    echo ""
    echo "명령어:"
    echo "  check       - 일회성 상태 확인"
    echo "  start       - 지속적 모니터링 시작"
    echo "  logs        - 실시간 로그 모니터링"
    echo "  summary     - 상태 요약 표시"
    echo "  help        - 도움말 표시"
}

# 메인 로직
case "$1" in
    "check")
        check_all
        ;;
    "start")
        start_monitoring
        ;;
    "logs")
        monitor_logs
        ;;
    "summary")
        show_summary
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        echo "알 수 없는 옵션: $1"
        show_help
        exit 1
        ;;
esac
