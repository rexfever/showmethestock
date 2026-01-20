#!/usr/bin/env python3
"""
v3 추천 시스템 서비스 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import json
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.recommendation_service import (
    get_trading_days_between,
    get_nth_trading_day_after,
    can_create_recommendation,
    create_recommendation,
    save_scan_results,
    process_scan_results_to_recommendations
)


class TestTradingDaysCalculation(unittest.TestCase):
    """거래일 계산 테스트"""
    
    def test_get_trading_days_between_same_date(self):
        """같은 날짜는 1일 반환"""
        result = get_trading_days_between("20251215", "20251215")
        self.assertEqual(result, 1)
    
    def test_get_trading_days_between_weekend(self):
        """주말 제외 테스트"""
        # 2025-12-15는 월요일, 2025-12-19는 금요일 (5일)
        result = get_trading_days_between("20251215", "20251219")
        self.assertEqual(result, 5)
    
    def test_get_trading_days_between_invalid_date(self):
        """잘못된 날짜 형식 테스트"""
        result = get_trading_days_between("invalid", "20251215")
        self.assertEqual(result, 0)


class TestCanCreateRecommendation(unittest.TestCase):
    """추천 생성 가능 여부 테스트"""
    
    @patch('services.recommendation_service.db_manager')
    def test_can_create_when_no_active(self, mock_db_manager):
        """ACTIVE 추천이 없으면 생성 가능"""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        can_create, reason = can_create_recommendation("047810", "20251215")
        self.assertTrue(can_create)
        self.assertIsNone(reason)
    
    @patch('services.recommendation_service.db_manager')
    def test_cannot_create_when_active_exists(self, mock_db_manager):
        """ACTIVE 추천이 있으면 생성 불가"""
        mock_cur = MagicMock()
        # 첫 번째 호출: ACTIVE 추천 존재
        mock_cur.fetchone.side_effect = [
            (1, date(2025, 12, 10), "ACTIVE"),  # ACTIVE 추천 존재
            None  # BROKEN 추천 없음
        ]
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        can_create, reason = can_create_recommendation("047810", "20251215")
        self.assertFalse(can_create)
        self.assertIn("ACTIVE", reason)
    
    @patch('services.recommendation_service.db_manager')
    @patch('services.recommendation_service.get_trading_days_between')
    def test_cannot_create_during_cooldown(self, mock_trading_days, mock_db_manager):
        """쿨다운 기간 중에는 생성 불가"""
        mock_cur = MagicMock()
        # ACTIVE 없음, BROKEN 있음
        mock_cur.fetchone.side_effect = [
            None,  # ACTIVE 없음
            (1, datetime(2025, 12, 13, 10, 0, 0), date(2025, 12, 10))  # BROKEN 있음
        ]
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        # 쿨다운 기간 중 (2일 경과, 3일 필요)
        mock_trading_days.return_value = 2
        
        can_create, reason = can_create_recommendation("047810", "20251215", cooldown_days=3)
        self.assertFalse(can_create)
        self.assertIn("쿨다운", reason)
    
    @patch('services.recommendation_service.db_manager')
    @patch('services.recommendation_service.get_trading_days_between')
    def test_can_create_after_cooldown(self, mock_trading_days, mock_db_manager):
        """쿨다운 기간 이후에는 생성 가능"""
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [
            None,  # ACTIVE 없음
            (1, datetime(2025, 12, 10, 10, 0, 0), date(2025, 12, 10))  # BROKEN 있음
        ]
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        # 쿨다운 기간 경과 (5일 경과, 3일 필요)
        mock_trading_days.return_value = 5
        
        can_create, reason = can_create_recommendation("047810", "20251215", cooldown_days=3)
        self.assertTrue(can_create)
        self.assertIsNone(reason)


class TestCreateRecommendation(unittest.TestCase):
    """추천 생성 테스트"""
    
    @patch('services.recommendation_service.can_create_recommendation')
    @patch('services.recommendation_service.get_trading_date')
    @patch('services.recommendation_service.yyyymmdd_to_date')
    @patch('services.recommendation_service.get_anchor_close')
    @patch('services.recommendation_service.db_manager')
    def test_create_recommendation_success(self, mock_db_manager, mock_get_anchor_close,
                                           mock_yyyymmdd_to_date, mock_get_trading_date,
                                           mock_can_create):
        """추천 생성 성공 테스트"""
        # Mock 설정
        mock_can_create.return_value = (True, None)
        mock_get_trading_date.return_value = "20251215"
        mock_yyyymmdd_to_date.return_value = date(2025, 12, 15)
        mock_get_anchor_close.return_value = 50000.0
        
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [
            None,  # 기존 ACTIVE 없음
            (1,)  # 새 추천 ID
        ]
        mock_cur.execute.return_value = None
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        result = create_recommendation(
            ticker="047810",
            name="한국항공우주",
            scan_date="20251215",
            strategy="midterm",
            score=8.5,
            score_label="Strong",
            indicators={"close": 50000},
            flags={},
            details={}
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result, 1)
    
    @patch('services.recommendation_service.can_create_recommendation')
    def test_create_recommendation_when_cannot_create(self, mock_can_create):
        """생성 불가 시 None 반환"""
        mock_can_create.return_value = (False, "이미 ACTIVE 상태")
        
        result = create_recommendation(
            ticker="047810",
            name="한국항공우주",
            scan_date="20251215",
            strategy="midterm",
            score=8.5,
            score_label="Strong",
            indicators={},
            flags={},
            details={}
        )
        
        self.assertIsNone(result)


class TestSaveScanResults(unittest.TestCase):
    """스캔 결과 저장 테스트"""
    
    @patch('services.recommendation_service.db_manager')
    @patch('services.recommendation_service.yyyymmdd_to_date')
    def test_save_scan_results_success(self, mock_yyyymmdd_to_date, mock_db_manager):
        """스캔 결과 저장 성공"""
        mock_yyyymmdd_to_date.return_value = date(2025, 12, 15)
        
        mock_cur = MagicMock()
        mock_cur.execute.return_value = None
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        scan_items = [
            {
                "ticker": "047810",
                "name": "한국항공우주",
                "score": 8.5,
                "score_label": "Strong",
                "strategy": "midterm",
                "indicators": {"close": 50000},
                "flags": {},
                "details": {}
            }
        ]
        
        result = save_scan_results(scan_items, "20251215")
        self.assertEqual(result, 1)
    
    def test_save_scan_results_empty(self):
        """빈 스캔 결과는 0 반환"""
        result = save_scan_results([], "20251215")
        self.assertEqual(result, 0)
    
    def test_save_scan_results_skip_noresult(self):
        """NORESULT는 건너뜀"""
        scan_items = [
            {"ticker": "NORESULT", "name": "추천종목 없음"}
        ]
        
        with patch('services.recommendation_service.db_manager') as mock_db_manager:
            mock_cur = MagicMock()
            mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
            mock_db_manager.get_cursor.return_value.__exit__.return_value = None
            
            result = save_scan_results(scan_items, "20251215")
            # execute가 호출되지 않아야 함
            mock_cur.execute.assert_not_called()
            self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()



