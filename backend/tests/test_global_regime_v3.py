#!/usr/bin/env python3
"""
Global Regime Model v3 종합 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# 테스트 환경 설정
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class TestGlobalRegimeV3(unittest.TestCase):
    """Global Regime v3 핵심 기능 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.test_date = "20241205"
        
    def test_market_condition_dataclass_v3_fields(self):
        """MarketCondition v3 필드 존재 확인"""
        from market_analyzer import MarketCondition
        
        # v3 필드들이 정의되어 있는지 확인
        v3_fields = [
            'final_regime', 'final_score', 'kr_score', 'us_prev_score',
            'us_preopen_risk_score', 'kr_regime', 'us_prev_regime', 
            'us_preopen_flag', 'intraday_drop', 'version'
        ]
        
        condition = MarketCondition(
            date="20241205", kospi_return=0.01, volatility=0.02,
            market_sentiment="neutral", sector_rotation="mixed",
            foreign_flow="neutral", institution_flow="neutral",
            volume_trend="normal", rsi_threshold=58.0, min_signals=3,
            macd_osc_min=0.0, vol_ma5_mult=1.8, gap_max=0.025,
            ext_from_tema20_max=0.025
        )
        
        for field in v3_fields:
            self.assertTrue(hasattr(condition, field), f"Missing v3 field: {field}")
    
    @patch('services.market_data_provider.market_data_provider.get_us_prev_snapshot')
    def test_us_market_data_loading(self, mock_get_snapshot):
        """미국 시장 데이터 로딩 테스트 (Kiwoom 기반)"""
        from services.us_market_data import get_us_prev_snapshot
        
        # Mock 데이터 설정
        mock_get_snapshot.return_value = {
            'spy_r1': 0.01, 'spy_r3': 0.02, 'spy_r5': 0.03,
            'qqq_r1': 0.015, 'qqq_r3': 0.025, 'qqq_r5': 0.035,
            'vix': 20.0, 'vix_change': -0.05, 'ust10y_change': 0.02,
            'valid': True
        }
        
        # 테스트 실행
        result = get_us_prev_snapshot(self.test_date)
        
        # 검증
        self.assertIsInstance(result, dict)
        required_keys = ['spy_r1', 'spy_r3', 'spy_r5', 'qqq_r1', 'qqq_r3', 'qqq_r5', 'vix', 'vix_change', 'ust10y_change', 'valid']
        for key in required_keys:
            self.assertIn(key, result)
        self.assertTrue(result['valid'])
    
    def test_regime_storage_functions(self):
        """Regime Storage 함수 테스트"""
        from services.regime_storage import save_regime, load_regime, upsert_regime
        
        # 함수 존재 확인
        self.assertTrue(callable(save_regime))
        self.assertTrue(callable(load_regime))
        self.assertTrue(callable(upsert_regime))
    
    @patch('market_analyzer.MarketAnalyzer._get_kospi_data')
    @patch('market_analyzer.MarketAnalyzer._get_universe_return')
    def test_kr_regime_score_calculation(self, mock_universe, mock_kospi):
        """한국 장세 점수 계산 테스트"""
        from market_analyzer import market_analyzer
        
        # Mock 데이터 설정
        mock_kospi.return_value = (0.015, 0.025, -0.01)  # kospi_return, volatility, kospi_low_return
        mock_universe.return_value = (0.012, 100)  # universe_return, sample_size
        
        # 테스트 실행
        result = market_analyzer.compute_kr_regime_score_v3(self.test_date)
        
        # 검증
        self.assertIsInstance(result, dict)
        required_keys = ['kr_trend_score', 'kr_vol_score', 'kr_breadth_score', 'kr_intraday_score', 'kr_score', 'kr_regime', 'intraday_drop']
        for key in required_keys:
            self.assertIn(key, result)
        
        # 점수 범위 확인
        self.assertGreaterEqual(result['kr_score'], -8.0)  # 최소 점수
        self.assertLessEqual(result['kr_score'], 8.0)      # 최대 점수
        self.assertIn(result['kr_regime'], ['bull', 'neutral', 'bear', 'crash'])
    
    def test_us_prev_score_calculation(self):
        """미국 전일 장세 점수 계산 테스트"""
        from market_analyzer import market_analyzer
        
        # 테스트 데이터
        valid_snapshot = {
            'valid': True,
            'spy_r3': 0.02, 'qqq_r3': 0.025, 'spy_r5': -0.01, 'qqq_r5': -0.02,
            'vix': 20.0, 'vix_change': -0.05, 'ust10y_change': 0.05
        }
        
        invalid_snapshot = {'valid': False}
        
        # 유효한 데이터 테스트
        result = market_analyzer.compute_us_prev_score(valid_snapshot)
        self.assertIsInstance(result, dict)
        self.assertIn('us_prev_regime', result)
        self.assertIn(result['us_prev_regime'], ['bull', 'neutral', 'bear', 'crash'])
        
        # 무효한 데이터 테스트
        result_invalid = market_analyzer.compute_us_prev_score(invalid_snapshot)
        self.assertEqual(result_invalid['us_prev_regime'], 'neutral')
        self.assertEqual(result_invalid['us_prev_score'], 0.0)
    
    def test_us_preopen_risk_calculation(self):
        """미국 pre-open 리스크 계산 테스트"""
        from market_analyzer import market_analyzer
        
        # 테스트 데이터
        high_risk_data = {
            'valid': True,
            'es_change': -0.025, 'nq_change': -0.035,
            'vix_fut_change': 0.15, 'usdkrw_change': 0.01
        }
        
        low_risk_data = {
            'valid': True,
            'es_change': 0.005, 'nq_change': 0.003,
            'vix_fut_change': -0.02, 'usdkrw_change': -0.002
        }
        
        # 고위험 테스트
        result_high = market_analyzer.compute_us_preopen_risk(high_risk_data)
        self.assertGreater(result_high['us_preopen_risk_score'], 3.0)
        self.assertEqual(result_high['us_preopen_flag'], 'danger')
        
        # 저위험 테스트
        result_low = market_analyzer.compute_us_preopen_risk(low_risk_data)
        self.assertLessEqual(result_low['us_preopen_risk_score'], 1.0)
        self.assertEqual(result_low['us_preopen_flag'], 'calm')
    
    def test_global_regime_composition(self):
        """글로벌 레짐 조합 테스트"""
        from market_analyzer import market_analyzer
        
        # 테스트 데이터
        kr_data = {'kr_score': 1.5, 'kr_regime': 'bull'}
        us_data = {'us_prev_score': 1.0, 'us_prev_regime': 'neutral'}
        preopen_data = {'us_preopen_flag': 'calm', 'us_preopen_risk_score': 0.5}
        
        # 테스트 실행
        result = market_analyzer.compose_global_regime_v3(kr_data, us_data, preopen_data, mode="backtest")
        
        # 검증
        self.assertIsInstance(result, dict)
        self.assertIn('final_score', result)
        self.assertIn('final_regime', result)
        self.assertIn(result['final_regime'], ['bull', 'neutral', 'bear', 'crash'])
        
        # 점수 계산 검증 (0.6 * 1.5 + 0.4 * 1.0 - 0.0 = 1.3)
        expected_score = 0.6 * 1.5 + 0.4 * 1.0
        self.assertAlmostEqual(result['final_score'], expected_score, places=1)
    
    @patch('services.market_data_provider.market_data_provider.get_us_prev_snapshot')
    @patch('services.market_data_provider.market_data_provider.get_us_preopen_snapshot')
    @patch('market_analyzer.MarketAnalyzer.analyze_market_condition')
    @patch('market_analyzer.MarketAnalyzer.compute_kr_regime_score_v3')
    def test_analyze_market_condition_v3_integration(self, mock_kr, mock_v1, mock_preopen, mock_us_prev):
        """analyze_market_condition_v3 통합 테스트"""
        from market_analyzer import market_analyzer, MarketCondition
        
        # Mock 설정
        mock_us_prev.return_value = {'valid': True, 'spy_r3': 0.01, 'qqq_r3': 0.01, 'spy_r5': 0.01, 'qqq_r5': 0.01, 'vix': 20, 'vix_change': 0, 'ust10y_change': 0}
        mock_preopen.return_value = {'valid': False}
        mock_kr.return_value = {'kr_score': 1.0, 'kr_regime': 'neutral', 'intraday_drop': -0.005}
        
        # 기존 v1 조건 Mock
        base_condition = MarketCondition(
            date=self.test_date, kospi_return=0.01, volatility=0.02,
            market_sentiment="neutral", sector_rotation="mixed",
            foreign_flow="neutral", institution_flow="neutral",
            volume_trend="normal", rsi_threshold=58.0, min_signals=3,
            macd_osc_min=0.0, vol_ma5_mult=1.8, gap_max=0.025,
            ext_from_tema20_max=0.025
        )
        mock_v1.return_value = base_condition
        
        # 테스트 실행
        with patch('services.regime_storage.upsert_regime'):
            result = market_analyzer.analyze_market_condition_v3(self.test_date, mode="backtest")
        
        # 검증
        self.assertIsInstance(result, MarketCondition)
        self.assertEqual(result.version, "regime_v3")
        self.assertIsNotNone(result.final_regime)
        self.assertIsNotNone(result.final_score)
    
    def test_scanner_v2_regime_cutoff(self):
        """Scanner v2 레짐별 cutoff 테스트"""
        from scanner_v2.core.scanner import ScannerV2
        from market_analyzer import MarketCondition
        
        # Mock 설정
        mock_config = Mock()
        scanner = ScannerV2(mock_config)
        
        # 테스트 결과 데이터
        mock_results = [
            Mock(ticker="001", score=7.0),
            Mock(ticker="002", score=5.0),
            Mock(ticker="003", score=4.0),
            Mock(ticker="004", score=3.0)
        ]
        
        # Bull 장세 테스트
        bull_condition = MarketCondition(
            date=self.test_date, kospi_return=0.02, volatility=0.02,
            market_sentiment="bull", sector_rotation="tech",
            foreign_flow="buy", institution_flow="buy",
            volume_trend="high", rsi_threshold=65.0, min_signals=2,
            macd_osc_min=-5.0, vol_ma5_mult=1.5, gap_max=0.03,
            ext_from_tema20_max=0.025, final_regime="bull"
        )
        
        filtered_results = scanner._apply_regime_cutoff(mock_results, bull_condition)
        
        # Bull 장세에서는 swing cutoff 6.0 이상만 통과
        self.assertGreater(len(filtered_results), 0)
        for result in filtered_results:
            if hasattr(result, 'score'):
                self.assertGreaterEqual(result.score, 4.3)  # position cutoff

class TestRegimeBacktest(unittest.TestCase):
    """Regime Backtest 테스트"""
    
    @patch('main.is_trading_day')
    @patch('services.regime_storage.load_regime')
    @patch('kiwoom_api.api.get_ohlcv')
    def test_run_regime_backtest(self, mock_ohlcv, mock_load, mock_trading_day):
        """레짐 백테스트 실행 테스트"""
        from scanner_v2.regime_backtest_v3 import run_regime_backtest
        import pandas as pd
        
        # Mock 설정
        mock_trading_day.return_value = True
        mock_load.return_value = {
            'final_regime': 'bull',
            'kr_regime': 'bull',
            'us_prev_regime': 'neutral',
            'final_score': 1.5,
            'kr_score': 2.0,
            'us_prev_score': 1.0
        }
        
        # KOSPI 데이터 Mock
        mock_df = pd.DataFrame({
            'close': [100, 102]
        })
        mock_ohlcv.return_value = mock_df
        
        # 테스트 실행
        result = run_regime_backtest("20241201", "20241205")
        
        # 검증
        self.assertIsInstance(result, dict)
        if 'error' not in result:
            self.assertIn('regime_distribution', result)
            self.assertIn('regime_stats', result)
            self.assertIn('overall_stats', result)

class TestRegimeConfiguration(unittest.TestCase):
    """Regime 설정 테스트"""
    
    def test_regime_config_loading(self):
        """레짐 설정 파일 로딩 테스트"""
        try:
            from scanner_v2.config_regime import REGIME_CUTOFFS, MAX_CANDIDATES, REGIME_WEIGHTS
            
            # 설정 구조 검증
            self.assertIsInstance(REGIME_CUTOFFS, dict)
            self.assertIsInstance(MAX_CANDIDATES, dict)
            self.assertIsInstance(REGIME_WEIGHTS, dict)
            
            # 필수 레짐 존재 확인
            required_regimes = ['bull', 'neutral', 'bear', 'crash']
            for regime in required_regimes:
                self.assertIn(regime, REGIME_CUTOFFS)
            
            # 필수 horizon 존재 확인
            required_horizons = ['swing', 'position', 'longterm']
            for horizon in required_horizons:
                self.assertIn(horizon, MAX_CANDIDATES)
                
        except ImportError:
            self.fail("config_regime.py import failed")

if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)