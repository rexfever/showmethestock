"""
스캐너 설정 관리자 테스트
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner_settings_manager import (
    create_scanner_settings_table,
    get_scanner_setting,
    set_scanner_setting,
    get_all_scanner_settings,
    get_scanner_version,
    get_scanner_v2_enabled
)


class TestScannerSettingsManager(unittest.TestCase):
    """스캐너 설정 관리자 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.mock_cursor = MagicMock()
        self.mock_connection = MagicMock()
        self.mock_connection.__enter__ = Mock(return_value=self.mock_connection)
        self.mock_connection.__exit__ = Mock(return_value=False)
        self.mock_connection.cursor.return_value.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_connection.cursor.return_value.__exit__ = Mock(return_value=False)
    
    @patch('scanner_settings_manager.db_manager')
    def test_create_scanner_settings_table(self, mock_db_manager):
        """테이블 생성 테스트"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [0]  # 기본값 없음
        mock_db_manager.get_cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_db_manager.get_cursor.return_value.__exit__ = Mock(return_value=False)
        
        # 테이블 생성 함수 호출
        create_scanner_settings_table(mock_cursor)
        
        # 테이블 생성 쿼리 호출 확인
        self.assertTrue(mock_cursor.execute.called)
        # 기본값 INSERT 쿼리 호출 확인 (2번: scanner_version, scanner_v2_enabled)
        self.assertEqual(mock_cursor.execute.call_count, 3)  # CREATE + COUNT + INSERT
    
    @patch('scanner_settings_manager.db_manager')
    def test_get_scanner_setting_existing(self, mock_db_manager):
        """기존 설정 조회 테스트"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ['v2']  # DB에 값이 있음
        mock_db_manager.get_cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_db_manager.get_cursor.return_value.__exit__ = Mock(return_value=False)
        
        result = get_scanner_setting('scanner_version', 'v1')
        
        self.assertEqual(result, 'v2')
        mock_cursor.execute.assert_called_once()
    
    @patch('scanner_settings_manager.db_manager')
    def test_get_scanner_setting_not_existing(self, mock_db_manager):
        """존재하지 않는 설정 조회 테스트 (기본값 반환)"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # DB에 값이 없음
        mock_db_manager.get_cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_db_manager.get_cursor.return_value.__exit__ = Mock(return_value=False)
        
        result = get_scanner_setting('scanner_version', 'v1')
        
        self.assertEqual(result, 'v1')  # 기본값 반환
    
    @patch('scanner_settings_manager.db_manager')
    def test_set_scanner_setting_new(self, mock_db_manager):
        """새 설정 저장 테스트"""
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_db_manager.get_cursor.return_value.__exit__ = Mock(return_value=False)
        
        result = set_scanner_setting('scanner_version', 'v2', '테스트', 'admin@test.com')
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called()
    
    @patch('scanner_settings_manager.db_manager')
    def test_set_scanner_setting_update(self, mock_db_manager):
        """기존 설정 업데이트 테스트"""
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_db_manager.get_cursor.return_value.__exit__ = Mock(return_value=False)
        
        # 첫 번째 호출: 기존 값 조회
        # 두 번째 호출: 업데이트
        result = set_scanner_setting('scanner_version', 'v2', '업데이트', 'admin@test.com')
        
        self.assertTrue(result)
        # INSERT ... ON CONFLICT 쿼리가 호출되었는지 확인
        self.assertTrue(mock_cursor.execute.called)
    
    @patch('scanner_settings_manager.db_manager')
    def test_get_all_scanner_settings(self, mock_db_manager):
        """모든 설정 조회 테스트"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('scanner_version', 'v2'),
            ('scanner_v2_enabled', 'true')
        ]
        mock_db_manager.get_cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_db_manager.get_cursor.return_value.__exit__ = Mock(return_value=False)
        
        result = get_all_scanner_settings()
        
        self.assertEqual(result, {
            'scanner_version': 'v2',
            'scanner_v2_enabled': 'true'
        })
    
    @patch('scanner_settings_manager.get_scanner_setting')
    @patch.dict(os.environ, {}, clear=True)
    def test_get_scanner_version_from_db(self, mock_get_setting):
        """DB에서 스캐너 버전 조회 테스트"""
        mock_get_setting.return_value = 'v2'
        
        result = get_scanner_version()
        
        self.assertEqual(result, 'v2')
        mock_get_setting.assert_called_once_with('scanner_version')
    
    @patch('scanner_settings_manager.get_scanner_setting')
    @patch.dict(os.environ, {'SCANNER_VERSION': 'v1'}, clear=False)
    def test_get_scanner_version_fallback_to_env(self, mock_get_setting):
        """DB에 없을 때 .env에서 조회 테스트"""
        mock_get_setting.return_value = None  # DB에 없음
        
        result = get_scanner_version()
        
        self.assertEqual(result, 'v1')  # .env에서 읽음
    
    @patch('scanner_settings_manager.get_scanner_setting')
    def test_get_scanner_v2_enabled_from_db(self, mock_get_setting):
        """DB에서 V2 활성화 여부 조회 테스트"""
        mock_get_setting.return_value = 'true'
        
        result = get_scanner_v2_enabled()
        
        self.assertTrue(result)
        mock_get_setting.assert_called_once_with('scanner_v2_enabled')
    
    @patch('scanner_settings_manager.get_scanner_setting')
    @patch.dict(os.environ, {'SCANNER_V2_ENABLED': 'true'}, clear=False)
    def test_get_scanner_v2_enabled_fallback_to_env(self, mock_get_setting):
        """DB에 없을 때 .env에서 조회 테스트"""
        mock_get_setting.return_value = None  # DB에 없음
        
        result = get_scanner_v2_enabled()
        
        self.assertTrue(result)  # .env에서 읽음


if __name__ == '__main__':
    unittest.main()

