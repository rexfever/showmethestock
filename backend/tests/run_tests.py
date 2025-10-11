#!/usr/bin/env python3
"""
통합 테스트 실행 스크립트
"""
import unittest
import sys
import os
import subprocess
import time
import requests

def check_server_status():
    """서버 상태 확인"""
    try:
        response = requests.get("http://localhost:8010/recurring-stocks", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_server():
    """서버 시작"""
    print("🚀 서버 시작 중...")
    try:
        # 서버 시작
        process = subprocess.Popen([
            "python3", "-m", "uvicorn", "main:app", 
            "--host", "0.0.0.0", "--port", "8010", "--reload"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 서버 시작 대기
        for i in range(30):  # 30초 대기
            if check_server_status():
                print("✅ 서버 시작 완료")
                return process
            time.sleep(1)
        
        print("❌ 서버 시작 실패")
        process.terminate()
        return None
        
    except Exception as e:
        print(f"❌ 서버 시작 오류: {e}")
        return None

def run_tests():
    """테스트 실행"""
    print("🧪 테스트 실행 중...")
    
    # 테스트 디스커버리
    loader = unittest.TestLoader()
    start_dir = '.'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def main():
    """메인 함수"""
    print("🧪 **통합 테스트 시작**")
    print("=====================")
    
    # 서버 상태 확인
    if not check_server_status():
        print("⚠️ 서버가 실행 중이지 않습니다.")
        server_process = start_server()
        if not server_process:
            print("❌ 서버 시작 실패로 테스트를 중단합니다.")
            return False
    else:
        print("✅ 서버가 이미 실행 중입니다.")
        server_process = None
    
    try:
        # 테스트 실행
        success = run_tests()
        
        if success:
            print("\n🎯 **모든 테스트 통과!**")
            print("===================")
        else:
            print("\n❌ **일부 테스트 실패**")
            print("===================")
        
        return success
        
    finally:
        # 서버 정리
        if server_process:
            print("🔄 서버 종료 중...")
            server_process.terminate()
            server_process.wait()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
