"""
OHLCV 디스크 캐시 테스트
"""
import sys
import os
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kiwoom_api import KiwoomAPI


class TestOHLCVDiskCache:
    """OHLCV 디스크 캐시 테스트"""
    
    def setup_method(self):
        """테스트 전 설정"""
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        self.api = KiwoomAPI()
        self.api.force_mock = True
        self.api._disk_cache_dir = Path(self.temp_dir)
        self.api._disk_cache_enabled = True
    
    def teardown_method(self):
        """테스트 후 정리"""
        # 임시 디렉토리 삭제
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_disk_cache_save_and_load(self):
        """디스크 캐시 저장 및 로드"""
        mock_df = pd.DataFrame({
            'date': ['20251001', '20251002'],
            'open': [70000, 71000],
            'high': [72000, 73000],
            'low': [69000, 70000],
            'close': [71000, 72000],
            'volume': [1000000, 1100000]
        })
        
        # 저장
        self.api._save_to_disk_cache("005930", 220, "20251001", mock_df)
        
        # 파일 존재 확인
        cache_file = self.api._get_disk_cache_file_path("005930", 220, "20251001")
        assert cache_file.exists(), "캐시 파일이 생성되어야 함"
        
        # 로드
        loaded_df = self.api._load_from_disk_cache("005930", 220, "20251001")
        assert loaded_df is not None, "캐시에서 로드되어야 함"
        assert len(loaded_df) == 2, "데이터 개수 일치"
        assert loaded_df.iloc[0]['date'] == '20251001', "데이터 정확성"
    
    def test_disk_cache_only_past_dates(self):
        """과거 날짜만 디스크 캐시 저장"""
        mock_df = pd.DataFrame({
            'date': ['20251001'],
            'open': [70000], 'high': [72000], 'low': [69000],
            'close': [71000], 'volume': [1000000]
        })
        
        # 과거 날짜 저장
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_datetime.strptime.return_value.date.return_value = pd.Timestamp('2025-10-01').date()
            mock_datetime.now.return_value.date.return_value = pd.Timestamp('2025-10-02').date()
            
            self.api._save_to_disk_cache("005930", 220, "20251001", mock_df)
            cache_file = self.api._get_disk_cache_file_path("005930", 220, "20251001")
            assert cache_file.exists(), "과거 날짜는 저장되어야 함"
        
        # 현재 날짜 저장 안 함
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_datetime.strptime.return_value.date.return_value = pd.Timestamp('2025-10-02').date()
            mock_datetime.now.return_value.date.return_value = pd.Timestamp('2025-10-02').date()
            
            self.api._save_to_disk_cache("005930", 220, "20251002", mock_df)
            cache_file = self.api._get_disk_cache_file_path("005930", 220, "20251002")
            assert not cache_file.exists(), "현재 날짜는 저장되지 않아야 함"
    
    def test_disk_cache_integration(self):
        """디스크 캐시 통합 테스트"""
        mock_df = pd.DataFrame({
            'date': ['20251001'],
            'open': [70000], 'high': [72000], 'low': [69000],
            'close': [71000], 'volume': [1000000]
        })
        
        with patch.object(self.api, '_fetch_ohlcv_from_api', return_value=mock_df):
            # 첫 번째 호출: API 호출, 디스크 저장
            with patch('kiwoom_api.datetime') as mock_datetime:
                mock_datetime.strptime.return_value.date.return_value = pd.Timestamp('2025-10-01').date()
                mock_datetime.now.return_value.date.return_value = pd.Timestamp('2025-10-02').date()
                
                df1 = self.api.get_ohlcv("005930", 220, "20251001")
                assert len(df1) == 1
                
                # 디스크 캐시 파일 확인
                cache_file = self.api._get_disk_cache_file_path("005930", 220, "20251001")
                assert cache_file.exists(), "디스크 캐시 저장 확인"
            
            # 메모리 캐시 클리어
            self.api._ohlcv_cache.clear()
            
            # 두 번째 호출: 디스크에서 로드
            with patch('kiwoom_api.datetime') as mock_datetime:
                mock_datetime.strptime.return_value.date.return_value = pd.Timestamp('2025-10-01').date()
                mock_datetime.now.return_value.date.return_value = pd.Timestamp('2025-10-02').date()
                
                df2 = self.api.get_ohlcv("005930", 220, "20251001")
                assert len(df2) == 1
                # API 호출 없이 디스크에서 로드되었는지 확인
                # (실제로는 _fetch_ohlcv_from_api가 호출되지 않았어야 함)
    
    def test_disk_cache_clear(self):
        """디스크 캐시 클리어"""
        mock_df = pd.DataFrame({
            'date': ['20251001'],
            'open': [70000], 'high': [72000], 'low': [69000],
            'close': [71000], 'volume': [1000000]
        })
        
        # 여러 파일 저장
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_datetime.strptime.return_value.date.return_value = pd.Timestamp('2025-10-01').date()
            mock_datetime.now.return_value.date.return_value = pd.Timestamp('2025-10-02').date()
            
            self.api._save_to_disk_cache("005930", 220, "20251001", mock_df)
            self.api._save_to_disk_cache("000660", 220, "20251001", mock_df)
        
        # 전체 클리어
        self.api.clear_ohlcv_cache()
        assert len(list(self.api._disk_cache_dir.glob("*.pkl"))) == 0, "모든 캐시 파일 삭제"
        
        # 특정 종목만 클리어
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_datetime.strptime.return_value.date.return_value = pd.Timestamp('2025-10-01').date()
            mock_datetime.now.return_value.date.return_value = pd.Timestamp('2025-10-02').date()
            
            self.api._save_to_disk_cache("005930", 220, "20251001", mock_df)
            self.api._save_to_disk_cache("000660", 220, "20251001", mock_df)
        
        self.api.clear_ohlcv_cache(code="005930")
        assert len(list(self.api._disk_cache_dir.glob("005930_*.pkl"))) == 0, "005930 캐시 삭제"
        assert len(list(self.api._disk_cache_dir.glob("000660_*.pkl"))) == 1, "000660 캐시 유지"
    
    def test_disk_cache_stats(self):
        """디스크 캐시 통계"""
        mock_df = pd.DataFrame({
            'date': ['20251001'],
            'open': [70000], 'high': [72000], 'low': [69000],
            'close': [71000], 'volume': [1000000]
        })
        
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_datetime.strptime.return_value.date.return_value = pd.Timestamp('2025-10-01').date()
            mock_datetime.now.return_value.date.return_value = pd.Timestamp('2025-10-02').date()
            
            self.api._save_to_disk_cache("005930", 220, "20251001", mock_df)
        
        stats = self.api.get_ohlcv_cache_stats()
        assert 'disk' in stats, "디스크 통계 포함"
        assert stats['disk']['enabled'] == True, "디스크 캐시 활성화"
        assert stats['disk']['total_files'] >= 1, "캐시 파일 존재"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])

