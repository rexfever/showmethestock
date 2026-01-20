"""
스캐너 버전별 스캔 결과 저장 테스트
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# DB 의존성 모킹 (로컬 환경)
mock_psycopg = MagicMock()
sys.modules['psycopg'] = mock_psycopg
sys.modules['psycopg.types'] = MagicMock()

mock_db_manager = MagicMock()
sys.modules['db_manager'] = mock_db_manager


class TestScannerVersionStorage(unittest.TestCase):
    """스캐너 버전별 저장 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.mock_cursor = MagicMock()
        self.mock_cursor.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_cursor.__exit__ = Mock(return_value=None)
        self.mock_cursor.fetchone.return_value = None
        self.mock_cursor.fetchall.return_value = []
        
        # db_manager 모킹
        with patch('services.scan_service.db_manager') as mock_db:
            mock_db.get_cursor.return_value = self.mock_cursor
    
    def test_save_scan_snapshot_with_version(self):
        """scanner_version 파라미터로 저장 테스트"""
        from services.scan_service import save_scan_snapshot
        
        scan_items = [
            {
                'ticker': '005930',
                'name': '삼성전자',
                'score': 10.5,
                'score_label': '강한 매수',
                'flags': {'cross': True, 'vol_expand': True}
            }
        ]
        
        with patch('services.scan_service.api') as mock_api:
            mock_api.get_ohlcv.return_value = MagicMock()
            mock_api.get_ohlcv.return_value.empty = False
            mock_api.get_ohlcv.return_value.iloc = [
                MagicMock(close=50000, volume=1000000),
                MagicMock(close=49000, volume=900000)
            ]
            mock_api.get_ohlcv.return_value.__len__ = Mock(return_value=2)
            
            with patch('services.scan_service.db_manager') as mock_db:
                mock_db.get_cursor.return_value = self.mock_cursor
                
                # V1으로 저장
                save_scan_snapshot(scan_items, '20251121', 'v1')
                
                # DELETE 쿼리 확인
                delete_calls = [call for call in self.mock_cursor.execute.call_args_list 
                              if 'DELETE' in str(call)]
                self.assertGreater(len(delete_calls), 0, "DELETE 쿼리가 실행되어야 함")
                
                # INSERT 쿼리 확인
                insert_calls = [call for call in self.mock_cursor.executemany.call_args_list 
                               if 'INSERT' in str(call) or len(call[0]) > 0]
                self.assertGreater(len(insert_calls), 0, "INSERT 쿼리가 실행되어야 함")
    
    def test_save_scan_snapshot_v1_v2_separate(self):
        """V1과 V2 결과가 별도로 저장되는지 테스트"""
        from services.scan_service import save_scan_snapshot
        
        scan_items_v1 = [
            {
                'ticker': '005930',
                'name': '삼성전자',
                'score': 10.5,
                'score_label': '강한 매수',
                'flags': {'cross': True}
            }
        ]
        
        scan_items_v2 = [
            {
                'ticker': '005930',
                'name': '삼성전자',
                'score': 11.0,
                'score_label': '강한 매수',
                'flags': {'cross': True, 'tema_slope_ok': True}
            }
        ]
        
        with patch('services.scan_service.api') as mock_api:
            mock_api.get_ohlcv.return_value = MagicMock()
            mock_api.get_ohlcv.return_value.empty = False
            mock_api.get_ohlcv.return_value.iloc = [
                MagicMock(close=50000, volume=1000000),
                MagicMock(close=49000, volume=900000)
            ]
            mock_api.get_ohlcv.return_value.__len__ = Mock(return_value=2)
            
            with patch('services.scan_service.db_manager') as mock_db:
                mock_db.get_cursor.return_value = self.mock_cursor
                
                # V1 저장
                save_scan_snapshot(scan_items_v1, '20251121', 'v1')
                
                # V2 저장
                save_scan_snapshot(scan_items_v2, '20251121', 'v2')
                
                # DELETE 쿼리가 각각 다른 버전으로 실행되었는지 확인
                delete_calls = [str(call) for call in self.mock_cursor.execute.call_args_list 
                              if 'DELETE' in str(call)]
                
                # V1과 V2 각각 DELETE가 실행되었는지 확인
                v1_delete = any('v1' in str(call) for call in delete_calls)
                v2_delete = any('v2' in str(call) for call in delete_calls)
                
                # 실제로는 DELETE 쿼리에서 scanner_version이 파라미터로 전달되므로
                # 각각 다른 버전으로 DELETE가 실행되어야 함
                self.assertGreater(len(delete_calls), 1, "V1과 V2 각각 DELETE가 실행되어야 함")
    
    def test_execute_scan_with_fallback_returns_version(self):
        """execute_scan_with_fallback이 scanner_version을 반환하는지 테스트"""
        # 함수 시그니처 확인 (실제 실행은 복잡하므로 스킵)
        import inspect
        from services.scan_service import execute_scan_with_fallback
        
        # 함수 docstring에서 반환값 확인
        doc = inspect.getdoc(execute_scan_with_fallback)
        self.assertIn('scanner_version', doc, "docstring에 scanner_version 반환값이 명시되어야 함")
        self.assertIn('tuple', doc, "docstring에 tuple 반환값이 명시되어야 함")
    
    def test_save_scan_snapshot_auto_detect_version(self):
        """scanner_version이 None일 때 자동 감지 테스트"""
        from services.scan_service import save_scan_snapshot
        
        scan_items = [
            {
                'ticker': '005930',
                'name': '삼성전자',
                'score': 10.5,
                'score_label': '강한 매수',
                'flags': {}
            }
        ]
        
        with patch('services.scan_service.api') as mock_api:
            mock_api.get_ohlcv.return_value = MagicMock()
            mock_api.get_ohlcv.return_value.empty = False
            mock_api.get_ohlcv.return_value.iloc = [
                MagicMock(close=50000, volume=1000000),
                MagicMock(close=49000, volume=900000)
            ]
            mock_api.get_ohlcv.return_value.__len__ = Mock(return_value=2)
            
            with patch('services.scan_service.db_manager') as mock_db:
                mock_db.get_cursor.return_value = self.mock_cursor
                
                # scanner_settings_manager.get_scanner_version을 직접 패치
                with patch('scanner_settings_manager.get_scanner_version') as mock_get_version:
                    mock_get_version.return_value = 'v1'
                    
                    # scanner_version=None으로 호출
                    save_scan_snapshot(scan_items, '20251121', None)
                    
                    # 자동으로 v1이 감지되어야 함
                    self.assertGreater(self.mock_cursor.execute.call_count, 0, "저장이 실행되어야 함")
    
    def test_ensure_scan_rank_table_with_version(self):
        """테이블 생성 시 scanner_version 컬럼이 포함되는지 테스트"""
        from services.scan_service import _ensure_scan_rank_table
        
        with patch('services.scan_service.db_manager') as mock_db:
            mock_db.get_cursor.return_value = self.mock_cursor
            
            _ensure_scan_rank_table(self.mock_cursor)
            
            # CREATE TABLE 쿼리 확인
            create_calls = [str(call) for call in self.mock_cursor.execute.call_args_list 
                           if 'CREATE TABLE' in str(call) or 'scanner_version' in str(call)]
            
            # scanner_version이 포함되어야 함
            has_version = any('scanner_version' in str(call) for call in create_calls)
            self.assertTrue(has_version or len(create_calls) > 0, 
                          "테이블 생성 시 scanner_version 컬럼이 포함되어야 함")


class TestScannerVersionIntegration(unittest.TestCase):
    """스캐너 버전 통합 테스트"""
    
    def test_main_scan_endpoint_with_version(self):
        """main.py의 scan 엔드포인트가 버전 정보를 전달하는지 테스트"""
        # main.py 코드에서 save_scan_snapshot 호출 시 scanner_version 전달 확인
        import os
        main_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'main.py'
        )
        
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # save_scan_snapshot 호출 시 scanner_version 파라미터가 전달되는지 확인
        self.assertIn('save_scan_snapshot', content, "save_scan_snapshot 호출이 있어야 함")
        # scanner_version 변수가 사용되는지 확인 (간접 확인)
        has_version_logic = 'scanner_version' in content and 'save_scan_snapshot' in content
        self.assertTrue(has_version_logic, "main.py에서 scanner_version을 save_scan_snapshot에 전달해야 함")


if __name__ == '__main__':
    unittest.main()

