"""
Fallback Step 제한 테스트 (Step 0~3까지만 사용, Step 7 제거)
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 의존성 mock
sys.modules['psycopg'] = MagicMock()
sys.modules['psycopg.connection'] = MagicMock()
sys.modules['psycopg.cursor'] = MagicMock()
sys.modules['psycopg_pool'] = MagicMock()
sys.modules['psycopg_pool.ConnectionPool'] = MagicMock()
sys.modules['psycopg_pool.PoolClosed'] = MagicMock()

from services.scan_service import execute_scan_with_fallback
from market_analyzer import MarketCondition
from config import config


class TestFallbackStepLimitation(unittest.TestCase):
    """Fallback Step 제한 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.universe = ["005930", "000660", "051910", "035420", "006400"]
        self.bull_condition = MarketCondition(
            date="20251114",
            kospi_return=0.02,  # +2%
            volatility=0.02,
            market_sentiment='bull',
            sector_rotation='tech',
            foreign_flow='buy',
            institution_flow='buy',
            volume_trend='high',
            rsi_threshold=65.0,
            min_signals=2,
            macd_osc_min=-5.0,
            vol_ma5_mult=1.5,
            gap_max=0.02,
            ext_from_tema20_max=0.02
        )
        
        # 원본 설정 저장
        self.original_fallback = config.fallback_enable
        self.original_target_min = config.fallback_target_min_bull
        self.original_target_max = config.fallback_target_max_bull
        
        # 테스트 설정
        config.fallback_enable = True
        config.fallback_target_min_bull = 3
        config.fallback_target_max_bull = 5
    
    def tearDown(self):
        """테스트 후 정리"""
        config.fallback_enable = self.original_fallback
        config.fallback_target_min_bull = self.original_target_min
        config.fallback_target_max_bull = self.original_target_max
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_0_success(self, mock_scan):
        """Step 0에서 목표 달성 시 Step 0 반환"""
        # Step 0: 10점 이상 5개 반환 (목표 3개 이상)
        mock_scan.return_value = [
            {"ticker": "005930", "name": "삼성전자", "score": 10.0},
            {"ticker": "000660", "name": "SK하이닉스", "score": 10.5},
            {"ticker": "051910", "name": "LG화학", "score": 11.0},
            {"ticker": "035420", "name": "NAVER", "score": 10.2},
            {"ticker": "006400", "name": "삼성SDI", "score": 9.5},  # 10점 미만
        ]
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 0에서 목표 달성했으므로 Step 0 반환
        self.assertEqual(chosen_step, 0)
        self.assertEqual(len(items), 4)  # 10점 이상 4개
        self.assertTrue(all(item["score"] >= 10 for item in items))
        
        # Step 0만 호출되어야 함
        self.assertEqual(mock_scan.call_count, 1)
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_1_success(self, mock_scan):
        """Step 1에서 목표 달성 시 Step 1 반환"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 10.0},
                    {"ticker": "000660", "name": "SK하이닉스", "score": 9.5},  # 10점 미만
                ]
            elif preset == config.fallback_presets[1]:  # Step 1
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 10.0},
                    {"ticker": "000660", "name": "SK하이닉스", "score": 10.5},
                    {"ticker": "051910", "name": "LG화학", "score": 11.0},
                    {"ticker": "035420", "name": "NAVER", "score": 10.2},
                ]
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 1에서 목표 달성했으므로 Step 1 반환
        self.assertEqual(chosen_step, 1)
        self.assertEqual(len(items), 4)  # 10점 이상 4개
        self.assertTrue(all(item["score"] >= 10 for item in items))
        
        # Step 0, Step 1 호출
        self.assertEqual(mock_scan.call_count, 2)
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_2_success(self, mock_scan):
        """Step 2에서 목표 달성 시 Step 2 반환"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 9.5},
                ]
            elif preset == config.fallback_presets[1]:  # Step 1
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 9.5},
                    {"ticker": "000660", "name": "SK하이닉스", "score": 8.5},
                    {"ticker": "051910", "name": "LG화학", "score": 8.8},
                    {"ticker": "035420", "name": "NAVER", "score": 8.2},
                ]
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 2에서 목표 달성했으므로 Step 2 반환
        self.assertEqual(chosen_step, 2)
        self.assertEqual(len(items), 4)  # 8점 이상 4개
        self.assertTrue(all(item["score"] >= 8 for item in items))
        
        # Step 0, Step 1 호출 (Step 2는 Step 1의 결과를 재사용)
        self.assertEqual(mock_scan.call_count, 2)
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_3_success(self, mock_scan):
        """Step 3에서 목표 달성 시 Step 3 반환"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 9.5},
                ]
            elif preset == config.fallback_presets[1]:  # Step 1
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 7.5},
                ]
            elif preset == config.fallback_presets[2]:  # Step 3
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 8.5},
                    {"ticker": "000660", "name": "SK하이닉스", "score": 8.8},
                    {"ticker": "051910", "name": "LG화학", "score": 9.0},
                    {"ticker": "035420", "name": "NAVER", "score": 8.2},
                ]
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 3에서 목표 달성했으므로 Step 3 반환
        self.assertEqual(chosen_step, 3)
        self.assertEqual(len(items), 4)  # 8점 이상 4개
        self.assertTrue(all(item["score"] >= 8 for item in items))
        
        # Step 0, Step 1, Step 3 호출
        self.assertEqual(mock_scan.call_count, 3)
    
    @patch('services.scan_service.scan_with_preset')
    def test_all_steps_fail_returns_empty(self, mock_scan):
        """Step 0~3 모두 목표 미달 시 빈 리스트 반환 (Step 7 제거 확인)"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 9.5},
                ]
            elif preset == config.fallback_presets[1]:  # Step 1
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 7.5},
                ]
            elif preset == config.fallback_presets[2]:  # Step 3
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 8.5},
                    {"ticker": "000660", "name": "SK하이닉스", "score": 7.8},  # 8점 미만
                ]
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 0~3 모두 목표 미달이므로 빈 리스트 반환
        self.assertEqual(len(items), 0)
        self.assertIsNone(chosen_step)  # Step 7이 아닌 None 반환
        
        # Step 0, Step 1, Step 3 호출
        self.assertEqual(mock_scan.call_count, 3)
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_4_not_executed(self, mock_scan):
        """Step 4 이상으로 진행하지 않는지 확인"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 9.5},
                ]
            elif preset == config.fallback_presets[1]:  # Step 1
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 7.5},
                ]
            elif preset == config.fallback_presets[2]:  # Step 3
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 7.5},
                ]
            # Step 4 이상은 호출되지 않아야 함
            elif preset == config.fallback_presets[3]:  # Step 4
                self.fail("Step 4가 호출되었습니다! Step 3까지만 호출되어야 합니다.")
            elif preset == config.fallback_presets[4]:  # Step 5
                self.fail("Step 5가 호출되었습니다! Step 3까지만 호출되어야 합니다.")
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 0~3 모두 목표 미달이므로 빈 리스트 반환
        self.assertEqual(len(items), 0)
        self.assertIsNone(chosen_step)
        
        # Step 0, Step 1, Step 3만 호출 (Step 4 이상은 호출되지 않음)
        self.assertEqual(mock_scan.call_count, 3)
        
        # 호출된 preset 확인
        call_args_list = [call[0][1] for call in mock_scan.call_args_list]
        self.assertIn({}, call_args_list)  # Step 0
        self.assertIn(config.fallback_presets[1], call_args_list)  # Step 1
        self.assertIn(config.fallback_presets[2], call_args_list)  # Step 3
        self.assertNotIn(config.fallback_presets[3], call_args_list)  # Step 4 호출 안 됨
        self.assertNotIn(config.fallback_presets[4], call_args_list)  # Step 5 호출 안 됨
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_3_with_exact_target_min(self, mock_scan):
        """Step 3에서 정확히 목표 최소값 달성 시 Step 3 반환"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 9.5},
                ]
            elif preset == config.fallback_presets[1]:  # Step 1
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 7.5},
                ]
            elif preset == config.fallback_presets[2]:  # Step 3
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 8.5},
                    {"ticker": "000660", "name": "SK하이닉스", "score": 8.8},
                    {"ticker": "051910", "name": "LG화학", "score": 9.0},  # 정확히 3개
                ]
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 3에서 정확히 목표 최소값(3개) 달성했으므로 Step 3 반환
        self.assertEqual(chosen_step, 3)
        self.assertEqual(len(items), 3)  # 정확히 3개
        self.assertTrue(all(item["score"] >= 8 for item in items))
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_3_with_below_target_min(self, mock_scan):
        """Step 3에서 목표 최소값 미달 시 빈 리스트 반환"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 9.5},
                ]
            elif preset == config.fallback_presets[1]:  # Step 1
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 7.5},
                ]
            elif preset == config.fallback_presets[2]:  # Step 3
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 8.5},
                    {"ticker": "000660", "name": "SK하이닉스", "score": 8.8},  # 2개만 (목표 3개 미달)
                ]
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 3에서 목표 최소값(3개) 미달이므로 빈 리스트 반환
        self.assertEqual(len(items), 0)
        self.assertIsNone(chosen_step)
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_3_with_zero_results(self, mock_scan):
        """Step 3에서 결과가 0개일 때 빈 리스트 반환"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 9.5},
                ]
            elif preset == config.fallback_presets[1]:  # Step 1
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 7.5},
                ]
            elif preset == config.fallback_presets[2]:  # Step 3
                return []  # 결과 없음
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 3에서 결과가 0개이므로 빈 리스트 반환
        self.assertEqual(len(items), 0)
        self.assertIsNone(chosen_step)


if __name__ == '__main__':
    unittest.main()

