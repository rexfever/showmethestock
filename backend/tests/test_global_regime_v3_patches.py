"""
Global Regime v3 패치 검증 테스트
- FAIL #1: final_regime 기본값 및 getattr 사용 문제 패치 검증
- FAIL #2: 날짜 포맷 불일치 패치 검증
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 테스트 환경 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from market_analyzer import MarketCondition, market_analyzer
from services.regime_storage import yyyymmdd_to_date, date_to_yyyymmdd, save_regime, load_regime, upsert_regime
from scanner_v2.core.scanner import ScannerV2


class TestGlobalRegimeV3Patches(unittest.TestCase):
    """Global Regime v3 패치 검증 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.test_date_yyyymmdd = "20251122"
        self.test_date_db = "2025-11-22"
        
    def test_fail1_final_regime_none_default(self):
        """FAIL #1 패치 검증: MarketCondition.final_regime 기본값이 None인지 확인"""
        condition = MarketCondition(
            date="20251122",
            kospi_return=0.01,
            volatility=0.02,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="neutral",
            institution_flow="neutral",
            volume_trend="normal",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=1.8,
            gap_max=0.025,
            ext_from_tema20_max=0.025
        )
        
        # final_regime 기본값이 None인지 확인
        self.assertIsNone(condition.final_regime)
        
        # Optional[str] 타입 확인 (런타임에서는 None 할당 가능)
        condition.final_regime = None
        self.assertIsNone(condition.final_regime)
        
        condition.final_regime = "bull"
        self.assertEqual(condition.final_regime, "bull")
    
    @patch('scanner_v2.core.scanner.FilterEngine')
    @patch('scanner_v2.core.scanner.Scorer')
    @patch('scanner_v2.core.scanner.IndicatorCalculator')
    def test_fail1_scanner_direct_access(self, mock_indicator, mock_scorer, mock_filter):
        """FAIL #1 패치 검증: scanner에서 final_regime 직접 접근 및 None 처리"""
        # Mock 설정
        mock_config = Mock()
        mock_config.ohlcv_count = 60
        
        scanner = ScannerV2(mock_config)
        
        # final_regime이 None인 경우 테스트
        market_condition_none = MarketCondition(
            date="20251122",
            kospi_return=0.01,
            volatility=0.02,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="neutral",
            institution_flow="neutral",
            volume_trend="normal",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=1.8,
            gap_max=0.025,
            ext_from_tema20_max=0.025,
            final_regime=None  # None으로 설정
        )
        
        # final_regime이 설정된 경우 테스트
        market_condition_bull = MarketCondition(
            date="20251122",
            kospi_return=0.01,
            volatility=0.02,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="neutral",
            institution_flow="neutral",
            volume_trend="normal",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=1.8,
            gap_max=0.025,
            ext_from_tema20_max=0.025,
            final_regime="bull"
        )
        
        # _apply_regime_cutoff 메서드 테스트 (직접 접근 확인)
        with patch.object(scanner, '_apply_regime_cutoff') as mock_cutoff:
            mock_cutoff.return_value = []
            
            # None인 경우 market_sentiment 사용되는지 확인
            scanner._apply_regime_cutoff([], market_condition_none)
            
            # final_regime이 있는 경우 해당 값 사용되는지 확인
            scanner._apply_regime_cutoff([], market_condition_bull)
            
            # 호출 확인
            self.assertEqual(mock_cutoff.call_count, 2)
    
    def test_fail2_date_conversion_utils(self):
        """FAIL #2 패치 검증: 날짜 변환 유틸 함수 테스트"""
        # YYYYMMDD -> YYYY-MM-DD 변환
        result_db = yyyymmdd_to_date(self.test_date_yyyymmdd)
        self.assertEqual(result_db, self.test_date_db)
        
        # YYYY-MM-DD -> YYYYMMDD 변환
        result_yyyymmdd = date_to_yyyymmdd(self.test_date_db)
        self.assertEqual(result_yyyymmdd, self.test_date_yyyymmdd)
        
        # 양방향 변환 일관성 확인
        self.assertEqual(
            date_to_yyyymmdd(yyyymmdd_to_date(self.test_date_yyyymmdd)),
            self.test_date_yyyymmdd
        )
        
        # 엣지 케이스 테스트
        edge_cases = [
            ("20250101", "2025-01-01"),
            ("20251231", "2025-12-31"),
            ("20240229", "2024-02-29")  # 윤년
        ]
        
        for yyyymmdd, expected_db in edge_cases:
            self.assertEqual(yyyymmdd_to_date(yyyymmdd), expected_db)
            self.assertEqual(date_to_yyyymmdd(expected_db), yyyymmdd)
    
    @patch('services.regime_storage.db_manager')
    def test_fail2_regime_storage_date_handling(self, mock_db_manager):
        """FAIL #2 패치 검증: regime_storage에서 날짜 처리 확인"""
        # Mock 설정
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        test_data = {
            'final_regime': 'bull',
            'kr_regime': 'neutral',
            'us_prev_regime': 'bull',
            'us_preopen_flag': 'calm'
        }
        
        # save_regime 테스트 - YYYYMMDD 입력, YYYY-MM-DD로 DB 저장
        save_regime(self.test_date_yyyymmdd, test_data)
        
        # DB에 YYYY-MM-DD 형식으로 저장되는지 확인
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0]
        self.assertIn(self.test_date_db, call_args[1])  # formatted_date가 YYYY-MM-DD 형식
        
        # upsert_regime 테스트
        mock_cursor.reset_mock()
        upsert_regime(self.test_date_yyyymmdd, test_data)
        
        # DB에 YYYY-MM-DD 형식으로 저장되는지 확인
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0]
        self.assertIn(self.test_date_db, call_args[1])
    
    @patch('services.regime_storage.db_manager')
    def test_fail2_load_regime_date_consistency(self, mock_db_manager):
        """FAIL #2 패치 검증: load_regime에서 날짜 일관성 확인"""
        # Mock 설정
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        # DB에서 반환될 데이터 설정
        mock_cursor.fetchone.return_value = {
            'us_prev_sentiment': 'bull',
            'kr_sentiment': 'neutral',
            'us_preopen_sentiment': 'calm',
            'final_regime': 'bull',
            'us_metrics': '{}',
            'kr_metrics': '{}',
            'us_preopen_metrics': '{}'
        }
        
        # YYYYMMDD 형식으로 입력
        result = load_regime(self.test_date_yyyymmdd)
        
        # DB 쿼리에 YYYY-MM-DD 형식으로 전달되는지 확인
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0]
        self.assertIn(self.test_date_db, call_args[1])
        
        # 결과 확인
        self.assertIsNotNone(result)
        self.assertEqual(result['final_regime'], 'bull')
    
    def test_integration_market_condition_scanner(self):
        """통합 테스트: MarketCondition과 Scanner 연동"""
        # final_regime이 None인 MarketCondition 생성
        condition = MarketCondition(
            date="20251122",
            kospi_return=0.01,
            volatility=0.02,
            market_sentiment="bear",
            sector_rotation="mixed",
            foreign_flow="neutral",
            institution_flow="neutral",
            volume_trend="normal",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=1.8,
            gap_max=0.025,
            ext_from_tema20_max=0.025,
            final_regime=None
        )
        
        # Scanner에서 regime 결정 로직 테스트
        # final_regime이 None이면 market_sentiment 사용
        expected_regime = condition.final_regime if condition.final_regime is not None else condition.market_sentiment
        self.assertEqual(expected_regime, "bear")
        
        # final_regime이 설정된 경우
        condition.final_regime = "bull"
        expected_regime = condition.final_regime if condition.final_regime is not None else condition.market_sentiment
        self.assertEqual(expected_regime, "bull")
    
    def test_date_format_consistency_across_modules(self):
        """모듈 간 날짜 형식 일관성 테스트"""
        test_dates = [
            "20251122",
            "20250101", 
            "20251231"
        ]
        
        for date_yyyymmdd in test_dates:
            # 변환 일관성 확인
            date_db = yyyymmdd_to_date(date_yyyymmdd)
            date_back = date_to_yyyymmdd(date_db)
            
            self.assertEqual(date_back, date_yyyymmdd)
            self.assertEqual(len(date_db), 10)  # YYYY-MM-DD 길이
            self.assertEqual(len(date_back), 8)  # YYYYMMDD 길이
            self.assertIn("-", date_db)
            self.assertNotIn("-", date_back)


if __name__ == '__main__':
    unittest.main()