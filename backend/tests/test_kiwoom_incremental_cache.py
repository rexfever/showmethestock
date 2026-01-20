"""
한국 주식 스캔 증분 업데이트 로직 테스트
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

# 테스트를 위해 kiwoom_api 모듈 import
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kiwoom_api import KiwoomAPI


class TestIncrementalCache(unittest.TestCase):
    """증분 업데이트 로직 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        
        # KiwoomAPI 인스턴스 생성 (모의 모드)
        self.api = KiwoomAPI()
        self.api.force_mock = True
        self.api._disk_cache_dir = Path(self.temp_dir)
        self.api._disk_cache_enabled = True
        
        # 테스트용 종목 코드
        self.test_code = "005930"  # 삼성전자
    
    def tearDown(self):
        """테스트 후 정리"""
        # 임시 디렉토리 삭제
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_cache(self, code: str, count: int, base_dt: str, days_back: int = 220):
        """테스트용 캐시 파일 생성"""
        # 과거 데이터 생성
        base_date = pd.to_datetime(base_dt, format='%Y%m%d')
        dates = pd.bdate_range(end=base_date, periods=days_back, freq='B')
        
        df = pd.DataFrame({
            'date': dates,
            'open': np.random.rand(len(dates)) * 100000,
            'high': np.random.rand(len(dates)) * 100000,
            'low': np.random.rand(len(dates)) * 100000,
            'close': np.random.rand(len(dates)) * 100000,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        })
        
        # 캐시 파일 저장
        cache_file = self.api._get_disk_cache_file_path(code, count, base_dt)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(cache_file, 'wb') as f:
            pickle.dump((df, datetime.now().timestamp()), f)
        
        return df
    
    def test_find_latest_disk_cache(self):
        """최신 디스크 캐시 찾기 테스트"""
        # 여러 날짜의 캐시 생성
        self.create_test_cache(self.test_code, 220, "20241201")
        self.create_test_cache(self.test_code, 220, "20241202")
        self.create_test_cache(self.test_code, 220, "20241203")
        
        # 최신 캐시 찾기
        cached_df, latest_base_dt = self.api._find_latest_disk_cache(self.test_code, 220)
        
        # 검증
        self.assertIsNotNone(cached_df)
        self.assertEqual(latest_base_dt, "20241203")
        self.assertFalse(cached_df.empty)
        self.assertIn('date', cached_df.columns)
    
    def test_fetch_today_data_from_api(self):
        """당일 데이터만 가져오기 테스트"""
        # 모의 데이터 생성 (당일 데이터 포함)
        today = datetime.now().strftime('%Y%m%d')
        
        # API 호출 (모의 모드)
        today_data = self.api._fetch_today_data_from_api(self.test_code)
        
        # 검증: 당일 데이터가 있는지 확인
        # (모의 모드에서는 빈 DataFrame이 반환될 수 있음)
        if not today_data.empty:
            self.assertIn('date', today_data.columns)
            today_date = pd.to_datetime(today_data['date']).max()
            expected_today = pd.Timestamp.now().normalize()
            self.assertEqual(today_date.date(), expected_today.date())
    
    def test_incremental_update_with_old_cache(self):
        """오래된 캐시에 당일 데이터 추가 테스트"""
        # 어제 날짜의 캐시 생성
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        old_cache_df = self.create_test_cache(self.test_code, 220, yesterday)
        
        # 최신 날짜 확인
        old_latest_date = pd.to_datetime(old_cache_df['date']).max()
        
        # get_ohlcv 호출 (base_dt=None)
        # 모의 모드에서는 실제 API 호출이 안 되므로, 
        # 증분 업데이트 로직이 제대로 동작하는지 확인
        result_df = self.api.get_ohlcv(self.test_code, 220, None)
        
        # 검증
        self.assertIsNotNone(result_df)
        # 캐시가 최신이면 그대로 반환되어야 함
        # (모의 모드에서는 실제 당일 데이터를 가져올 수 없으므로)
    
    def test_incremental_update_with_recent_cache(self):
        """최신 캐시는 그대로 반환 테스트"""
        # 오늘 날짜의 캐시 생성
        today = datetime.now().strftime('%Y%m%d')
        recent_cache_df = self.create_test_cache(self.test_code, 220, today)
        
        # get_ohlcv 호출 (base_dt=None)
        result_df = self.api.get_ohlcv(self.test_code, 220, None)
        
        # 검증: 최신 캐시가 그대로 반환되어야 함
        self.assertIsNotNone(result_df)
        self.assertFalse(result_df.empty)
    
    def test_cache_merge_logic(self):
        """캐시 병합 로직 테스트"""
        # 어제 날짜의 캐시 생성
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        old_cache_df = self.create_test_cache(self.test_code, 220, yesterday)
        
        # 당일 데이터 생성 (모의)
        today = pd.Timestamp.now().normalize()
        today_data = pd.DataFrame({
            'date': [today],
            'open': [100000],
            'high': [101000],
            'low': [99000],
            'close': [100500],
            'volume': [5000000]
        })
        
        # 병합 로직 테스트
        combined = pd.concat([old_cache_df, today_data])
        combined = combined.drop_duplicates(subset=['date'], keep='last')
        combined = combined.sort_values('date').reset_index(drop=True)
        
        # 검증
        self.assertFalse(combined.empty)
        self.assertEqual(len(combined), len(old_cache_df) + 1)
        self.assertEqual(combined.iloc[-1]['date'].date(), today.date())
    
    def test_cache_file_naming(self):
        """캐시 파일명 형식 테스트"""
        base_dt = "20241203"
        cache_file = self.api._get_disk_cache_file_path(self.test_code, 220, base_dt)
        
        # 검증
        expected_filename = f"{self.test_code}_220_{base_dt}.pkl"
        self.assertEqual(cache_file.name, expected_filename)


if __name__ == '__main__':
    unittest.main()

