#!/usr/bin/env python3
"""
자동화 모니터링 스크립트
파일 변경 감지 시 자동으로 테스트 실행
"""
import os
import time
import subprocess
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TestHandler(FileSystemEventHandler):
    """파일 변경 감지 핸들러"""
    
    def __init__(self):
        self.last_test_time = 0
        self.test_cooldown = 5  # 5초 쿨다운
    
    def on_modified(self, event):
        """파일 수정 감지"""
        if event.is_directory:
            return
        
        # Python 파일만 감지
        if not event.src_path.endswith('.py'):
            return
        
        # 백엔드 관련 파일만 감지
        if not any(keyword in event.src_path for keyword in ['main.py', 'scanner.py', 'config.py']):
            return
        
        current_time = time.time()
        if current_time - self.last_test_time < self.test_cooldown:
            return
        
        self.last_test_time = current_time
        
        print(f"\n🔍 **파일 변경 감지**: {event.src_path}")
        print("=" * 50)
        
        # 테스트 실행
        self.run_tests()
    
    def run_tests(self):
        """테스트 실행"""
        print("🧪 **자동 테스트 실행**")
        print("===================")
        
        try:
            # 테스트 실행
            result = subprocess.run([
                sys.executable, "run_tests.py"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ **모든 테스트 통과!**")
            else:
                print("❌ **테스트 실패**")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
        except subprocess.TimeoutExpired:
            print("⏰ **테스트 시간 초과**")
        except Exception as e:
            print(f"❌ **테스트 실행 오류**: {e}")

def main():
    """메인 함수"""
    print("🔍 **자동화 모니터링 시작**")
    print("========================")
    print("백엔드 파일 변경 감지 중...")
    print("Ctrl+C로 종료")
    
    # 모니터링 대상 디렉토리
    watch_directory = ".."
    
    # 이벤트 핸들러 생성
    event_handler = TestHandler()
    observer = Observer()
    observer.schedule(event_handler, watch_directory, recursive=False)
    
    try:
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 모니터링 중단")
        observer.stop()
    
    observer.join()

if __name__ == '__main__':
    main()
