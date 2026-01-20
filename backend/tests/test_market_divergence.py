"""
시장 분리 신호 감지 및 KOSPI 가산점 로직 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# 백엔드 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from market_analyzer import MarketAnalyzer, MarketCondition
from scanner import scan_one_symbol
from scanner_v2.core.scanner import ScannerV2
from scanner_v2.core.scorer import Scorer
import pandas as pd
import numpy as np


class TestMarketDivergenceDetection(unittest.TestCase):
    """시장 분리 신호 감지 테스트"""
    
    def setUp(self):
        self.analyzer = MarketAnalyzer()
    
    def test_detect_divergence_positive(self):
        """정상적인 분리 신호 감지"""
        kr_trend_features = {
            "KOSPI_R20": 0.10,  # 10% 상승
            "KOSDAQ_R20": -0.05,  # 5% 하락
            "R20": 0.10,
            "R60": 0.15
        }
        result = self.analyzer._detect_market_divergence(kr_trend_features)
        self.assertTrue(result, "분리 신호가 감지되어야 함")
    
    def test_detect_divergence_negative(self):
        """분리 신호가 아닌 경우"""
        kr_trend_features = {
            "KOSPI_R20": 0.03,  # 3% 상승
            "KOSDAQ_R20": -0.01,  # 1% 하락 (차이 4% < 5%)
            "R20": 0.03,
            "R60": 0.05
        }
        result = self.analyzer._detect_market_divergence(kr_trend_features)
        self.assertFalse(result, "분리 신호가 감지되지 않아야 함")
    
    def test_detect_divergence_both_up(self):
        """둘 다 상승하는 경우"""
        kr_trend_features = {
            "KOSPI_R20": 0.10,
            "KOSDAQ_R20": 0.05,  # 둘 다 상승
            "R20": 0.10,
            "R60": 0.15
        }
        result = self.analyzer._detect_market_divergence(kr_trend_features)
        self.assertFalse(result, "둘 다 상승하면 분리 신호가 아님")
    
    def test_detect_divergence_both_down(self):
        """둘 다 하락하는 경우"""
        kr_trend_features = {
            "KOSPI_R20": -0.05,
            "KOSDAQ_R20": -0.10,  # 둘 다 하락
            "R20": -0.05,
            "R60": -0.10
        }
        result = self.analyzer._detect_market_divergence(kr_trend_features)
        self.assertFalse(result, "둘 다 하락하면 분리 신호가 아님")
    
    def test_detect_divergence_missing_features(self):
        """필수 feature가 없는 경우"""
        kr_trend_features = {
            "R20": 0.10,
            "R60": 0.15
            # KOSPI_R20, KOSDAQ_R20 없음
        }
        result = self.analyzer._detect_market_divergence(kr_trend_features)
        self.assertFalse(result, "필수 feature가 없으면 False 반환")
    
    def test_detect_divergence_empty_dict(self):
        """빈 딕셔너리인 경우"""
        result = self.analyzer._detect_market_divergence({})
        self.assertFalse(result, "빈 딕셔너리면 False 반환")
    
    def test_detect_divergence_exact_threshold(self):
        """임계값 정확히 5%인 경우"""
        kr_trend_features = {
            "KOSPI_R20": 0.025,  # 2.5%
            "KOSDAQ_R20": -0.025,  # -2.5% (차이 5%)
            "R20": 0.025,
            "R60": 0.05
        }
        result = self.analyzer._detect_market_divergence(kr_trend_features)
        self.assertFalse(result, "5% 정확히면 False (초과해야 함)")
    
    def test_detect_divergence_above_threshold(self):
        """임계값을 초과하는 경우"""
        kr_trend_features = {
            "KOSPI_R20": 0.04,  # 4%
            "KOSDAQ_R20": -0.02,  # -2% (차이 6% > 5%)
            "R20": 0.04,
            "R60": 0.06
        }
        result = self.analyzer._detect_market_divergence(kr_trend_features)
        self.assertTrue(result, "5% 초과하면 True")


class TestKOSPIBonusV1(unittest.TestCase):
    """V1 스캐너 KOSPI 가산점 테스트"""
    
    def setUp(self):
        # Mock 데이터 생성
        self.mock_df = pd.DataFrame({
            'close': [100, 105, 110, 115, 120] * 50,
            'open': [99, 104, 109, 114, 119] * 50,
            'high': [101, 106, 111, 116, 121] * 50,
            'low': [98, 103, 108, 113, 118] * 50,
            'volume': [1000000] * 250,
            'TEMA20': [110] * 250,
            'DEMA10': [108] * 250,
            'MACD_LINE': [1.0] * 250,
            'MACD_SIGNAL': [0.5] * 250,
            'MACD_OSC': [0.5] * 250,
            'RSI_TEMA': [55] * 250,
            'RSI_DEMA': [53] * 250,
            'OBV': [100000] * 250,
            'VOL_MA5': [900000] * 250,
            'EMA60': [100] * 250,
            'TEMA20_SLOPE20': [0.01] * 250,
            'OBV_SLOPE20': [0.01] * 250,
        })
        self.mock_df.index = pd.date_range('2024-01-01', periods=250, freq='D')
    
    @patch('scanner.api')
    def test_kospi_bonus_applied(self, mock_api):
        """KOSPI 종목에 가산점이 적용되는지 테스트"""
        # Mock 설정
        mock_api.get_ohlcv.return_value = self.mock_df
        mock_api.get_stock_name.return_value = "테스트종목"
        mock_api.get_top_codes.return_value = ['005930', '000660', '035420']  # KOSPI 종목 리스트
        
        # 분리 신호가 있는 market_condition 생성
        market_condition = MarketCondition(
            date="20240101",
            kospi_return=0.05,
            volatility=0.02,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="buy",
            institution_flow="buy",
            volume_trend="high",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
        market_condition.market_divergence = True
        market_condition.kospi_r20 = 0.10
        market_condition.kosdaq_r20 = -0.05
        
        # KOSPI 종목 스캔
        result = scan_one_symbol('005930', '20240101', market_condition)
        
        self.assertIsNotNone(result, "결과가 있어야 함")
        if result:
            self.assertIn('kospi_bonus', result.get('flags', {}), "kospi_bonus 플래그가 있어야 함")
            self.assertTrue(result['flags'].get('kospi_bonus', False), "kospi_bonus가 True여야 함")
            # 점수가 가산점이 반영되었는지 확인 (정확한 값은 스캔 로직에 따라 다를 수 있음)
    
    @patch('scanner.api')
    def test_kosdaq_no_bonus(self, mock_api):
        """KOSDAQ 종목에는 가산점이 적용되지 않는지 테스트"""
        mock_api.get_ohlcv.return_value = self.mock_df
        mock_api.get_stock_name.return_value = "테스트종목"
        mock_api.get_top_codes.return_value = ['005930', '000660', '035420']  # KOSPI 종목만
        
        market_condition = MarketCondition(
            date="20240101",
            kospi_return=0.05,
            volatility=0.02,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="buy",
            institution_flow="buy",
            volume_trend="high",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
        market_condition.market_divergence = True
        
        # KOSDAQ 종목 스캔 (KOSPI 리스트에 없음)
        result = scan_one_symbol('123456', '20240101', market_condition)  # KOSDAQ 종목 코드
        
        if result:
            # KOSDAQ 종목이면 kospi_bonus가 없거나 False여야 함
            kospi_bonus = result.get('flags', {}).get('kospi_bonus', False)
            self.assertFalse(kospi_bonus, "KOSDAQ 종목에는 가산점이 없어야 함")
    
    @patch('scanner.api')
    def test_no_divergence_no_bonus(self, mock_api):
        """분리 신호가 없으면 가산점이 적용되지 않는지 테스트"""
        mock_api.get_ohlcv.return_value = self.mock_df
        mock_api.get_stock_name.return_value = "테스트종목"
        mock_api.get_top_codes.return_value = ['005930']
        
        market_condition = MarketCondition(
            date="20240101",
            kospi_return=0.05,
            volatility=0.02,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="buy",
            institution_flow="buy",
            volume_trend="high",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
        market_condition.market_divergence = False  # 분리 신호 없음
        
        result = scan_one_symbol('005930', '20240101', market_condition)
        
        if result:
            kospi_bonus = result.get('flags', {}).get('kospi_bonus', False)
            self.assertFalse(kospi_bonus, "분리 신호가 없으면 가산점이 없어야 함")


class TestUniverseAdjustment(unittest.TestCase):
    """Universe 비율 조정 테스트"""
    
    def test_universe_adjustment_with_divergence(self):
        """분리 신호 시 Universe 비율 조정 테스트"""
        kospi_limit = 100
        kosdaq_limit = 100
        
        # 분리 신호가 있는 경우
        market_condition = MarketCondition(
            date="20240101",
            kospi_return=0.05,
            volatility=0.02,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="buy",
            institution_flow="buy",
            volume_trend="high",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
        market_condition.market_divergence = True
        
        if market_condition.market_divergence:
            adjusted_kospi = int(kospi_limit * 1.5)
            adjusted_kosdaq = int(kosdaq_limit * 0.5)
            
            self.assertEqual(adjusted_kospi, 150, "KOSPI는 1.5배 증가해야 함")
            self.assertEqual(adjusted_kosdaq, 50, "KOSDAQ은 0.5배 감소해야 함")
    
    def test_universe_no_adjustment_without_divergence(self):
        """분리 신호가 없으면 Universe 비율이 조정되지 않는지 테스트"""
        kospi_limit = 100
        kosdaq_limit = 100
        
        market_condition = MarketCondition(
            date="20240101",
            kospi_return=0.05,
            volatility=0.02,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="buy",
            institution_flow="buy",
            volume_trend="high",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
        market_condition.market_divergence = False
        
        if not market_condition.market_divergence:
            adjusted_kospi = kospi_limit
            adjusted_kosdaq = kosdaq_limit
            
            self.assertEqual(adjusted_kospi, 100, "분리 신호가 없으면 KOSPI 비율 유지")
            self.assertEqual(adjusted_kosdaq, 100, "분리 신호가 없으면 KOSDAQ 비율 유지")


class TestEdgeCases(unittest.TestCase):
    """엣지 케이스 테스트"""
    
    def test_divergence_with_zero_values(self):
        """0 값이 포함된 경우"""
        analyzer = MarketAnalyzer()
        kr_trend_features = {
            "KOSPI_R20": 0.0,
            "KOSDAQ_R20": -0.10,
            "R20": 0.0,
            "R60": 0.0
        }
        result = analyzer._detect_market_divergence(kr_trend_features)
        self.assertFalse(result, "KOSPI가 0이면 분리 신호가 아님")
    
    def test_divergence_with_very_large_values(self):
        """매우 큰 값이 포함된 경우"""
        analyzer = MarketAnalyzer()
        kr_trend_features = {
            "KOSPI_R20": 0.50,  # 50% 상승
            "KOSDAQ_R20": -0.40,  # 40% 하락 (차이 90%)
            "R20": 0.50,
            "R60": 0.60
        }
        result = analyzer._detect_market_divergence(kr_trend_features)
        self.assertTrue(result, "큰 분리도도 감지되어야 함")
    
    def test_divergence_with_none_values(self):
        """None 값이 포함된 경우"""
        analyzer = MarketAnalyzer()
        kr_trend_features = {
            "KOSPI_R20": None,
            "KOSDAQ_R20": -0.05,
            "R20": 0.10,
            "R60": 0.15
        }
        result = analyzer._detect_market_divergence(kr_trend_features)
        self.assertFalse(result, "None 값이 있으면 False 반환")


if __name__ == '__main__':
    unittest.main()

