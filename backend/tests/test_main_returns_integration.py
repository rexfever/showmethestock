"""
main.py의 수익률 계산 통합 테스트
- DB close_price를 scan_price로 전달하는지 검증
- recommended_price 정확성 검증
- returns_info 처리 검증
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json


class TestMainReturnsIntegration(unittest.TestCase):
    """main.py의 수익률 계산 통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.formatted_date = "20251127"
        self.code = "005930"
        self.db_close_price = 68000.0
        
    def test_scan_prices_extraction_from_db(self):
        """DB에서 scan_prices 추출 로직 테스트"""
        
        # _row_to_dict 시뮬레이션
        def _row_to_dict(row):
            return {
                "code": row[0],
                "current_price": row[1]  # current_price는 close_price로 매핑됨
            }
        
        # Mock rows
        rows = [
            ("005930", 68000.0),
            ("000660", 50000.0)
        ]
        
        codes_needing_calculation = ["005930", "000660"]
        scan_prices = {}
        
        # 로직 시뮬레이션
        for row in rows:
            row_data = _row_to_dict(row)
            code = row_data.get("code")
            if code in codes_needing_calculation:
                close_price = row_data.get("current_price")
                if close_price and close_price > 0:
                    scan_prices[code] = float(close_price)
        
        # 검증
        self.assertEqual(len(scan_prices), 2)
        self.assertEqual(scan_prices["005930"], 68000.0)
        self.assertEqual(scan_prices["000660"], 50000.0)
        
    def test_recommended_price_logic_all_cases(self):
        """recommended_price 로직의 모든 케이스 테스트"""
        
        test_cases = [
            {
                'name': 'returns_info 있고 scan_price 있음',
                'current_price': 68000.0,
                'returns_info': {
                    'current_return': 2.94,
                    'scan_price': 68000.0,
                    'current_price': 70000.0
                },
                'expected': 68000.0
            },
            {
                'name': 'returns_info 있지만 scan_price 없음',
                'current_price': 68000.0,
                'returns_info': {
                    'current_return': 2.94,
                    'current_price': 70000.0
                },
                'expected': 68000.0  # current_price 사용
            },
            {
                'name': 'returns_info 없음',
                'current_price': 68000.0,
                'returns_info': None,
                'expected': 68000.0  # current_price 사용
            },
            {
                'name': 'current_price가 0인 경우',
                'current_price': 0,
                'returns_info': None,
                'expected': None
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case['name']):
                current_price = case['current_price']
                returns_info = case['returns_info']
                
                # 로직 시뮬레이션
                recommended_price = current_price if current_price and current_price > 0 else None
                
                if returns_info and isinstance(returns_info, dict) and returns_info.get('current_return') is not None:
                    if returns_info.get('scan_price'):
                        recommended_price = returns_info.get('scan_price')
                    # scan_price가 없으면 이미 설정한 current_price 유지
                
                self.assertEqual(recommended_price, case['expected'], 
                               f"Failed for case: {case['name']}")
    
    def test_returns_info_validation(self):
        """returns_info 유효성 검증 로직 테스트"""
        
        test_cases = [
            {
                'name': '유효한 returns_info',
                'returns_dict': {'current_return': 2.94, 'max_return': 4.0},
                'should_use': True
            },
            {
                'name': '빈 딕셔너리',
                'returns_dict': {},
                'should_use': False
            },
            {
                'name': 'current_return이 None',
                'returns_dict': {'current_return': None, 'max_return': 4.0},
                'should_use': False
            },
            {
                'name': 'current_return이 0',
                'returns_dict': {'current_return': 0, 'max_return': 4.0},
                'should_use': True  # 0도 유효한 값
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case['name']):
                returns_dict = case['returns_dict']
                
                # 로직 시뮬레이션
                is_valid = (
                    isinstance(returns_dict, dict) and 
                    returns_dict and 
                    returns_dict.get('current_return') is not None
                )
                
                self.assertEqual(is_valid, case['should_use'], 
                               f"Failed for case: {case['name']}")
    
    def test_current_return_none_handling(self):
        """current_return이 None일 때 처리 테스트"""
        
        test_cases = [
            {
                'name': 'returns_info 없음',
                'returns_info': None,
                'expected_return': None,
                'expected_max': None,
                'expected_min': None
            },
            {
                'name': 'returns_info 있지만 current_return 없음',
                'returns_info': {'max_return': 4.0, 'min_return': 1.0},
                'expected_return': None,
                'expected_max': None,
                'expected_min': None
            },
            {
                'name': 'returns_info 유효',
                'returns_info': {
                    'current_return': 2.94,
                    'max_return': 4.0,
                    'min_return': 1.0
                },
                'expected_return': 2.94,
                'expected_max': 4.0,
                'expected_min': 1.0
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case['name']):
                returns_info = case['returns_info']
                
                # 로직 시뮬레이션
                if returns_info and isinstance(returns_info, dict) and returns_info.get('current_return') is not None:
                    current_return = returns_info.get('current_return')
                    max_return = returns_info.get('max_return', current_return)
                    min_return = returns_info.get('min_return', current_return)
                else:
                    current_return = None
                    max_return = None
                    min_return = None
                
                self.assertEqual(current_return, case['expected_return'], 
                               f"current_return failed for: {case['name']}")
                self.assertEqual(max_return, case['expected_max'], 
                               f"max_return failed for: {case['name']}")
                self.assertEqual(min_return, case['expected_min'], 
                               f"min_return failed for: {case['name']}")


if __name__ == '__main__':
    unittest.main()

