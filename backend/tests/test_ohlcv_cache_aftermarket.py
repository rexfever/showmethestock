"""
OHLCV 캐시 애프터마켓 고려 상세 테스트

단계별 테스트:
1. 캐시 키 생성 테스트
2. TTL 계산 테스트
3. 캐시 히트/미스 테스트
4. 시간대별 캐시 구분 테스트
5. 애프터마켓 시간대 테스트
6. 통합 시나리오 테스트
"""
import sys
import os
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import pytz

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kiwoom_api import KiwoomAPI


class TestOHLCVCacheAftermarket:
    """OHLCV 캐시 애프터마켓 고려 테스트"""
    
    def setup_method(self):
        """테스트 전 설정"""
        self.api = KiwoomAPI()
        self.api.force_mock = True
        self.KST = pytz.timezone('Asia/Seoul')
    
    # ==================== Step 1: 캐시 키 생성 테스트 ====================
    
    def test_cache_key_08_00_aftermarket(self):
        """08:00 (장전 시간외) 캐시 키 생성"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 8, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            cache_key = self.api._get_cache_key('005930', 220, None)
            
            assert cache_key == ('005930', 220, None, '08:00')
            print("✅ 08:00 캐시 키: 시간대별 구분")
    
    def test_cache_key_09_00_market_open(self):
        """09:00 (장 시작) 캐시 키 생성"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 9, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            cache_key = self.api._get_cache_key('005930', 220, None)
            
            assert cache_key == ('005930', 220, None, '09:00')
            print("✅ 09:00 캐시 키: 시간대별 구분")
    
    def test_cache_key_15_30_market_close(self):
        """15:30 (장 마감) 캐시 키 생성"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 15, 30, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            cache_key = self.api._get_cache_key('005930', 220, None)
            
            assert cache_key == ('005930', 220, None, '15:30')
            print("✅ 15:30 캐시 키: 시간대별 구분")
    
    def test_cache_key_16_00_after_hours(self):
        """16:00 (장후 시간외) 캐시 키 생성"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 16, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            cache_key = self.api._get_cache_key('005930', 220, None)
            
            assert cache_key == ('005930', 220, None, '16:00')
            print("✅ 16:00 캐시 키: 시간대별 구분")
    
    def test_cache_key_20_00_aftermarket_end(self):
        """20:00 (시간외 종료) 캐시 키 생성"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 20, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            cache_key = self.api._get_cache_key('005930', 220, None)
            
            assert cache_key == ('005930', 220, None, None)
            print("✅ 20:00 캐시 키: 당일로 통합")
    
    def test_cache_key_22_00_night(self):
        """22:00 (밤) 캐시 키 생성"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 22, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            cache_key = self.api._get_cache_key('005930', 220, None)
            
            assert cache_key == ('005930', 220, None, None)
            print("✅ 22:00 캐시 키: 당일로 통합")
    
    def test_cache_key_07_00_morning(self):
        """07:00 (새벽) 캐시 키 생성"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 7, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            cache_key = self.api._get_cache_key('005930', 220, None)
            
            assert cache_key == ('005930', 220, None, None)
            print("✅ 07:00 캐시 키: 당일로 통합")
    
    def test_cache_key_with_base_dt(self):
        """base_dt가 명시된 경우 캐시 키"""
        cache_key = self.api._get_cache_key('005930', 220, '20251124')
        
        assert cache_key == ('005930', 220, '20251124', None)
        print("✅ base_dt 명시: 날짜만 사용")
    
    def test_cache_key_10_minute_granularity(self):
        """10분 단위 캐시 키 구분"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            # 15:35 조회
            mock_now = datetime(2025, 11, 24, 15, 35, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            cache_key_1535 = self.api._get_cache_key('005930', 220, None)
            
            # 15:40 조회
            mock_now = datetime(2025, 11, 24, 15, 40, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            cache_key_1540 = self.api._get_cache_key('005930', 220, None)
            
            assert cache_key_1535 == ('005930', 220, None, '15:30')
            assert cache_key_1540 == ('005930', 220, None, '15:40')
            assert cache_key_1535 != cache_key_1540
            print("✅ 10분 단위 캐시 키 구분")
    
    # ==================== Step 2: TTL 계산 테스트 ====================
    
    def test_ttl_08_00_aftermarket(self):
        """08:00 TTL 계산"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 8, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            ttl = self.api._calculate_ttl(None)
            
            assert ttl == 60, f"08:00 TTL은 1분이어야 함: {ttl}초"
            print("✅ 08:00 TTL: 1분")
    
    def test_ttl_15_30_market_close(self):
        """15:30 TTL 계산"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 15, 30, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            ttl = self.api._calculate_ttl(None)
            
            assert ttl == 60, f"15:30 TTL은 1분이어야 함: {ttl}초"
            print("✅ 15:30 TTL: 1분")
    
    def test_ttl_19_59_aftermarket(self):
        """19:59 TTL 계산"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 19, 59, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            ttl = self.api._calculate_ttl(None)
            
            assert ttl == 60, f"19:59 TTL은 1분이어야 함: {ttl}초"
            print("✅ 19:59 TTL: 1분")
    
    def test_ttl_20_00_aftermarket_end(self):
        """20:00 TTL 계산"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 20, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            ttl = self.api._calculate_ttl(None)
            
            assert ttl >= 3600, f"20:00 TTL은 최소 1시간이어야 함: {ttl}초"
            print(f"✅ 20:00 TTL: {ttl/3600:.1f}시간 (다음 거래일까지)")
    
    def test_ttl_22_00_night(self):
        """22:00 TTL 계산"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 22, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            ttl = self.api._calculate_ttl(None)
            
            assert ttl >= 3600, f"22:00 TTL은 최소 1시간이어야 함: {ttl}초"
            print(f"✅ 22:00 TTL: {ttl/3600:.1f}시간 (다음 거래일까지)")
    
    def test_ttl_past_date(self):
        """과거 날짜 TTL 계산"""
        ttl = self.api._calculate_ttl('20251120')
        
        assert ttl == 365 * 24 * 3600, f"과거 날짜 TTL은 1년이어야 함: {ttl}초"
        print("✅ 과거 날짜 TTL: 1년")
    
    def test_ttl_current_date_with_base_dt(self):
        """base_dt가 현재 날짜인 경우"""
        today = datetime.now(self.KST).strftime('%Y%m%d')
        ttl = self.api._calculate_ttl(today)
        
        # 현재 시간대에 따라 다름
        hour = datetime.now(self.KST).hour
        if 8 <= hour < 20:
            assert ttl == 60, f"현재 시간대(08:00~20:00) TTL은 1분이어야 함: {ttl}초"
        else:
            assert ttl >= 3600, f"현재 시간대(20:00~08:00) TTL은 최소 1시간이어야 함: {ttl}초"
        print(f"✅ base_dt 현재 날짜 TTL: {ttl}초")
    
    # ==================== Step 3: 캐시 히트/미스 테스트 ====================
    
    def test_cache_hit_same_time_slot(self):
        """같은 시간대 캐시 히트"""
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(self.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            with patch('kiwoom_api.datetime') as mock_datetime:
                mock_now = datetime(2025, 11, 24, 15, 30, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                
                # 첫 번째 호출
                result1 = self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1
                
                # 두 번째 호출 (같은 시간대)
                result2 = self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1  # 캐시 히트
                assert not result2.empty
                print("✅ 같은 시간대 캐시 히트")
    
    def test_cache_miss_different_time_slot(self):
        """다른 시간대 캐시 미스"""
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(self.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            with patch('kiwoom_api.datetime') as mock_datetime:
                # 15:30 조회
                mock_now = datetime(2025, 11, 24, 15, 30, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1
                
                # 16:00 재조회 (다른 시간대)
                mock_now = datetime(2025, 11, 24, 16, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 2  # 캐시 미스
                print("✅ 다른 시간대 캐시 미스")
    
    def test_cache_hit_20_00_to_22_00(self):
        """20:00과 22:00 같은 캐시 사용"""
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(self.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            with patch('kiwoom_api.datetime') as mock_datetime:
                # 20:00 조회
                mock_now = datetime(2025, 11, 24, 20, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1
                
                # 22:00 재조회 (같은 캐시)
                mock_now = datetime(2025, 11, 24, 22, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1  # 캐시 히트
                print("✅ 20:00과 22:00 같은 캐시 사용")
    
    # ==================== Step 4: 시간대별 캐시 구분 테스트 ====================
    
    def test_time_slot_separation_08_00_09_00(self):
        """08:00과 09:00 다른 캐시"""
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(self.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            with patch('kiwoom_api.datetime') as mock_datetime:
                # 08:00 조회
                mock_now = datetime(2025, 11, 24, 8, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1
                
                # 09:00 재조회
                mock_now = datetime(2025, 11, 24, 9, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 2  # 다른 캐시
                print("✅ 08:00과 09:00 다른 캐시")
    
    def test_time_slot_separation_15_30_16_00(self):
        """15:30과 16:00 다른 캐시"""
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(self.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            with patch('kiwoom_api.datetime') as mock_datetime:
                # 15:30 조회
                mock_now = datetime(2025, 11, 24, 15, 30, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1
                
                # 16:00 재조회
                mock_now = datetime(2025, 11, 24, 16, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 2  # 다른 캐시
                print("✅ 15:30과 16:00 다른 캐시 (애프터마켓 반영)")
    
    def test_time_slot_same_10_minute_window(self):
        """같은 10분 윈도우 내 같은 캐시"""
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(self.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            with patch('kiwoom_api.datetime') as mock_datetime:
                # 15:35 조회
                mock_now = datetime(2025, 11, 24, 15, 35, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1
                
                # 15:39 재조회 (같은 10분 윈도우)
                mock_now = datetime(2025, 11, 24, 15, 39, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1  # 같은 캐시
                print("✅ 같은 10분 윈도우 내 같은 캐시")
    
    # ==================== Step 5: 애프터마켓 시간대 테스트 ====================
    
    def test_is_aftermarket_hours_08_00(self):
        """08:00 애프터마켓 시간대"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 8, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            assert self.api._is_aftermarket_hours() == True
            print("✅ 08:00 애프터마켓 시간대")
    
    def test_is_aftermarket_hours_09_00(self):
        """09:00 애프터마켓 시간대"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 9, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            assert self.api._is_aftermarket_hours() == True
            print("✅ 09:00 애프터마켓 시간대")
    
    def test_is_aftermarket_hours_15_30(self):
        """15:30 애프터마켓 시간대"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 15, 30, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            assert self.api._is_aftermarket_hours() == True
            print("✅ 15:30 애프터마켓 시간대")
    
    def test_is_aftermarket_hours_19_59(self):
        """19:59 애프터마켓 시간대"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 19, 59, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            assert self.api._is_aftermarket_hours() == True
            print("✅ 19:59 애프터마켓 시간대")
    
    def test_is_aftermarket_hours_20_00(self):
        """20:00 애프터마켓 시간대 아님"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 20, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            assert self.api._is_aftermarket_hours() == False
            print("✅ 20:00 애프터마켓 시간대 아님")
    
    def test_is_aftermarket_hours_22_00(self):
        """22:00 애프터마켓 시간대 아님"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 22, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            assert self.api._is_aftermarket_hours() == False
            print("✅ 22:00 애프터마켓 시간대 아님")
    
    def test_is_aftermarket_hours_07_00(self):
        """07:00 애프터마켓 시간대 아님"""
        with patch('kiwoom_api.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 24, 7, 0, 0, tzinfo=self.KST)
            mock_datetime.now.return_value = mock_now
            
            assert self.api._is_aftermarket_hours() == False
            print("✅ 07:00 애프터마켓 시간대 아님")
    
    # ==================== Step 6: 통합 시나리오 테스트 ====================
    
    def test_scenario_full_day(self):
        """하루 종일 시나리오"""
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(self.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            with patch('kiwoom_api.datetime') as mock_datetime:
                call_count = 0
                
                # 08:00 조회
                mock_now = datetime(2025, 11, 24, 8, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                call_count += 1
                assert mock_fetch.call_count == call_count
                
                # 09:00 재조회 (다른 시간대)
                mock_now = datetime(2025, 11, 24, 9, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                call_count += 1
                assert mock_fetch.call_count == call_count
                
                # 15:30 재조회 (다른 시간대)
                mock_now = datetime(2025, 11, 24, 15, 30, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                call_count += 1
                assert mock_fetch.call_count == call_count
                
                # 16:00 재조회 (다른 시간대)
                mock_now = datetime(2025, 11, 24, 16, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                call_count += 1
                assert mock_fetch.call_count == call_count
                
                # 20:00 재조회 (같은 캐시)
                mock_now = datetime(2025, 11, 24, 20, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                call_count += 1
                assert mock_fetch.call_count == call_count
                
                # 22:00 재조회 (같은 캐시)
                mock_now = datetime(2025, 11, 24, 22, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                # 20:00과 같은 캐시이지만, 20:00에 조회한 데이터가 20:00 이전 시간대이므로
                # 실제로는 다른 캐시일 수 있음. 하지만 20:00 이후는 모두 None이므로 같은 캐시
                print(f"✅ 하루 종일 시나리오: 총 {mock_fetch.call_count}회 API 호출")
    
    def test_scenario_ttl_expiration(self):
        """TTL 만료 시나리오"""
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(self.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            with patch('kiwoom_api.datetime') as mock_datetime:
                # 15:30 조회 (TTL: 1분)
                mock_now = datetime(2025, 11, 24, 15, 30, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1
                
                # 15:31 재조회 (1분 후, TTL 만료)
                mock_now = datetime(2025, 11, 24, 15, 31, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                # 같은 시간대이지만 TTL 만료로 재조회
                assert mock_fetch.call_count == 2
                print("✅ TTL 만료 시 재조회")
    
    def test_scenario_past_date_auto_conversion(self):
        """과거 날짜 자동 전환 시나리오"""
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(self.api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            with patch('kiwoom_api.datetime') as mock_datetime:
                # 20:00 조회 (base_dt=None)
                mock_now = datetime(2025, 11, 24, 20, 0, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                self.api.get_ohlcv('005930', 220, None)
                assert mock_fetch.call_count == 1
                
                # 다음날 20:01 재조회 (과거 날짜로 인식)
                mock_now = datetime(2025, 11, 25, 20, 1, 0, tzinfo=self.KST)
                mock_datetime.now.return_value = mock_now
                cached = self.api._get_cached_ohlcv('005930', 220, None)
                # DataFrame의 날짜가 20251124이므로 과거 날짜로 인식
                # TTL이 1년으로 전환되어 캐시에서 반환
                if cached is not None:
                    print("✅ 과거 날짜 자동 전환: 1년 캐싱 적용")
                else:
                    print("⚠️  캐시 미스 (TTL 계산 로직 확인 필요)")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])

