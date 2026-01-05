#!/usr/bin/env python3
"""
v3 추천 시스템 제약 조건 강제 테스트
DB 제약과 코드 로직이 실제로 작동하는지 증명
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import date
import uuid
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.recommendation_service_v2 import (
    create_recommendation_transaction,
    transition_recommendation_status_transaction
)
from db_manager import db_manager


class TestDuplicateActiveConstraint(unittest.TestCase):
    """동일 ticker ACTIVE 중복 방지 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.test_ticker = f"TEST{uuid.uuid4().hex[:6].upper()}"
        self.test_date = date(2025, 12, 15)
    
    def tearDown(self):
        """테스트 후 정리"""
        try:
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("""
                    DELETE FROM recommendations
                    WHERE ticker = %s
                """, (self.test_ticker,))
        except:
            pass
    
    def test_duplicate_active_should_replace(self):
        """동일 ticker로 ACTIVE 2개 생성 시 첫 번째가 REPLACED로 전환되어야 함"""
        # 첫 번째 ACTIVE 생성
        rec_id_1 = create_recommendation_transaction(
            ticker=self.test_ticker,
            anchor_date=self.test_date,
            anchor_close=50000,
            anchor_source="TEST",
            reason_code="TEST_1"
        )
        
        self.assertIsNotNone(rec_id_1, "첫 번째 추천 생성 실패")
        
        # 두 번째 ACTIVE 생성 (첫 번째가 REPLACED되어야 함)
        rec_id_2 = create_recommendation_transaction(
            ticker=self.test_ticker,
            anchor_date=self.test_date,
            anchor_close=51000,
            anchor_source="TEST",
            reason_code="TEST_2"
        )
        
        self.assertIsNotNone(rec_id_2, "두 번째 추천 생성 실패")
        
        # 첫 번째 상태 확인
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT status, replaced_by_recommendation_id
                FROM recommendations
                WHERE recommendation_id = %s
            """, (rec_id_1,))
            first_rec = cur.fetchone()
            
            self.assertIsNotNone(first_rec, "첫 번째 추천을 찾을 수 없음")
            
            if isinstance(first_rec, dict):
                status = first_rec.get('status')
                replaced_by = first_rec.get('replaced_by_recommendation_id')
            else:
                status = first_rec[0]
                replaced_by = first_rec[1] if len(first_rec) > 1 else None
            
            self.assertEqual(status, 'REPLACED', "첫 번째 추천이 REPLACED로 전환되어야 함")
            self.assertEqual(str(replaced_by), str(rec_id_2), "replaced_by_recommendation_id가 두 번째 추천 ID와 일치해야 함")
        
        # ACTIVE는 1개만 존재해야 함
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM recommendations
                WHERE ticker = %s AND status = 'ACTIVE'
            """, (self.test_ticker,))
            count = cur.fetchone()[0] if isinstance(cur.fetchone(), tuple) else cur.fetchone().get('count')
            
            self.assertEqual(count, 1, f"ACTIVE는 1개만 존재해야 함 (현재: {count}개)")


class TestBrokenToActiveForbidden(unittest.TestCase):
    """BROKEN → ACTIVE 전이 금지 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.test_ticker = f"TEST{uuid.uuid4().hex[:6].upper()}"
        self.test_date = date(2025, 12, 15)
        self.rec_id = None
    
    def tearDown(self):
        """테스트 후 정리"""
        if self.rec_id:
            try:
                with db_manager.get_cursor(commit=True) as cur:
                    cur.execute("""
                        DELETE FROM recommendations
                        WHERE recommendation_id = %s
                    """, (self.rec_id,))
            except:
                pass
    
    def test_broken_to_active_forbidden(self):
        """BROKEN 상태에서 ACTIVE로 전이 시도 시 실패해야 함"""
        # ACTIVE 추천 생성
        self.rec_id = create_recommendation_transaction(
            ticker=self.test_ticker,
            anchor_date=self.test_date,
            anchor_close=50000,
            anchor_source="TEST",
            reason_code="TEST_BROKEN"
        )
        
        self.assertIsNotNone(self.rec_id, "추천 생성 실패")
        
        # ACTIVE → BROKEN 전이
        success = transition_recommendation_status_transaction(
            recommendation_id=self.rec_id,
            to_status="BROKEN",
            reason_code="HARD_STOP",
            reason_text="손절가 도달"
        )
        
        self.assertTrue(success, "ACTIVE → BROKEN 전이 실패")
        
        # BROKEN → ACTIVE 전이 시도 (금지)
        success = transition_recommendation_status_transaction(
            recommendation_id=self.rec_id,
            to_status="ACTIVE",
            reason_code="RECOVERY",
            reason_text="회복"
        )
        
        self.assertFalse(success, "BROKEN → ACTIVE 전이는 금지되어야 함")
        
        # 상태 확인 (여전히 BROKEN이어야 함)
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT status
                FROM recommendations
                WHERE recommendation_id = %s
            """, (self.rec_id,))
            status = cur.fetchone()[0] if isinstance(cur.fetchone(), tuple) else cur.fetchone().get('status')
            
            self.assertEqual(status, 'BROKEN', "상태가 여전히 BROKEN이어야 함")


class TestAnchorCloseImmutability(unittest.TestCase):
    """anchor_close 불변성 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.test_ticker = f"TEST{uuid.uuid4().hex[:6].upper()}"
        self.test_date = date(2025, 12, 15)
        self.test_anchor_close = 50000
        self.rec_id = None
    
    def tearDown(self):
        """테스트 후 정리"""
        if self.rec_id:
            try:
                with db_manager.get_cursor(commit=True) as cur:
                    cur.execute("""
                        DELETE FROM recommendations
                        WHERE recommendation_id = %s
                    """, (self.rec_id,))
            except:
                pass
    
    def test_anchor_close_does_not_change(self):
        """anchor_close는 생성 후 변경되지 않아야 함"""
        # 추천 생성
        self.rec_id = create_recommendation_transaction(
            ticker=self.test_ticker,
            anchor_date=self.test_date,
            anchor_close=self.test_anchor_close,
            anchor_source="TEST",
            reason_code="TEST_IMMUTABILITY"
        )
        
        self.assertIsNotNone(self.rec_id, "추천 생성 실패")
        
        # 첫 번째 조회
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT anchor_close, anchor_date
                FROM recommendations
                WHERE recommendation_id = %s
            """, (self.rec_id,))
            first = cur.fetchone()
            
            first_close = first[0] if isinstance(first, tuple) else first.get('anchor_close')
            first_date = first[1] if isinstance(first, tuple) else first.get('anchor_date')
        
        # 두 번째 조회 (시간 경과 후)
        import time
        time.sleep(0.5)
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT anchor_close, anchor_date
                FROM recommendations
                WHERE recommendation_id = %s
            """, (self.rec_id,))
            second = cur.fetchone()
            
            second_close = second[0] if isinstance(second, tuple) else second.get('anchor_close')
            second_date = second[1] if isinstance(second, tuple) else second.get('anchor_date')
        
        # 값이 동일해야 함
        self.assertEqual(first_close, second_close, "anchor_close가 변경되면 안 됨")
        self.assertEqual(first_date, second_date, "anchor_date가 변경되면 안 됨")
        self.assertEqual(first_close, self.test_anchor_close, "anchor_close가 생성 시 값과 일치해야 함")


if __name__ == '__main__':
    unittest.main()


