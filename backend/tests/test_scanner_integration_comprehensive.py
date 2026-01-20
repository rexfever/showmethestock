"""
스캐너 통합 테스트 - 상세 테스트
"""
import unittest
from unittest.mock import patch, MagicMock, Mock, call
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner_factory import get_scanner, scan_with_scanner
from scanner_settings_manager import (
    get_scanner_setting, 
    set_scanner_setting, 
    get_all_scanner_settings,
    get_scanner_version,
    get_scanner_v2_enabled
)
from market_analyzer import MarketCondition


class TestScannerSettingsManager(unittest.TestCase):
    """스캐너 설정 관리자 테스트"""
    
    @patch('scanner_settings_manager.db_manager')
    def test_get_scanner_setting_exists(self, mock_db_manager):
        """DB에 설정이 있을 때 조회 테스트"""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.fetchone.return_value = ('v2',)
        
        mock_db_manager.get_cursor.return_value = mock_cursor
        
        result = get_scanner_setting('scanner_version', 'v1')
        
        self.assertEqual(result, 'v2')
        mock_cursor.execute.assert_called()
    
    @patch('scanner_settings_manager.db_manager')
    def test_get_scanner_setting_not_exists(self, mock_db_manager):
        """DB에 설정이 없을 때 기본값 반환 테스트"""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.fetchone.return_value = None
        
        mock_db_manager.get_cursor.return_value = mock_cursor
        
        result = get_scanner_setting('scanner_version', 'v1')
        
        self.assertEqual(result, 'v1')
    
    @patch('scanner_settings_manager.db_manager')
    def test_set_scanner_setting_new(self, mock_db_manager):
        """새로운 설정 저장 테스트"""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        mock_db_manager.get_cursor.return_value = mock_cursor
        
        result = set_scanner_setting('scanner_version', 'v2', '설명', 'admin@test.com')
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called()
    
    @patch('scanner_settings_manager.db_manager')
    def test_set_scanner_setting_update(self, mock_db_manager):
        """기존 설정 업데이트 테스트"""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        mock_db_manager.get_cursor.return_value = mock_cursor
        
        result = set_scanner_setting('scanner_version', 'v2', '업데이트 설명', 'admin@test.com')
        
        self.assertTrue(result)
        # ON CONFLICT DO UPDATE가 포함된 SQL 확인
        call_args = mock_cursor.execute.call_args[0][0]
        self.assertIn('ON CONFLICT', call_args)
    
    @patch('scanner_settings_manager.db_manager')
    def test_get_all_scanner_settings(self, mock_db_manager):
        """모든 설정 조회 테스트"""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.fetchall.return_value = [
            ('scanner_version', 'v2'),
            ('scanner_v2_enabled', 'true')
        ]
        
        mock_db_manager.get_cursor.return_value = mock_cursor
        
        result = get_all_scanner_settings()
        
        self.assertEqual(result['scanner_version'], 'v2')
        self.assertEqual(result['scanner_v2_enabled'], 'true')
    
    @patch('scanner_settings_manager.get_scanner_setting')
    @patch.dict(os.environ, {}, clear=True)
    def test_get_scanner_version_db_priority(self, mock_get_setting):
        """DB 우선 조회 테스트"""
        mock_get_setting.return_value = 'v2'
        
        result = get_scanner_version()
        
        self.assertEqual(result, 'v2')
        mock_get_setting.assert_called_once_with('scanner_version')
    
    @patch('scanner_settings_manager.get_scanner_setting')
    @patch.dict(os.environ, {'SCANNER_VERSION': 'v1'}, clear=False)
    def test_get_scanner_version_env_fallback(self, mock_get_setting):
        """DB 없을 때 .env fallback 테스트"""
        mock_get_setting.return_value = None
        
        result = get_scanner_version()
        
        self.assertEqual(result, 'v1')
    
    @patch('scanner_settings_manager.get_scanner_setting')
    def test_get_scanner_v2_enabled_true(self, mock_get_setting):
        """V2 활성화 true 테스트"""
        mock_get_setting.return_value = 'true'
        
        result = get_scanner_v2_enabled()
        
        self.assertTrue(result)
    
    @patch('scanner_settings_manager.get_scanner_setting')
    def test_get_scanner_v2_enabled_false(self, mock_get_setting):
        """V2 활성화 false 테스트"""
        mock_get_setting.return_value = 'false'
        
        result = get_scanner_v2_enabled()
        
        self.assertFalse(result)
    
    @patch('scanner_settings_manager.get_scanner_setting')
    @patch.dict(os.environ, {'SCANNER_V2_ENABLED': 'true'}, clear=False)
    def test_get_scanner_v2_enabled_env_fallback(self, mock_get_setting):
        """DB 없을 때 .env fallback 테스트"""
        mock_get_setting.return_value = None
        
        result = get_scanner_v2_enabled()
        
        self.assertTrue(result)


class TestConfigScannerSettings(unittest.TestCase):
    """Config의 스캐너 설정 property 테스트"""
    
    @patch('scanner_settings_manager.get_scanner_version')
    @patch('scanner_settings_manager.get_scanner_v2_enabled')
    def test_config_scanner_version_property(self, mock_v2_enabled, mock_version):
        """config.scanner_version property 테스트"""
        mock_version.return_value = 'v2'
        mock_v2_enabled.return_value = True
        
        from config import config
        
        # property이므로 직접 접근
        version = config.scanner_version
        v2_enabled = config.scanner_v2_enabled
        
        self.assertEqual(version, 'v2')
        self.assertTrue(v2_enabled)
        mock_version.assert_called_once()
        mock_v2_enabled.assert_called_once()
    
    @patch('scanner_settings_manager.get_scanner_version')
    @patch.dict(os.environ, {'SCANNER_VERSION': 'v1'}, clear=False)
    def test_config_scanner_version_fallback(self, mock_version):
        """DB 연결 실패 시 .env fallback 테스트"""
        mock_version.side_effect = Exception("DB 연결 실패")
        
        from config import config
        
        version = config.scanner_version
        
        self.assertEqual(version, 'v1')


class TestScannerFactoryComprehensive(unittest.TestCase):
    """스캐너 팩토리 상세 테스트"""
    
    @patch('scanner_v2.ScannerV2')
    @patch('config.config')
    def test_get_scanner_version_none_uses_config(self, mock_config, mock_scanner_v2):
        """version=None일 때 config에서 읽기"""
        mock_config.scanner_version = 'v2'
        mock_config.scanner_v2_enabled = True
        mock_config.market_analysis_enable = True
        
        mock_instance = MagicMock()
        mock_scanner_v2.return_value = mock_instance
        
        scanner = get_scanner()
        
        self.assertEqual(scanner, mock_instance)
    
    @patch('config.config')
    def test_get_scanner_version_explicit(self, mock_config):
        """명시적 version 지정 테스트"""
        mock_config.scanner_v2_enabled = False
        mock_config.market_analysis_enable = True
        
        # v1 명시
        scanner_v1 = get_scanner('v1')
        self.assertTrue(callable(scanner_v1))
        
        # v2 명시하지만 비활성화
        scanner_v2_disabled = get_scanner('v2')
        self.assertTrue(callable(scanner_v2_disabled))  # v1으로 fallback
    
    @patch('scanner_factory.get_scanner')
    @patch('config.config')
    def test_scan_with_scanner_version_auto_detect(self, mock_config, mock_get_scanner):
        """version=None일 때 자동 감지 테스트"""
        mock_config.scanner_version = 'v2'
        mock_config.scanner_v2_enabled = True
        
        mock_v2_scanner = MagicMock()
        from scanner_v2.core.scanner import ScanResult
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
        
        results = scan_with_scanner(['005930'], None, '20251119', None, None)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['ticker'], '005930')
    
    @patch('scanner_factory.get_scanner')
    @patch('config.config')
    def test_scan_with_scanner_preset_overrides_all_fields(self, mock_config, mock_get_scanner):
        """preset_overrides의 모든 필드 반영 테스트"""
        mock_config.scanner_version = 'v2'
        mock_config.scanner_v2_enabled = True
        mock_config.vol_ma20_mult = 1.2
        
        mock_v2_scanner = MagicMock()
        mock_v2_scanner.scan.return_value = []
        mock_get_scanner.return_value = mock_v2_scanner
        
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
            'vol_ma5_mult': 3.0,
            'vol_ma20_mult': 1.5,
            'gap_max': 0.025,
            'ext_from_tema20_max': 0.030
        }
        
        scan_with_scanner(['005930'], preset_overrides, '20251119', market_condition, 'v2')
        
        # market_condition이 수정되었는지 확인
        call_args = mock_v2_scanner.scan.call_args
        modified_mc = call_args[0][2]
        
        self.assertEqual(modified_mc.min_signals, 4)
        self.assertEqual(modified_mc.vol_ma5_mult, 3.0)
        self.assertEqual(modified_mc.vol_ma20_mult, 1.5)
        self.assertEqual(modified_mc.gap_max, 0.025)
        self.assertEqual(modified_mc.ext_from_tema20_max, 0.030)
    
    @patch('scanner_factory.get_scanner')
    @patch('config.config')
    def test_scan_with_scanner_preset_overrides_no_market_condition(self, mock_config, mock_get_scanner):
        """preset_overrides가 있지만 market_condition이 None일 때"""
        mock_config.scanner_version = 'v2'
        mock_config.scanner_v2_enabled = True
        
        mock_v2_scanner = MagicMock()
        mock_v2_scanner.scan.return_value = []
        mock_get_scanner.return_value = mock_v2_scanner
        
        preset_overrides = {'min_signals': 4}
        
        # market_condition이 None이면 preset_overrides 무시
        scan_with_scanner(['005930'], preset_overrides, '20251119', None, 'v2')
        
        # 정상적으로 호출되었는지 확인
        mock_v2_scanner.scan.assert_called_once()
        call_args = mock_v2_scanner.scan.call_args
        self.assertIsNone(call_args[0][2])  # market_condition이 None
    
    @patch('scanner_factory.get_scanner')
    @patch('config.config')
    def test_scan_with_scanner_v1_preset_overrides(self, mock_config, mock_get_scanner):
        """V1에서 preset_overrides 전달 테스트"""
        mock_config.scanner_version = 'v1'
        
        mock_v1_scanner = MagicMock()
        mock_v1_scanner.return_value = [{'ticker': '005930', 'score': 10}]
        mock_get_scanner.return_value = mock_v1_scanner
        
        preset_overrides = {'min_signals': 4}
        
        results = scan_with_scanner(['005930'], preset_overrides, '20251119', None, 'v1')
        
        # V1 스캐너에 preset_overrides가 전달되었는지 확인
        mock_v1_scanner.assert_called_once_with(['005930'], preset_overrides, '20251119', None)


class TestScanServiceIntegration(unittest.TestCase):
    """scan_service.py 통합 테스트"""
    
    @patch('services.scan_service.scan_with_scanner')
    @patch('services.scan_service.config')
    def test_scan_service_uses_scan_with_scanner(self, mock_config, mock_scan):
        """scan_service가 scan_with_scanner를 사용하는지 테스트"""
        from services.scan_service import execute_scan_with_fallback
        
        mock_config.fallback_enable = False
        mock_config.top_k = 5
        mock_scan.return_value = [
            {'ticker': '005930', 'score': 10, 'match': True}
        ]
        
        results, step = execute_scan_with_fallback(['005930'], '20251119', None)
        
        # scan_with_scanner가 호출되었는지 확인
        mock_scan.assert_called()
        self.assertEqual(len(results), 1)
    
    @patch('services.scan_service.scan_with_scanner')
    @patch('services.scan_service.config')
    def test_scan_service_fallback_steps(self, mock_config, mock_scan):
        """Fallback 단계별 scan_with_scanner 호출 테스트"""
        from services.scan_service import execute_scan_with_fallback
        
        mock_config.fallback_enable = True
        mock_config.fallback_target_min_bull = 3
        mock_config.fallback_target_max_bull = 5
        mock_config.top_k = 5
        mock_config.fallback_presets = [
            {},  # Step 0
            {'gap_max': 0.020},  # Step 1
            {'gap_max': 0.025}   # Step 3
        ]
        
        # Step 0에서 목표 미달, Step 1에서 목표 달성
        mock_scan.side_effect = [
            [{'ticker': '001', 'score': 10, 'match': True}],  # Step 0: 1개만
            [  # Step 1: 3개
                {'ticker': '001', 'score': 10, 'match': True},
                {'ticker': '002', 'score': 9, 'match': True},
                {'ticker': '003', 'score': 8, 'match': True}
            ]
        ]
        
        results, step = execute_scan_with_fallback(['001', '002', '003'], '20251119', None)
        
        # Step 0과 Step 1이 호출되었는지 확인
        self.assertEqual(mock_scan.call_count, 2)
        self.assertEqual(step, 1)
        self.assertEqual(len(results), 3)


class TestEndToEnd(unittest.TestCase):
    """End-to-End 테스트"""
    
    @patch('scanner_settings_manager.db_manager')
    @patch('scanner_factory.config')
    def test_db_to_scanner_flow(self, mock_config, mock_db_manager):
        """DB 설정 → Config → Scanner 흐름 테스트"""
        # DB 모킹
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.fetchone.return_value = ('v2',)
        mock_db_manager.get_cursor.return_value = mock_cursor
        
        # Config 모킹
        mock_config.market_analysis_enable = True
        
        # Scanner V2 모킹
        with patch('scanner_factory.ScannerV2') as mock_scanner_v2:
            mock_instance = MagicMock()
            mock_scanner_v2.return_value = mock_instance
            
            # DB에서 설정 읽기
            version = get_scanner_version()
            self.assertEqual(version, 'v2')
            
            # Scanner 가져오기
            scanner = get_scanner(version)
            self.assertEqual(scanner, mock_instance)


if __name__ == '__main__':
    unittest.main()

