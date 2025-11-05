"""
장세 분석 로직 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from market_analyzer import MarketAnalyzer, MarketCondition

class TestMarketAnalyzer(unittest.TestCase):
    """장세 분석기 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.analyzer = MarketAnalyzer()
        
    def test_determine_market_sentiment_bull(self):
        """강세장 감지 테스트"""
        # +2% 이상 (초과)
        sentiment = self.analyzer._determine_market_sentiment(0.03, 0.02)  # +3%
        self.assertEqual(sentiment, 'bull')
        
        sentiment = self.analyzer._determine_market_sentiment(0.021, 0.02)  # +2.1% (> 0.02)
        self.assertEqual(sentiment, 'bull')
        
        # +2% 정확히는 neutral (경계값)
        sentiment = self.analyzer._determine_market_sentiment(0.02, 0.02)  # +2%
        self.assertEqual(sentiment, 'neutral')
    
    def test_determine_market_sentiment_neutral(self):
        """중립장 감지 테스트"""
        # -2% ~ +2%
        sentiment = self.analyzer._determine_market_sentiment(0.01, 0.02)  # +1%
        self.assertEqual(sentiment, 'neutral')
        
        sentiment = self.analyzer._determine_market_sentiment(0.0, 0.02)  # 0%
        self.assertEqual(sentiment, 'neutral')
        
        sentiment = self.analyzer._determine_market_sentiment(-0.01, 0.02)  # -1%
        self.assertEqual(sentiment, 'neutral')
    
    def test_determine_market_sentiment_bear(self):
        """약세장 감지 테스트"""
        # -3% ~ -2% (초과)
        sentiment = self.analyzer._determine_market_sentiment(-0.025, 0.02)  # -2.5%
        self.assertEqual(sentiment, 'bear')
        
        sentiment = self.analyzer._determine_market_sentiment(-0.021, 0.02)  # -2.1% (< -0.02)
        self.assertEqual(sentiment, 'bear')
        
        # -2% 정확히는 neutral (경계값)
        sentiment = self.analyzer._determine_market_sentiment(-0.02, 0.02)  # -2%
        self.assertEqual(sentiment, 'neutral')
        
        # -3% 정확히는 bear (경계값)
        sentiment = self.analyzer._determine_market_sentiment(-0.03, 0.02)  # -3%
        self.assertEqual(sentiment, 'bear')
    
    def test_determine_market_sentiment_crash(self):
        """급락장 감지 테스트"""
        # -3% 미만
        sentiment = self.analyzer._determine_market_sentiment(-0.04, 0.02)  # -4%
        self.assertEqual(sentiment, 'crash')
        
        sentiment = self.analyzer._determine_market_sentiment(-0.05, 0.02)  # -5%
        self.assertEqual(sentiment, 'crash')
    
    def test_adjust_conditions_bull(self):
        """강세장 조건 조정 테스트"""
        conditions = self.analyzer._adjust_conditions('bull', 0.03, 0.02, 'normal')
        
        self.assertEqual(conditions['rsi_threshold'], 65.0)
        self.assertEqual(conditions['min_signals'], 2)
        self.assertEqual(conditions['macd_osc_min'], -5.0)
        self.assertEqual(conditions['vol_ma5_mult'], 1.5)
        self.assertEqual(conditions['gap_max'], 0.02)
    
    def test_adjust_conditions_neutral(self):
        """중립장 조건 조정 테스트"""
        conditions = self.analyzer._adjust_conditions('neutral', 0.0, 0.02, 'normal')
        
        self.assertEqual(conditions['rsi_threshold'], 58.0)
        self.assertEqual(conditions['min_signals'], 3)
        self.assertEqual(conditions['macd_osc_min'], 0.0)
        self.assertEqual(conditions['vol_ma5_mult'], 1.6)
        self.assertEqual(conditions['gap_max'], 0.018)
    
    def test_adjust_conditions_bear(self):
        """약세장 조건 조정 테스트"""
        conditions = self.analyzer._adjust_conditions('bear', -0.025, 0.02, 'normal')
        
        self.assertEqual(conditions['rsi_threshold'], 45.0)
        self.assertEqual(conditions['min_signals'], 4)
        self.assertEqual(conditions['macd_osc_min'], 5.0)
        self.assertEqual(conditions['vol_ma5_mult'], 2.0)
        self.assertEqual(conditions['gap_max'], 0.01)
    
    def test_adjust_conditions_crash(self):
        """급락장 조건 조정 테스트"""
        conditions = self.analyzer._adjust_conditions('crash', -0.04, 0.02, 'normal')
        
        self.assertEqual(conditions['rsi_threshold'], 40.0)
        self.assertEqual(conditions['min_signals'], 999)
        self.assertEqual(conditions['macd_osc_min'], 999.0)
        self.assertEqual(conditions['vol_ma5_mult'], 999.0)
        self.assertEqual(conditions['gap_max'], 0.001)
    
    def test_adjust_conditions_high_volatility(self):
        """고변동성 조건 조정 테스트"""
        conditions = self.analyzer._adjust_conditions('neutral', 0.0, 0.05, 'normal')  # 5% 변동성
        
        # 고변동성: RSI 임계값 +2, 최소 신호 +1
        self.assertGreater(conditions['rsi_threshold'], 58.0)
        self.assertGreater(conditions['min_signals'], 3)
    
    def test_adjust_conditions_low_volatility(self):
        """저변동성 조건 조정 테스트"""
        conditions = self.analyzer._adjust_conditions('neutral', 0.0, 0.01, 'normal')  # 1% 변동성
        
        # 저변동성: RSI 임계값 -1
        self.assertLess(conditions['rsi_threshold'], 58.0)
    
    def test_adjust_conditions_high_volume(self):
        """거래량 많음 조건 조정 테스트"""
        conditions = self.analyzer._adjust_conditions('neutral', 0.0, 0.02, 'high')
        
        # 거래량 많음: vol_ma5_mult -0.2
        self.assertLess(conditions['vol_ma5_mult'], 1.6)
    
    def test_adjust_conditions_low_volume(self):
        """거래량 적음 조건 조정 테스트"""
        conditions = self.analyzer._adjust_conditions('neutral', 0.0, 0.02, 'low')
        
        # 거래량 적음: vol_ma5_mult +0.2
        self.assertGreater(conditions['vol_ma5_mult'], 1.6)
    
    @patch('kiwoom_api.api')
    def test_get_kospi_data(self, mock_api):
        """KOSPI 데이터 가져오기 테스트"""
        # Mock 데이터 생성
        mock_df = pd.DataFrame({
            'close': [100.0, 103.0],  # 전일 100, 오늘 103 (+3%)
            'high': [104.0],
            'low': [102.0]
        })
        mock_api.get_ohlcv.return_value = mock_df
        
        kospi_return, volatility = self.analyzer._get_kospi_data('20251105')
        
        # +3% 수익률 확인
        self.assertAlmostEqual(kospi_return, 0.03, places=2)
        # 변동성 확인 (high - low) / close
        self.assertAlmostEqual(volatility, (104.0 - 102.0) / 103.0, places=2)
    
    @patch('kiwoom_api.api')
    def test_analyze_market_condition(self, mock_api):
        """시장 상황 분석 통합 테스트"""
        # Mock KOSPI 데이터 (+3% 상승)
        mock_df = pd.DataFrame({
            'close': [100.0, 103.0],
            'high': [104.0],
            'low': [102.0]
        })
        mock_api.get_ohlcv.return_value = mock_df
        
        condition = self.analyzer.analyze_market_condition('20251105')
        
        self.assertIsInstance(condition, MarketCondition)
        self.assertEqual(condition.market_sentiment, 'bull')
        self.assertAlmostEqual(condition.kospi_return, 0.03, places=2)
        self.assertEqual(condition.rsi_threshold, 65.0)
        self.assertEqual(condition.min_signals, 2)
    
    def test_get_market_preset(self):
        """시장 상황별 프리셋 테스트"""
        bull_preset = self.analyzer.get_market_preset('bull')
        self.assertEqual(bull_preset['rsi_threshold'], 65.0)
        self.assertEqual(bull_preset['min_signals'], 2)
        
        neutral_preset = self.analyzer.get_market_preset('neutral')
        self.assertEqual(neutral_preset['rsi_threshold'], 58.0)
        self.assertEqual(neutral_preset['min_signals'], 3)
        
        bear_preset = self.analyzer.get_market_preset('bear')
        self.assertEqual(bear_preset['rsi_threshold'], 45.0)
        self.assertEqual(bear_preset['min_signals'], 4)
        
        crash_preset = self.analyzer.get_market_preset('crash')
        self.assertEqual(crash_preset['rsi_threshold'], 40.0)
        self.assertEqual(crash_preset['min_signals'], 999)
    
    def test_cache_functionality(self):
        """캐시 기능 테스트"""
        # 캐시 클리어
        self.analyzer.clear_cache()
        self.assertEqual(len(self.analyzer._cache), 0)
        
        # 캐시에 데이터 저장
        mock_condition = MarketCondition(
            date='20251105',
            kospi_return=0.03,
            volatility=0.02,
            market_sentiment='bull',
            sector_rotation='mixed',
            foreign_flow='buy',
            volume_trend='high',
            rsi_threshold=65.0,
            min_signals=2,
            macd_osc_min=-5.0,
            vol_ma5_mult=1.5,
            gap_max=0.02,
            ext_from_tema20_max=0.02
        )
        self.analyzer._cache['market_analysis_20251105'] = (mock_condition, pd.Timestamp.now())
        
        self.assertEqual(len(self.analyzer._cache), 1)

if __name__ == '__main__':
    unittest.main()
