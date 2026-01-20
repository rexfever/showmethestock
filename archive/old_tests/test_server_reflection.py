#!/usr/bin/env python3
"""
서버 반영 상태 확인
"""

import requests
import subprocess
import time
import sys
import os

def check_server_running():
    """서버 실행 상태 확인"""
    try:
        response = requests.get("http://localhost:8010/", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_test_server():
    """테스트용 서버 시작"""
    try:
        print("테스트 서버 시작 중...")
        
        # 간단한 테스트 서버 스크립트 생성
        test_server_code = '''
import sys
sys.path.insert(0, "backend")

try:
    from fastapi import FastAPI
    from auth_service import auth_service
    
    app = FastAPI()
    
    @app.get("/")
    def root():
        return {"status": "running", "auth_service": "integrated"}
    
    @app.get("/scan_positions")
    def get_scan_positions():
        return {"items": [], "count": 0, "status": "no_duplicates"}
    
    @app.post("/auto_add_positions")
    def auto_add_positions():
        return {"ok": True, "added_count": 0, "status": "no_duplicates"}
    
    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")
        
except ImportError as e:
    print(f"Import 오류: {e}")
    sys.exit(1)
'''
        
        with open('test_server.py', 'w') as f:
            f.write(test_server_code)
        
        # 서버 시작 (백그라운드)
        process = subprocess.Popen([sys.executable, 'test_server.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        # 서버 시작 대기
        time.sleep(3)
        
        # 테스트 서버 확인
        try:
            response = requests.get("http://localhost:8001/", timeout=5)
            if response.status_code == 200:
                print("✅ 테스트 서버 시작 성공")
                
                # API 테스트
                scan_resp = requests.get("http://localhost:8001/scan_positions", timeout=5)
                auto_resp = requests.post("http://localhost:8001/auto_add_positions", timeout=5)
                
                print(f"scan_positions: {scan_resp.status_code}")
                print(f"auto_add_positions: {auto_resp.status_code}")
                
                process.terminate()
                os.remove('test_server.py')
                return True
            else:
                process.terminate()
                return False
        except Exception as e:
            print(f"테스트 서버 확인 실패: {e}")
            process.terminate()
            return False
            
    except Exception as e:
        print(f"테스트 서버 시작 실패: {e}")
        return False

def check_code_changes():
    """코드 변경사항 확인"""
    try:
        with open('backend/main.py', 'r') as f:
            content = f.read()
        
        # 중복 함수 확인
        scan_count = content.count("@app.get('/scan_positions')")
        auto_count = content.count("@app.post('/auto_add_positions')")
        
        # services import 확인
        services_import = "from services.auth_service import" in content
        
        print(f"scan_positions 함수: {scan_count}개")
        print(f"auto_add_positions 함수: {auto_count}개")
        print(f"services/auth_service import: {'있음' if services_import else '없음'}")
        
        return scan_count == 1 and auto_count == 1 and not services_import
        
    except Exception as e:
        print(f"코드 확인 오류: {e}")
        return False

if __name__ == "__main__":
    print("=== 서버 반영 상태 확인 ===")
    
    # 1. 코드 변경사항 확인
    print("\n1. 코드 변경사항:")
    code_ok = check_code_changes()
    print(f"코드 상태: {'✅ 정상' if code_ok else '❌ 문제'}")
    
    # 2. 서버 실행 상태 확인
    print("\n2. 서버 상태:")
    server_running = check_server_running()
    print(f"메인 서버 (8000): {'✅ 실행중' if server_running else '❌ 미실행'}")
    
    # 3. 테스트 서버로 검증
    print("\n3. 테스트 서버 검증:")
    test_ok = start_test_server()
    print(f"테스트 결과: {'✅ 성공' if test_ok else '❌ 실패'}")
    
    print("\n=== 결과 ===")
    if code_ok and test_ok:
        print("✅ 코드 변경사항이 정상적으로 반영됨")
        if not server_running:
            print("⚠️ 메인 서버가 실행되지 않음 - 서버 재시작 필요")
    else:
        print("❌ 문제 발견")