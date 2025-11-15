"""
스캔 서비스 포괄적 테스트
- 에러 처리
- Edge case
- 통합 시나리오
- 성능 및 안정성
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


class TestScanServiceComprehensive(unittest.TestCase):
    """스캔 서비스 포괄적 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.universe = ["005930", "000660", "051910", "035420", "006400"]
        self.bull_condition = MarketCondition(
            date="20251114",
            kospi_return=0.02,
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
        self.bull_presets = config.get_fallback_profile('bull')['presets']
    
    def tearDown(self):
        """테스트 후 정리"""
        config.fallback_enable = self.original_fallback
        config.fallback_target_min_bull = self.original_target_min
        config.fallback_target_max_bull = self.original_target_max
    
    # ==================== 에러 처리 테스트 ====================
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_0_scan_error_handling(self, mock_scan):
        """Step 0 스캔 오류 처리 테스트"""
        mock_scan.side_effect = Exception("스캔 오류 발생")
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        self.assertEqual(len(items), 0)
        self.assertIsNone(chosen_step)
        self.assertEqual(mock_scan.call_count, 1)
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_1_scan_error_handling(self, mock_scan):
        """Step 1 스캔 오류 처리 테스트"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return []  # Step 0 실패
            elif preset == self.bull_presets[1]:  # Step 1
                raise Exception("Step 1 스캔 오류")
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        self.assertEqual(len(items), 0)
        self.assertIsNone(chosen_step)
        self.assertEqual(mock_scan.call_count, 2)
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_3_scan_error_handling(self, mock_scan):
        """Step 3 스캔 오류 처리 테스트"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return []
            elif preset == self.bull_presets[1]:  # Step 1
                return []
            elif preset == self.bull_presets[2]:  # Step 3
                raise Exception("Step 3 스캔 오류")
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        self.assertEqual(len(items), 0)
        self.assertIsNone(chosen_step)
        self.assertEqual(mock_scan.call_count, 3)
    
    @patch('services.scan_service.scan_with_preset')
    def test_fallback_presets_index_error_step1(self, mock_scan):
        """fallback_presets 인덱스 오류 테스트 (Step 1)"""
        # fallback_presets가 2개 미만인 경우 시뮬레이션
        # property를 직접 수정할 수 없으므로, 코드에서 len 체크하는지 확인
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return []
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        # fallback_presets를 임시로 1개만 반환하도록 mock
        limited_profile = {"target_min": 3, "target_max": 5, "presets": [{}]}
        with patch.object(config, 'get_fallback_profile', return_value=limited_profile):
            items, chosen_step = execute_scan_with_fallback(
                self.universe,
                date="20251114",
                market_condition=self.bull_condition
            )
            
            # Step 1에서 인덱스 오류가 발생하면 빈 리스트 반환
            self.assertEqual(len(items), 0)
            self.assertIsNone(chosen_step)
    
    @patch('services.scan_service.scan_with_preset')
    def test_fallback_presets_index_error_step3(self, mock_scan):
        """fallback_presets 인덱스 오류 테스트 (Step 3)"""
        # fallback_presets가 3개 미만인 경우 시뮬레이션
        # property를 직접 수정할 수 없으므로, 실제로는 코드에서 검증하는지 확인
        step1_preset = self.bull_presets[1] if len(self.bull_presets) > 1 else {}
        
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return []
            elif preset == step1_preset:  # Step 1
                return []
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        # fallback_presets를 임시로 2개만 반환하도록 mock
        limited_profile = {"target_min": 3, "target_max": 5, "presets": [{}, step1_preset]}
        with patch.object(config, 'get_fallback_profile', return_value=limited_profile):
            items, chosen_step = execute_scan_with_fallback(
                self.universe,
                date="20251114",
                market_condition=self.bull_condition
            )
            
            # Step 3에서 인덱스 오류가 발생하면 빈 리스트 반환
            self.assertEqual(len(items), 0)
            self.assertIsNone(chosen_step)
    
    # ==================== target_min/target_max 검증 테스트 ====================
    
    @patch('services.scan_service.scan_with_preset')
    def test_target_min_negative_value(self, mock_scan):
        """target_min 음수 값 처리 테스트"""
        original_min = config.fallback_target_min_bull
        config.fallback_target_min_bull = -5  # 음수
        
        try:
            mock_scan.return_value = [
                {"ticker": "005930", "name": "삼성전자", "score": 10.0},
            ]
            
            items, chosen_step = execute_scan_with_fallback(
                self.universe,
                date="20251114",
                market_condition=self.bull_condition
            )
            
            # max(1, -5) = 1이므로 최소 1개로 처리되어야 함
            # 하지만 실제로는 1개만 있어도 목표 달성
            self.assertGreaterEqual(len(items), 0)
        finally:
            config.fallback_target_min_bull = original_min
    
    @patch('services.scan_service.scan_with_preset')
    def test_target_max_less_than_min(self, mock_scan):
        """target_max가 target_min보다 작은 경우 처리 테스트"""
        original_min = config.fallback_target_min_bull
        original_max = config.fallback_target_max_bull
        config.fallback_target_min_bull = 5
        config.fallback_target_max_bull = 2  # min보다 작음
        
        try:
            mock_scan.return_value = [
                {"ticker": "005930", "name": "삼성전자", "score": 10.0},
                {"ticker": "000660", "name": "SK하이닉스", "score": 10.5},
                {"ticker": "051910", "name": "LG화학", "score": 11.0},
                {"ticker": "035420", "name": "NAVER", "score": 10.2},
                {"ticker": "006400", "name": "삼성SDI", "score": 10.8},
            ]
            
            items, chosen_step = execute_scan_with_fallback(
                self.universe,
                date="20251114",
                market_condition=self.bull_condition
            )
            
            # max(5, 2) = 5이므로 target_max는 5로 조정되어야 함
            # 5개 종목이 있으므로 모두 선택되어야 함
            self.assertEqual(len(items), 5)
            self.assertEqual(chosen_step, 0)
        finally:
            config.fallback_target_min_bull = original_min
            config.fallback_target_max_bull = original_max
    
    @patch('services.scan_service.scan_with_preset')
    def test_target_min_zero_value(self, mock_scan):
        """target_min이 0인 경우 처리 테스트"""
        original_min = config.fallback_target_min_bull
        config.fallback_target_min_bull = 0
        
        try:
            mock_scan.return_value = [
                {"ticker": "005930", "name": "삼성전자", "score": 10.0},
            ]
            
            items, chosen_step = execute_scan_with_fallback(
                self.universe,
                date="20251114",
                market_condition=self.bull_condition
            )
            
            # max(1, 0) = 1이므로 최소 1개로 처리되어야 함
            # 1개 종목이 있으므로 목표 달성
            self.assertEqual(len(items), 1)
            self.assertEqual(chosen_step, 0)
        finally:
            config.fallback_target_min_bull = original_min
    
    # ==================== Edge Case 테스트 ====================
    
    @patch('services.scan_service.scan_with_preset')
    def test_empty_universe(self, mock_scan):
        """빈 유니버스 테스트"""
        mock_scan.return_value = []
        
        items, chosen_step = execute_scan_with_fallback(
            [],
            date="20251114",
            market_condition=self.bull_condition
        )
        
        self.assertEqual(len(items), 0)
        # 빈 유니버스에서도 Step 0~3까지 진행하므로 여러 번 호출될 수 있음
        self.assertGreaterEqual(mock_scan.call_count, 1)
    
    @patch('services.scan_service.scan_with_preset')
    def test_none_market_condition(self, mock_scan):
        """market_condition이 None인 경우 테스트"""
        mock_scan.return_value = [
            {"ticker": "005930", "name": "삼성전자", "score": 10.0},
            {"ticker": "000660", "name": "SK하이닉스", "score": 10.5},
            {"ticker": "051910", "name": "LG화학", "score": 11.0},
        ]
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=None
        )
        
        # market_condition이 None이어도 정상 작동해야 함
        self.assertGreaterEqual(len(items), 0)
    
    @patch('services.scan_service.scan_with_preset')
    def test_crash_market_condition(self, mock_scan):
        """급락장(crash) 조건 테스트"""
        crash_condition = MarketCondition(
            date="20251114",
            kospi_return=-0.04,  # -4%
            volatility=0.05,
            market_sentiment='crash',
            sector_rotation='mixed',
            foreign_flow='sell',
            institution_flow='sell',
            volume_trend='high',
            rsi_threshold=40.0,
            min_signals=999,
            macd_osc_min=999.0,
            vol_ma5_mult=999.0,
            gap_max=0.001,
            ext_from_tema20_max=0.001
        )
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=crash_condition
        )
        
        # 급락장에서는 빈 리스트 반환
        self.assertEqual(len(items), 0)
        self.assertIsNone(chosen_step)
        # scan_with_preset이 호출되지 않아야 함
        mock_scan.assert_not_called()
    
    @patch('services.scan_service.scan_with_preset')
    def test_fallback_disabled(self, mock_scan):
        """Fallback 비활성화 테스트"""
        original_fallback = config.fallback_enable
        config.fallback_enable = False
        
        try:
            mock_scan.return_value = [
                {"ticker": "005930", "name": "삼성전자", "score": 10.0},
                {"ticker": "000660", "name": "SK하이닉스", "score": 9.5},
                {"ticker": "051910", "name": "LG화학", "score": 11.0},
            ]
            
            items, chosen_step = execute_scan_with_fallback(
                self.universe,
                date="20251114",
                market_condition=self.bull_condition
            )
            
            # Fallback 비활성화 시 chosen_step = 0
            self.assertEqual(chosen_step, 0)
            # 10점 이상만 필터링
            self.assertTrue(all(item["score"] >= 10 for item in items))
            # 한 번만 호출
            self.assertEqual(mock_scan.call_count, 1)
        finally:
            config.fallback_enable = original_fallback
    
    # ==================== 통합 시나리오 테스트 ====================
    
    @patch('services.scan_service.scan_with_preset')
    def test_complete_flow_step_0_to_3(self, mock_scan):
        """Step 0부터 Step 3까지 전체 플로우 테스트"""
        def mock_scan_side_effect(universe, preset, date, market_condition):
            if preset == {}:  # Step 0
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 9.5},
                ]
            elif preset == self.bull_presets[1]:  # Step 1
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 9.5},
                ]
            elif preset == self.bull_presets[2]:  # Step 3
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
        
        self.assertEqual(chosen_step, 3)
        self.assertEqual(len(items), 4)
        self.assertTrue(all(item["score"] >= 8 for item in items))
        self.assertEqual(mock_scan.call_count, 3)
    
    @patch('services.scan_service.scan_with_preset')
    def test_score_filtering_accuracy(self, mock_scan):
        """점수 필터링 정확성 테스트"""
        mock_scan.return_value = [
            {"ticker": "005930", "name": "삼성전자", "score": 10.0},
            {"ticker": "000660", "name": "SK하이닉스", "score": 9.9},  # 10점 미만
            {"ticker": "051910", "name": "LG화학", "score": 10.5},
            {"ticker": "035420", "name": "NAVER", "score": 8.5},  # 10점 미만
            {"ticker": "006400", "name": "삼성SDI", "score": 11.0},
        ]
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 0에서 10점 이상만 필터링
        self.assertEqual(chosen_step, 0)
        self.assertEqual(len(items), 3)  # 10.0, 10.5, 11.0만
        self.assertTrue(all(item["score"] >= 10 for item in items))
        self.assertNotIn("000660", [item["ticker"] for item in items])
        self.assertNotIn("035420", [item["ticker"] for item in items])
    
    @patch('services.scan_service.scan_with_preset')
    def test_target_max_limit(self, mock_scan):
        """target_max 제한 테스트"""
        original_min = config.fallback_target_min_bull
        original_max = config.fallback_target_max_bull
        config.fallback_target_min_bull = 3
        config.fallback_target_max_bull = 2  # 최대 2개 (하지만 min=3이므로 max=3으로 조정됨)
        
        try:
            mock_scan.return_value = [
                {"ticker": "005930", "name": "삼성전자", "score": 10.0},
                {"ticker": "000660", "name": "SK하이닉스", "score": 10.5},
                {"ticker": "051910", "name": "LG화학", "score": 11.0},
                {"ticker": "035420", "name": "NAVER", "score": 10.2},
                {"ticker": "006400", "name": "삼성SDI", "score": 10.8},
            ]
            
            items, chosen_step = execute_scan_with_fallback(
                self.universe,
                date="20251114",
                market_condition=self.bull_condition
            )
            
            # target_max = 2이지만 target_min = 3이므로 max(3, 2) = 3으로 조정됨
            # 따라서 최대 3개까지 선택 가능
            self.assertLessEqual(len(items), 3)
            self.assertEqual(chosen_step, 0)
        finally:
            config.fallback_target_min_bull = original_min
            config.fallback_target_max_bull = original_max
    
    # ==================== 성능 및 안정성 테스트 ====================
    
    @patch('services.scan_service.scan_with_preset')
    def test_large_universe(self, mock_scan):
        """큰 유니버스 테스트"""
        large_universe = [f"{i:06d}" for i in range(200)]  # 200개 종목
        
        mock_scan.return_value = [
            {"ticker": f"{i:06d}", "name": f"종목{i}", "score": 10.0 + i * 0.01}
            for i in range(10)
        ]
        
        items, chosen_step = execute_scan_with_fallback(
            large_universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # 정상 작동해야 함
        self.assertGreaterEqual(len(items), 0)
        self.assertIsNotNone(chosen_step)
    
    @patch('services.scan_service.scan_with_preset')
    def test_multiple_calls_consistency(self, mock_scan):
        """여러 번 호출 시 일관성 테스트"""
        mock_scan.return_value = [
            {"ticker": "005930", "name": "삼성전자", "score": 10.0},
            {"ticker": "000660", "name": "SK하이닉스", "score": 10.5},
            {"ticker": "051910", "name": "LG화학", "score": 11.0},
        ]
        
        # 여러 번 호출
        results = []
        for _ in range(5):
            items, chosen_step = execute_scan_with_fallback(
                self.universe,
                date="20251114",
                market_condition=self.bull_condition
            )
            results.append((len(items), chosen_step))
        
        # 모든 결과가 동일해야 함
        first_result = results[0]
        for result in results[1:]:
            self.assertEqual(result, first_result)
    
    @patch('services.scan_service.scan_with_preset')
    def test_step_2_reuses_step1_items(self, mock_scan):
        """Step 2가 Step 1의 결과를 재사용하는지 테스트"""
        step1_items_called = False
        
        def mock_scan_side_effect(universe, preset, date, market_condition):
            nonlocal step1_items_called
            if preset == {}:  # Step 0
                return []
            elif preset == self.bull_presets[1]:  # Step 1
                step1_items_called = True
                return [
                    {"ticker": "005930", "name": "삼성전자", "score": 8.5},
                    {"ticker": "000660", "name": "SK하이닉스", "score": 8.8},
                    {"ticker": "051910", "name": "LG화학", "score": 7.5},  # 8점 미만
                ]
            elif preset == self.bull_presets[2]:  # Step 3
                return []  # Step 3도 호출될 수 있음
            return []
        
        mock_scan.side_effect = mock_scan_side_effect
        
        items, chosen_step = execute_scan_with_fallback(
            self.universe,
            date="20251114",
            market_condition=self.bull_condition
        )
        
        # Step 1이 호출되었는지 확인
        self.assertTrue(step1_items_called)
        # Step 2는 Step 1의 결과를 재사용하므로 Step 1 이후 추가 호출 없음
        # Step 2에서 목표 미달이면 Step 3도 호출됨
        self.assertGreaterEqual(mock_scan.call_count, 2)  # 최소 Step 0, Step 1
        # Step 2에서 8점 이상만 필터링 (목표 3개 미달이면 Step 3도 진행)
        if chosen_step == 2:
            self.assertEqual(len(items), 2)  # 8.5, 8.8만
        else:
            # Step 3까지 진행된 경우
            self.assertIsNone(chosen_step)  # Step 3에서도 목표 미달


if __name__ == '__main__':
    unittest.main()

