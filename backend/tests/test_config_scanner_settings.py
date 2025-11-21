"""
Config의 스캐너 설정 property 테스트
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config


class TestConfigScannerSettings(unittest.TestCase):
    """Config의 스캐너 설정 property 테스트"""
    
    @patch('scanner_settings_manager.get_scanner_version')
    def test_scanner_version_property_from_db(self, mock_get_version):
        """DB에서 스캐너 버전 조회 테스트"""
        mock_get_version.return_value = 'v2'
        
        result = config.scanner_version
        
        self.assertEqual(result, 'v2')
        mock_get_version.assert_called_once()
    
    @patch('scanner_settings_manager.get_scanner_version')
    @patch('os.getenv')
    def test_scanner_version_property_fallback_to_env(self, mock_getenv, mock_get_version):
        """DB 연결 실패 시 .env에서 조회 테스트"""
        mock_get_version.side_effect = Exception("DB 연결 실패")
        mock_getenv.return_value = 'v1'
        
        result = config.scanner_version
        
        self.assertEqual(result, 'v1')
        mock_getenv.assert_called_once_with('SCANNER_VERSION', 'v1')
    
    @patch('scanner_settings_manager.get_scanner_v2_enabled')
    def test_scanner_v2_enabled_property_from_db(self, mock_get_enabled):
        """DB에서 V2 활성화 여부 조회 테스트"""
        mock_get_enabled.return_value = True
        
        result = config.scanner_v2_enabled
        
        self.assertTrue(result)
        mock_get_enabled.assert_called_once()
    
    @patch('scanner_settings_manager.get_scanner_v2_enabled')
    @patch('os.getenv')
    def test_scanner_v2_enabled_property_fallback_to_env(self, mock_getenv, mock_get_enabled):
        """DB 연결 실패 시 .env에서 조회 테스트"""
        mock_get_enabled.side_effect = Exception("DB 연결 실패")
        mock_getenv.return_value = 'true'
        
        result = config.scanner_v2_enabled
        
        self.assertTrue(result)
        mock_getenv.assert_called_once_with('SCANNER_V2_ENABLED', 'false')


if __name__ == '__main__':
    unittest.main()

