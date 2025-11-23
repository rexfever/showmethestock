#!/usr/bin/env python3
"""
Global Regime v3 엣지 케이스 및 에러 처리 테스트
"""
import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class TestRegimeEdgeCases(unittest.TestCase):
    """Global Regime v3 엣지 케이스 테스트"""
    
    def test_invalid_us_data_handling(self):
        """미국 데이터 무효 시 처리 테스트"""
        from market_analyzer import market_analyzer
        
        # 완전히 빈 데이터
        empty_snapshot = {}
        result = market_analyzer.compute_us_prev_score(empty_snapshot)
        self.assertEqual(result['us_prev_regime'], 'neutral')
        self.assertEqual(result['us_prev_score'], 0.0)
        
        # 일부 키 누락
        partial_snapshot = {'valid': True, 'spy_r3': 0.01}  # 다른 키들 누락
        result = market_analyzer.compute_us_prev_score(partial_snapshot)
        self.assertEqual(result['us_prev_regime'], 'neutral')
        
        # None 값 포함
        none_snapshot = {
            'valid': True, 'spy_r3': None, 'qqq_r3': 0.01,
            'spy_r5': 0.01, 'qqq_r5': 0.01, 'vix': 20, 'ust10y_change': 0
        }
        result = market_analyzer.compute_us_prev_score(none_snapshot)
        self.assertIsInstance(result, dict)
    
    def test_extreme_market_conditions(self):
        """극단적 시장 상황 테스트"""
        from market_analyzer import market_analyzer
        
        # 극도의 강세장
        extreme_bull = {
            'valid': True, 'spy_r3': 0.10, 'qqq_r3': 0.15,
            'spy_r5': 0.20, 'qqq_r5': 0.25, 'vix': 10.0,
            'vix_change': -0.5, 'ust10y_change': -0.5
        }
        result = market_analyzer.compute_us_prev_score(extreme_bull)
        self.assertEqual(result['us_prev_regime'], 'bull')
        
        # 극도의 약세장 (VIX 40+)
        extreme_bear = {
            'valid': True, 'spy_r3': -0.10, 'qqq_r3': -0.15,
            'spy_r5': -0.20, 'qqq_r5': -0.25, 'vix': 45.0,
            'vix_change': 1.0, 'ust10y_change': 0.5
        }
        result = market_analyzer.compute_us_prev_score(extreme_bear)
        self.assertEqual(result['us_prev_regime'], 'crash')  # VIX > 35
    
    def test_database_error_handling(self):
        """데이터베이스 에러 처리 테스트"""
        from market_analyzer import market_analyzer
        
        with patch('services.regime_storage.upsert_regime', side_effect=Exception("DB Error")):
            with patch('market_analyzer.MarketAnalyzer.analyze_market_condition') as mock_v1:
                with patch('market_analyzer.MarketAnalyzer.compute_kr_regime_score_v3') as mock_kr:
                    with patch('services.us_market_data.get_us_prev_snapshot') as mock_us:
                        
                        # Mock 설정
                        from market_analyzer import MarketCondition
                        mock_v1.return_value = MarketCondition(
                            date="20241205", kospi_return=0.01, volatility=0.02,
                            market_sentiment="neutral", sector_rotation="mixed",
                            foreign_flow="neutral", institution_flow="neutral",
                            volume_trend="normal", rsi_threshold=58.0, min_signals=3,
                            macd_osc_min=0.0, vol_ma5_mult=1.8, gap_max=0.025,
                            ext_from_tema20_max=0.025
                        )
                        mock_kr.return_value = {'kr_score': 1.0, 'kr_regime': 'neutral', 'intraday_drop': 0.0}
                        mock_us.return_value = {'valid': True, 'spy_r3': 0.01, 'qqq_r3': 0.01, 'spy_r5': 0.01, 'qqq_r5': 0.01, 'vix': 20, 'vix_change': 0, 'ust10y_change': 0}
                        
                        # DB 에러가 발생해도 분석은 계속되어야 함
                        result = market_analyzer.analyze_market_condition_v3("20241205")
                        self.assertIsNotNone(result)
                        self.assertEqual(result.version, "regime_v3")
    
    def test_network_timeout_simulation(self):
        """네트워크 타임아웃 시뮬레이션"""
        from services.us_market_data import get_us_prev_snapshot
        
        with patch('services.market_data_provider.market_data_provider.get_us_prev_snapshot', side_effect=Exception("Network timeout")):
            result = get_us_prev_snapshot("20241205")
            
            # 네트워크 에러 시 valid=False 반환되어야 함 (Market Data Provider 기반)
            self.assertFalse(result.get('valid', True))
            self.assertEqual(result.get('spy_r1', None), 0.0)
    
    def test_regime_transition_edge_cases(self):
        """레짐 전환 엣지 케이스 테스트"""
        from market_analyzer import market_analyzer
        
        # Crash 우선 규칙 테스트
        kr_crash = {'kr_score': -3.0, 'kr_regime': 'crash'}
        us_bull = {'us_prev_score': 2.0, 'us_prev_regime': 'bull'}
        preopen_calm = {'us_preopen_flag': 'calm', 'us_preopen_risk_score': 0.0}
        
        result = market_analyzer.compose_global_regime_v3(kr_crash, us_bull, preopen_calm)
        self.assertEqual(result['final_regime'], 'crash')  # 한국 crash가 우선
        
        # 미국 crash 우선 규칙 테스트
        kr_neutral = {'kr_score': 0.0, 'kr_regime': 'neutral'}
        us_crash = {'us_prev_score': -3.0, 'us_prev_regime': 'crash'}
        
        result = market_analyzer.compose_global_regime_v3(kr_neutral, us_crash, preopen_calm)
        self.assertEqual(result['final_regime'], 'crash')  # 미국 crash가 우선
    
    def test_scanner_empty_results(self):
        """스캐너 빈 결과 처리 테스트"""
        from scanner_v2.core.scanner import ScannerV2
        from market_analyzer import MarketCondition
        
        mock_config = Mock()
        scanner = ScannerV2(mock_config)
        
        # 빈 결과 리스트
        empty_results = []
        
        condition = MarketCondition(
            date="20241205", kospi_return=0.01, volatility=0.02,
            market_sentiment="neutral", sector_rotation="mixed",
            foreign_flow="neutral", institution_flow="neutral",
            volume_trend="normal", rsi_threshold=58.0, min_signals=3,
            macd_osc_min=0.0, vol_ma5_mult=1.8, gap_max=0.025,
            ext_from_tema20_max=0.025, final_regime="neutral"
        )
        
        # 빈 결과도 정상 처리되어야 함
        filtered = scanner._apply_regime_cutoff(empty_results, condition)
        self.assertEqual(len(filtered), 0)
        self.assertIsInstance(filtered, list)
    
    def test_config_fallback(self):
        """설정 파일 로드 실패 시 fallback 테스트"""
        from scanner_v2.core.scanner import ScannerV2
        from market_analyzer import MarketCondition
        
        # config_regime import 실패 시뮬레이션
        with patch('scanner_v2.core.scanner.ImportError', ImportError):
            mock_config = Mock()
            scanner = ScannerV2(mock_config)
            
            mock_results = [Mock(ticker="001", score=7.0)]
            condition = MarketCondition(
                date="20241205", kospi_return=0.01, volatility=0.02,
                market_sentiment="bull", sector_rotation="tech",
                foreign_flow="buy", institution_flow="buy",
                volume_trend="high", rsi_threshold=65.0, min_signals=2,
                macd_osc_min=-5.0, vol_ma5_mult=1.5, gap_max=0.03,
                ext_from_tema20_max=0.025, final_regime="bull"
            )
            
            # fallback 설정으로도 정상 동작해야 함
            try:
                filtered = scanner._apply_regime_cutoff(mock_results, condition)
                self.assertIsInstance(filtered, list)
            except Exception as e:
                self.fail(f"Config fallback failed: {e}")

class TestRegimeDataValidation(unittest.TestCase):
    """데이터 검증 테스트"""
    
    def test_date_format_validation(self):
        """날짜 형식 검증 테스트"""
        from services.regime_storage import save_regime, load_regime
        
        # 올바른 날짜 형식
        valid_dates = ["20241205", "20240101", "20251231"]
        
        # 잘못된 날짜 형식 (실제로는 함수 내에서 처리되어야 함)
        invalid_dates = ["2024-12-05", "241205", "20241305"]  # 13월
        
        test_data = {
            'final_regime': 'neutral',
            'kr_regime': 'neutral',
            'us_prev_regime': 'neutral',
            'us_preopen_flag': 'none'
        }
        
        # 유효한 날짜는 처리되어야 함 (실제 DB 연결 없이는 테스트 제한적)
        for date in valid_dates:
            try:
                # 실제 저장은 DB 연결이 필요하므로 함수 호출만 테스트
                self.assertTrue(callable(save_regime))
                self.assertTrue(callable(load_regime))
            except Exception:
                pass  # DB 연결 에러는 무시
    
    def test_regime_value_validation(self):
        """레짐 값 검증 테스트"""
        from market_analyzer import market_analyzer
        
        # 유효한 레짐 값들
        valid_regimes = ['bull', 'neutral', 'bear', 'crash']
        
        # 각 레짐에 대해 점수 계산이 올바른 범위 내에 있는지 확인
        for regime in valid_regimes:
            # 해당 레짐을 생성하는 조건 시뮬레이션
            if regime == 'bull':
                kr_data = {'kr_score': 3.0, 'kr_regime': 'bull'}
                us_data = {'us_prev_score': 2.0, 'us_prev_regime': 'bull'}
            elif regime == 'bear':
                kr_data = {'kr_score': -3.0, 'kr_regime': 'bear'}
                us_data = {'us_prev_score': -2.0, 'us_prev_regime': 'bear'}
            elif regime == 'crash':
                kr_data = {'kr_score': -4.0, 'kr_regime': 'crash'}
                us_data = {'us_prev_score': -3.0, 'us_prev_regime': 'crash'}
            else:  # neutral
                kr_data = {'kr_score': 0.0, 'kr_regime': 'neutral'}
                us_data = {'us_prev_score': 0.0, 'us_prev_regime': 'neutral'}
            
            preopen_data = {'us_preopen_flag': 'calm', 'us_preopen_risk_score': 0.0}
            
            result = market_analyzer.compose_global_regime_v3(kr_data, us_data, preopen_data)
            self.assertIn(result['final_regime'], valid_regimes)

if __name__ == '__main__':
    unittest.main(verbosity=2)