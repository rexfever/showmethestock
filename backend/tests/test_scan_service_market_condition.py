"""
스캔 서비스의 장세 로직 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from services.scan_service import execute_scan_with_fallback
from market_analyzer import MarketCondition

class TestScanServiceMarketCondition(unittest.TestCase):
    """스캔 서비스 장세 로직 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.universe = ["005930", "000660", "051910"]  # 삼성전자, SK하이닉스, LG화학
    
    def test_execute_scan_with_fallback_crash(self):
        """급락장 시 빈 리스트 반환 테스트"""
        crash_condition = MarketCondition(
            date="20251105",
            kospi_return=-0.04,  # -4%
            volatility=0.05,
            market_sentiment='crash',
            sector_rotation='mixed',
            foreign_flow='sell',
            volume_trend='high',
            rsi_threshold=40.0,
            min_signals=999,
            macd_osc_min=999.0,
            vol_ma5_mult=999.0,
            gap_max=0.001,
            ext_from_tema20_max=0.001
        )
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251105",
            market_condition=crash_condition
        )
        
        # 급락장에서는 빈 리스트 반환
        self.assertEqual(len(items), 0)
        self.assertIsNone(chosen_step)
    
    @patch('services.scan_service.scan_with_preset')
    def test_execute_scan_with_fallback_bull(self, mock_scan):
        """강세장 스캔 테스트"""
        bull_condition = MarketCondition(
            date="20251105",
            kospi_return=0.03,  # +3%
            volatility=0.02,
            market_sentiment='bull',
            sector_rotation='tech',
            foreign_flow='buy',
            volume_trend='high',
            rsi_threshold=65.0,
            min_signals=2,
            macd_osc_min=-5.0,
            vol_ma5_mult=1.5,
            gap_max=0.02,
            ext_from_tema20_max=0.02
        )
        
        # Mock 스캔 결과
        mock_scan.return_value = [
            {"ticker": "005930", "name": "삼성전자", "score": 8.5},
            {"ticker": "000660", "name": "SK하이닉스", "score": 7.5}
        ]
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251105",
            market_condition=bull_condition
        )
        
        # market_condition이 전달되었는지 확인
        mock_scan.assert_called_once()
        call_args = mock_scan.call_args
        self.assertEqual(call_args[0][2], "20251105")  # date
        self.assertEqual(call_args[0][3], bull_condition)  # market_condition
    
    @patch('services.scan_service.scan_with_preset')
    def test_execute_scan_with_fallback_bear(self, mock_scan):
        """약세장 스캔 테스트"""
        bear_condition = MarketCondition(
            date="20251105",
            kospi_return=-0.025,  # -2.5%
            volatility=0.03,
            market_sentiment='bear',
            sector_rotation='value',
            foreign_flow='sell',
            volume_trend='low',
            rsi_threshold=45.0,
            min_signals=4,
            macd_osc_min=5.0,
            vol_ma5_mult=2.0,
            gap_max=0.01,
            ext_from_tema20_max=0.01
        )
        
        # Mock 스캔 결과 (약세장에서는 결과가 적을 수 있음)
        mock_scan.return_value = [
            {"ticker": "005930", "name": "삼성전자", "score": 6.5}
        ]
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251105",
            market_condition=bear_condition
        )
        
        # market_condition이 전달되었는지 확인
        mock_scan.assert_called_once()
        call_args = mock_scan.call_args
        self.assertEqual(call_args[0][3], bear_condition)  # market_condition
    
    @patch('services.scan_service.scan_with_preset')
    def test_execute_scan_with_fallback_neutral(self, mock_scan):
        """중립장 스캔 테스트"""
        neutral_condition = MarketCondition(
            date="20251105",
            kospi_return=0.0,  # 0%
            volatility=0.02,
            market_sentiment='neutral',
            sector_rotation='mixed',
            foreign_flow='neutral',
            volume_trend='normal',
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=1.6,
            gap_max=0.018,
            ext_from_tema20_max=0.018
        )
        
        # Mock 스캔 결과
        mock_scan.return_value = [
            {"ticker": "005930", "name": "삼성전자", "score": 7.5},
            {"ticker": "000660", "name": "SK하이닉스", "score": 7.0},
            {"ticker": "051910", "name": "LG화학", "score": 6.5}
        ]
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251105",
            market_condition=neutral_condition
        )
        
        # market_condition이 전달되었는지 확인
        mock_scan.assert_called_once()
        call_args = mock_scan.call_args
        self.assertEqual(call_args[0][3], neutral_condition)  # market_condition

if __name__ == '__main__':
    unittest.main()

