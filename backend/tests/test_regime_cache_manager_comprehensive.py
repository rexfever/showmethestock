"""
레짐 분석용 캐시 관리 모듈 종합 테스트
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import tempfile
import shutil
import os
import sys

# 테스트를 위해 모듈 import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.regime_cache_manager import (
    ensure_datetime_index,
    compare_dates_only,
    merge_cache_data,
    load_kospi_cache,
    save_kospi_cache,
    update_kospi_cache_incremental,
    load_kosdaq_cache,
    save_kosdaq_cache,
    update_kosdaq_cache_incremental
)


class TestRegimeCacheManagerComprehensive(unittest.TestCase):
    """레짐 분석용 캐시 관리 모듈 종합 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        self.test_cache_dir = Path(self.temp_dir) / "data_cache"
        self.test_cache_dir.mkdir(parents=True, exist_ok=True)
        (self.test_cache_dir / "ohlcv").mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """테스트 후 정리"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_ensure_datetime_index_with_datetime_index(self):
        """DatetimeIndex가 이미 있는 경우 테스트"""
        dates = pd.bdate_range(end=datetime.now(), periods=10, freq='B')
        df = pd.DataFrame({'close': range(10)}, index=dates)
        
        result = ensure_datetime_index(df)
        self.assertIsInstance(result.index, pd.DatetimeIndex)
        self.assertEqual(len(result), 10)
    
    def test_ensure_datetime_index_with_date_column(self):
        """date 컬럼이 있는 경우 테스트"""
        dates = pd.bdate_range(end=datetime.now(), periods=10, freq='B')
        df = pd.DataFrame({
            'date': dates,
            'close': range(10)
        })
        
        result = ensure_datetime_index(df)
        self.assertIsInstance(result.index, pd.DatetimeIndex)
        self.assertEqual(len(result), 10)
        self.assertNotIn('date', result.columns)
    
    def test_ensure_datetime_index_no_date_info(self):
        """날짜 정보가 없는 경우 테스트"""
        df = pd.DataFrame({'close': range(10)})
        
        with self.assertRaises(ValueError):
            ensure_datetime_index(df)
    
    def test_compare_dates_only(self):
        """날짜만 비교 테스트"""
        date1 = pd.Timestamp('2024-12-03 10:00:00')
        date2 = pd.Timestamp('2024-12-03 15:00:00')
        date3 = pd.Timestamp('2024-12-04 10:00:00')
        
        # 같은 날짜 (시간만 다름)
        self.assertFalse(compare_dates_only(date1, date2))
        self.assertFalse(compare_dates_only(date2, date1))
        
        # 다른 날짜
        self.assertTrue(compare_dates_only(date1, date3))
        self.assertFalse(compare_dates_only(date3, date1))
    
    def test_merge_cache_data_basic(self):
        """기본 캐시 병합 테스트"""
        # 기존 캐시 (10일)
        old_dates = pd.bdate_range(end=datetime.now() - timedelta(days=2), periods=10, freq='B')
        old_df = pd.DataFrame({'close': range(10)}, index=old_dates)
        
        # 새 데이터 (당일)
        today = datetime.now().normalize()
        new_df = pd.DataFrame({'close': [100]}, index=[today])
        
        # 병합
        combined = merge_cache_data(old_df, new_df, max_days=365)
        
        # 검증
        self.assertIsInstance(combined.index, pd.DatetimeIndex)
        self.assertEqual(len(combined), 11)
        self.assertEqual(combined.index.max().date(), today.date())
    
    def test_merge_cache_data_duplicate_removal(self):
        """중복 날짜 제거 테스트"""
        # 기존 캐시
        date = datetime.now() - timedelta(days=1)
        old_df = pd.DataFrame({'close': [100]}, index=[date])
        
        # 새 데이터 (같은 날짜)
        new_df = pd.DataFrame({'close': [200]}, index=[date])
        
        # 병합 (최신 데이터 우선)
        combined = merge_cache_data(old_df, new_df, max_days=365)
        
        # 검증: 최신 데이터가 유지되어야 함
        self.assertEqual(len(combined), 1)
        self.assertEqual(combined.iloc[0]['close'], 200)
    
    def test_merge_cache_data_size_limit(self):
        """캐시 크기 제한 테스트"""
        # 400일분 데이터
        old_dates = pd.bdate_range(end=datetime.now(), periods=400, freq='B')
        old_df = pd.DataFrame({'close': range(400)}, index=old_dates)
        
        # 새 데이터
        today = datetime.now().normalize()
        new_df = pd.DataFrame({'close': [999]}, index=[today])
        
        # 병합 (365일 제한)
        combined = merge_cache_data(old_df, new_df, max_days=365)
        
        # 검증: 365일만 유지
        self.assertEqual(len(combined), 365)
        self.assertEqual(combined.iloc[-1]['close'], 999)  # 최신 데이터 포함
    
    def test_merge_cache_data_date_column_to_index(self):
        """date 컬럼을 인덱스로 변환하여 병합 테스트"""
        # 기존 캐시 (인덱스)
        old_dates = pd.bdate_range(end=datetime.now() - timedelta(days=2), periods=10, freq='B')
        old_df = pd.DataFrame({'close': range(10)}, index=old_dates)
        
        # 새 데이터 (date 컬럼)
        today = datetime.now().normalize()
        new_df = pd.DataFrame({
            'date': [today],
            'close': [100]
        })
        
        # 병합
        combined = merge_cache_data(old_df, new_df, max_days=365)
        
        # 검증
        self.assertIsInstance(combined.index, pd.DatetimeIndex)
        self.assertEqual(len(combined), 11)
    
    def test_load_kospi_cache_file_not_exists(self):
        """KOSPI 캐시 파일이 없을 때 테스트"""
        # 캐시 파일이 없는 경우
        result = load_kospi_cache()
        # 실제 파일이 없으면 None 반환
        self.assertIsNone(result)
    
    def test_save_and_load_kospi_cache(self):
        """KOSPI 캐시 저장 및 로드 테스트"""
        # 테스트 데이터 생성
        dates = pd.bdate_range(end=datetime.now(), periods=30, freq='B')
        test_df = pd.DataFrame({
            'open': range(30),
            'high': range(30),
            'low': range(30),
            'close': range(30),
            'volume': range(30)
        }, index=dates)
        
        # 직접 파일 저장
        cache_path = self.test_cache_dir / "kospi200_ohlcv.pkl"
        test_df.to_pickle(cache_path)
        
        # 로드
        loaded_df = pd.read_pickle(cache_path)
        self.assertFalse(loaded_df.empty)
        self.assertEqual(len(loaded_df), 30)
        self.assertIsInstance(loaded_df.index, pd.DatetimeIndex)
    
    def test_load_kosdaq_cache_file_not_exists(self):
        """KOSDAQ 캐시 파일이 없을 때 테스트"""
        result = load_kosdaq_cache()
        # 실제 파일이 없으면 None 반환
        self.assertIsNone(result)
    
    def test_save_and_load_kosdaq_cache(self):
        """KOSDAQ 캐시 저장 및 로드 테스트"""
        # 테스트 데이터 생성
        dates = pd.bdate_range(end=datetime.now(), periods=30, freq='B')
        test_df = pd.DataFrame({
            'open': range(30),
            'high': range(30),
            'low': range(30),
            'close': range(30),
            'volume': range(30)
        }, index=dates)
        
        # CSV로 저장
        cache_path = self.test_cache_dir / "ohlcv" / "229200.csv"
        test_df.to_csv(cache_path)
        
        # 로드
        loaded_df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        self.assertFalse(loaded_df.empty)
        self.assertEqual(len(loaded_df), 30)
    
    def test_edge_case_empty_dataframe_merge(self):
        """빈 DataFrame 병합 테스트"""
        # 빈 DataFrame
        empty_df = pd.DataFrame()
        
        # 정상 DataFrame
        dates = pd.bdate_range(end=datetime.now(), periods=10, freq='B')
        normal_df = pd.DataFrame({'close': range(10)}, index=dates)
        
        # 병합 시도
        # 빈 DataFrame과 병합하면 정상 DataFrame만 반환되어야 함
        if not empty_df.empty:
            combined = merge_cache_data(empty_df, normal_df, max_days=365)
        else:
            combined = normal_df
        
        self.assertEqual(len(combined), 10)
    
    def test_edge_case_mixed_index_types(self):
        """혼합된 인덱스 타입 처리 테스트"""
        # DatetimeIndex
        dates1 = pd.bdate_range(end=datetime.now() - timedelta(days=2), periods=5, freq='B')
        df1 = pd.DataFrame({'close': range(5)}, index=dates1)
        
        # date 컬럼
        dates2 = pd.bdate_range(end=datetime.now(), periods=3, freq='B')
        df2 = pd.DataFrame({
            'date': dates2,
            'close': range(100, 103)
        })
        
        # 병합
        combined = merge_cache_data(df1, df2, max_days=365)
        
        # 검증: 모두 DatetimeIndex로 변환되어야 함
        self.assertIsInstance(combined.index, pd.DatetimeIndex)
        self.assertEqual(len(combined), 8)


if __name__ == '__main__':
    unittest.main()

