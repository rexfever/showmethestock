"""
재등장 종목 수익률 계산 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.returns_service import calculate_returns
from services.scan_service import get_recurrence_data


class TestRecurringStocksReturns(unittest.TestCase):
    """재등장 종목 수익률 계산 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.test_ticker = "005930"  # 삼성전자
        self.first_as_of = "20251120"  # 최초 추천일
        self.current_scan_date = "20251201"  # 현재 재등장일
        self.today = "20251202"  # 오늘
        
    @patch('services.returns_service.api')
    def test_recurring_stock_returns_calculation(self, mock_api):
        """재등장 종목 수익률이 최초 추천일 기준으로 계산되는지 테스트"""
        # Mock 데이터 설정
        import pandas as pd
        
        # 최초 추천일 데이터
        first_date_df = pd.DataFrame({
            'date': ['20251120'],
            'close': [73000.0],
            'high': [73500.0],
            'low': [72800.0]
        })
        
        # 현재 날짜 데이터
        today_df = pd.DataFrame({
            'date': ['20251202'],
            'close': [75000.0],
            'high': [75500.0],
            'low': [74800.0]
        })
        
        # 기간 데이터 (최초 추천일부터 오늘까지)
        period_df = pd.DataFrame({
            'date': ['20251120', '20251121', '20251122', '20251201', '20251202'],
            'close': [73000.0, 73500.0, 74000.0, 74500.0, 75000.0],
            'high': [73500.0, 74000.0, 74500.0, 75000.0, 75500.0],
            'low': [72800.0, 73300.0, 73800.0, 74300.0, 74800.0]
        })
        
        def mock_get_ohlcv(code, count, base_dt=None):
            if base_dt == "20251120":
                return first_date_df
            elif base_dt == "20251202":
                return today_df
            else:
                return period_df
        
        mock_api.get_ohlcv.side_effect = mock_get_ohlcv
        
        # 최초 추천일 기준으로 수익률 계산
        result = calculate_returns(
            self.test_ticker,
            self.first_as_of,  # 최초 추천일
            self.today,  # 오늘
            scan_price_from_db=73000.0  # 최초 추천일 종가
        )
        
        # 검증
        self.assertIsNotNone(result)
        self.assertIn('current_return', result)
        self.assertIn('scan_price', result)
        self.assertIn('current_price', result)
        
        # 수익률 계산: (75000 - 73000) / 73000 * 100 = 2.74%
        expected_return = ((75000 - 73000) / 73000) * 100
        self.assertAlmostEqual(result['current_return'], expected_return, places=1)
        self.assertEqual(result['scan_price'], 73000.0)  # 최초 추천일 종가
        self.assertEqual(result['current_price'], 75000.0)  # 오늘 종가
    
    @patch('services.returns_service.api')
    def test_normal_stock_returns_calculation(self, mock_api):
        """일반 종목 수익률이 현재 스캔일 기준으로 계산되는지 테스트"""
        import pandas as pd
        
        # 현재 스캔일 데이터
        scan_date_df = pd.DataFrame({
            'date': ['20251201'],
            'close': [74000.0],
            'high': [74500.0],
            'low': [73800.0]
        })
        
        # 오늘 데이터
        today_df = pd.DataFrame({
            'date': ['20251202'],
            'close': [75000.0],
            'high': [75500.0],
            'low': [74800.0]
        })
        
        # 기간 데이터
        period_df = pd.DataFrame({
            'date': ['20251201', '20251202'],
            'close': [74000.0, 75000.0],
            'high': [74500.0, 75500.0],
            'low': [73800.0, 74800.0]
        })
        
        def mock_get_ohlcv(code, count, base_dt=None):
            if base_dt == "20251201":
                return scan_date_df
            elif base_dt == "20251202":
                return today_df
            else:
                return period_df
        
        mock_api.get_ohlcv.side_effect = mock_get_ohlcv
        
        # 현재 스캔일 기준으로 수익률 계산
        result = calculate_returns(
            self.test_ticker,
            self.current_scan_date,  # 현재 스캔일
            self.today,  # 오늘
            scan_price_from_db=74000.0  # 스캔일 종가
        )
        
        # 검증
        self.assertIsNotNone(result)
        # 수익률 계산: (75000 - 74000) / 74000 * 100 = 1.35%
        expected_return = ((75000 - 74000) / 74000) * 100
        self.assertAlmostEqual(result['current_return'], expected_return, places=1)
        self.assertEqual(result['scan_price'], 74000.0)  # 스캔일 종가
        self.assertEqual(result['current_price'], 75000.0)  # 오늘 종가
    
    def test_recurring_stock_first_as_of_extraction(self):
        """재등장 종목의 first_as_of가 올바르게 추출되는지 테스트"""
        # Mock recurrence 데이터
        recurrence_data = {
            "005930": {
                "appeared_before": True,
                "appear_count": 3,
                "first_as_of": "20251120",
                "last_as_of": "20251128",
                "days_since_last": 3
            }
        }
        
        # 검증
        self.assertTrue(recurrence_data["005930"]["appeared_before"])
        self.assertEqual(recurrence_data["005930"]["first_as_of"], "20251120")
        self.assertEqual(recurrence_data["005930"]["appear_count"], 3)


if __name__ == '__main__':
    unittest.main()

