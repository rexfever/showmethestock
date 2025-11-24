"""
OHLCV 캐싱 기능 테스트
"""
import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kiwoom_api import KiwoomAPI


class TestOHLCVCaching:
    """OHLCV 캐싱 테스트"""
    
    def test_cache_hit(self):
        """캐시 히트 테스트"""
        api = KiwoomAPI()
        
        # 모의 데이터
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            # 첫 번째 호출: API 호출
            result1 = api.get_ohlcv("005930", 220, "20251124")
            assert mock_fetch.call_count == 1
            assert not result1.empty
            
            # 두 번째 호출: 캐시에서 반환
            result2 = api.get_ohlcv("005930", 220, "20251124")
            assert mock_fetch.call_count == 1  # 추가 호출 없음
            assert not result2.empty
            assert result1.equals(result2)
    
    def test_cache_miss_different_params(self):
        """다른 파라미터로 캐시 미스 테스트"""
        api = KiwoomAPI()
        
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            # 첫 번째 호출
            api.get_ohlcv("005930", 220, "20251124")
            assert mock_fetch.call_count == 1
            
            # 다른 count로 호출: 캐시 미스
            api.get_ohlcv("005930", 100, "20251124")
            assert mock_fetch.call_count == 2
            
            # 다른 날짜로 호출: 캐시 미스
            api.get_ohlcv("005930", 220, "20251123")
            assert mock_fetch.call_count == 3
    
    def test_cache_ttl_expiration(self):
        """캐시 TTL 만료 테스트"""
        api = KiwoomAPI()
        api._cache_ttl = 1  # 1초로 설정
        
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            # 첫 번째 호출
            api.get_ohlcv("005930", 220, "20251124")
            assert mock_fetch.call_count == 1
            
            # 즉시 재호출: 캐시 히트
            api.get_ohlcv("005930", 220, "20251124")
            assert mock_fetch.call_count == 1
            
            # 1초 대기 후 재호출: 캐시 만료
            time.sleep(1.1)
            api.get_ohlcv("005930", 220, "20251124")
            assert mock_fetch.call_count == 2
    
    def test_cache_maxsize_limit(self):
        """캐시 최대 크기 제한 테스트"""
        api = KiwoomAPI()
        api._cache_maxsize = 3  # 최대 3개로 설정
        
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(api, '_fetch_ohlcv_from_api', return_value=mock_df) as mock_fetch:
            # 3개 항목 추가
            api.get_ohlcv("005930", 220, "20251124")
            api.get_ohlcv("000660", 220, "20251124")
            api.get_ohlcv("051910", 220, "20251124")
            assert len(api._ohlcv_cache) == 3
            
            # 4번째 항목 추가: 가장 오래된 항목 제거
            api.get_ohlcv("207940", 220, "20251124")
            assert len(api._ohlcv_cache) == 3
            assert ("005930", 220, "20251124") not in api._ohlcv_cache
    
    def test_clear_cache_all(self):
        """전체 캐시 클리어 테스트"""
        api = KiwoomAPI()
        
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(api, '_fetch_ohlcv_from_api', return_value=mock_df):
            api.get_ohlcv("005930", 220, "20251124")
            api.get_ohlcv("000660", 220, "20251124")
            assert len(api._ohlcv_cache) == 2
            
            api.clear_ohlcv_cache()
            assert len(api._ohlcv_cache) == 0
    
    def test_clear_cache_specific_code(self):
        """특정 종목 캐시 클리어 테스트"""
        api = KiwoomAPI()
        
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(api, '_fetch_ohlcv_from_api', return_value=mock_df):
            api.get_ohlcv("005930", 220, "20251124")
            api.get_ohlcv("005930", 100, "20251124")
            api.get_ohlcv("000660", 220, "20251124")
            assert len(api._ohlcv_cache) == 3
            
            # 005930만 클리어
            api.clear_ohlcv_cache("005930")
            assert len(api._ohlcv_cache) == 1
            assert ("000660", 220, "20251124") in api._ohlcv_cache
    
    def test_cache_stats(self):
        """캐시 통계 테스트"""
        api = KiwoomAPI()
        
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(api, '_fetch_ohlcv_from_api', return_value=mock_df):
            api.get_ohlcv("005930", 220, "20251124")
            api.get_ohlcv("000660", 220, "20251124")
            
            stats = api.get_ohlcv_cache_stats()
            assert stats["total"] == 2
            assert stats["valid"] == 2
            assert stats["expired"] == 0
            assert stats["maxsize"] == 1000
            assert stats["ttl"] == 300
    
    def test_empty_dataframe_not_cached(self):
        """빈 DataFrame은 캐시하지 않음"""
        api = KiwoomAPI()
        
        empty_df = pd.DataFrame()
        
        with patch.object(api, '_fetch_ohlcv_from_api', return_value=empty_df) as mock_fetch:
            api.get_ohlcv("005930", 220, "20251124")
            assert len(api._ohlcv_cache) == 0
            
            # 재호출 시에도 캐시 없음
            api.get_ohlcv("005930", 220, "20251124")
            assert mock_fetch.call_count == 2
    
    def test_cache_returns_copy(self):
        """캐시에서 반환된 DataFrame은 복사본"""
        api = KiwoomAPI()
        
        mock_df = pd.DataFrame({
            'date': ['20251124'],
            'open': [70000],
            'high': [71000],
            'low': [69000],
            'close': [70500],
            'volume': [1000000]
        })
        
        with patch.object(api, '_fetch_ohlcv_from_api', return_value=mock_df):
            result1 = api.get_ohlcv("005930", 220, "20251124")
            result2 = api.get_ohlcv("005930", 220, "20251124")
            
            # 수정해도 서로 영향 없음
            result1.loc[0, 'close'] = 99999
            assert result2.loc[0, 'close'] == 70500  # 원본 값 유지


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

