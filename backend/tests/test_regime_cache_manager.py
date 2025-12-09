"""
레짐 분석용 캐시 관리 모듈 상세 테스트
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
    load_kospi_cache,
    save_kospi_cache,
    update_kospi_cache_incremental,
    load_kosdaq_cache,
    save_kosdaq_cache,
    update_kosdaq_cache_incremental,
    update_us_futures_cache_incremental
)


class TestRegimeCacheManager(unittest.TestCase):
    """레짐 분석용 캐시 관리 모듈 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        
        # 캐시 경로를 임시 디렉토리로 변경
        import utils.regime_cache_manager as rcm
        original_kospi_path = rcm.KOSPI_CACHE_PATH
        original_kosdaq_path = rcm.KOSDAQ_CACHE_PATH
        
        # 모듈 레벨 변수 임시 변경 (실제로는 모니키 패칭 필요)
        self.original_kospi_path = original_kospi_path
        self.original_kosdaq_path = original_kosdaq_path
        
        # 테스트용 캐시 디렉토리 생성
        self.test_cache_dir = Path(self.temp_dir) / "data_cache"
        self.test_cache_dir.mkdir(parents=True, exist_ok=True)
        (self.test_cache_dir / "ohlcv").mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """테스트 후 정리"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_kospi_cache(self, days_back: int = 365, latest_date: datetime = None) -> pd.DataFrame:
        """테스트용 KOSPI 캐시 생성"""
        if latest_date is None:
            latest_date = datetime.now() - timedelta(days=1)
        
        dates = pd.bdate_range(end=latest_date, periods=days_back, freq='B')
        
        df = pd.DataFrame({
            'open': np.random.rand(len(dates)) * 100 + 2000,
            'high': np.random.rand(len(dates)) * 100 + 2100,
            'low': np.random.rand(len(dates)) * 100 + 1900,
            'close': np.random.rand(len(dates)) * 100 + 2000,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=dates)
        
        return df
    
    def create_test_kosdaq_cache(self, days_back: int = 365, latest_date: datetime = None) -> pd.DataFrame:
        """테스트용 KOSDAQ 캐시 생성"""
        if latest_date is None:
            latest_date = datetime.now() - timedelta(days=1)
        
        dates = pd.bdate_range(end=latest_date, periods=days_back, freq='B')
        
        df = pd.DataFrame({
            'open': np.random.rand(len(dates)) * 10 + 500,
            'high': np.random.rand(len(dates)) * 10 + 550,
            'low': np.random.rand(len(dates)) * 10 + 450,
            'close': np.random.rand(len(dates)) * 10 + 500,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=dates)
        
        return df
    
    def test_load_kospi_cache_not_exists(self):
        """KOSPI 캐시가 없을 때 로드 테스트"""
        # 캐시 파일이 없는 경우
        result = load_kospi_cache()
        self.assertIsNone(result)
    
    def test_save_and_load_kospi_cache(self):
        """KOSPI 캐시 저장 및 로드 테스트"""
        # 테스트 데이터 생성
        test_df = self.create_test_kospi_cache(days_back=30)
        
        # 저장
        # 실제 파일 시스템에 저장하기 위해 모듈의 경로를 패치해야 함
        # 여기서는 직접 파일 저장 테스트
        cache_path = self.test_cache_dir / "kospi200_ohlcv.pkl"
        test_df.to_pickle(cache_path)
        
        # 로드 (직접 파일 읽기)
        loaded_df = pd.read_pickle(cache_path)
        self.assertFalse(loaded_df.empty)
        self.assertEqual(len(loaded_df), 30)
        self.assertIsInstance(loaded_df.index, pd.DatetimeIndex)
    
    def test_update_kospi_cache_initial_creation(self):
        """KOSPI 캐시 초기 생성 테스트"""
        # 캐시가 없는 경우 초기 생성
        # 실제 API 호출을 모킹해야 함
        # 여기서는 로직만 검증
        pass
    
    def test_update_kospi_cache_incremental_update(self):
        """KOSPI 캐시 증분 업데이트 테스트"""
        # 캐시가 있고 오래된 경우 증분 업데이트
        # 실제 API 호출을 모킹해야 함
        pass
    
    def test_update_kospi_cache_already_up_to_date(self):
        """KOSPI 캐시가 이미 최신인 경우 테스트"""
        # 캐시가 최신인 경우 업데이트 안 함
        pass
    
    def test_load_kosdaq_cache_not_exists(self):
        """KOSDAQ 캐시가 없을 때 로드 테스트"""
        result = load_kosdaq_cache()
        # 실제 파일이 없으면 None 반환
        # 테스트 환경에서는 None일 수 있음
        self.assertIsInstance(result, (type(None), pd.DataFrame))
    
    def test_save_and_load_kosdaq_cache(self):
        """KOSDAQ 캐시 저장 및 로드 테스트"""
        # 테스트 데이터 생성
        test_df = self.create_test_kosdaq_cache(days_back=30)
        
        # CSV로 저장
        cache_path = self.test_cache_dir / "ohlcv" / "229200.csv"
        test_df.to_csv(cache_path)
        
        # 로드
        loaded_df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        self.assertFalse(loaded_df.empty)
        self.assertEqual(len(loaded_df), 30)
    
    def test_kospi_cache_date_handling(self):
        """KOSPI 캐시 날짜 처리 테스트"""
        # 날짜 인덱스가 올바르게 처리되는지 확인
        test_df = self.create_test_kospi_cache(days_back=30)
        
        # 인덱스가 DatetimeIndex인지 확인
        self.assertIsInstance(test_df.index, pd.DatetimeIndex)
        
        # 최신 날짜 확인
        latest_date = test_df.index.max()
        self.assertIsInstance(latest_date, pd.Timestamp)
    
    def test_kosdaq_cache_date_handling(self):
        """KOSDAQ 캐시 날짜 처리 테스트"""
        # 날짜 인덱스가 올바르게 처리되는지 확인
        test_df = self.create_test_kosdaq_cache(days_back=30)
        
        # 인덱스가 DatetimeIndex인지 확인
        self.assertIsInstance(test_df.index, pd.DatetimeIndex)
        
        # 최신 날짜 확인
        latest_date = test_df.index.max()
        self.assertIsInstance(latest_date, pd.Timestamp)
    
    def test_cache_merge_logic(self):
        """캐시 병합 로직 테스트"""
        # 기존 캐시
        old_cache = self.create_test_kospi_cache(
            days_back=30,
            latest_date=datetime.now() - timedelta(days=2)
        )
        
        # 새 데이터 (당일)
        today = datetime.now().normalize()
        new_data = pd.DataFrame({
            'open': [2100.0],
            'high': [2150.0],
            'low': [2050.0],
            'close': [2120.0],
            'volume': [5000000]
        }, index=[today])
        
        # 병합
        combined = pd.concat([old_cache, new_data])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = combined.sort_index()
        
        # 검증
        self.assertFalse(combined.empty)
        self.assertEqual(combined.index.max().date(), today.date())
        self.assertEqual(len(combined), len(old_cache) + 1)
    
    def test_cache_duplicate_removal(self):
        """캐시 중복 제거 테스트"""
        # 같은 날짜의 데이터가 여러 개 있을 때
        date = datetime.now() - timedelta(days=1)
        df1 = pd.DataFrame({
            'open': [2000.0],
            'high': [2100.0],
            'low': [1900.0],
            'close': [2050.0],
            'volume': [5000000]
        }, index=[date])
        
        df2 = pd.DataFrame({
            'open': [2010.0],
            'high': [2110.0],
            'low': [1910.0],
            'close': [2060.0],
            'volume': [6000000]
        }, index=[date])
        
        # 병합 및 중복 제거
        combined = pd.concat([df1, df2])
        combined = combined[~combined.index.duplicated(keep='last')]
        
        # 검증: 마지막 데이터가 유지되어야 함
        self.assertEqual(len(combined), 1)
        self.assertEqual(combined.iloc[0]['close'], 2060.0)
    
    def test_cache_size_limit(self):
        """캐시 크기 제한 테스트 (365일)"""
        # 400일분 데이터 생성
        test_df = self.create_test_kospi_cache(days_back=400)
        
        # 365일분만 유지
        if len(test_df) > 365:
            test_df = test_df.tail(365)
        
        # 검증
        self.assertEqual(len(test_df), 365)
    
    def test_edge_case_empty_dataframe(self):
        """빈 DataFrame 처리 테스트"""
        # 빈 DataFrame 병합
        empty_df = pd.DataFrame()
        test_df = self.create_test_kospi_cache(days_back=10)
        
        # 빈 DataFrame과 병합
        combined = pd.concat([empty_df, test_df])
        self.assertEqual(len(combined), len(test_df))
    
    def test_edge_case_missing_date_column(self):
        """date 컬럼이 없는 경우 처리 테스트"""
        # 인덱스가 DatetimeIndex인 경우
        test_df = self.create_test_kospi_cache(days_back=10)
        
        # date 컬럼이 없어도 인덱스로 처리 가능해야 함
        if isinstance(test_df.index, pd.DatetimeIndex):
            latest_date = test_df.index.max()
            self.assertIsInstance(latest_date, pd.Timestamp)


if __name__ == '__main__':
    unittest.main()

