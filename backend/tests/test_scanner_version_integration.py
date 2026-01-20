"""
스캐너 버전 선택 통합 테스트
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestScannerVersionIntegration(unittest.TestCase):
    """스캐너 버전 선택 통합 테스트"""
    
    @patch('scanner_factory.config')
    @patch('scanner_factory.ScannerV2')
    @patch('scanner_factory.scanner_v2_config')
    @patch('scanner_settings_manager.get_scanner_version')
    @patch('scanner_settings_manager.get_scanner_v2_enabled')
    def test_v2_scanner_selection_flow(self, mock_get_enabled, mock_get_version, 
                                       mock_config_v2, mock_scanner_v2, mock_config):
        """V2 스캐너 선택 플로우 테스트"""
        # DB에서 V2 설정 조회
        mock_get_version.return_value = 'v2'
        mock_get_enabled.return_value = True
        mock_config.market_analysis_enable = True
        
        # V2 스캐너 인스턴스 생성
        mock_v2_instance = MagicMock()
        mock_scanner_v2.return_value = mock_v2_instance
        
        from scanner_factory import get_scanner
        scanner = get_scanner()
        
        # V2 스캐너가 반환되었는지 확인
        self.assertEqual(scanner, mock_v2_instance)
        mock_scanner_v2.assert_called_once()
    
    @patch('scanner_factory.config')
    @patch('scanner_settings_manager.get_scanner_version')
    @patch('scanner_settings_manager.get_scanner_v2_enabled')
    def test_v1_scanner_selection_flow(self, mock_get_enabled, mock_get_version, mock_config):
        """V1 스캐너 선택 플로우 테스트"""
        # DB에서 V1 설정 조회
        mock_get_version.return_value = 'v1'
        mock_get_enabled.return_value = False
        
        from scanner_factory import get_scanner
        scanner = get_scanner()
        
        # V1은 함수를 반환하므로 callable 확인
        self.assertTrue(callable(scanner))
    
    @patch('scanner_factory.config')
    @patch('scanner_settings_manager.get_scanner_version')
    @patch('scanner_settings_manager.get_scanner_v2_enabled')
    def test_v2_disabled_fallback_to_v1(self, mock_get_enabled, mock_get_version, mock_config):
        """V2 비활성화 시 V1으로 fallback 테스트"""
        # DB에서 V2 설정이지만 비활성화
        mock_get_version.return_value = 'v2'
        mock_get_enabled.return_value = False
        
        from scanner_factory import get_scanner
        scanner = get_scanner()
        
        # V1으로 fallback
        self.assertTrue(callable(scanner))
    
    @patch('scanner_factory.scan_with_scanner')
    @patch('scanner_factory.config')
    @patch('scanner_settings_manager.get_scanner_version')
    @patch('scanner_settings_manager.get_scanner_v2_enabled')
    def test_scan_service_uses_correct_scanner(self, mock_get_enabled, mock_get_version,
                                                mock_config, mock_scan_with_scanner):
        """scan_service가 올바른 스캐너 사용 테스트"""
        mock_get_version.return_value = 'v2'
        mock_get_enabled.return_value = True
        mock_config.fallback_enable = False
        mock_config.top_k = 5
        
        mock_scan_with_scanner.return_value = [
            {'ticker': '005930', 'score': 10, 'match': True}
        ]
        
        from services.scan_service import execute_scan_with_fallback
        from market_analyzer import MarketCondition
        
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
        
        items, step = execute_scan_with_fallback(
            ['005930'], '20251119', market_condition
        )
        
        # scan_with_scanner가 호출되었는지 확인
        self.assertTrue(mock_scan_with_scanner.called)
        # V2 설정이 반영되었는지 확인
        self.assertEqual(len(items), 1)


if __name__ == '__main__':
    unittest.main()

