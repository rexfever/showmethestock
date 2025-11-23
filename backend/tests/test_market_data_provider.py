"""
Market Data Provider 테스트
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from services.market_data_provider import KiwoomMarketDataProvider, market_data_provider

class TestKiwoomMarketDataProvider:
    """Kiwoom Market Data Provider 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.provider = KiwoomMarketDataProvider(cache_dir="test_cache")
        self.test_date = "20241201"
        self.start_date = "20241101"
    
    def test_get_ohlcv_korea_success(self):
        """한국 종목 OHLCV 조회 성공 테스트"""
        with patch('kiwoom_api.api') as mock_api:
            # Mock 데이터 설정
            mock_df = pd.DataFrame({
                'date': ['20241201', '20241202'],
                'open': [50000, 51000],
                'high': [52000, 53000],
                'low': [49000, 50000],
                'close': [51000, 52000],
                'volume': [1000000, 1200000]
            })
            mock_api.get_ohlcv.return_value = mock_df
            
            # 테스트 실행
            result = self.provider.get_ohlcv_korea("005930", self.start_date, self.test_date)
            
            # 검증
            assert not result.empty
            assert len(result) == 2
            assert 'date' in result.columns
            assert 'close' in result.columns
            mock_api.get_ohlcv.assert_called_once()
    
    def test_get_ohlcv_korea_empty_data(self):
        """한국 종목 데이터 없음 테스트"""
        with patch('kiwoom_api.api') as mock_api:
            mock_api.get_ohlcv.return_value = pd.DataFrame()
            
            result = self.provider.get_ohlcv_korea("999999", self.start_date, self.test_date)
            
            assert result.empty
    
    def test_get_ohlcv_us_mock_data(self):
        """미국 종목 모의 데이터 생성 테스트"""
        result = self.provider.get_ohlcv_us("SPY", self.start_date, self.test_date)
        
        assert not result.empty
        assert 'date' in result.columns
        assert 'close' in result.columns
        assert 'volume' in result.columns
        
        # SPY 기본 가격 범위 확인
        assert result['close'].min() > 300  # SPY는 보통 300 이상
        assert result['close'].max() < 600  # SPY는 보통 600 이하
    
    def test_get_vix_data(self):
        """VIX 데이터 조회 테스트"""
        result = self.provider.get_vix(self.start_date, self.test_date)
        
        assert not result.empty
        # VIX는 보통 10-50 범위
        assert result['close'].min() > 5
        assert result['close'].max() < 100
    
    def test_us_prev_snapshot(self):
        """미국 전일 스냅샷 테스트"""
        result = self.provider.get_us_prev_snapshot(self.test_date)
        
        # 기본 구조 확인
        expected_keys = ["spy_r1", "spy_r3", "spy_r5", "qqq_r1", "qqq_r3", "qqq_r5", 
                        "vix", "vix_change", "ust10y_change", "valid"]
        for key in expected_keys:
            assert key in result
        
        # 데이터 타입 확인
        assert isinstance(result["spy_r1"], float)
        assert isinstance(result["vix"], float)
        assert isinstance(result["valid"], bool)
    
    def test_us_preopen_snapshot(self):
        """미국 pre-open 스냅샷 테스트"""
        result = self.provider.get_us_preopen_snapshot(self.test_date)
        
        expected_keys = ["es_change", "nq_change", "vix_fut_change", "usdkrw_change", "valid"]
        for key in expected_keys:
            assert key in result
        
        assert isinstance(result["es_change"], float)
        assert isinstance(result["valid"], bool)
    
    def test_cache_functionality(self):
        """캐시 기능 테스트"""
        with patch('kiwoom_api.api') as mock_api:
            mock_df = pd.DataFrame({
                'date': ['20241201'],
                'open': [50000],
                'high': [52000],
                'low': [49000],
                'close': [51000],
                'volume': [1000000]
            })
            mock_api.get_ohlcv.return_value = mock_df
            
            # 첫 번째 호출
            result1 = self.provider.get_ohlcv_korea("005930", self.start_date, self.test_date)
            
            # 두 번째 호출 (캐시에서 로드되어야 함)
            result2 = self.provider.get_ohlcv_korea("005930", self.start_date, self.test_date)
            
            # API는 한 번만 호출되어야 함
            assert mock_api.get_ohlcv.call_count == 1
            
            # 결과는 동일해야 함
            pd.testing.assert_frame_equal(result1, result2)

class TestUSMarketDataIntegration:
    """US Market Data 통합 테스트"""
    
    def test_get_us_prev_snapshot_integration(self):
        """get_us_prev_snapshot 통합 테스트"""
        from services.us_market_data import get_us_prev_snapshot
        
        result = get_us_prev_snapshot("20241201")
        
        # 기본 구조 확인
        expected_keys = ["spy_r1", "spy_r3", "spy_r5", "qqq_r1", "qqq_r3", "qqq_r5", 
                        "vix", "vix_change", "ust10y_change", "valid"]
        for key in expected_keys:
            assert key in result
    
    def test_get_us_preopen_snapshot_integration(self):
        """get_us_preopen_snapshot 통합 테스트"""
        from services.us_market_data import get_us_preopen_snapshot
        
        result = get_us_preopen_snapshot("20241201")
        
        expected_keys = ["es_change", "nq_change", "vix_fut_change", "usdkrw_change", "valid"]
        for key in expected_keys:
            assert key in result

class TestMarketAnalyzerV3Integration:
    """Market Analyzer v3 통합 테스트"""
    
    def test_analyze_market_condition_v3_no_yfinance(self):
        """v3 장세 분석에서 yfinance 사용하지 않는지 확인"""
        from market_analyzer import market_analyzer
        
        # yfinance import가 없어야 함
        import sys
        yfinance_modules = [name for name in sys.modules.keys() if 'yfinance' in name.lower()]
        
        # v3 분석 실행
        result = market_analyzer.analyze_market_condition_v3("20241201")
        
        # 결과 구조 확인
        assert hasattr(result, 'final_regime')
        assert hasattr(result, 'final_score')
        assert hasattr(result, 'version')
        assert result.version in ['regime_v1', 'regime_v3']
        
        # yfinance가 import되지 않았는지 확인
        new_yfinance_modules = [name for name in sys.modules.keys() if 'yfinance' in name.lower()]
        assert len(new_yfinance_modules) == len(yfinance_modules), "yfinance가 새로 import되었습니다"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])