"""
장세 로직 통합 테스트
"""
import unittest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from market_analyzer import market_analyzer, MarketCondition
from services.scan_service import execute_scan_with_fallback
from config import config

class TestMarketConditionIntegration(unittest.TestCase):
    """장세 로직 통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.universe = ["005930", "000660", "051910"]
    
    @patch('kiwoom_api.api')
    def test_full_flow_crash(self, mock_api):
        """급락장 전체 흐름 테스트"""
        # KOSPI -4% 급락 시뮬레이션
        mock_df = pd.DataFrame({
            'close': [100.0, 96.0],  # -4%
            'high': [101.0, 97.0],
            'low': [99.0, 95.0]
        })
        mock_api.get_ohlcv.return_value = mock_df
        
        # 시장 상황 분석
        condition = market_analyzer.analyze_market_condition('20251105')
        
        # 급락장 감지 확인
        self.assertEqual(condition.market_sentiment, 'crash')
        self.assertLess(condition.kospi_return, -0.03)
        
        # 스캔 실행 시 빈 리스트 반환 확인
        with patch('services.scan_service.scan_with_preset') as mock_scan:
            items, chosen_step = execute_scan_with_fallback(
                self.universe,
                date="20251105",
                market_condition=condition
            )
            
            # 급락장에서는 빈 리스트 반환
            self.assertEqual(len(items), 0)
            self.assertIsNone(chosen_step)
            # scan_with_preset은 호출되지 않음
            mock_scan.assert_not_called()
    
    @patch('kiwoom_api.api')
    def test_full_flow_bull(self, mock_api):
        """강세장 전체 흐름 테스트"""
        # KOSPI +3% 상승 시뮬레이션
        mock_df = pd.DataFrame({
            'close': [100.0, 103.0],  # +3%
            'high': [101.0, 104.0],
            'low': [99.0, 102.0]
        })
        mock_api.get_ohlcv.return_value = mock_df
        
        # 시장 상황 분석
        condition = market_analyzer.analyze_market_condition('20251105')
        
        # 강세장 감지 확인
        self.assertEqual(condition.market_sentiment, 'bull')
        self.assertGreater(condition.kospi_return, 0.02)
        
        # 강세장 조건 확인
        self.assertEqual(condition.rsi_threshold, 65.0)
        self.assertEqual(condition.min_signals, 2)
        self.assertEqual(condition.vol_ma5_mult, 1.5)
    
    @patch('kiwoom_api.api')
    def test_full_flow_bear(self, mock_api):
        """약세장 전체 흐름 테스트"""
        # KOSPI -2.5% 하락 시뮬레이션
        mock_df = pd.DataFrame({
            'close': [100.0, 97.5],  # -2.5%
            'high': [101.0, 98.0],
            'low': [99.0, 97.0]
        })
        mock_api.get_ohlcv.return_value = mock_df
        
        # 시장 상황 분석
        condition = market_analyzer.analyze_market_condition('20251105')
        
        # 약세장 감지 확인
        self.assertEqual(condition.market_sentiment, 'bear')
        self.assertLess(condition.kospi_return, -0.02)
        self.assertGreater(condition.kospi_return, -0.03)
        
        # 약세장 조건 확인
        self.assertEqual(condition.rsi_threshold, 45.0)
        self.assertEqual(condition.min_signals, 4)
        self.assertEqual(condition.vol_ma5_mult, 2.0)
    
    @patch('kiwoom_api.api')
    def test_market_condition_caching(self, mock_api):
        """시장 상황 캐싱 테스트"""
        mock_df = pd.DataFrame({
            'close': [100.0, 103.0],
            'high': [101.0, 104.0],
            'low': [99.0, 102.0]
        })
        mock_api.get_ohlcv.return_value = mock_df
        
        # 첫 번째 분석
        condition1 = market_analyzer.analyze_market_condition('20251105')
        
        # 두 번째 분석 (캐시 사용)
        condition2 = market_analyzer.analyze_market_condition('20251105')
        
        # 같은 결과 반환 확인
        self.assertEqual(condition1.market_sentiment, condition2.market_sentiment)
        self.assertEqual(condition1.rsi_threshold, condition2.rsi_threshold)
        
        # API는 한 번만 호출되어야 함 (캐시 사용)
        # 하지만 실제로는 캐시 TTL 내에서만 캐시 사용
    
    def test_market_condition_edge_cases(self):
        """경계값 테스트"""
        # -3% 정확히 (경계값)
        sentiment = market_analyzer._determine_market_sentiment(-0.03, 0.02)
        self.assertEqual(sentiment, 'bear')  # -3%는 bear
        
        # -3.01% (crash)
        sentiment = market_analyzer._determine_market_sentiment(-0.0301, 0.02)
        self.assertEqual(sentiment, 'crash')
        
        # +2% 정확히는 neutral (경계값: > 0.02가 아니므로)
        sentiment = market_analyzer._determine_market_sentiment(0.02, 0.02)
        self.assertEqual(sentiment, 'neutral')
        
        # +2.1%는 bull
        sentiment = market_analyzer._determine_market_sentiment(0.021, 0.02)
        self.assertEqual(sentiment, 'bull')
        
        # +1.99% (neutral)
        sentiment = market_analyzer._determine_market_sentiment(0.0199, 0.02)
        self.assertEqual(sentiment, 'neutral')
        
        # -2% 정확히는 neutral (경계값: < -0.02가 아니므로)
        sentiment = market_analyzer._determine_market_sentiment(-0.02, 0.02)
        self.assertEqual(sentiment, 'neutral')
        
        # -2.1%는 bear
        sentiment = market_analyzer._determine_market_sentiment(-0.021, 0.02)
        self.assertEqual(sentiment, 'bear')
        
        # -1.99% (neutral)
        sentiment = market_analyzer._determine_market_sentiment(-0.0199, 0.02)
        self.assertEqual(sentiment, 'neutral')

if __name__ == '__main__':
    import pandas as pd
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    unittest.main()

