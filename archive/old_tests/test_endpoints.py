#!/usr/bin/env python3
"""
API 엔드포인트 테스트
"""

import requests
import json
import time

BASE_URL = "http://localhost:8010"

def test_server_health():
    """서버 상태 확인"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_scan_positions():
    """scan_positions 엔드포인트 테스트"""
    try:
        response = requests.get(f"{BASE_URL}/scan_positions", timeout=10)
        print(f"GET /scan_positions: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  응답: {data.get('count', 0)}개 포지션")
            return True
        return False
    except Exception as e:
        print(f"scan_positions 오류: {e}")
        return False

def test_auto_add_positions():
    """auto_add_positions 엔드포인트 테스트"""
    try:
        response = requests.post(f"{BASE_URL}/auto_add_positions", 
                               params={"score_threshold": 10, "default_quantity": 1},
                               timeout=15)
        print(f"POST /auto_add_positions: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  응답: {data.get('added_count', 0)}개 포지션 추가")
            return True
        return False
    except Exception as e:
        print(f"auto_add_positions 오류: {e}")
        return False

def test_environment():
    """environment 엔드포인트 테스트"""
    try:
        response = requests.get(f"{BASE_URL}/environment", timeout=5)
        print(f"GET /environment: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"environment 오류: {e}")
        return False

if __name__ == "__main__":
    print("=== API 엔드포인트 테스트 ===")
    
    if not test_server_health():
        print("❌ 서버가 실행되지 않았습니다")
        exit(1)
    
    tests = [
        ("environment", test_environment),
        ("scan_positions", test_scan_positions),
        ("auto_add_positions", test_auto_add_positions),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"{name} 테스트 오류: {e}")
            results.append((name, False))
    
    print("\n=== 테스트 결과 ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{name}: {status}")
    
    print(f"\n통과: {passed}/{total}")
    if passed == total:
        print("🎉 모든 테스트 통과!")
    else:
        print("⚠️ 일부 테스트 실패")