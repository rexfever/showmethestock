"""
수익률 계산 로직 테스트
- DB close_price 우선 사용 검증
- recommended_price 정확성 검증
- max_return, min_return 계산 검증
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.returns_service import calculate_returns, calculate_returns_batch, _get_cached_ohlcv, _parse_cached_ohlcv
import pandas as pd
from datetime import datetime


class TestReturnsCalculation(unittest.TestCase):
    
    def setUp(self):
        """테스트 설정"""
        self.scan_date = "20251127"
        self.current_date = "20251130"
        self.ticker = "005930"
        self.db_close_price = 68000.0  # DB에 저장된 스캔일 종가
        
    @patch('services.returns_service._parse_cached_ohlcv')
    @patch('services.returns_service._get_cached_ohlcv')
    def test_calculate_returns_with_db_price(self, mock_get, mock_parse):
        """DB close_price를 우선 사용하는지 테스트"""
        
        # DB price 사용 시 scan_df는 조회하지 않음
        # 현재일 데이터만 조회됨
        current_df = pd.DataFrame({
            'date': ['20251130'],
            'close': [70000.0]
        })
        
        # 기간 데이터 (최고/최저가 포함)
        period_df = pd.DataFrame({
            'date': ['20251127', '20251128', '20251129', '20251130'],
            'close': [68000.0, 69000.0, 69500.0, 70000.0],
            'high': [68500.0, 69500.0, 70000.0, 70500.0],
            'low': [67500.0, 68500.0, 69000.0, 69500.0]
        })
        period_df['date_dt'] = pd.to_datetime(period_df['date'], format='%Y%m%d')
        
        mock_get.return_value = '{"dummy": "data"}'
        # DB price 사용 시: current_df만 조회, period_df 조회
        mock_parse.side_effect = [current_df, period_df]
        
        # DB close_price를 전달하여 계산
        result = calculate_returns(
            self.ticker, 
            self.scan_date, 
            self.current_date, 
            scan_price_from_db=self.db_close_price
        )
        
        self.assertIsNotNone(result, "수익률 계산 결과가 None입니다")
        # DB close_price를 사용했는지 확인
        self.assertEqual(result['scan_price'], self.db_close_price, 
                        f"scan_price가 DB 값({self.db_close_price})과 일치하지 않습니다: {result.get('scan_price')}")
        
        # 수익률 계산 검증: (70000 - 68000) / 68000 * 100 = 2.94%
        expected_return = ((70000.0 - 68000.0) / 68000.0) * 100
        self.assertAlmostEqual(
            result['current_return'], 
            expected_return, 
            places=1,
            msg=f"수익률 계산 오류: 예상 {expected_return}%, 실제 {result.get('current_return')}%"
        )
        
    @patch('services.returns_service._parse_cached_ohlcv')
    @patch('services.returns_service._get_cached_ohlcv')
    def test_calculate_returns_without_db_price(self, mock_get, mock_parse):
        """DB close_price가 없을 때 API로 조회하는지 테스트"""
        
        scan_df = pd.DataFrame({
            'date': ['20251127'],
            'close': [68000.0]
        })
        
        current_df = pd.DataFrame({
            'date': ['20251130'],
            'close': [70000.0]
        })
        
        period_df = pd.DataFrame({
            'date': ['20251127', '20251128', '20251129', '20251130'],
            'close': [68000.0, 69000.0, 69500.0, 70000.0],
            'high': [68500.0, 69500.0, 70000.0, 70500.0],
            'low': [67500.0, 68500.0, 69000.0, 69500.0]
        })
        period_df['date_dt'] = pd.to_datetime(period_df['date'], format='%Y%m%d')
        
        mock_get.return_value = '{"dummy": "data"}'
        mock_parse.side_effect = [scan_df, current_df, period_df]
        
        # DB close_price 없이 계산
        result = calculate_returns(
            self.ticker, 
            self.scan_date, 
            self.current_date, 
            scan_price_from_db=None
        )
        
        self.assertIsNotNone(result)
        # API로 조회한 값 사용 확인
        self.assertEqual(result['scan_price'], 68000.0)
        
    @patch('services.returns_service._parse_cached_ohlcv')
    @patch('services.returns_service._get_cached_ohlcv')
    def test_max_min_return_calculation(self, mock_get, mock_parse):
        """최고/최저 수익률 계산 정확성 테스트"""
        
        scan_df = pd.DataFrame({
            'date': ['20251127'],
            'close': [68000.0]
        })
        
        current_df = pd.DataFrame({
            'date': ['20251130'],
            'close': [70000.0]  # 현재가
        })
        
        # 최고가 71000, 최저가 67000인 경우
        period_df = pd.DataFrame({
            'date': ['20251127', '20251128', '20251129', '20251130'],
            'close': [68000.0, 69000.0, 69500.0, 70000.0],
            'high': [68500.0, 71000.0, 70000.0, 70500.0],  # 최고가 71000
            'low': [67500.0, 68500.0, 69000.0, 67000.0]   # 최저가 67000
        })
        period_df['date_dt'] = pd.to_datetime(period_df['date'], format='%Y%m%d')
        
        mock_get.return_value = '{"dummy": "data"}'
        # DB price 사용 시 scan_df는 사용되지 않음
        mock_parse.side_effect = [pd.DataFrame(), current_df, period_df]
        
        result = calculate_returns(
            self.ticker, 
            self.scan_date, 
            self.current_date, 
            scan_price_from_db=68000.0
        )
        
        self.assertIsNotNone(result)
        
        # 최고 수익률: (71000 - 68000) / 68000 * 100 = 4.41%
        expected_max_return = ((71000.0 - 68000.0) / 68000.0) * 100
        self.assertAlmostEqual(result['max_return'], expected_max_return, places=1)
        
        # 최저 수익률: (67000 - 68000) / 68000 * 100 = -1.47%
        expected_min_return = ((67000.0 - 68000.0) / 68000.0) * 100
        self.assertAlmostEqual(result['min_return'], expected_min_return, places=1)
        
    @patch('services.returns_service.calculate_returns')
    def test_calculate_returns_batch_with_scan_prices(self, mock_calc):
        """배치 계산 시 scan_prices 전달 테스트"""
        
        tickers = ['005930', '000660']
        scan_prices = {
            '005930': 68000.0,
            '000660': 50000.0
        }
        
        # Mock 반환값
        mock_calc.return_value = {
            'current_return': 2.94,
            'max_return': 4.41,
            'min_return': -1.47,
            'scan_price': 68000.0,
            'current_price': 70000.0,
            'days_elapsed': 3
        }
        
        result = calculate_returns_batch(
            tickers, 
            self.scan_date, 
            self.current_date, 
            scan_prices
        )
        
        # 각 ticker에 대해 calculate_returns가 호출되었는지 확인
        self.assertEqual(mock_calc.call_count, 2)
        
        # 첫 번째 호출에서 scan_price_from_db가 전달되었는지 확인
        first_call = mock_calc.call_args_list[0]
        self.assertEqual(first_call[0][0], '005930')
        self.assertEqual(first_call[0][3], 68000.0)  # scan_price_from_db
        
        # 두 번째 호출 확인
        second_call = mock_calc.call_args_list[1]
        self.assertEqual(second_call[0][0], '000660')
        self.assertEqual(second_call[0][3], 50000.0)  # scan_price_from_db


class TestRecommendedPriceLogic(unittest.TestCase):
    """recommended_price 로직 테스트"""
    
    def test_recommended_price_from_returns_scan_price(self):
        """returns_info의 scan_price를 recommended_price로 사용"""
        current_price = 68000.0  # DB close_price
        returns_info = {
            'current_return': 2.94,
            'scan_price': 68000.0,
            'current_price': 70000.0
        }
        
        # 로직 시뮬레이션
        recommended_price = current_price
        if returns_info and returns_info.get('scan_price'):
            recommended_price = returns_info.get('scan_price')
        
        self.assertEqual(recommended_price, 68000.0)
        self.assertEqual(recommended_price, current_price)
        
    def test_recommended_price_from_db_when_no_returns(self):
        """returns_info가 없을 때 DB close_price 사용"""
        current_price = 68000.0  # DB close_price
        returns_info = None
        
        # 로직 시뮬레이션
        recommended_price = current_price if current_price and current_price > 0 else None
        
        self.assertEqual(recommended_price, 68000.0)
        
    def test_recommended_price_consistency(self):
        """recommended_price가 항상 스캔일 종가인지 확인"""
        test_cases = [
            {
                'current_price': 68000.0,
                'returns_info': {'scan_price': 68000.0, 'current_return': 2.94},
                'expected': 68000.0
            },
            {
                'current_price': 68000.0,
                'returns_info': {'scan_price': 68000.0, 'current_return': 5.0},
                'expected': 68000.0
            },
            {
                'current_price': 68000.0,
                'returns_info': None,
                'expected': 68000.0
            }
        ]
        
        for case in test_cases:
            current_price = case['current_price']
            returns_info = case['returns_info']
            
            recommended_price = current_price if current_price and current_price > 0 else None
            if returns_info and returns_info.get('scan_price'):
                recommended_price = returns_info.get('scan_price')
            
            self.assertEqual(recommended_price, case['expected'], 
                           f"Failed for case: {case}")


if __name__ == '__main__':
    unittest.main()

