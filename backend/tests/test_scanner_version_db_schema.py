"""
스캐너 버전 DB 스키마 테스트
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestScannerVersionDBSchema(unittest.TestCase):
    """DB 스키마 변경 테스트"""
    
    def test_migration_script_exists(self):
        """마이그레이션 스크립트가 존재하는지 확인"""
        migration_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'sql',
            'add_scanner_version_to_scan_rank.sql'
        )
        self.assertTrue(os.path.exists(migration_file), 
                       f"마이그레이션 스크립트가 존재해야 함: {migration_file}")
    
    def test_migration_script_content(self):
        """마이그레이션 스크립트 내용 확인"""
        migration_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'sql',
            'add_scanner_version_to_scan_rank.sql'
        )
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 필수 내용 확인
        self.assertIn('scanner_version', content, "scanner_version 컬럼 추가가 포함되어야 함")
        self.assertIn('PRIMARY KEY', content, "Primary Key 변경이 포함되어야 함")
        self.assertIn('idx_scan_rank_scanner_version', content, "인덱스 생성이 포함되어야 함")
    
    def test_schema_file_updated(self):
        """postgres_schema.sql이 업데이트되었는지 확인"""
        schema_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'sql',
            'postgres_schema.sql'
        )
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # scanner_version 컬럼 확인
        self.assertIn('scanner_version', content, "scanner_version 컬럼이 포함되어야 함")
        
        # Primary Key에 scanner_version 포함 확인
        # PRIMARY KEY (date, code, scanner_version) 형태
        pk_pattern = 'PRIMARY KEY.*scanner_version'
        import re
        self.assertTrue(re.search(pk_pattern, content, re.IGNORECASE | re.DOTALL),
                       "Primary Key에 scanner_version이 포함되어야 함")


if __name__ == '__main__':
    unittest.main()

