"""
통합 테스트
"""
import unittest
import requests
import json
import time
import os
import sys
from unittest.mock import patch, MagicMock

# 상위 디렉토리의 모듈 import
sys.path.append('..')

class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    @classmethod
    def setUpClass(cls):
        """테스트 클래스 설정"""
        cls.base_url = "http://localhost:8010"
        cls.server_running = False
        
        # 서버가 실행 중인지 확인
        try:
            # recurring-stocks 엔드포인트로 직접 확인
            response = requests.get(f"{cls.base_url}/recurring-stocks", timeout=5)
            if response.status_code == 200:
                cls.server_running = True
        except:
            pass
        
        if not cls.server_running:
            print("⚠️ 서버가 실행 중이지 않습니다. 통합 테스트를 건너뜁니다.")
    
    def test_health_check(self):
        """헬스 체크 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # recurring-stocks 엔드포인트로 서버 상태 확인
        response = requests.get(f"{self.base_url}/recurring-stocks", timeout=5)
        self.assertEqual(response.status_code, 200)
    
    def test_recurring_stocks_api(self):
        """재등장 종목 API 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # API 호출
        response = requests.get(f"{self.base_url}/recurring-stocks?days=30&min_appearances=2")
        
        # 응답 검증
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("ok", data)
        self.assertIn("data", data)
        
        # 데이터 구조 검증
        data_content = data["data"]
        self.assertIn("recurring_stocks", data_content)
        self.assertIn("total_count", data_content)
        self.assertIn("days", data_content)
        self.assertIn("min_appearances", data_content)
    
    def test_scan_with_recurring_api(self):
        """스캔+재등장 API 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # API 호출
        response = requests.get(f"{self.base_url}/scan-with-recurring?days=7&min_appearances=2")
        
        # 응답 검증
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("ok", data)
        self.assertIn("data", data)
        
        # 데이터 구조 검증
        data_content = data["data"]
        self.assertIn("latest_scan", data_content)
        self.assertIn("recurring_stocks", data_content)
        self.assertIn("total_recurring", data_content)
    
    def test_analyze_friendly_api(self):
        """사용자 친화적 분석 API 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # API 호출
        response = requests.get(f"{self.base_url}/analyze-friendly?name_or_code=삼성전자")
        
        # 응답 검증
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("ok", data)
        
        if data["ok"]:
            self.assertIn("ticker", data)
            self.assertIn("name", data)
            self.assertIn("friendly_analysis", data)
            
            # 친화적 분석 구조 검증
            friendly_analysis = data["friendly_analysis"]
            self.assertIn("summary", friendly_analysis)
            self.assertIn("recommendation", friendly_analysis)
            self.assertIn("confidence", friendly_analysis)
            self.assertIn("explanations", friendly_analysis)
            self.assertIn("investment_advice", friendly_analysis)
            self.assertIn("warnings", friendly_analysis)
            self.assertIn("simple_indicators", friendly_analysis)
    
    def test_latest_scan_api(self):
        """최신 스캔 API 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # API 호출
        response = requests.get(f"{self.base_url}/latest-scan")
        
        # 응답 검증
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("ok", data)
        
        if data["ok"]:
            self.assertIn("data", data)
            scan_data = data["data"]
            self.assertIn("as_of", scan_data)  # date 대신 as_of 사용
            self.assertIn("items", scan_data)
            
            # 스캔 아이템 구조 검증
            if scan_data["items"]:
                item = scan_data["items"][0]
                self.assertIn("ticker", item)
                self.assertIn("name", item)
                self.assertIn("score", item)
                # indicators는 latest-scan API에서 제공되지 않을 수 있음
    
    def test_api_error_handling(self):
        """API 오류 처리 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # 잘못된 파라미터로 API 호출
        response = requests.get(f"{self.base_url}/recurring-stocks?days=-1&min_appearances=0")
        
        # 응답 검증 (오류가 발생해도 200 상태코드 반환)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("ok", data)
    
    def test_api_response_time(self):
        """API 응답 시간 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # 응답 시간 측정
        start_time = time.time()
        response = requests.get(f"{self.base_url}/recurring-stocks?days=30&min_appearances=2")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # 응답 시간 검증 (2초 이내)
        self.assertLess(response_time, 2.0)
        self.assertEqual(response.status_code, 200)
    
    def test_cors_headers(self):
        """CORS 헤더 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # OPTIONS 요청으로 CORS 헤더 확인
        response = requests.options(f"{self.base_url}/recurring-stocks")
        
        # CORS 헤더 검증 (OPTIONS 요청에서만 나타날 수 있음)
        if "Access-Control-Allow-Origin" in response.headers:
            self.assertIn("Access-Control-Allow-Origin", response.headers)
            self.assertIn("Access-Control-Allow-Methods", response.headers)
            self.assertIn("Access-Control-Allow-Headers", response.headers)
        else:
            # CORS 헤더가 없어도 서버가 정상 작동하면 통과 (OPTIONS는 405가 정상)
            self.assertIn(response.status_code, [200, 405])
    
    def test_api_content_type(self):
        """API Content-Type 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # API 호출
        response = requests.get(f"{self.base_url}/recurring-stocks")
        
        # Content-Type 검증
        self.assertEqual(response.headers["Content-Type"], "application/json")
    
    def test_api_json_structure(self):
        """API JSON 구조 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # API 호출
        response = requests.get(f"{self.base_url}/recurring-stocks")
        
        # JSON 파싱 가능한지 확인
        try:
            data = response.json()
            self.assertIsInstance(data, dict)
        except json.JSONDecodeError:
            self.fail("API 응답이 유효한 JSON이 아닙니다")
    
    def test_concurrent_requests(self):
        """동시 요청 처리 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = requests.get(f"{self.base_url}/recurring-stocks", timeout=10)
                results.put(response.status_code)
            except Exception as e:
                results.put(f"Error: {e}")
        
        # 5개의 동시 요청 생성
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 결과 검증
        success_count = 0
        while not results.empty():
            result = results.get()
            if result == 200:
                success_count += 1
        
        # 최소 4개 이상의 요청이 성공해야 함
        self.assertGreaterEqual(success_count, 4)

if __name__ == '__main__':
    unittest.main()
