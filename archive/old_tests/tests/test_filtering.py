"""
필터링 로직 테스트
"""
import unittest
import pandas as pd
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.scanner import scan_one_symbol
from backend.config import Config

class TestFiltering(unittest.TestCase):
    """필터링 로직 테스트 클래스"""
    
    def setUp(self):
        """테스트 설정"""
        self.config = Config()
    
    def test_inverse_etf_filtering(self):
        """인버스 ETF 필터링 테스트"""
        # 인버스 ETF 종목들 (실제로는 존재하지 않는 코드이지만 테스트용)
        inverse_etf_codes = [
            "114800",  # KODEX 인버스
            "252670",  # KODEX 2X 레버리지
            "233740",  # KODEX SHORT
        ]
        
        # 각 인버스 ETF가 필터링되는지 확인
        for code in inverse_etf_codes:
            with self.subTest(code=code):
                result = scan_one_symbol(code, "2024-09-01")
                self.assertIsNone(result, f"인버스 ETF {code}가 필터링되지 않았습니다")
    
    def test_rsi_upper_limit_filtering(self):
        """RSI 상한선 필터링 테스트"""
        # RSI가 70을 초과하는 종목이 필터링되는지 확인
        # (실제 테스트를 위해서는 RSI가 높은 종목의 코드가 필요)
        pass  # 실제 데이터가 필요하므로 추후 구현
    
    def test_config_values(self):
        """설정 값 테스트"""
        # RSI 상한선 설정 확인
        self.assertIsInstance(self.config.rsi_upper_limit, float)
        self.assertGreater(self.config.rsi_upper_limit, 0)
        
        # 인버스 ETF 키워드 설정 확인
        self.assertIsInstance(self.config.inverse_etf_keywords, list)
        self.assertGreater(len(self.config.inverse_etf_keywords), 0)
        
        # 필수 키워드 포함 확인
        required_keywords = ['인버스', '2X', '레버리지']
        for keyword in required_keywords:
            self.assertIn(keyword, self.config.inverse_etf_keywords)
    
    def test_keyword_matching(self):
        """키워드 매칭 테스트"""
        test_cases = [
            ("KODEX 인버스", True),
            ("KODEX 2X 레버리지", True),
            ("KODEX SHORT", True),
            ("삼성전자", False),
            ("SK하이닉스", False),
            ("NAVER", False),
        ]
        
        for stock_name, should_match in test_cases:
            with self.subTest(stock_name=stock_name):
                matches = any(keyword in stock_name for keyword in self.config.inverse_etf_keywords)
                self.assertEqual(matches, should_match, 
                               f"{stock_name}의 키워드 매칭 결과가 예상과 다릅니다")

if __name__ == '__main__':
    unittest.main()
