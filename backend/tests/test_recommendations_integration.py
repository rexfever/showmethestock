#!/usr/bin/env python3
"""
v3 추천 시스템 통합 테스트
실제 DB 연결 없이 주요 로직 검증
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import json
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRecommendationFlow(unittest.TestCase):
    """추천 생성 플로우 통합 테스트"""
    
    @patch('services.recommendation_service.db_manager')
    @patch('services.recommendation_service.get_trading_date')
    @patch('services.recommendation_service.yyyymmdd_to_date')
    @patch('services.recommendation_service.get_anchor_close')
    def test_create_recommendation_archives_existing_active(self, mock_get_anchor_close,
                                                           mock_yyyymmdd_to_date,
                                                           mock_get_trading_date,
                                                           mock_db_manager):
        """새 추천 생성 시 기존 ACTIVE 추천을 ARCHIVED로 전이"""
        from services.recommendation_service import create_recommendation
        
        # Mock 설정
        mock_get_trading_date.return_value = "20251215"
        mock_yyyymmdd_to_date.return_value = date(2025, 12, 15)
        mock_get_anchor_close.return_value = 50000.0
        
        mock_cur = MagicMock()
        # 첫 번째 호출: 기존 ACTIVE 추천 존재
        # 두 번째 호출: 새 추천 ID
        mock_cur.fetchone.side_effect = [
            (1,),  # 기존 ACTIVE 추천 ID
            (2,)   # 새 추천 ID
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
        
        # 기존 ACTIVE를 ARCHIVED로 업데이트하는 쿼리가 호출되었는지 확인
        update_calls = [call for call in mock_cur.execute.call_args_list 
                       if 'UPDATE recommendations' in str(call)]
        self.assertGreater(len(update_calls), 0, "기존 ACTIVE를 ARCHIVED로 업데이트해야 함")
        
        # 상태 변경 이벤트가 기록되었는지 확인
        event_calls = [call for call in mock_cur.execute.call_args_list 
                      if 'recommendation_state_events' in str(call)]
        self.assertGreater(len(event_calls), 0, "상태 변경 이벤트가 기록되어야 함")
        
        self.assertIsNotNone(result)
        self.assertEqual(result, 2)


class TestStateTransitionFlow(unittest.TestCase):
    """상태 전이 플로우 통합 테스트"""
    
    @patch('services.state_transition_service.db_manager')
    def test_broken_to_active_forbidden(self, mock_db_manager):
        """BROKEN → ACTIVE 전이 금지"""
        from services.state_transition_service import transition_recommendation_status
        
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = ("BROKEN", "047810")
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        result = transition_recommendation_status(
            recommendation_id=1,
            to_status="ACTIVE",
            reason="회복"
        )
        
        self.assertFalse(result, "BROKEN → ACTIVE 전이는 금지되어야 함")
        
        # UPDATE 쿼리가 호출되지 않았는지 확인
        update_calls = [call for call in mock_cur.execute.call_args_list 
                       if 'UPDATE recommendations' in str(call)]
        self.assertEqual(len(update_calls), 0, "잘못된 전이는 실행되지 않아야 함")


class TestCooldownLogic(unittest.TestCase):
    """쿨다운 로직 테스트"""
    
    @patch('services.recommendation_service.db_manager')
    @patch('services.recommendation_service.get_trading_days_between')
    def test_cooldown_same_day(self, mock_trading_days, mock_db_manager):
        """BROKEN 당일에는 추천 생성 불가"""
        from services.recommendation_service import can_create_recommendation
        
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [
            None,  # ACTIVE 없음
            (1, datetime(2025, 12, 15, 10, 0, 0), date(2025, 12, 10))  # BROKEN 있음 (오늘)
        ]
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        can_create, reason = can_create_recommendation("047810", "20251215", cooldown_days=3)
        
        self.assertFalse(can_create, "BROKEN 당일에는 추천 생성 불가")
        self.assertIn("쿨다운", reason)
    
    @patch('services.recommendation_service.db_manager')
    @patch('services.recommendation_service.get_trading_days_between')
    def test_cooldown_after_period(self, mock_trading_days, mock_db_manager):
        """쿨다운 기간 경과 후에는 추천 생성 가능"""
        from services.recommendation_service import can_create_recommendation
        
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [
            None,  # ACTIVE 없음
            (1, datetime(2025, 12, 10, 10, 0, 0), date(2025, 12, 10))  # BROKEN 있음 (5일 전)
        ]
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        # 5 거래일 경과 (쿨다운 3일 초과)
        mock_trading_days.return_value = 5
        
        can_create, reason = can_create_recommendation("047810", "20251215", cooldown_days=3)
        
        self.assertTrue(can_create, "쿨다운 기간 경과 후에는 추천 생성 가능")
        self.assertIsNone(reason)


class TestActiveUniqueness(unittest.TestCase):
    """ACTIVE 유일성 테스트"""
    
    @patch('services.recommendation_service.db_manager')
    @patch('services.recommendation_service.get_trading_date')
    @patch('services.recommendation_service.yyyymmdd_to_date')
    @patch('services.recommendation_service.get_anchor_close')
    def test_only_one_active_per_ticker(self, mock_get_anchor_close,
                                        mock_yyyymmdd_to_date,
                                        mock_get_trading_date,
                                        mock_db_manager):
        """동일 ticker는 ACTIVE 1개만"""
        from services.recommendation_service import create_recommendation
        
        mock_get_trading_date.return_value = "20251215"
        mock_yyyymmdd_to_date.return_value = date(2025, 12, 15)
        mock_get_anchor_close.return_value = 50000.0
        
        mock_cur = MagicMock()
        # 기존 ACTIVE가 있으면 ARCHIVED로 전이
        mock_cur.fetchone.side_effect = [
            (1,),  # 기존 ACTIVE ID
            (2,)   # 새 추천 ID
        ]
        mock_cur.execute.return_value = None
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        # 첫 번째 추천 생성
        result1 = create_recommendation(
            ticker="047810",
            name="한국항공우주",
            scan_date="20251210",
            strategy="midterm",
            score=8.0,
            score_label="Strong",
            indicators={},
            flags={},
            details={}
        )
        
        # 두 번째 추천 생성 (기존 ACTIVE가 ARCHIVED되어야 함)
        result2 = create_recommendation(
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
        
        # 기존 ACTIVE를 ARCHIVED로 업데이트하는 쿼리가 호출되었는지 확인
        archive_calls = [call for call in mock_cur.execute.call_args_list 
                        if 'ARCHIVED' in str(call) and 'UPDATE' in str(call)]
        self.assertGreater(len(archive_calls), 0, "기존 ACTIVE가 ARCHIVED되어야 함")


if __name__ == '__main__':
    unittest.main()


