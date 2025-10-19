#!/usr/bin/env python3
"""
관리자 재스캔 기능 테스트
- /scan/historical API의 save_snapshot 파라미터 테스트
- DB 저장 확인
- 날짜 형식 검증
"""

import requests
import sqlite3
import json
import os
from datetime import datetime, timedelta

# 테스트 설정
BASE_URL = "http://localhost:8010"
DB_PATH = "snapshots.db"

def test_historical_scan_with_save():
    """과거 스캔 API의 save_snapshot 파라미터 테스트"""
    print("🧪 테스트 1: /scan/historical API save_snapshot 파라미터")
    
    # 테스트 날짜 (거래일)
    test_date = "20251001"
    
    try:
        # save_snapshot=True로 호출
        response = requests.get(f"{BASE_URL}/scan/historical?date={test_date}&save_snapshot=true", timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API 호출 성공")
            print(f"   - 매칭된 종목 수: {data.get('matched_count', 0)}")
            print(f"   - 스캔 날짜: {data.get('as_of', 'N/A')}")
            return True
        else:
            print(f"❌ API 호출 실패: HTTP {response.status_code}")
            print(f"   응답: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ API 호출 오류: {e}")
        return False

def test_db_save():
    """DB에 데이터가 저장되었는지 확인"""
    print("\n🧪 테스트 2: DB 저장 확인")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ DB 파일이 존재하지 않습니다: {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # 최신 스캔 날짜 조회
        cur.execute("SELECT MAX(date) FROM scan_rank")
        latest_date = cur.fetchone()[0]
        
        if not latest_date:
            print("❌ DB에 스캔 데이터가 없습니다")
            conn.close()
            return False
        
        print(f"✅ 최신 스캔 날짜: {latest_date}")
        
        # 해당 날짜의 데이터 수 조회
        cur.execute("SELECT COUNT(*) FROM scan_rank WHERE date = ?", (latest_date,))
        count = cur.fetchone()[0]
        
        print(f"✅ 저장된 종목 수: {count}개")
        
        # 샘플 데이터 조회
        cur.execute("""
            SELECT code, name, score, close_price 
            FROM scan_rank 
            WHERE date = ? 
            ORDER BY score DESC 
            LIMIT 3
        """, (latest_date,))
        
        samples = cur.fetchall()
        print("✅ 상위 3개 종목:")
        for code, name, score, price in samples:
            print(f"   - {code}: {name} (점수: {score}, 가격: {price})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ DB 확인 오류: {e}")
        return False

def test_date_format():
    """날짜 형식 검증 테스트"""
    print("\n🧪 테스트 3: 날짜 형식 검증")
    
    test_cases = [
        ("20251001", True, "올바른 YYYYMMDD 형식"),
        ("2025-10-01", False, "YYYY-MM-DD 형식 (API에서 거부되어야 함)"),
        ("2025101", False, "잘못된 형식 (8자리 아님)"),
        ("20251301", False, "잘못된 월 (13월)"),
        ("20251032", False, "잘못된 일 (32일)")
    ]
    
    results = []
    
    for date_str, should_succeed, description in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/scan/historical?date={date_str}&save_snapshot=false", timeout=30)
            
            if should_succeed:
                if response.status_code == 200:
                    print(f"✅ {description}: 성공")
                    results.append(True)
                else:
                    print(f"❌ {description}: 실패 (HTTP {response.status_code})")
                    results.append(False)
            else:
                if response.status_code != 200:
                    print(f"✅ {description}: 예상대로 실패")
                    results.append(True)
                else:
                    print(f"❌ {description}: 예상과 달리 성공")
                    results.append(False)
                    
        except Exception as e:
            print(f"❌ {description}: 오류 - {e}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n📊 날짜 형식 검증 성공률: {success_rate:.1f}%")
    return success_rate >= 80

def test_save_snapshot_parameter():
    """save_snapshot 파라미터 동작 테스트"""
    print("\n🧪 테스트 4: save_snapshot 파라미터 동작")
    
    test_date = "20251001"
    
    # save_snapshot=False로 호출
    try:
        response1 = requests.get(f"{BASE_URL}/scan/historical?date={test_date}&save_snapshot=false", timeout=60)
        
        if response1.status_code == 200:
            print("✅ save_snapshot=False 호출 성공")
        else:
            print(f"❌ save_snapshot=False 호출 실패: HTTP {response1.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ save_snapshot=False 호출 오류: {e}")
        return False
    
    # save_snapshot=True로 호출
    try:
        response2 = requests.get(f"{BASE_URL}/scan/historical?date={test_date}&save_snapshot=true", timeout=60)
        
        if response2.status_code == 200:
            print("✅ save_snapshot=True 호출 성공")
        else:
            print(f"❌ save_snapshot=True 호출 실패: HTTP {response2.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ save_snapshot=True 호출 오류: {e}")
        return False
    
    # 두 응답이 동일한지 확인 (데이터는 같아야 함)
    if response1.json() == response2.json():
        print("✅ save_snapshot 파라미터와 관계없이 동일한 데이터 반환")
        return True
    else:
        print("❌ save_snapshot 파라미터에 따라 다른 데이터 반환")
        return False

def test_backend_health():
    """백엔드 서버 상태 확인"""
    print("🧪 테스트 0: 백엔드 서버 상태 확인")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 백엔드 서버 정상: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ 백엔드 서버 오류: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 백엔드 서버 연결 실패: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("🚀 관리자 재스캔 기능 테스트 시작\n")
    
    # 백엔드 서버 상태 확인
    if not test_backend_health():
        print("\n❌ 백엔드 서버가 실행되지 않았습니다. 먼저 서버를 시작해주세요.")
        return
    
    # 테스트 실행
    tests = [
        test_historical_scan_with_save,
        test_db_save,
        test_date_format,
        test_save_snapshot_parameter
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ 테스트 실행 오류: {e}")
            results.append(False)
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 테스트 결과 요약")
    print("="*50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ 통과: {passed}/{total}")
    print(f"❌ 실패: {total - passed}/{total}")
    print(f"📈 성공률: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 모든 테스트가 통과했습니다!")
    else:
        print(f"\n⚠️  {total - passed}개의 테스트가 실패했습니다.")

if __name__ == "__main__":
    main()







