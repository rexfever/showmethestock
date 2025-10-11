"""
시장 분석기 테스트
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import pandas as pd

# 상위 디렉토리의 모듈 import
sys.path.append('..')
from market_analyzer import MarketAnalyzer, MarketCondition

class TestMarketAnalyzer(unittest.TestCase):
    """시장 분석기 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.analyzer = MarketAnalyzer()
        
        # 샘플 KOSPI 데이터 생성
        self.sample_kospi_data = pd.DataFrame({
            'close': [2500, 2550, 2520, 2580, 2600, 2570, 2620, 2650, 2630, 2680],
            'volume': [1000000, 1200000, 1100000, 1300000, 1400000, 1350000, 1450000, 1500000, 1420000, 1480000],
            'high': [2520, 2560, 2530, 2590, 2610, 2580, 2630, 2660, 2640, 2690],
            'low': [2480, 2530, 2500, 2560, 2580, 2550, 2600, 2630, 2610, 2660]
        })
    
    def test_market_condition_creation(self):
        """시장 상황 객체 생성 테스트"""
        condition = MarketCondition(
            market_sentiment="bull",
            kospi_change=2.5,
            volatility=0.8,
            rsi_threshold=60.0
        )
        
        self.assertEqual(condition.market_sentiment, "bull")
        self.assertEqual(condition.kospi_change, 2.5)
        self.assertEqual(condition.volatility, 0.8)
        self.assertEqual(condition.rsi_threshold, 60.0)
    
    @patch('market_analyzer.KiwoomAPI')
    def test_analyze_market_bull(self, mock_kiwoom_api):
        """상승장 분석 테스트"""
        # Mock 설정
        mock_api = MagicMock()
        mock_api.get_ohlcv.return_value = self.sample_kospi_data
        mock_kiwoom_api.return_value = mock_api
        
        # 상승장 데이터 (KOSPI +2.5%)
        bull_data = self.sample_kospi_data.copy()
        bull_data['close'] = [2500, 2550, 2600, 2650, 2700, 2750, 2800, 2850, 2900, 2950]
        
        mock_api.get_ohlcv.return_value = bull_data
        
        # 분석 실행
        result = self.analyzer.analyze_market()
        
        # 검증
        self.assertIsInstance(result, MarketCondition)
        self.assertEqual(result.market_sentiment, "bull")
        self.assertGreater(result.kospi_change, 0)
        self.assertGreater(result.rsi_threshold, 50)  # 상승장에서는 RSI 임계값이 높아야 함
    
    @patch('market_analyzer.KiwoomAPI')
    def test_analyze_market_bear(self, mock_kiwoom_api):
        """하락장 분석 테스트"""
        # Mock 설정
        mock_api = MagicMock()
        mock_kiwoom_api.return_value = mock_api
        
        # 하락장 데이터 (KOSPI -2.5%)
        bear_data = self.sample_kospi_data.copy()
        bear_data['close'] = [2500, 2450, 2400, 2350, 2300, 2250, 2200, 2150, 2100, 2050]
        
        mock_api.get_ohlcv.return_value = bear_data
        
        # 분석 실행
        result = self.analyzer.analyze_market()
        
        # 검증
        self.assertIsInstance(result, MarketCondition)
        self.assertEqual(result.market_sentiment, "bear")
        self.assertLess(result.kospi_change, 0)
        self.assertLess(result.rsi_threshold, 50)  # 하락장에서는 RSI 임계값이 낮아야 함
    
    @patch('market_analyzer.KiwoomAPI')
    def test_analyze_market_neutral(self, mock_kiwoom_api):
        """중립장 분석 테스트"""
        # Mock 설정
        mock_api = MagicMock()
        mock_kiwoom_api.return_value = mock_api
        
        # 중립장 데이터 (KOSPI 변화 거의 없음)
        neutral_data = self.sample_kospi_data.copy()
        neutral_data['close'] = [2500, 2505, 2495, 2502, 2498, 2503, 2497, 2501, 2499, 2500]
        
        mock_api.get_ohlcv.return_value = neutral_data
        
        # 분석 실행
        result = self.analyzer.analyze_market()
        
        # 검증
        self.assertIsInstance(result, MarketCondition)
        self.assertEqual(result.market_sentiment, "neutral")
        self.assertAlmostEqual(result.kospi_change, 0, delta=1.0)  # 거의 0에 가까움
    
    def test_calculate_volatility(self):
        """변동성 계산 테스트"""
        # 변동성이 높은 데이터
        high_vol_data = pd.DataFrame({
            'close': [100, 120, 80, 140, 60, 160, 40, 180, 20, 200]
        })
        
        volatility = self.analyzer._calculate_volatility(high_vol_data)
        
        # 변동성이 높은지 확인
        self.assertGreater(volatility, 1.0)
    
    def test_calculate_volatility_low(self):
        """낮은 변동성 계산 테스트"""
        # 변동성이 낮은 데이터
        low_vol_data = pd.DataFrame({
            'close': [100, 101, 99, 102, 98, 103, 97, 104, 96, 105]
        })
        
        volatility = self.analyzer._calculate_volatility(low_vol_data)
        
        # 변동성이 낮은지 확인
        self.assertLess(volatility, 0.5)
    
    def test_adjust_conditions_by_volatility(self):
        """변동성에 따른 조건 조정 테스트"""
        base_condition = MarketCondition(
            market_sentiment="neutral",
            kospi_change=0.0,
            volatility=1.0,
            rsi_threshold=55.0
        )
        
        # 높은 변동성으로 조정
        adjusted = self.analyzer._adjust_conditions_by_volatility(base_condition, 2.0)
        
        # 높은 변동성에서는 RSI 임계값이 조정되어야 함
        self.assertNotEqual(adjusted.rsi_threshold, base_condition.rsi_threshold)
    
    def test_cache_functionality(self):
        """캐시 기능 테스트"""
        # 첫 번째 호출
        result1 = self.analyzer.analyze_market()
        
        # 두 번째 호출 (캐시에서 반환되어야 함)
        result2 = self.analyzer.analyze_market()
        
        # 같은 결과인지 확인
        self.assertEqual(result1.market_sentiment, result2.market_sentiment)
        self.assertEqual(result1.rsi_threshold, result2.rsi_threshold)
    
    def test_clear_cache(self):
        """캐시 클리어 테스트"""
        # 캐시 설정
        self.analyzer.analyze_market()
        
        # 캐시 클리어
        self.analyzer.clear_cache()
        
        # 캐시가 클리어되었는지 확인
        self.assertIsNone(self.analyzer._cache)
        self.assertIsNone(self.analyzer._cache_timestamp)
    
    def test_market_condition_edge_cases(self):
        """시장 상황 엣지 케이스 테스트"""
        # 극단적인 상승
        extreme_bull = MarketCondition(
            market_sentiment="bull",
            kospi_change=10.0,
            volatility=3.0,
            rsi_threshold=80.0
        )
        
        self.assertEqual(extreme_bull.market_sentiment, "bull")
        self.assertEqual(extreme_bull.kospi_change, 10.0)
        
        # 극단적인 하락
        extreme_bear = MarketCondition(
            market_sentiment="bear",
            kospi_change=-10.0,
            volatility=3.0,
            rsi_threshold=20.0
        )
        
        self.assertEqual(extreme_bear.market_sentiment, "bear")
        self.assertEqual(extreme_bear.kospi_change, -10.0)

if __name__ == '__main__':
    unittest.main()
