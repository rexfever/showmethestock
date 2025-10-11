"""
스캐너 핵심 기능 테스트
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

# 상위 디렉토리의 모듈 import
sys.path.append('..')
from scanner import compute_indicators, match_stats, score_conditions
from config import config

class TestScannerCore(unittest.TestCase):
    """스캐너 핵심 기능 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # 샘플 OHLCV 데이터 생성
        self.sample_data = pd.DataFrame({
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109],
            'volume': [1000, 1200, 1100, 1300, 1400, 1350, 1450, 1500, 1420, 1480],
            'high': [101, 103, 102, 104, 106, 105, 107, 109, 108, 110],
            'low': [99, 101, 100, 102, 104, 103, 105, 107, 106, 108]
        })
    
    def test_compute_indicators_basic(self):
        """기본 지표 계산 테스트"""
        indicators = compute_indicators(self.sample_data)
        
        # 필수 지표들이 계산되었는지 확인
        required_indicators = ['TEMA20', 'DEMA10', 'MACD_OSC', 'RSI_TEMA', 'RSI_DEMA', 'OBV']
        for indicator in required_indicators:
            self.assertIn(indicator, indicators.columns)
            self.assertIsNotNone(indicators[indicator].iloc[-1])
    
    def test_compute_indicators_data_types(self):
        """지표 데이터 타입 테스트"""
        indicators = compute_indicators(self.sample_data)
        
        # 수치형 지표들이 올바른 타입인지 확인
        numeric_indicators = ['TEMA20', 'DEMA10', 'MACD_OSC', 'RSI_TEMA', 'RSI_DEMA']
        for indicator in numeric_indicators:
            value = indicators[indicator].iloc[-1]
            self.assertIsInstance(value, (int, float, np.number))
    
    def test_match_condition_basic(self):
        """기본 조건 매칭 테스트"""
        indicators = compute_indicators(self.sample_data)
        
        # 기본 조건 테스트 (match_stats 함수 사용)
        result = match_stats(indicators)
        
        # 결과가 튜플인지 확인
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)  # (matched, signals_true, total_signals)
    
    def test_match_condition_score_range(self):
        """점수 범위 테스트"""
        indicators = compute_indicators(self.sample_data)
        result = match_stats(indicators)
        
        # 신호 개수가 0-8 범위 내에 있는지 확인
        matched, signals_true, total_signals = result
        self.assertGreaterEqual(signals_true, 0)
        self.assertLessEqual(signals_true, total_signals)
    
    def test_score_conditions_basic(self):
        """기본 점수 계산 테스트"""
        indicators = compute_indicators(self.sample_data)
        flags = {
            'tema_dema_golden_cross': True,
            'macd_osc_positive': True,
            'rsi_tema_above_threshold': True,
            'volume_surge': True,
            'price_uptrend': True,
            'obv_uptrend': True,
            'consecutive_up_days': True,
            'rsi_momentum': True
        }
        
        score, score_flags = score_conditions(flags)
        
        # 점수가 올바르게 계산되었는지 확인
        self.assertIsInstance(score, (int, float))
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 15)
        self.assertIsInstance(score_flags, dict)
    
    def test_score_conditions_all_true(self):
        """모든 조건이 True일 때 점수 테스트"""
        flags = {
            'tema_dema_golden_cross': True,
            'macd_osc_positive': True,
            'rsi_tema_above_threshold': True,
            'volume_surge': True,
            'price_uptrend': True,
            'obv_uptrend': True,
            'consecutive_up_days': True,
            'rsi_momentum': True
        }
        
        score, score_flags = score_conditions(flags)
        
        # 모든 조건이 True일 때 최대 점수인지 확인
        self.assertEqual(score, 15)
    
    def test_score_conditions_all_false(self):
        """모든 조건이 False일 때 점수 테스트"""
        flags = {
            'tema_dema_golden_cross': False,
            'macd_osc_positive': False,
            'rsi_tema_above_threshold': False,
            'volume_surge': False,
            'price_uptrend': False,
            'obv_uptrend': False,
            'consecutive_up_days': False,
            'rsi_momentum': False
        }
        
        score, score_flags = score_conditions(flags)
        
        # 모든 조건이 False일 때 최소 점수인지 확인
        self.assertEqual(score, 0)
    
    def test_indicators_with_insufficient_data(self):
        """데이터 부족 시 지표 계산 테스트"""
        # 데이터가 부족한 경우 (5개 미만)
        insufficient_data = pd.DataFrame({
            'close': [100, 102, 101],
            'volume': [1000, 1200, 1100],
            'high': [101, 103, 102],
            'low': [99, 101, 100]
        })
        
        # 예외가 발생하지 않는지 확인
        try:
            indicators = compute_indicators(insufficient_data)
            # 기본값들이 설정되었는지 확인
            self.assertIsNotNone(indicators)
        except Exception as e:
            self.fail(f"데이터 부족 시 예외 발생: {e}")
    
    def test_match_condition_with_none_indicators(self):
        """None 지표로 조건 매칭 테스트"""
        # None 값이 포함된 DataFrame 생성
        none_data = pd.DataFrame({
            'close': [None, None, None, None, None],
            'volume': [None, None, None, None, None],
            'high': [None, None, None, None, None],
            'low': [None, None, None, None, None]
        })
        
        # 예외가 발생하지 않는지 확인
        try:
            result = match_stats(none_data)
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 3)
        except Exception as e:
            self.fail(f"None 지표로 매칭 시 예외 발생: {e}")

if __name__ == '__main__':
    unittest.main()
