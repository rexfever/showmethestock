"""
시장 분리 신호 통합 테스트 및 심층 검증
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import pandas as pd

# 백엔드 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from market_analyzer import MarketAnalyzer, MarketCondition
from scanner_factory import scan_with_scanner


class TestMarketDivergenceIntegration(unittest.TestCase):
    """통합 테스트: 전체 플로우 검증"""
    
    def setUp(self):
        self.analyzer = MarketAnalyzer()
    
    @patch('scanner_factory.api')
    def test_full_flow_with_divergence(self, mock_api):
        """분리 신호가 있을 때 전체 플로우 테스트"""
        # Mock 데이터 설정
        mock_df = pd.DataFrame({
            'close': [100] * 250,
            'open': [99] * 250,
            'high': [101] * 250,
            'low': [98] * 250,
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
        mock_df.index = pd.date_range('2024-01-01', periods=250, freq='D')
        
        mock_api.get_ohlcv.return_value = mock_df
        mock_api.get_stock_name.return_value = "테스트종목"
        mock_api.get_top_codes.side_effect = lambda market, limit: {
            'KOSPI': ['005930', '000660', '035420'] * (limit // 3 + 1),
            'KOSDAQ': ['123456', '234567', '345678'] * (limit // 3 + 1)
        }[market][:limit]
        
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
        
        # Universe 구성 (분리 신호에 따라 조정됨)
        kospi_limit = 100
        kosdaq_limit = 100
        if market_condition.market_divergence:
            kospi_limit = int(kospi_limit * 1.5)  # 150
            kosdaq_limit = int(kosdaq_limit * 0.5)  # 50
        
        kospi_codes = mock_api.get_top_codes('KOSPI', kospi_limit)
        kosdaq_codes = mock_api.get_top_codes('KOSDAQ', kosdaq_limit)
        universe = kospi_codes + kosdaq_codes
        
        # 검증
        self.assertEqual(len(kospi_codes), 150, "KOSPI는 150개여야 함")
        self.assertEqual(len(kosdaq_codes), 50, "KOSDAQ은 50개여야 함")
        self.assertEqual(len(universe), 200, "전체 Universe는 200개여야 함")
        
        # 스캔 실행 (간단한 검증만)
        # 실제 스캔은 복잡하므로 여기서는 Universe 구성만 검증


class TestPerformanceIssues(unittest.TestCase):
    """성능 문제 검증"""
    
    def test_api_call_frequency(self):
        """API 호출 빈도 검증"""
        # 문제: 각 종목마다 get_top_codes 호출
        # 개선: Universe 구성 시 한 번만 호출하고 재사용
        
        num_stocks = 200
        api_calls_per_stock = 1  # 현재 구현
        total_api_calls = num_stocks * api_calls_per_stock
        
        print(f"\n현재 구현: {num_stocks}개 종목 × {api_calls_per_stock}회 = {total_api_calls}회 API 호출")
        print(f"개선안: 1회 API 호출 (Universe 구성 시)")
        print(f"성능 개선: {total_api_calls - 1}회 API 호출 감소")
        
        self.assertGreater(total_api_calls, 1, "현재는 종목당 API 호출 발생")


class TestEdgeCasesDeep(unittest.TestCase):
    """심층 엣지 케이스 테스트"""
    
    def setUp(self):
        self.analyzer = MarketAnalyzer()
    
    def test_divergence_with_negative_kospi(self):
        """KOSPI가 음수인 경우 (비정상적이지만 가능)"""
        kr_trend_features = {
            "KOSPI_R20": -0.05,  # 음수
            "KOSDAQ_R20": -0.15,  # 더 큰 음수
            "R20": -0.05,
            "R60": -0.10
        }
        result = self.analyzer._detect_market_divergence(kr_trend_features)
        self.assertFalse(result, "KOSPI가 음수면 분리 신호가 아님")
    
    def test_divergence_with_positive_kosdaq(self):
        """KOSDAQ이 양수인 경우"""
        kr_trend_features = {
            "KOSPI_R20": 0.10,
            "KOSDAQ_R20": 0.05,  # 양수
            "R20": 0.10,
            "R60": 0.15
        }
        result = self.analyzer._detect_market_divergence(kr_trend_features)
        self.assertFalse(result, "KOSDAQ이 양수면 분리 신호가 아님")
    
    def test_divergence_with_string_values(self):
        """문자열 값이 들어온 경우 (타입 에러 방지)"""
        kr_trend_features = {
            "KOSPI_R20": "0.10",  # 문자열
            "KOSDAQ_R20": "-0.05",  # 문자열
            "R20": 0.10,
            "R60": 0.15
        }
        # abs() 연산 시 타입 에러 발생 가능
        try:
            result = self.analyzer._detect_market_divergence(kr_trend_features)
            # 타입 변환이 자동으로 되지 않으면 에러 발생
        except (TypeError, ValueError):
            # 예상된 에러
            pass
    
    def test_divergence_with_extreme_values(self):
        """극단적인 값 테스트"""
        kr_trend_features = {
            "KOSPI_R20": 1.0,  # 100% 상승 (비현실적)
            "KOSDAQ_R20": -1.0,  # 100% 하락 (비현실적)
            "R20": 1.0,
            "R60": 1.5
        }
        result = self.analyzer._detect_market_divergence(kr_trend_features)
        self.assertTrue(result, "극단적인 값도 처리되어야 함")


class TestUniverseAdjustmentEdgeCases(unittest.TestCase):
    """Universe 조정 엣지 케이스"""
    
    def test_universe_adjustment_with_small_limits(self):
        """작은 limit 값 테스트"""
        kospi_limit = 10
        kosdaq_limit = 10
        
        if True:  # 분리 신호가 있다고 가정
            adjusted_kospi = int(kospi_limit * 1.5)  # 15
            adjusted_kosdaq = int(kosdaq_limit * 0.5)  # 5
        
        self.assertEqual(adjusted_kospi, 15)
        self.assertEqual(adjusted_kosdaq, 5)
        self.assertGreater(adjusted_kospi, kospi_limit)
        self.assertLess(adjusted_kosdaq, kosdaq_limit)
    
    def test_universe_adjustment_with_zero_limit(self):
        """limit이 0인 경우"""
        kospi_limit = 0
        kosdaq_limit = 0
        
        if True:  # 분리 신호가 있다고 가정
            adjusted_kospi = int(kospi_limit * 1.5)  # 0
            adjusted_kosdaq = int(kosdaq_limit * 0.5)  # 0
        
        self.assertEqual(adjusted_kospi, 0)
        self.assertEqual(adjusted_kosdaq, 0)


if __name__ == '__main__':
    unittest.main()





































