"""
스캐너 팩토리 테스트
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner_factory import get_scanner, scan_with_scanner
from market_analyzer import MarketCondition


class TestScannerFactory(unittest.TestCase):
    """스캐너 팩토리 테스트"""
    
    @patch('config.config')
    def test_get_scanner_v1_default(self, mock_config):
        """기본값으로 V1 스캐너 반환 테스트"""
        mock_config.scanner_version = 'v1'
        mock_config.scanner_v2_enabled = False
        
        scanner = get_scanner()
        
        # V1은 함수를 반환하므로 callable 확인
        self.assertTrue(callable(scanner))
    
    @patch('scanner_v2.ScannerV2')
    @patch('scanner_v2.config_v2.scanner_v2_config')
    @patch('config.config')
    def test_get_scanner_v2_enabled(self, mock_config, mock_config_v2, mock_scanner_v2):
        """V2 활성화 시 V2 스캐너 반환 테스트"""
        mock_config.scanner_version = 'v2'
        mock_config.scanner_v2_enabled = True
        mock_config.market_analysis_enable = True
        
        mock_scanner_instance = MagicMock()
        mock_scanner_v2.return_value = mock_scanner_instance
        
        scanner = get_scanner()
        
        self.assertEqual(scanner, mock_scanner_instance)
        mock_scanner_v2.assert_called_once()
    
    @patch('config.config')
    def test_get_scanner_v2_disabled_fallback_to_v1(self, mock_config):
        """V2 비활성화 시 V1으로 fallback 테스트"""
        mock_config.scanner_version = 'v2'
        mock_config.scanner_v2_enabled = False
        
        scanner = get_scanner()
        
        # V1 함수 반환 확인
        self.assertTrue(callable(scanner))
    
    @patch('scanner_factory.get_scanner')
    @patch('config.config')
    def test_scan_with_scanner_v1(self, mock_config, mock_get_scanner):
        """V1 스캐너로 스캔 테스트"""
        mock_config.scanner_version = 'v1'
        
        # V1 스캐너 모킹
        mock_v1_scanner = MagicMock()
        mock_v1_scanner.return_value = [
            {'ticker': '005930', 'score': 10, 'match': True}
        ]
        mock_get_scanner.return_value = mock_v1_scanner
        
        universe = ['005930']
        results = scan_with_scanner(universe, {}, '20251119', None)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['ticker'], '005930')
        mock_v1_scanner.assert_called_once_with(universe, {}, '20251119', None)
    
    @patch('scanner_factory.get_scanner')
    @patch('config.config')
    def test_scan_with_scanner_v2(self, mock_config, mock_get_scanner):
        """V2 스캐너로 스캔 테스트"""
        mock_config.scanner_version = 'v2'
        mock_config.scanner_v2_enabled = True
        
        # V2 스캐너 모킹
        from scanner_v2.core.scanner import ScanResult
        mock_v2_scanner = MagicMock()
        mock_v2_scanner.scan.return_value = [
            ScanResult(
                ticker='005930',
                name='삼성전자',
                match=True,
                score=10.0,
                indicators={},
                trend={},
                strategy='스윙',
                flags={},
                score_label='강한 매수'
            )
        ]
        mock_get_scanner.return_value = mock_v2_scanner
        
        universe = ['005930']
        market_condition = MarketCondition(
            market_sentiment='neutral',
            kospi_return=0.01,
            volatility=0.02,
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015,
            institution_flow=0.0
        )
        
        results = scan_with_scanner(universe, {}, '20251119', market_condition, 'v2')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['ticker'], '005930')
        self.assertEqual(results[0]['score'], 10.0)
        mock_v2_scanner.scan.assert_called_once()
    
    @patch('scanner_factory.get_scanner')
    @patch('config.config')
    def test_scan_with_scanner_v2_preset_overrides(self, mock_config, mock_get_scanner):
        """V2 스캐너에서 preset_overrides를 market_condition에 반영 테스트"""
        mock_config.scanner_version = 'v2'
        mock_config.scanner_v2_enabled = True
        mock_config.vol_ma20_mult = 1.2
        
        # V2 스캐너 모킹
        from scanner_v2.core.scanner import ScanResult
        mock_v2_scanner = MagicMock()
        mock_v2_scanner.scan.return_value = []
        mock_get_scanner.return_value = mock_v2_scanner
        
        universe = ['005930']
        market_condition = MarketCondition(
            date='20251119',
            kospi_return=0.01,
            volatility=0.02,
            market_sentiment='neutral',
            sector_rotation='mixed',
            foreign_flow='neutral',
            institution_flow='neutral',
            volume_trend='normal',
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
        
        preset_overrides = {
            'min_signals': 4,
            'gap_max': 0.025
        }
        
        results = scan_with_scanner(universe, preset_overrides, '20251119', market_condition, 'v2')
        
        # market_condition이 deepcopy되어 수정되었는지 확인
        mock_v2_scanner.scan.assert_called_once()
        call_args = mock_v2_scanner.scan.call_args
        modified_market_condition = call_args[0][2]  # 세 번째 인자
        
        # preset_overrides가 반영되었는지 확인
        self.assertEqual(modified_market_condition.min_signals, 4)
        self.assertEqual(modified_market_condition.gap_max, 0.025)


if __name__ == '__main__':
    unittest.main()

