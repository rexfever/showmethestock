"""
스캐너 설정 API 테스트
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestScannerSettingsAPI(unittest.TestCase):
    """스캐너 설정 API 테스트"""
    
    @patch('main.get_admin_user')
    @patch('scanner_settings_manager.get_all_scanner_settings')
    def test_get_scanner_settings(self, mock_get_all, mock_get_admin):
        """GET /admin/scanner-settings 테스트"""
        from main import app
        from fastapi.testclient import TestClient
        
        # 관리자 모킹
        mock_user = MagicMock()
        mock_user.email = 'admin@test.com'
        mock_get_admin.return_value = mock_user
        
        # 설정 모킹
        mock_get_all.return_value = {
            'scanner_version': 'v2',
            'scanner_v2_enabled': 'true'
        }
        
        client = TestClient(app)
        response = client.get(
            '/admin/scanner-settings',
            headers={'Authorization': 'Bearer test_token'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['settings']['scanner_version'], 'v2')
    
    @patch('main.get_admin_user')
    @patch('scanner_settings_manager.set_scanner_setting')
    @patch('scanner_settings_manager.get_scanner_setting')
    def test_update_scanner_settings(self, mock_get_setting, mock_set_setting, mock_get_admin):
        """POST /admin/scanner-settings 테스트"""
        from main import app
        from fastapi.testclient import TestClient
        
        # 관리자 모킹
        mock_user = MagicMock()
        mock_user.email = 'admin@test.com'
        mock_get_admin.return_value = mock_user
        
        # 기존 값 모킹
        mock_get_setting.return_value = 'v1'
        mock_set_setting.return_value = True
        
        client = TestClient(app)
        response = client.post(
            '/admin/scanner-settings',
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json'
            },
            json={
                'scanner_version': 'v2',
                'scanner_v2_enabled': True
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertIn('changes', data)
    
    @patch('main.get_admin_user')
    def test_update_scanner_settings_invalid_version(self, mock_get_admin):
        """잘못된 버전 값 테스트"""
        from main import app
        from fastapi.testclient import TestClient
        
        # 관리자 모킹
        mock_user = MagicMock()
        mock_user.email = 'admin@test.com'
        mock_get_admin.return_value = mock_user
        
        client = TestClient(app)
        response = client.post(
            '/admin/scanner-settings',
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json'
            },
            json={
                'scanner_version': 'v3',  # 잘못된 값
                'scanner_v2_enabled': True
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertIn('error', data)


if __name__ == '__main__':
    unittest.main()
