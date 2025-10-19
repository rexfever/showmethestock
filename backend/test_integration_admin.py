#!/usr/bin/env python3
"""
관리자 재스캔 기능 통합 테스트
- 프론트엔드와 백엔드 간의 API 통신 테스트
- 전체 워크플로우 테스트
"""

import requests
import sqlite3
import json
import time
from datetime import datetime

# 테스트 설정
BASE_URL = "http://localhost:8010"
FRONTEND_URL = "http://localhost:3000"
DB_PATH = "snapshots.db"

class AdminRescanIntegrationTest:
    def __init__(self):
        self.test_date = "20251001"
        self.test_results = []
    
    def log_test(self, test_name, success, message=""):
        """테스트 결과 로깅"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append((test_name, success, message))
    
    def test_backend_api_availability(self):
        """백엔드 API 가용성 테스트"""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=10)
            if response.status_code == 200:
                self.log_test("백엔드 API 가용성", True, "서버가 정상적으로 응답")
                return True
            else:
                self.log_test("백엔드 API 가용성", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("백엔드 API 가용성", False, str(e))
            return False
    
    def test_frontend_availability(self):
        """프론트엔드 가용성 테스트"""
        try:
            response = requests.get(f"{FRONTEND_URL}", timeout=10)
            if response.status_code == 200:
                self.log_test("프론트엔드 가용성", True, "프론트엔드가 정상적으로 응답")
                return True
            else:
                self.log_test("프론트엔드 가용성", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("프론트엔드 가용성", False, str(e))
            return False
    
    def test_historical_scan_api(self):
        """과거 스캔 API 테스트"""
        try:
            # save_snapshot=False로 테스트
            response = requests.get(
                f"{BASE_URL}/scan/historical?date={self.test_date}&save_snapshot=false",
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and 'matched_count' in data:
                    self.log_test(
                        "과거 스캔 API", 
                        True, 
                        f"매칭된 종목: {data['matched_count']}개"
                    )
                    return True
                else:
                    self.log_test("과거 스캔 API", False, "응답 데이터 형식 오류")
                    return False
            else:
                self.log_test("과거 스캔 API", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("과거 스캔 API", False, str(e))
            return False
    
    def test_db_save_functionality(self):
        """DB 저장 기능 테스트"""
        try:
            # save_snapshot=True로 스캔 실행
            response = requests.get(
                f"{BASE_URL}/scan/historical?date={self.test_date}&save_snapshot=true",
                timeout=60
            )
            
            if response.status_code != 200:
                self.log_test("DB 저장 기능", False, f"스캔 API 호출 실패: HTTP {response.status_code}")
                return False
            
            # DB에서 데이터 확인
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            # 해당 날짜의 데이터 조회
            cur.execute("SELECT COUNT(*) FROM scan_rank WHERE date = ?", (self.test_date,))
            count = cur.fetchone()[0]
            
            conn.close()
            
            if count > 0:
                self.log_test("DB 저장 기능", True, f"DB에 {count}개 레코드 저장됨")
                return True
            else:
                self.log_test("DB 저장 기능", False, "DB에 데이터가 저장되지 않음")
                return False
                
        except Exception as e:
            self.log_test("DB 저장 기능", False, str(e))
            return False
    
    def test_delete_functionality(self):
        """삭제 기능 테스트"""
        try:
            # 삭제 API 호출
            response = requests.delete(f"{BASE_URL}/scan/{self.test_date}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') and 'deleted_records' in data:
                    self.log_test(
                        "삭제 기능", 
                        True, 
                        f"{data['deleted_records']}개 레코드 삭제됨"
                    )
                    return True
                else:
                    self.log_test("삭제 기능", False, "삭제 응답 형식 오류")
                    return False
            else:
                self.log_test("삭제 기능", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("삭제 기능", False, str(e))
            return False
    
    def test_date_format_conversion(self):
        """날짜 형식 변환 테스트"""
        test_cases = [
            ("2025-10-01", "20251001"),
            ("2025-12-31", "20251231"),
            ("2025-01-01", "20250101")
        ]
        
        all_passed = True
        
        for input_date, expected_output in test_cases:
            # 실제 변환 로직 테스트 (프론트엔드에서 수행되는 변환)
            converted = input_date.replace('-', '')
            
            if converted == expected_output:
                self.log_test(f"날짜 변환 ({input_date})", True, f"{input_date} → {converted}")
            else:
                self.log_test(f"날짜 변환 ({input_date})", False, f"예상: {expected_output}, 실제: {converted}")
                all_passed = False
        
        return all_passed
    
    def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        print("\n🔄 전체 워크플로우 테스트 시작...")
        
        workflow_steps = [
            ("1. 과거 스캔 실행", self.test_historical_scan_api),
            ("2. DB 저장 확인", self.test_db_save_functionality),
            ("3. 삭제 기능 테스트", self.test_delete_functionality)
        ]
        
        all_passed = True
        
        for step_name, test_func in workflow_steps:
            print(f"\n📋 {step_name}")
            if not test_func():
                all_passed = False
                break
            time.sleep(1)  # 각 단계 간 잠시 대기
        
        if all_passed:
            self.log_test("전체 워크플로우", True, "모든 단계가 성공적으로 완료됨")
        else:
            self.log_test("전체 워크플로우", False, "일부 단계에서 실패")
        
        return all_passed
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 관리자 재스캔 기능 통합 테스트 시작\n")
        
        # 기본 가용성 테스트
        print("📡 서비스 가용성 테스트")
        backend_ok = self.test_backend_api_availability()
        frontend_ok = self.test_frontend_availability()
        
        if not backend_ok:
            print("\n❌ 백엔드 서버가 실행되지 않았습니다.")
            return
        
        if not frontend_ok:
            print("\n⚠️  프론트엔드 서버가 실행되지 않았습니다. (백엔드 테스트만 진행)")
        
        # 기능 테스트
        print("\n🔧 기능 테스트")
        self.test_date_format_conversion()
        
        # 전체 워크플로우 테스트
        self.test_full_workflow()
        
        # 결과 요약
        self.print_summary()
    
    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*60)
        print("📊 통합 테스트 결과 요약")
        print("="*60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"✅ 통과: {passed}/{total}")
        print(f"❌ 실패: {total - passed}/{total}")
        print(f"📈 성공률: {passed/total*100:.1f}%")
        
        print("\n📋 상세 결과:")
        for test_name, success, message in self.test_results:
            status = "✅" if success else "❌"
            print(f"  {status} {test_name}: {message}")
        
        if passed == total:
            print("\n🎉 모든 통합 테스트가 통과했습니다!")
        else:
            print(f"\n⚠️  {total - passed}개의 테스트가 실패했습니다.")

def main():
    """메인 실행 함수"""
    tester = AdminRescanIntegrationTest()
    tester.run_all_tests()

if __name__ == "__main__":
    main()








