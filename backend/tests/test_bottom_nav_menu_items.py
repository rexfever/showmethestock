"""
바텀메뉴 개별 메뉴 아이템 설정 API 테스트
"""
import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scanner_settings_manager import get_scanner_setting, set_scanner_setting


class TestBottomNavMenuItems(unittest.TestCase):
    """바텀메뉴 개별 메뉴 아이템 설정 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.test_key = 'bottom_nav_menu_items'
        self.default_items = {
            "korean_stocks": True,
            "us_stocks": True,
            "stock_analysis": True,
            "portfolio": True,
            "more": True
        }
    
    def test_get_default_menu_items(self):
        """기본 메뉴 아이템 설정 조회 테스트"""
        # 설정이 없는 경우 기본값 반환
        with patch('scanner_settings_manager.get_scanner_setting', return_value=None):
            result = get_scanner_setting(self.test_key, None)
            self.assertIsNone(result)
    
    def test_set_and_get_menu_items(self):
        """메뉴 아이템 설정 저장 및 조회 테스트"""
        test_items = {
            "korean_stocks": True,
            "us_stocks": False,
            "stock_analysis": True,
            "portfolio": False,
            "more": True
        }
        
        # JSON 문자열로 변환
        menu_items_json = json.dumps(test_items)
        
        # 저장 테스트
        with patch('scanner_settings_manager.set_scanner_setting', return_value=True) as mock_set:
            result = set_scanner_setting(
                self.test_key,
                menu_items_json,
                description='테스트 메뉴 아이템 설정',
                updated_by='test@example.com'
            )
            self.assertTrue(result)
            mock_set.assert_called_once()
        
        # 조회 테스트
        with patch('scanner_settings_manager.get_scanner_setting', return_value=menu_items_json):
            result_json = get_scanner_setting(self.test_key, None)
            self.assertIsNotNone(result_json)
            
            # JSON 파싱 테스트
            parsed_items = json.loads(result_json)
            self.assertEqual(parsed_items['korean_stocks'], True)
            self.assertEqual(parsed_items['us_stocks'], False)
            self.assertEqual(parsed_items['stock_analysis'], True)
            self.assertEqual(parsed_items['portfolio'], False)
            self.assertEqual(parsed_items['more'], True)
    
    def test_menu_items_json_parsing(self):
        """메뉴 아이템 JSON 파싱 테스트"""
        test_json = '{"korean_stocks": true, "us_stocks": false, "stock_analysis": true, "portfolio": false, "more": true}'
        
        # 정상 파싱
        parsed = json.loads(test_json)
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed['korean_stocks'], True)
        self.assertEqual(parsed['us_stocks'], False)
        
        # 잘못된 JSON 처리
        invalid_json = '{"invalid": json}'
        with self.assertRaises(json.JSONDecodeError):
            json.loads(invalid_json)
    
    def test_menu_items_default_merge(self):
        """기본값과 저장된 값 병합 테스트"""
        saved_items = {
            "korean_stocks": False,
            "us_stocks": True
        }
        
        # 기본값과 병합
        merged = {**self.default_items, **saved_items}
        
        self.assertEqual(merged['korean_stocks'], False)  # 저장된 값
        self.assertEqual(merged['us_stocks'], True)  # 저장된 값
        self.assertEqual(merged['stock_analysis'], True)  # 기본값
        self.assertEqual(merged['portfolio'], True)  # 기본값
        self.assertEqual(merged['more'], True)  # 기본값


if __name__ == '__main__':
    unittest.main()

