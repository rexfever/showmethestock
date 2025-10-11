import unittest
import requests
import json
import time

class TestAPIEndpoints(unittest.TestCase):
    """API 엔드포인트 테스트"""
    
    @classmethod
    def setUpClass(cls):
        """테스트 클래스 설정"""
        cls.base_url = "http://localhost:8010"
        cls.server_running = False
        
        # 서버가 실행 중인지 확인
        try:
            response = requests.get(f"{cls.base_url}/recurring-stocks", timeout=5)
            cls.server_running = response.status_code == 200
        except:
            cls.server_running = False
    
    def test_recurring_stocks_endpoint(self):
        """재등장 종목 API 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # API 호출
        response = requests.get(f"{self.base_url}/recurring-stocks?days=30&min_appearances=2")
        
        # 응답 검증
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("ok", data)
        self.assertTrue(data["ok"])
        self.assertIn("data", data)
        
        # 데이터 구조 검증
        data_content = data["data"]
        self.assertIn("recurring_stocks", data_content)
        self.assertIn("total_count", data_content)
        self.assertIn("days", data_content)
        self.assertIn("min_appearances", data_content)
        
        # 파라미터 검증
        self.assertEqual(data_content["days"], 30)
        self.assertEqual(data_content["min_appearances"], 2)
    
    def test_scan_with_recurring_endpoint(self):
        """스캔+재등장 API 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # API 호출
        response = requests.get(f"{self.base_url}/scan-with-recurring?days=7&min_appearances=2")
        
        # 응답 검증
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("ok", data)
        self.assertTrue(data["ok"])
        self.assertIn("data", data)
        
        # 데이터 구조 검증
        data_content = data["data"]
        self.assertIn("latest_scan", data_content)
        self.assertIn("recurring_stocks", data_content)
        self.assertIn("total_recurring", data_content)
        
        # latest_scan 구조 검증
        latest_scan = data_content["latest_scan"]
        self.assertIn("date", latest_scan)
        self.assertIn("stocks", latest_scan)
    
    def test_api_response_time(self):
        """API 응답 시간 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # 응답 시간 측정
        start_time = time.time()
        response = requests.get(f"{self.base_url}/recurring-stocks?days=30&min_appearances=2")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # 응답 시간 검증 (1초 이내)
        self.assertLess(response_time, 1.0)
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
