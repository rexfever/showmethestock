#!/usr/bin/env python3
"""
OHLCV 캐시 애프터마켓 고려 상세 테스트 실행 스크립트

단계별 테스트 실행 및 결과 리포트
"""
import sys
import os
import time
from datetime import datetime, timedelta
from unittest.mock import patch
import pandas as pd
import pytz

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kiwoom_api import KiwoomAPI


class TestRunner:
    """테스트 실행기"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.api = KiwoomAPI()
        self.api.force_mock = True
        self.KST = pytz.timezone('Asia/Seoul')
    
    def run_test(self, test_name, test_func):
        """단일 테스트 실행"""
        try:
            test_func()
            self.passed += 1
            return True
        except Exception as e:
            self.failed += 1
            error_msg = f"❌ {test_name}: {str(e)}"
            self.errors.append(error_msg)
            import traceback
            traceback.print_exc()
            return False
    
    def print_summary(self):
        """테스트 결과 요약"""
        total = self.passed + self.failed
        print("\n" + "="*60)
        print(f"테스트 결과: {self.passed}/{total} 통과")
        if self.failed > 0:
            print(f"실패: {self.failed}")
            print("\n실패한 테스트:")
            for error in self.errors:
                print(f"  {error}")
        print("="*60)


runner = TestRunner()


# ==================== Step 1: 캐시 키 생성 테스트 ====================

def test_cache_key_08_00():
    """08:00 캐시 키"""
    # _get_cache_key 내부에서 datetime.now(KST)를 직접 호출하므로
    # datetime 모듈 전체를 모킹해야 함
    with patch('kiwoom_api.datetime') as mock_datetime_module:
        mock_now = datetime(2025, 11, 24, 8, 0, 0, tzinfo=runner.KST)
        # datetime.now를 모킹
        def mock_now_func(tz=None):
            if tz:
                return mock_now.astimezone(tz)
            return mock_now
        mock_datetime_module.now = mock_now_func
        mock_datetime_module.strptime = datetime.strptime
        
        cache_key = runner.api._get_cache_key('005930', 220, None)
        assert cache_key == ('005930', 220, None, '08:00'), f"실제: {cache_key}"


def test_cache_key_15_30():
    """15:30 캐시 키"""
    with patch('kiwoom_api.datetime') as mock_datetime_module:
        mock_now = datetime(2025, 11, 24, 15, 30, 0, tzinfo=runner.KST)
        def mock_now_func(tz=None):
            if tz:
                return mock_now.astimezone(tz)
            return mock_now
        mock_datetime_module.now = mock_now_func
        mock_datetime_module.strptime = datetime.strptime
        
        cache_key = runner.api._get_cache_key('005930', 220, None)
        assert cache_key == ('005930', 220, None, '15:30'), f"실제: {cache_key}"


def test_cache_key_20_00():
    """20:00 캐시 키"""
    with patch('kiwoom_api.datetime') as mock_datetime_module:
        mock_now = datetime(2025, 11, 24, 20, 0, 0, tzinfo=runner.KST)
        def mock_now_func(tz=None):
            if tz:
                return mock_now.astimezone(tz)
            return mock_now
        mock_datetime_module.now = mock_now_func
        mock_datetime_module.strptime = datetime.strptime
        
        cache_key = runner.api._get_cache_key('005930', 220, None)
        assert cache_key == ('005930', 220, None, None), f"실제: {cache_key}"


def test_cache_key_10_min_granularity():
    """10분 단위 구분"""
    with patch('kiwoom_api.datetime') as mock_datetime_module:
        # 15:35
        mock_now1 = datetime(2025, 11, 24, 15, 35, 0, tzinfo=runner.KST)
        def mock_now_func1(tz=None):
            if tz:
                return mock_now1.astimezone(tz)
            return mock_now1
        mock_datetime_module.now = mock_now_func1
        mock_datetime_module.strptime = datetime.strptime
        key1 = runner.api._get_cache_key('005930', 220, None)
        
        # 15:40
        mock_now2 = datetime(2025, 11, 24, 15, 40, 0, tzinfo=runner.KST)
        def mock_now_func2(tz=None):
            if tz:
                return mock_now2.astimezone(tz)
            return mock_now2
        mock_datetime_module.now = mock_now_func2
        key2 = runner.api._get_cache_key('005930', 220, None)
        
        assert key1 == ('005930', 220, None, '15:30'), f"실제: {key1}"
        assert key2 == ('005930', 220, None, '15:40'), f"실제: {key2}"
        assert key1 != key2


# ==================== Step 2: TTL 계산 테스트 ====================

def test_ttl_08_00():
    """08:00 TTL"""
    with patch('kiwoom_api.datetime') as mock_datetime_module:
        mock_now = datetime(2025, 11, 24, 8, 0, 0, tzinfo=runner.KST)
        def mock_now_func(tz=None):
            if tz:
                return mock_now.astimezone(tz)
            return mock_now
        mock_datetime_module.now = mock_now_func
        mock_datetime_module.strptime = datetime.strptime
        
        ttl = runner.api._calculate_ttl(None)
        assert ttl == 60, f"실제: {ttl}초"


def test_ttl_20_00():
    """20:00 TTL"""
    with patch('kiwoom_api.datetime') as mock_datetime_module:
        mock_now = datetime(2025, 11, 24, 20, 0, 0, tzinfo=runner.KST)
        def mock_now_func(tz=None):
            if tz:
                return mock_now.astimezone(tz)
            return mock_now
        mock_datetime_module.now = mock_now_func
        mock_datetime_module.strptime = datetime.strptime
        mock_datetime_module.combine = datetime.combine
        mock_datetime_module.min = datetime.min
        
        ttl = runner.api._calculate_ttl(None)
        assert ttl >= 3600, f"실제: {ttl}초 (최소 1시간)"


def test_ttl_past_date():
    """과거 날짜 TTL"""
    ttl = runner.api._calculate_ttl('20251120')
    assert ttl == 365 * 24 * 3600, f"실제: {ttl}초"


# ==================== Step 3: 캐시 히트/미스 테스트 ====================

def test_cache_hit_same_time():
    """같은 시간대 캐시 히트"""
    mock_df = pd.DataFrame({
        'date': ['20251124'],
        'open': [70000], 'high': [71000], 'low': [69000],
        'close': [70500], 'volume': [1000000]
    })
    
    with patch.object(runner.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
        with patch('kiwoom_api.datetime') as mock_datetime_module:
            mock_now = datetime(2025, 11, 24, 15, 30, 0, tzinfo=runner.KST)
            def mock_now_func(tz=None):
                if tz:
                    return mock_now.astimezone(tz)
                return mock_now
            mock_datetime_module.now = mock_now_func
            mock_datetime_module.strptime = datetime.strptime
            
            runner.api.get_ohlcv('005930', 220, None)
            assert mock_fetch.call_count == 1
            
            runner.api.get_ohlcv('005930', 220, None)
            assert mock_fetch.call_count == 1, "캐시 히트되어야 함"


def test_cache_miss_different_time():
    """다른 시간대 캐시 미스"""
    mock_df = pd.DataFrame({
        'date': ['20251124'],
        'open': [70000], 'high': [71000], 'low': [69000],
        'close': [70500], 'volume': [1000000]
    })
    
    with patch.object(runner.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
        with patch('kiwoom_api.datetime') as mock_datetime_module:
            # 15:30
            mock_now1 = datetime(2025, 11, 24, 15, 30, 0, tzinfo=runner.KST)
            def mock_now_func1(tz=None):
                if tz:
                    return mock_now1.astimezone(tz)
                return mock_now1
            mock_datetime_module.now = mock_now_func1
            mock_datetime_module.strptime = datetime.strptime
            runner.api.get_ohlcv('005930', 220, None)
            assert mock_fetch.call_count == 1
            
            # 16:00
            mock_now2 = datetime(2025, 11, 24, 16, 0, 0, tzinfo=runner.KST)
            def mock_now_func2(tz=None):
                if tz:
                    return mock_now2.astimezone(tz)
                return mock_now2
            mock_datetime_module.now = mock_now_func2
            runner.api.get_ohlcv('005930', 220, None)
            assert mock_fetch.call_count == 2, "캐시 미스되어야 함"


def test_cache_hit_20_00_22_00():
    """20:00과 22:00 같은 캐시"""
    mock_df = pd.DataFrame({
        'date': ['20251124'],
        'open': [70000], 'high': [71000], 'low': [69000],
        'close': [70500], 'volume': [1000000]
    })
    
    with patch.object(runner.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
        with patch('kiwoom_api.datetime') as mock_datetime_module:
            # 20:00
            mock_now1 = datetime(2025, 11, 24, 20, 0, 0, tzinfo=runner.KST)
            def mock_now_func1(tz=None):
                if tz:
                    return mock_now1.astimezone(tz)
                return mock_now1
            mock_datetime_module.now = mock_now_func1
            mock_datetime_module.strptime = datetime.strptime
            mock_datetime_module.combine = datetime.combine
            mock_datetime_module.min = datetime.min
            runner.api.get_ohlcv('005930', 220, None)
            assert mock_fetch.call_count == 1
            
            # 22:00
            mock_now2 = datetime(2025, 11, 24, 22, 0, 0, tzinfo=runner.KST)
            def mock_now_func2(tz=None):
                if tz:
                    return mock_now2.astimezone(tz)
                return mock_now2
            mock_datetime_module.now = mock_now_func2
            runner.api.get_ohlcv('005930', 220, None)
            assert mock_fetch.call_count == 1, "같은 캐시 사용되어야 함"


# ==================== Step 4: 애프터마켓 시간대 테스트 ====================

def test_is_aftermarket_hours():
    """애프터마켓 시간대 확인"""
    test_cases = [
        (8, 0, True),
        (9, 0, True),
        (15, 30, True),
        (19, 59, True),
        (20, 0, False),
        (22, 0, False),
        (7, 0, False),
    ]
    
    with patch('kiwoom_api.datetime') as mock_datetime_module:
        for hour, minute, expected in test_cases:
            mock_now = datetime(2025, 11, 24, hour, minute, 0, tzinfo=runner.KST)
            def mock_now_func(tz=None):
                if tz:
                    return mock_now.astimezone(tz)
                return mock_now
            mock_datetime_module.now = mock_now_func
            mock_datetime_module.strptime = datetime.strptime
            
            result = runner.api._is_aftermarket_hours()
            assert result == expected, f"{hour:02d}:{minute:02d} 예상: {expected}, 실제: {result}"


# ==================== Step 5: 통합 시나리오 테스트 ====================

def test_scenario_full_day():
    """하루 종일 시나리오"""
    mock_df = pd.DataFrame({
        'date': ['20251124'],
        'open': [70000], 'high': [71000], 'low': [69000],
        'close': [70500], 'volume': [1000000]
    })
    
    with patch.object(runner.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
        with patch('kiwoom_api.datetime') as mock_datetime_module:
            times = [
                (8, 0),   # 장전 시간외
                (9, 0),   # 장 시작
                (15, 30), # 장 마감
                (16, 0),  # 장후 시간외
                (20, 0),  # 시간외 종료
                (22, 0),  # 밤
            ]
            
            for hour, minute in times:
                mock_now = datetime(2025, 11, 24, hour, minute, 0, tzinfo=runner.KST)
                def mock_now_func(tz=None):
                    if tz:
                        return mock_now.astimezone(tz)
                    return mock_now
                mock_datetime_module.now = mock_now_func
                mock_datetime_module.strptime = datetime.strptime
                mock_datetime_module.combine = datetime.combine
                mock_datetime_module.min = datetime.min
                
                runner.api.get_ohlcv('005930', 220, None)
            
            # 08:00, 09:00, 15:30, 16:00, 20:00는 각각 다른 캐시
            # 22:00는 20:00와 같은 캐시
            assert mock_fetch.call_count >= 5, f"최소 5회 호출되어야 함: {mock_fetch.call_count}"


# ==================== 메인 실행 ====================

def main():
    """모든 테스트 실행"""
    print("="*60)
    print("OHLCV 캐시 애프터마켓 고려 상세 테스트")
    print("="*60)
    print()
    
    print("Step 1: 캐시 키 생성 테스트")
    print("-" * 60)
    runner.run_test("08:00 캐시 키", test_cache_key_08_00)
    runner.run_test("15:30 캐시 키", test_cache_key_15_30)
    runner.run_test("20:00 캐시 키", test_cache_key_20_00)
    runner.run_test("10분 단위 구분", test_cache_key_10_min_granularity)
    print()
    
    print("Step 2: TTL 계산 테스트")
    print("-" * 60)
    runner.run_test("08:00 TTL", test_ttl_08_00)
    runner.run_test("20:00 TTL", test_ttl_20_00)
    runner.run_test("과거 날짜 TTL", test_ttl_past_date)
    print()
    
    print("Step 3: 캐시 히트/미스 테스트")
    print("-" * 60)
    runner.run_test("같은 시간대 캐시 히트", test_cache_hit_same_time)
    runner.run_test("다른 시간대 캐시 미스", test_cache_miss_different_time)
    runner.run_test("20:00과 22:00 같은 캐시", test_cache_hit_20_00_22_00)
    print()
    
    print("Step 4: 애프터마켓 시간대 테스트")
    print("-" * 60)
    runner.run_test("애프터마켓 시간대 확인", test_is_aftermarket_hours)
    print()
    
    print("Step 5: 통합 시나리오 테스트")
    print("-" * 60)
    runner.run_test("하루 종일 시나리오", test_scenario_full_day)
    print()
    
    runner.print_summary()
    
    return runner.failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

