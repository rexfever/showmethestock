#!/usr/bin/env python3
"""
v3 추천 상태 전이 서비스 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import json
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.state_transition_service import (
    transition_recommendation_status,
    _is_valid_transition,
    evaluate_active_recommendations
)


class TestStateTransitionValidation(unittest.TestCase):
    """상태 전이 유효성 검증 테스트"""
    
    def test_valid_transition_active_to_broken(self):
        """ACTIVE → BROKEN 허용"""
        self.assertTrue(_is_valid_transition("ACTIVE", "BROKEN"))
    
    def test_valid_transition_active_to_weak_warning(self):
        """ACTIVE → WEAK_WARNING 허용"""
        self.assertTrue(_is_valid_transition("ACTIVE", "WEAK_WARNING"))
    
    def test_valid_transition_broken_to_archived(self):
        """BROKEN → ARCHIVED 허용"""
        self.assertTrue(_is_valid_transition("BROKEN", "ARCHIVED"))
    
    def test_invalid_transition_broken_to_active(self):
        """BROKEN → ACTIVE 금지"""
        self.assertFalse(_is_valid_transition("BROKEN", "ACTIVE"))
    
    def test_invalid_transition_archived_to_active(self):
        """ARCHIVED → ACTIVE 금지"""
        self.assertFalse(_is_valid_transition("ARCHIVED", "ACTIVE"))
    
    def test_same_status_allowed(self):
        """동일 상태는 허용 (idempotent)"""
        self.assertTrue(_is_valid_transition("ACTIVE", "ACTIVE"))


class TestTransitionRecommendationStatus(unittest.TestCase):
    """추천 상태 전이 테스트"""
    
    @patch('services.state_transition_service.db_manager')
    def test_transition_success(self, mock_db_manager):
        """상태 전이 성공"""
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [
            ("ACTIVE", "047810"),  # 현재 상태
            None  # 이벤트 기록 후
        ]
        mock_cur.execute.return_value = None
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        result = transition_recommendation_status(
            recommendation_id=1,
            to_status="BROKEN",
            reason="HARD_STOP",
            metadata={"current_return": -5.0}
        )
        
        self.assertTrue(result)
    
    @patch('services.state_transition_service.db_manager')
    def test_transition_not_found(self, mock_db_manager):
        """추천을 찾을 수 없음"""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        result = transition_recommendation_status(
            recommendation_id=999,
            to_status="BROKEN",
            reason="HARD_STOP"
        )
        
        self.assertFalse(result)
    
    @patch('services.state_transition_service.db_manager')
    def test_transition_invalid(self, mock_db_manager):
        """잘못된 상태 전이"""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = ("BROKEN", "047810")  # 현재 상태: BROKEN
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cur
        mock_db_manager.get_cursor.return_value.__exit__.return_value = None
        
        # BROKEN → ACTIVE는 금지
        result = transition_recommendation_status(
            recommendation_id=1,
            to_status="ACTIVE",
            reason="회복"
        )
        
        self.assertFalse(result)


class TestEvaluateActiveRecommendations(unittest.TestCase):
    """ACTIVE 추천 평가 테스트"""
    
    @patch('services.state_transition_service.api')
    @patch('services.state_transition_service.db_manager')
    @patch('services.state_transition_service.get_kst_now')
    def test_evaluate_broken_condition(self, mock_get_kst_now, mock_db_manager, mock_api):
        """BROKEN 조건 달성 시 전이"""
        from datetime import datetime
        import pandas as pd
        
        mock_get_kst_now.return_value.strftime.return_value = "20251215"
        
        # ACTIVE 추천 조회
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            (
                1,  # id
                "047810",  # ticker
                "한국항공우주",  # name
                "ACTIVE",  # status
                date(2025, 12, 10),  # anchor_date
                50000.0,  # anchor_close
                "midterm",  # strategy
                json.dumps({}),  # flags
                json.dumps({})  # indicators
            )
        ]
        
        # 종가 조회 (손절가 이하)
        mock_df = pd.DataFrame({
            'close': [46000.0]  # -8% (손절가 -7% 이하)
        })
        mock_api.get_ohlcv.return_value = mock_df
        
        # flags 업데이트용 커서
        mock_update_cur = MagicMock()
        mock_update_cur.execute.return_value = None
        
        # 상태 전이용 커서
        mock_transition_cur = MagicMock()
        mock_transition_cur.fetchone.side_effect = [
            ("ACTIVE", "047810"),  # 현재 상태
            None  # 이벤트 기록 후
        ]
        mock_transition_cur.execute.return_value = None
        
        # 커서 모킹 (조회용, 업데이트용, 전이용)
        def cursor_side_effect(*args, **kwargs):
            if kwargs.get('commit', False):
                # 업데이트/전이용 커서
                if 'UPDATE recommendations' in str(mock_update_cur.execute.call_args):
                    return mock_update_cur
                return mock_transition_cur
            else:
                # 조회용 커서
                return mock_cur
        
        mock_db_manager.get_cursor.side_effect = cursor_side_effect
        
        with patch('services.state_transition_service.transition_recommendation_status') as mock_transition:
            mock_transition.return_value = True
            
            result = evaluate_active_recommendations("20251215")
            
            self.assertEqual(result['evaluated'], 1)
            # transition_recommendation_status가 호출되었는지 확인
            mock_transition.assert_called()


if __name__ == '__main__':
    unittest.main()


