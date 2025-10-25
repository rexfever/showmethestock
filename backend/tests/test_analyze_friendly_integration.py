"""
사용자 친화적 분석 기능 통합 테스트
"""
import unittest
import requests
import json
import time
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestAnalyzeFriendlyIntegration(unittest.TestCase):
    """사용자 친화적 분석 API 통합 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.base_url = "https://sohntech.ai.kr/api"
        self.server_running = self._check_server_status()
        
        # 테스트용 종목 코드들
        self.test_stocks = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "035420",  # NAVER
            "삼성전자",  # 종목명
            "SK하이닉스"  # 종목명
        ]

    def _check_server_status(self):
        """서버 상태 확인"""
        try:
            response = requests.get(f"{self.base_url}/scan", timeout=10)
            return response.status_code in [200, 422]  # 422는 파라미터 오류로 정상 응답
        except:
            return False

    def test_analyze_friendly_api_basic(self):
        """기본 analyze-friendly API 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # 삼성전자 분석 요청
        response = requests.get(f"{self.base_url}/analyze-friendly?name_or_code=005930")
        
        # 응답 상태 확인
        self.assertEqual(response.status_code, 200)
        
        # JSON 파싱
        data = response.json()
        
        # 기본 구조 검증
        self.assertIn("ok", data)
        self.assertIn("ticker", data)
        self.assertIn("name", data)
        self.assertIn("score", data)
        self.assertIn("match", data)
        self.assertIn("strategy", data)
        self.assertIn("friendly_analysis", data)
        
        # 성공 응답 검증
        if data["ok"]:
            self.assertEqual(data["ticker"], "005930")
            self.assertEqual(data["name"], "삼성전자")
            self.assertIsInstance(data["score"], (int, float))
            self.assertIsInstance(data["match"], bool)
            self.assertIsInstance(data["strategy"], str)
            
            # 친화적 분석 구조 검증
            friendly_analysis = data["friendly_analysis"]
            self.assertIn("summary", friendly_analysis)
            self.assertIn("recommendation", friendly_analysis)
            self.assertIn("confidence", friendly_analysis)
            self.assertIn("explanations", friendly_analysis)
            self.assertIn("investment_advice", friendly_analysis)
            self.assertIn("warnings", friendly_analysis)
            self.assertIn("simple_indicators", friendly_analysis)
            
            # 친화적 분석 내용 검증
            self.assertIsInstance(friendly_analysis["summary"], str)
            self.assertIsInstance(friendly_analysis["recommendation"], str)
            self.assertIsInstance(friendly_analysis["confidence"], str)
            self.assertIsInstance(friendly_analysis["explanations"], list)
            self.assertIsInstance(friendly_analysis["investment_advice"], list)
            self.assertIsInstance(friendly_analysis["warnings"], list)
            self.assertIsInstance(friendly_analysis["simple_indicators"], dict)

    def test_analyze_friendly_with_stock_name(self):
        """종목명으로 분석 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        response = requests.get(f"{self.base_url}/analyze-friendly?name_or_code=삼성전자")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        if data["ok"]:
            self.assertEqual(data["ticker"], "005930")
            self.assertEqual(data["name"], "삼성전자")

    def test_analyze_friendly_multiple_stocks(self):
        """여러 종목 분석 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        for stock in self.test_stocks[:3]:  # 처음 3개만 테스트
            with self.subTest(stock=stock):
                response = requests.get(f"{self.base_url}/analyze-friendly?name_or_code={stock}")
                
                self.assertEqual(response.status_code, 200)
                data = response.json()
                
                # 기본 필드 존재 확인
                self.assertIn("ok", data)
                self.assertIn("ticker", data)
                self.assertIn("name", data)
                self.assertIn("friendly_analysis", data)
                
                if data["ok"]:
                    # 친화적 분석 필드 확인
                    friendly_analysis = data["friendly_analysis"]
                    self.assertIn("summary", friendly_analysis)
                    self.assertIn("recommendation", friendly_analysis)
                    self.assertIn("confidence", friendly_analysis)

    def test_analyze_friendly_invalid_stock(self):
        """잘못된 종목 코드 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        response = requests.get(f"{self.base_url}/analyze-friendly?name_or_code=INVALID123")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # 실패 응답 검증
        self.assertFalse(data["ok"])
        self.assertIn("error", data)
        self.assertIsNone(data["friendly_analysis"])

    def test_analyze_friendly_empty_input(self):
        """빈 입력 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        response = requests.get(f"{self.base_url}/analyze-friendly?name_or_code=")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # 실패 응답 검증
        self.assertFalse(data["ok"])
        self.assertIn("error", data)

    def test_analyze_friendly_response_time(self):
        """응답 시간 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        start_time = time.time()
        response = requests.get(f"{self.base_url}/analyze-friendly?name_or_code=005930")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # 응답 시간이 10초 이내인지 확인
        self.assertLess(response_time, 10.0)
        self.assertEqual(response.status_code, 200)

    def test_analyze_friendly_content_quality(self):
        """응답 내용 품질 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        response = requests.get(f"{self.base_url}/analyze-friendly?name_or_code=005930")
        data = response.json()
        
        if data["ok"]:
            friendly_analysis = data["friendly_analysis"]
            
            # 요약이 비어있지 않은지 확인
            self.assertGreater(len(friendly_analysis["summary"]), 0)
            
            # 추천이 유효한 값인지 확인
            valid_recommendations = ["강력 추천", "추천", "관심", "신중", "비추천"]
            self.assertIn(friendly_analysis["recommendation"], valid_recommendations)
            
            # 신뢰도가 유효한 값인지 확인
            valid_confidence = ["높음", "보통", "낮음", "매우 낮음"]
            self.assertIn(friendly_analysis["confidence"], valid_confidence)
            
            # 설명이 비어있지 않은지 확인
            self.assertGreater(len(friendly_analysis["explanations"]), 0)
            
            # 투자 조언이 비어있지 않은지 확인
            self.assertGreater(len(friendly_analysis["investment_advice"]), 0)
            
            # 주의사항이 비어있지 않은지 확인
            self.assertGreater(len(friendly_analysis["warnings"]), 0)
            
            # 간단한 지표가 올바른 구조인지 확인
            simple_indicators = friendly_analysis["simple_indicators"]
            self.assertIn("current_price", simple_indicators)
            self.assertIn("volume", simple_indicators)
            self.assertIn("rsi", simple_indicators)
            self.assertIn("trend", simple_indicators)

    def test_analyze_friendly_vs_analyze_consistency(self):
        """analyze-friendly와 기존 analyze API 일관성 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # 두 API 모두 호출
        friendly_response = requests.get(f"{self.base_url}/analyze-friendly?name_or_code=005930")
        analyze_response = requests.get(f"{self.base_url}/analyze?name_or_code=005930")
        
        self.assertEqual(friendly_response.status_code, 200)
        self.assertEqual(analyze_response.status_code, 200)
        
        friendly_data = friendly_response.json()
        analyze_data = analyze_response.json()
        
        if friendly_data["ok"] and analyze_data["ok"]:
            # 기본 정보 일치 확인
            self.assertEqual(friendly_data["ticker"], analyze_data["item"]["ticker"])
            self.assertEqual(friendly_data["name"], analyze_data["item"]["name"])
            self.assertEqual(friendly_data["score"], analyze_data["item"]["score"])
            self.assertEqual(friendly_data["match"], analyze_data["item"]["match"])
            self.assertEqual(friendly_data["strategy"], analyze_data["item"]["strategy"])

    def test_analyze_friendly_error_handling(self):
        """오류 처리 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # 잘못된 파라미터 테스트
        test_cases = [
            "NONEXISTENT123",
            "존재하지않는종목",
            "123456789",  # 너무 긴 코드
            "A",  # 너무 짧은 코드
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                response = requests.get(f"{self.base_url}/analyze-friendly?name_or_code={test_case}")
                
                self.assertEqual(response.status_code, 200)
                data = response.json()
                
                # 오류 응답 구조 확인
                self.assertIn("ok", data)
                self.assertIn("error", data)
                self.assertIn("friendly_analysis", data)
                
                # 실패 시 friendly_analysis는 None이어야 함
                if not data["ok"]:
                    self.assertIsNone(data["friendly_analysis"])


if __name__ == '__main__':
    unittest.main()
