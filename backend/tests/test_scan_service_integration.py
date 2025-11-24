"""
scan_service의 scan_with_scanner 통합 테스트
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scan_service import execute_scan_with_fallback
from market_analyzer import MarketCondition


class TestScanServiceIntegration(unittest.TestCase):
    """scan_service 통합 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.universe = ['005930', '000660', '035420']
        self.date = '20251119'
        
        self.market_condition = MarketCondition(
            market_sentiment='neutral',
            kospi_return=0.01,
            volatility=0.02,
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015,
            institution_flow=0.0
        )
    
    @patch('services.scan_service.scan_with_scanner')
    @patch('services.scan_service.config')
    def test_execute_scan_with_fallback_disabled(self, mock_config, mock_scan):
        """Fallback 비활성화 시 테스트"""
        mock_config.fallback_enable = False
        mock_config.top_k = 5
        
        # 스캔 결과 모킹
        mock_scan.return_value = [
            {'ticker': '005930', 'score': 12, 'match': True},
            {'ticker': '000660', 'score': 10, 'match': True},
            {'ticker': '035420', 'score': 8, 'match': True}  # 10점 미만
        ]
        
        items, step = execute_scan_with_fallback(self.universe, self.date, self.market_condition)
        
        # 10점 이상만 필터링되어야 함
        self.assertEqual(len(items), 2)
        self.assertEqual(step, 0)
        mock_scan.assert_called_once_with(self.universe, {}, self.date, self.market_condition)
    
    @patch('services.scan_service.scan_with_scanner')
    @patch('services.scan_service.config')
    def test_execute_scan_with_fallback_step0_success(self, mock_config, mock_scan):
        """Step 0에서 목표 달성 테스트"""
        mock_config.fallback_enable = True
        mock_config.fallback_target_min_bull = 3
        mock_config.fallback_target_max_bull = 5
        mock_config.top_k = 5
        
        # Step 0 결과 모킹 (목표 달성)
        mock_scan.return_value = [
            {'ticker': '005930', 'score': 12, 'match': True},
            {'ticker': '000660', 'score': 11, 'match': True},
            {'ticker': '035420', 'score': 10, 'match': True},
            {'ticker': '051910', 'score': 9, 'match': True}
        ]
        
        items, step = execute_scan_with_fallback(self.universe, self.date, self.market_condition)
        
        self.assertEqual(len(items), 3)  # target_max = 5, top_k = 5 중 작은 값
        self.assertEqual(step, 0)
        # Step 0만 호출되어야 함
        self.assertEqual(mock_scan.call_count, 1)
    
    @patch('services.scan_service.scan_with_scanner')
    @patch('services.scan_service.config')
    def test_execute_scan_with_fallback_step1_success(self, mock_config, mock_scan):
        """Step 1에서 목표 달성 테스트"""
        mock_config.fallback_enable = True
        mock_config.fallback_target_min_bull = 3
        mock_config.fallback_target_max_bull = 5
        mock_config.top_k = 5
        mock_config.fallback_presets = [
            {},  # Step 0
            {'gap_max': 0.025},  # Step 1
            {'gap_max': 0.030}   # Step 3
        ]
        
        # Step 0: 목표 미달
        # Step 1: 목표 달성
        def scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:
                return [
                    {'ticker': '005930', 'score': 12, 'match': True},
                    {'ticker': '000660', 'score': 11, 'match': True}
                ]
            elif preset == {'gap_max': 0.025}:
                return [
                    {'ticker': '005930', 'score': 12, 'match': True},
                    {'ticker': '000660', 'score': 11, 'match': True},
                    {'ticker': '035420', 'score': 10, 'match': True},
                    {'ticker': '051910', 'score': 9, 'match': True}
                ]
            return []
        
        mock_scan.side_effect = scan_side_effect
        
        items, step = execute_scan_with_fallback(self.universe, self.date, self.market_condition)
        
        self.assertEqual(len(items), 3)
        self.assertEqual(step, 1)
        # Step 0, Step 1 호출 확인
        self.assertEqual(mock_scan.call_count, 2)
    
    @patch('services.scan_service.scan_with_scanner')
    @patch('services.scan_service.config')
    def test_execute_scan_with_fallback_signal_first_priority(self, mock_config, mock_scan):
        """신호 우선 원칙 테스트"""
        mock_config.fallback_enable = True
        mock_config.fallback_target_min_bull = 2
        mock_config.fallback_target_max_bull = 5
        mock_config.top_k = 5
        
        # 신호 충족하지만 점수 낮은 종목 포함
        mock_scan.return_value = [
            {'ticker': '005930', 'score': 12, 'match': True},   # 신호 충족, 점수 높음
            {'ticker': '000660', 'score': 6, 'match': True},   # 신호 충족, 점수 낮음 (포함됨)
            {'ticker': '035420', 'score': 15, 'match': False}  # 신호 미충족, 점수 높음 (제외됨)
        ]
        
        items, step = execute_scan_with_fallback(self.universe, self.date, self.market_condition)
        
        # 신호 충족한 종목만 포함 (점수 무관)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['ticker'], '005930')  # 점수 높은 순
        self.assertEqual(items[1]['ticker'], '000660')
        # 점수 높지만 신호 미충족한 종목은 제외
        self.assertNotIn('035420', [item['ticker'] for item in items])


if __name__ == '__main__':
    unittest.main()

