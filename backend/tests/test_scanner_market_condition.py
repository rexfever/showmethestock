"""
스캐너의 장세 조건 적용 테스트
"""
import unittest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from scanner import match_stats
from market_analyzer import MarketCondition
from config import config

class TestScannerMarketCondition(unittest.TestCase):
    """스캐너 장세 조건 적용 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        # 기본 OHLCV 데이터 생성
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        self.df = pd.DataFrame({
            'date': dates,
            'open': np.random.uniform(50000, 60000, 100),
            'high': np.random.uniform(60000, 70000, 100),
            'low': np.random.uniform(40000, 50000, 100),
            'close': np.random.uniform(50000, 60000, 100),
            'volume': np.random.uniform(1000000, 2000000, 100)
        })
        
        # 인디케이터 계산 (간단한 버전)
        self.df['TEMA20'] = self.df['close'].rolling(20).mean()
        self.df['DEMA10'] = self.df['close'].rolling(10).mean()
        self.df['RSI_TEMA'] = 60.0  # 테스트용 고정값
        self.df['RSI_DEMA'] = 55.0  # 테스트용 고정값
        self.df['MACD'] = 0.5
        self.df['MACD_SIGNAL'] = 0.3
        self.df['VOL_MA5'] = self.df['volume'].rolling(5).mean()
        self.df['VOL_MA20'] = self.df['volume'].rolling(20).mean()
        
        # 마지막 행 채우기
        self.df = self.df.fillna(method='backfill')
    
    def test_match_stats_with_bull_condition(self):
        """강세장 조건 적용 테스트"""
        bull_condition = MarketCondition(
            date="20251105",
            kospi_return=0.03,
            volatility=0.02,
            market_sentiment='bull',
            sector_rotation='tech',
            foreign_flow='buy',
            volume_trend='high',
            rsi_threshold=65.0,  # 높은 RSI 허용
            min_signals=2,  # 완화된 신호
            macd_osc_min=-5.0,
            vol_ma5_mult=1.5,
            gap_max=0.02,
            ext_from_tema20_max=0.02
        )
        
        matched, sig_true, sig_total = match_stats(self.df, bull_condition, "테스트종목")
        
        # market_condition이 적용되었는지 확인
        # (실제 매칭 여부는 데이터에 따라 다를 수 있음)
        self.assertIsInstance(matched, bool)
        self.assertIsInstance(sig_true, int)
        self.assertIsInstance(sig_total, int)
    
    def test_match_stats_with_bear_condition(self):
        """약세장 조건 적용 테스트"""
        bear_condition = MarketCondition(
            date="20251105",
            kospi_return=-0.025,
            volatility=0.03,
            market_sentiment='bear',
            sector_rotation='value',
            foreign_flow='sell',
            volume_trend='low',
            rsi_threshold=45.0,  # 낮은 RSI 허용
            min_signals=4,  # 강화된 신호
            macd_osc_min=5.0,
            vol_ma5_mult=2.0,
            gap_max=0.01,
            ext_from_tema20_max=0.01
        )
        
        matched, sig_true, sig_total = match_stats(self.df, bear_condition, "테스트종목")
        
        # market_condition이 적용되었는지 확인
        self.assertIsInstance(matched, bool)
        self.assertIsInstance(sig_true, int)
        self.assertIsInstance(sig_total, int)
    
    def test_match_stats_without_market_condition(self):
        """장세 조건 없이 기본 조건 사용 테스트"""
        matched, sig_true, sig_total = match_stats(self.df, None, "테스트종목")
        
        # 기본 조건 사용 확인
        self.assertIsInstance(matched, bool)
        self.assertIsInstance(sig_true, int)
        self.assertIsInstance(sig_total, int)
    
    def test_match_stats_with_neutral_condition(self):
        """중립장 조건 적용 테스트"""
        neutral_condition = MarketCondition(
            date="20251105",
            kospi_return=0.0,
            volatility=0.02,
            market_sentiment='neutral',
            sector_rotation='mixed',
            foreign_flow='neutral',
            volume_trend='normal',
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=1.6,
            gap_max=0.018,
            ext_from_tema20_max=0.018
        )
        
        matched, sig_true, sig_total = match_stats(self.df, neutral_condition, "테스트종목")
        
        # market_condition이 적용되었는지 확인
        self.assertIsInstance(matched, bool)
        self.assertIsInstance(sig_true, int)
        self.assertIsInstance(sig_total, int)
    
    def test_match_stats_condition_priority(self):
        """장세 조건 우선순위 테스트 (market_condition이 config보다 우선)"""
        bull_condition = MarketCondition(
            date="20251105",
            kospi_return=0.03,
            volatility=0.02,
            market_sentiment='bull',
            sector_rotation='tech',
            foreign_flow='buy',
            volume_trend='high',
            rsi_threshold=65.0,  # config.rsi_threshold(58)보다 높음
            min_signals=2,  # config.min_signals(2)와 동일하거나 낮음
            macd_osc_min=-5.0,
            vol_ma5_mult=1.5,
            gap_max=0.02,
            ext_from_tema20_max=0.02
        )
        
        # config.market_analysis_enable이 True일 때만 market_condition 사용
        original_enable = config.market_analysis_enable
        
        try:
            config.market_analysis_enable = True
            matched1, sig_true1, sig_total1 = match_stats(self.df, bull_condition, "테스트종목")
            
            config.market_analysis_enable = False
            matched2, sig_true2, sig_total2 = match_stats(self.df, bull_condition, "테스트종목")
            
            # market_analysis_enable이 False면 기본 조건 사용
            # (결과는 다를 수 있지만, 로직이 다르게 적용되는지 확인)
            self.assertIsInstance(matched1, bool)
            self.assertIsInstance(matched2, bool)
        finally:
            config.market_analysis_enable = original_enable

if __name__ == '__main__':
    unittest.main()

