#!/usr/bin/env python3
"""
API 엔드포인트 중복 제거 테스트
"""

import requests
import json

BASE_URL = "http://localhost:8010"

def test_scan_positions():
    """scan_positions 엔드포인트 테스트"""
    try:
        response = requests.get(f"{BASE_URL}/scan_positions")
        print(f"GET /scan_positions: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  - 응답: {data.get('count', 0)}개 포지션")
        else:
            print(f"  - 오류: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"GET /scan_positions 오류: {e}")
        return False

def test_auto_add_positions():
    """auto_add_positions 엔드포인트 테스트"""
    try:
        response = requests.post(f"{BASE_URL}/auto_add_positions", 
                               params={"score_threshold": 10, "default_quantity": 1})
        print(f"POST /auto_add_positions: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  - 응답: {data.get('added_count', 0)}개 포지션 추가")
        else:
            print(f"  - 오류: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"POST /auto_add_positions 오류: {e}")
        return False

def test_server_health():
    """서버 상태 확인"""
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"GET /: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  - 서버 상태: {data.get('status')}")
        return response.status_code == 200
    except Exception as e:
        print(f"서버 연결 오류: {e}")
        return False

if __name__ == "__main__":
    print("=== API 엔드포인트 중복 제거 테스트 ===")
    
    # 서버 상태 확인
    if not test_server_health():
        print("❌ 서버가 실행되지 않았습니다. 먼저 서버를 시작하세요.")
        exit(1)
    
    # 테스트 실행
    results = []
    results.append(("scan_positions", test_scan_positions()))
    results.append(("auto_add_positions", test_auto_add_positions()))
    
    # 결과 출력
    print("\n=== 테스트 결과 ===")
    all_passed = True
    for test_name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 모든 테스트가 통과했습니다!")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다.")